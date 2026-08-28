"""
Compute fraud proximity scores for all accounts based on graph structure.

Risk Score Formula:
  - If isKnownFraud: riskScore = 100, riskLevel = CRITICAL
  - Else: compute shortest path distance to nearest known-fraud account via shared attributes
    - 1 hop: riskScore = 70 (HIGH)
    - 2 hops: riskScore = 40 (MEDIUM)
    - 3 hops: riskScore = 15 (LOW)
    - 4+ hops or no path: riskScore = 5 (LOW)
  - Bonus: +10 per additional known-fraud account reachable within depth-3

Maps: LOW (0-24), MEDIUM (25-49), HIGH (50-79), CRITICAL (80-100)

Exposes importable async functions for use in both CLI and auto-startup.

Includes resilience features:
- Smaller batches to avoid long-running queries
- Retry logic with exponential backoff for transient failures
- Fresh sessions on retry to recover from connection issues
"""

import asyncio
import os
import logging
from dataclasses import dataclass
from neo4j import AsyncGraphDatabase
from neo4j import AsyncDriver
from neo4j.exceptions import ServiceUnavailable, SessionExpired, TransientError
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


@dataclass
class RiskScoreSummary:
    """Summary of risk score computation results"""
    accounts_scored: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    avg_score: float


async def compute_risk_scores(
    driver: AsyncDriver, verbose: bool = True
) -> RiskScoreSummary:
    """Main importable function to compute risk scores for all accounts.
    
    Args:
        driver: Neo4j AsyncDriver instance
        verbose: Whether to print progress messages
    
    Returns:
        RiskScoreSummary with scoring statistics
    
    Uses proximity to known-fraud accounts to compute risk scores.
    Overwrites existing scores (inherently idempotent as it sets values, not appends).
    Includes retry logic for transient network failures.
    """
    if verbose:
        print("\n" + "="*70)
        print("COMPUTING RISK SCORES FOR ALL ACCOUNTS")
        print("="*70 + "\n")
    
    try:
        async with driver.session() as session:
            return await _compute_and_write_scores(session, driver, verbose=verbose)
    except Exception as e:
        logger.error(f"Fatal error in compute_risk_scores: {str(e)}", exc_info=True)
        raise


async def _compute_and_write_scores(session, driver, verbose: bool = True) -> RiskScoreSummary:
    """Compute risk scores for all accounts and write to DB with resilience."""
    # Step 1: Set known-fraud accounts to CRITICAL (100)
    if verbose:
        print("[1/3] Marking known-fraud accounts as CRITICAL (score=100)...")
    
    result = await session.run("""
    MATCH (a:Account {is_known_fraud: true})
    SET a.risk_score = 100, a.risk_level = 'CRITICAL'
    RETURN count(a) as count
    """)
    records = await result.data()
    fraud_count = records[0]['count'] if records else 0
    
    if verbose:
        print(f"  OK - Set {fraud_count} known-fraud accounts to CRITICAL")
    
    # Step 2: For each non-fraud account, compute distance to nearest known-fraud
    if verbose:
        print("\n[2/3] Computing shortest paths to known-fraud accounts...")
    
    result = await session.run("""
    MATCH (a:Account {is_known_fraud: false})
    RETURN a.account_id as account_id
    """)
    records = await result.data()
    
    # RESILIENCE: Use smaller batch size to avoid long-running queries that timeout
    batch_size = 25  # Down from 100 - each batch should complete in seconds, not minutes
    processed = 0
    account_ids = [rec['account_id'] for rec in records]
    
    if verbose:
        print(f"  Processing {len(account_ids)} accounts in batches of {batch_size}...")
    
    for batch_start in range(0, len(account_ids), batch_size):
        batch = account_ids[batch_start:batch_start + batch_size]
        batch_num = batch_start // batch_size + 1
        
        # RESILIENCE: Retry logic with exponential backoff for transient failures
        batch_count = await _score_batch_with_retry(
            driver, batch, batch_num, verbose=verbose
        )
        processed += batch_count
    
    # Step 3: Verify and report distribution
    if verbose:
        print("\n[3/3] Verifying risk level distribution...")
    
    result = await session.run("""
    MATCH (a:Account)
    RETURN a.risk_level as level, count(a) as count
    """)
    records = await result.data()
    
    risk_distribution = {
        "CRITICAL": 0,
        "HIGH": 0,
        "MEDIUM": 0,
        "LOW": 0,
    }
    
    for rec in records:
        level = rec['level'] or 'NULL'
        count = rec['count']
        if level in risk_distribution:
            risk_distribution[level] = count
    
    if verbose:
        print("\n  Risk Level Distribution:")
        for level in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            count = risk_distribution[level]
            total = sum(risk_distribution.values())
            pct = (count / total * 100) if total > 0 else 0
            print(f"    {level:10s}: {count:5d} accounts ({pct:5.1f}%)")
    
    # Distribution sanity check
    result = await session.run("""
    MATCH (a:Account)
    RETURN 
      min(a.risk_score) as min_score,
      max(a.risk_score) as max_score,
      avg(a.risk_score) as avg_score
    """)
    records = await result.data()
    avg_score = 0.0
    
    if records:
        rec = records[0]
        avg_score = rec['avg_score'] or 0.0
        
        if verbose:
            print(f"\n  Score Statistics:")
            print(f"    Min: {rec['min_score']}, Max: {rec['max_score']}, Avg: {avg_score:.1f}")
    
    if verbose:
        print("\n" + "=" * 70)
        print("✓ Risk scores computed and written to database")
        print("=" * 70 + "\n")
    
    return RiskScoreSummary(
        accounts_scored=processed + fraud_count,
        critical_count=risk_distribution["CRITICAL"],
        high_count=risk_distribution["HIGH"],
        medium_count=risk_distribution["MEDIUM"],
        low_count=risk_distribution["LOW"],
        avg_score=avg_score,
    )


