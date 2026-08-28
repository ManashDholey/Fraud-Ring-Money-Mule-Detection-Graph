"""
Enhanced Fraud & Money-Mule Pattern Seeding
Creates deliberate fraud rings and money-mule chains that demonstrate real patterns.
Uses DTOs for all data transfer.
"""
import asyncio
import os
from neo4j import AsyncGraphDatabase
from dotenv import load_dotenv
from datetime import datetime, timedelta
import random


class EnhancedPatternSeeder:
    """Seeds deliberate fraud patterns for demonstration and testing."""
    
    def __init__(self):
        load_dotenv()
        self.driver = AsyncGraphDatabase.driver(
            os.getenv('COGNODB_URI'),
            auth=(os.getenv('COGNODB_USERNAME'), os.getenv('COGNODB_PASSWORD'))
        )
        self.random = random.Random(42)  # Deterministic for reproducibility
    
    async def close(self):
        await self.driver.close()
    
    async def create_deliberate_fraud_rings(self):
        """
        Create clear fraud rings by connecting known-fraud accounts 
        with shared devices, phones, and IPs.
        """
        print("\n[*] Creating deliberate fraud rings...")
        
        async with self.driver.session() as session:
            # Create 5 fraud rings, each with:
            # - 1-2 known-fraud accounts (high-risk)
            # - 2-3 suspicious accounts (medium-risk)
            # - Deliberate shared device/IP connections
            for ring_num in range(1, 6):
                # Pick known-fraud anchor accounts
                known_fraud_accounts = [
                    f"FRAUD_{i:05d}" for i in range((ring_num-1)*50 + 1, (ring_num-1)*50 + 3)
                ]
                
                # Pick suspicious accounts to connect
                susp_start = (ring_num-1)*200 + 1
                suspicious_accounts = [
                    f"SUSP_{i:05d}" for i in range(susp_start, susp_start + 4)
                ]
                
                all_ring_members = known_fraud_accounts + suspicious_accounts
                
                # Create shared devices connecting all members of this ring
                for dev_num in range(3):
                    device_id = f"RING{ring_num}_DEV{dev_num}"
                    device_name = f"Device_FraudRing{ring_num}_{dev_num}"
                    
                    await session.run("""
                    MERGE (d:Device {device_id: $device_id})
                    SET d.device_name = $device_name, d.device_type = 'PHONE'
                    """, {"device_id": device_id, "device_name": device_name})
                    
                    # Connect all members to this device
                    for account_id in all_ring_members:
                        await session.run("""
                        MATCH (a:Account {account_id: $account_id})
                        MATCH (d:Device {device_id: $device_id})
                        CREATE (a)-[:USES_DEVICE]->(d)
                        """, {"account_id": account_id, "device_id": device_id})
                
                # Create shared IP connecting all members
                ip_address = f"192.168.{ring_num}.{100 + ring_num}"
                await session.run("""
                MERGE (ip:IPAddress {ip_address: $ip_address})
                """, {"ip_address": ip_address})
                
                for account_id in all_ring_members:
                    await session.run("""
                    MATCH (a:Account {account_id: $account_id})
                    MATCH (ip:IPAddress {ip_address: $ip_address})
                    CREATE (a)-[:ACCESSED_FROM_IP]->(ip)
                    """, {"account_id": account_id, "ip_address": ip_address})
        
        print("  ✓ Created 5 deliberate fraud rings with shared devices and IPs")
    
    async def create_deliberate_money_mule_chains(self):
        """
        Create clear money-mule chains with known-fraud source/destination
        and intermediaries to launder funds.
        """
        print("\n[*] Creating deliberate money-mule chains...")
        
        async with self.driver.session() as session:
            transaction_id = 1
            
            # Create 10 money-mule chains
            for chain_num in range(1, 11):
                # Source: known-fraud account
                source = f"FRAUD_{100 + chain_num:05d}"
                
                # Intermediaries: suspicious accounts
                intermediaries = [
                    f"SUSP_{3000 + chain_num * 10 + i:05d}" for i in range(3)
                ]
                
                # Destination: another known-fraud or high-risk
                destination = f"FRAUD_{200 + chain_num:05d}"
                
                chain_accounts = [source] + intermediaries + [destination]
                base_amount = 50000
                
                # Create transactions along the chain
                timestamp = datetime(2024, 1, 15, 10, 0, 0)
                
                for i in range(len(chain_accounts) - 1):
                    from_account = chain_accounts[i]
                    to_account = chain_accounts[i + 1]
                    # Amounts decrease as money launders through chain
                    amount = max(5000, base_amount - (i * 5000))
                    
                    await session.run("""
                    MATCH (source:Account {account_id: $source_id})
                    MATCH (target:Account {account_id: $target_id})
                    CREATE (source)-[:TRANSACTED_WITH {
                        transaction_id: $transaction_id,
                        amount: $amount,
                        timestamp: $timestamp,
                        transaction_count: 1,
                        total_amount: $amount
                    }]->(target)
                    """, {
                        "source_id": from_account,
                        "target_id": to_account,
                        "transaction_id": f"TXN_{transaction_id:06d}",
                        "amount": amount,
                        "timestamp": timestamp.isoformat()
                    })
                    
                    timestamp += timedelta(hours=1)
                    transaction_id += 1
        
        print("  ✓ Created 10 deliberate money-mule chains with transaction sequences")
    
    async def enhance_seed_data(self):
        """Apply enhancements to existing seed data."""
        print("\n" + "="*70)
        print("ENHANCING FRAUD PATTERNS IN SEED DATA")
        print("="*70)
        
        await self.create_deliberate_fraud_rings()
        await self.create_deliberate_money_mule_chains()
        
        print("\n" + "="*70)
        print("ENHANCEMENT COMPLETE!")
        print("="*70)
        print("\nFraud rings and money-mule chains should now be visible in the UI.")


async def main():
    seeder = EnhancedPatternSeeder()
    try:
        await seeder.enhance_seed_data()
    finally:
        await seeder.close()


if __name__ == "__main__":
    asyncio.run(main())
