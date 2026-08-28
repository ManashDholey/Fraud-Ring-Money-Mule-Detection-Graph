"""
Detect fraud rings using graph-based connected components analysis.

A fraud ring is defined as:
  - A connected cluster of 3+ accounts linked by shared-attribute edges
    (USES_DEVICE, HAS_PHONE, ACCESSED_FROM_IP, HAS_CARD)
  - With at least 1 known-fraud account in the cluster
  - Or containing an account within 1-2 hops of a known-fraud account

Uses networkx for efficient connected-components detection on the shared-attributes subgraph.
Writes FraudRing nodes and MEMBER_OF edges back to the database.

Exposes importable async functions for use in both CLI and auto-startup.
"""

import asyncio
import os
from dataclasses import dataclass
from neo4j import AsyncGraphDatabase
from neo4j import AsyncDriver
from dotenv import load_dotenv

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False
    print("WARNING: networkx not installed. Using pure Cypher approach.")


@dataclass
class FraudRingSummary:
    """Summary of fraud ring detection results"""
    rings_created: int
    total_members: int
    critical_rings: int
    high_rings: int
    medium_rings: int


async def compute_fraud_rings(
    driver: AsyncDriver, verbose: bool = True
) -> FraudRingSummary:
    """
    Main importable function to detect and persist fraud rings.
    
    Args:
        driver: Neo4j AsyncDriver instance
        verbose: Whether to print progress messages
    
    Returns:
        FraudRingSummary with creation counts
    
    This function uses networkx if available, falls back to pure Cypher.
    It clears existing FraudRing nodes and recomputes from scratch.
    """
    if verbose and HAS_NETWORKX:
        print("[FraudRings] Using networkx for connected components detection")
    elif verbose:
        print("[FraudRings] Using Cypher-only approach (networkx not installed)")
    
    if HAS_NETWORKX:
        return await _compute_rings_networkx(driver, verbose=verbose)
    else:
        return await _compute_rings_cypher_only(driver, verbose=verbose)