async def _score_batch_with_retry(
    driver: AsyncDriver,
    batch: list,
    batch_num: int,
    max_retries: int = 3,
    verbose: bool = True
) -> int:
    """
    Score a single batch of accounts with retry logic.
    
    RESILIENCE: Retries on transient failures (ServiceUnavailable, SessionExpired, etc.)
    with exponential backoff. Uses fresh session on each retry.
    
    Args:
        driver: Neo4j driver
        batch: List of account_ids to score
        batch_num: Batch number for logging
        max_retries: Max retry attempts
        verbose: Whether to log
    
    Returns:
        Number of accounts processed in batch
    """
    for attempt in range(max_retries):
        try:
            # Fresh session for each attempt (previous one may be dead)
            async with driver.session() as session:
                result = await session.run("""
                UNWIND $account_ids as account_id
                MATCH (a:Account {account_id: account_id})
                
                OPTIONAL MATCH path = shortestPath(
                  (a)-[:USES_DEVICE|HAS_PHONE|ACCESSED_FROM_IP|HAS_CARD*1..4]-(fraud:Account {is_known_fraud: true})
                )
                
                WITH account_id, a, path,
                     CASE 
                       WHEN path is null THEN 5
                       WHEN length(path) <= 2 THEN 70
                       WHEN length(path) = 4 THEN 40
                       WHEN length(path) = 6 THEN 15
                       ELSE 5
                     END as distance_score
                
                OPTIONAL MATCH (a)-[:USES_DEVICE|HAS_PHONE|ACCESSED_FROM_IP|HAS_CARD*1..3]-(reachable:Account {is_known_fraud: true})
                WITH account_id, a, distance_score, count(DISTINCT reachable.account_id) as fraud_neighbor_count
                
                WITH account_id, a, 
                     distance_score + (CASE WHEN fraud_neighbor_count > 0 THEN (fraud_neighbor_count - 1) * 10 ELSE 0 END) as raw_score
                
                WITH account_id, a,
                     CASE
                       WHEN raw_score >= 80 THEN 100
                       WHEN raw_score < 0 THEN 0
                       ELSE raw_score
                     END as risk_score
                
                WITH account_id, a, risk_score,
                     CASE
                       WHEN risk_score >= 80 THEN 'CRITICAL'
                       WHEN risk_score >= 50 THEN 'HIGH'
                       WHEN risk_score >= 25 THEN 'MEDIUM'
                       ELSE 'LOW'
                     END as risk_level
                
                SET a.risk_score = risk_score, a.risk_level = risk_level
                RETURN count(*) as batch_count
                """, {"account_ids": batch})
                
                batch_records = await result.data()
                batch_count = batch_records[0]['batch_count'] if batch_records else 0
                
                if verbose:
                    print(f"  Batch {batch_num}: {batch_count} accounts processed")
                
                return batch_count
        
        except (ServiceUnavailable, SessionExpired, TransientError) as e:
            # Transient network/connection error - retry with backoff
            wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
            
            if attempt < max_retries - 1:
                logger.warning(
                    f"Transient error on batch {batch_num} (attempt {attempt + 1}/{max_retries}): {type(e).__name__}. "
                    f"Retrying in {wait_time}s..."
                )
                await asyncio.sleep(wait_time)
            else:
                # Final attempt failed
                logger.error(
                    f"Batch {batch_num} failed after {max_retries} attempts: {str(e)}"
                )
                raise
        
        except Exception as e:
            # Non-transient error - don't retry
            logger.error(f"Batch {batch_num} failed with non-transient error: {str(e)}", exc_info=True)
            raise
    
    return 0


# Backward-compatibility class wrapper
class RiskScoreComputer:
    """Computes risk scores for all accounts based on proximity to known fraud."""

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

    async def compute_and_write_scores(self):
        """Main entry point."""
        result = await compute_risk_scores(self.driver, verbose=True)
        return result


async def main():
    """Entry point for CLI."""
    computer = RiskScoreComputer()
    try:
        await computer.compute_and_write_scores()
    finally:
        await computer.close()


if __name__ == "__main__":
    asyncio.run(main())