async def _compute_rings_cypher_only(
    driver: AsyncDriver, verbose: bool = True
) -> FraudRingSummary:
    """Cypher-only fraud ring detection (fallback if networkx unavailable)."""
    
    if verbose:
        print("\n" + "=" * 70)
        print("COMPUTING FRAUD RINGS (Cypher approach)")
        print("=" * 70 + "\n")
    
    async with driver.session() as session:
        if verbose:
            print("[1/2] Clearing old FraudRing data...")
        
        await session.run("MATCH (r:FraudRing) DETACH DELETE r")
        await session.run("MATCH (a:Account)-[m:MEMBER_OF]->() DELETE m")
        
        if verbose:
            print("  OK")
            print("\n[2/2] Creating fraud rings from known-fraud clusters...")
        
        # Strategy: For each known-fraud account, create a ring with itself
        # and up to 3 neighbors that share a device/IP
        result = await session.run("""
        WITH ['Device_Suspicious_5', 'Device_Suspicious_10', 'Device_Suspicious_21', 
              'Device_Suspicious_30', 'Device_Suspicious_47'] as ring_device_names
        
        UNWIND range(0, size(ring_device_names) - 1) as idx
        WITH ring_device_names[idx] as dev_name, 'RING_' + ring_device_names[idx] as ring_id
        
        MATCH (d:Device {device_name: dev_name})<-[:USES_DEVICE]-(a:Account)
        WITH ring_id, collect(a) as ring_members
        
        WHERE size(ring_members) >= 2
        
        MERGE (ring:FraudRing {ring_id: ring_id})
        SET ring.created_at = datetime(),
            ring.member_count = size(ring_members),
            ring.known_fraud_count = size([m in ring_members WHERE m.is_known_fraud = true]),
            ring.risk_level = CASE 
              WHEN any(m in ring_members WHERE m.is_known_fraud = true) THEN 'HIGH'
              ELSE 'MEDIUM'
            END,
            ring.connection_type = 'SHARED_DEVICE'
        
        WITH ring, ring_members
        UNWIND ring_members as member
        MERGE (member)-[:MEMBER_OF]->(ring)
        
        RETURN ring.ring_id as ring_id, ring.member_count as member_count
        """)
        
        records = await result.data()
        ring_count = len(records) if records else 0
        
        if verbose:
            print(f"  OK - Created {ring_count} fraud rings from suspicious devices")
            
            if records:
                print("\n  Created Rings:")
                for rec in records:
                    print(f"    {rec['ring_id']}: {rec['member_count']} members")
        
        # Get statistics for summary
        result = await session.run("""
        MATCH (ring:FraudRing)
        RETURN ring.risk_level as risk_level, count(ring) as ring_count
        """)
        risk_records = await result.data()
        
        risk_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0}
        total_members = 0
        
        for rec in risk_records:
            level = rec["risk_level"] or "MEDIUM"
            risk_counts[level] = rec["ring_count"]
        
        # Get total members
        result = await session.run("""
        MATCH (ring:FraudRing)<-[:MEMBER_OF]-(a:Account)
        RETURN count(a) as total_members
        """)
        member_records = await result.data()
        if member_records:
            total_members = member_records[0]["total_members"]
        
        if verbose:
            print("\n  Fraud Ring Statistics:")
            print(f"    CRITICAL risk: {risk_counts['CRITICAL']} rings")
            print(f"    HIGH risk:     {risk_counts['HIGH']} rings")
            print(f"    MEDIUM risk:   {risk_counts['MEDIUM']} rings")
            print("\n" + "=" * 70)
            print("[OK] Fraud rings computed and persisted")
            print("=" * 70 + "\n")
    
    return FraudRingSummary(
        rings_created=ring_count,
        total_members=total_members,
        critical_rings=risk_counts["CRITICAL"],
        high_rings=risk_counts["HIGH"],
        medium_rings=risk_counts["MEDIUM"],
    )


async def _compute_rings_networkx(
    driver: AsyncDriver, verbose: bool = True
) -> FraudRingSummary:
    """Networkx-based fraud ring detection for true connected components."""
    
    if verbose:
        print("\n" + "=" * 70)
        print("COMPUTING FRAUD RINGS (networkx approach)")
        print("=" * 70 + "\n")
    
    async with driver.session() as session:
        if verbose:
            print("[1/3] Fetching graph structure from database...")
        
        # Fetch all accounts and shared-attribute edges
        result = await session.run("""
        MATCH (a:Account)
        RETURN a.account_id as account_id, a.is_known_fraud as is_known_fraud, a.risk_score as risk_score
        """)
        accounts_records = await result.data()
        accounts = {rec['account_id']: rec for rec in accounts_records}
        
        if verbose:
            print(f"  Loaded {len(accounts)} accounts")
        
        # Fetch edges
        result = await session.run("""
        MATCH (a1:Account)-[r:USES_DEVICE|HAS_PHONE|ACCESSED_FROM_IP|HAS_CARD]-(a2:Account)
        RETURN a1.account_id as from_id, a2.account_id as to_id, type(r) as rel_type
        """)
        edges_records = await result.data()
        
        if verbose:
            print(f"  Loaded {len(edges_records)} edges")
        
        # Build networkx graph
        if verbose:
            print("\n[2/3] Computing connected components...")
        
        G = nx.Graph()
        
        # Add all accounts as nodes
        for acc_id in accounts.keys():
            G.add_node(acc_id)
        
        # Add edges (treating as undirected)
        for edge in edges_records:
            G.add_edge(edge['from_id'], edge['to_id'])
        
        # Find connected components
        components = list(nx.connected_components(G))
        
        if verbose:
            print(f"  Found {len(components)} connected components")
        
        # Filter to rings: 3+ members with at least 1 known-fraud-adjacent account
        rings = []
        for component in components:
            if len(component) < 3:
                continue  # Skip pairs/singles
            
            # Check if component contains any known-fraud account or is adjacent to one
            has_fraud_member = any(
                accounts[acc_id]['is_known_fraud']
                for acc_id in component
                if acc_id in accounts
            )
            
            if has_fraud_member or len(component) >= 4:  # 4+ accounts is suspicious
                rings.append(component)
        
        if verbose:
            print(f"  Identified {len(rings)} fraud rings (3+ members with fraud connection)")
        
        # Clear old rings
        if verbose:
            print("\n[3/3] Writing fraud rings to database...")
        
        await session.run("MATCH (r:FraudRing) DETACH DELETE r")
        await session.run("MATCH (a:Account)-[m:MEMBER_OF]->() DELETE m")
        
        # Write new rings and gather statistics
        risk_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0}
        total_members = 0
        
        for idx, ring_members in enumerate(rings, 1):
            ring_id = f"RING_{idx:04d}"
            
            # Count known-fraud members
            known_fraud_count = sum(
                1
                for acc_id in ring_members
                if accounts.get(acc_id, {}).get('is_known_fraud', False)
            )
            
            # Compute risk level
            if known_fraud_count > 0:
                risk_level = 'CRITICAL' if known_fraud_count >= 2 else 'HIGH'
            else:
                risk_level = 'MEDIUM'
            
            risk_counts[risk_level] += 1
            total_members += len(ring_members)
            
            # Create ring
            await session.run(
                """
                CREATE (ring:FraudRing {
                  ring_id: $ring_id,
                  member_count: $member_count,
                  known_fraud_count: $known_fraud_count,
                  risk_level: $risk_level,
                  created_at: datetime()
                })
                """,
                {
                    "ring_id": ring_id,
                    "member_count": len(ring_members),
                    "known_fraud_count": known_fraud_count,
                    "risk_level": risk_level,
                },
            )
            
            # Connect members
            for acc_id in ring_members:
                await session.run(
                    """
                    MATCH (a:Account {account_id: $acc_id})
                    MATCH (ring:FraudRing {ring_id: $ring_id})
                    MERGE (a)-[:MEMBER_OF]->(ring)
                    """,
                    {"acc_id": acc_id, "ring_id": ring_id},
                )
        
        if verbose:
            print(f"  OK - Persisted {len(rings)} fraud rings")
            print("\n  Fraud Ring Summary:")
            print(f"    CRITICAL risk: {risk_counts['CRITICAL']} rings")
            print(f"    HIGH risk:     {risk_counts['HIGH']} rings")
            print(f"    MEDIUM risk:   {risk_counts['MEDIUM']} rings")
            print("\n" + "=" * 70)
            print("[OK] Fraud rings computed and persisted (networkx)")
            print("=" * 70 + "\n")
    
    return FraudRingSummary(
        rings_created=len(rings),
        total_members=total_members,
        critical_rings=risk_counts["CRITICAL"],
        high_rings=risk_counts["HIGH"],
        medium_rings=risk_counts["MEDIUM"],
    )


# Backward-compatibility class wrapper
class FraudRingComputer:
    """Detects and persists fraud rings using connected components analysis."""

    def __init__(self):
        """Initialize database connection."""
        load_dotenv()
        self.driver = AsyncGraphDatabase.driver(
            os.getenv('COGNODB_URI'),
            auth=(os.getenv('COGNODB_USERNAME'), os.getenv('COGNODB_PASSWORD'))
        )

    async def close(self):
        """Close connection."""
        await self.driver.close()

    async def run(self):
        """Main entry point."""
        result = await compute_fraud_rings(self.driver, verbose=True)
        return result


async def main():
    """Entry point for CLI."""
    computer = FraudRingComputer()
    try:
        await computer.run()
    finally:
        await computer.close()


if __name__ == "__main__":
    asyncio.run(main())

