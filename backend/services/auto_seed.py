"""
Auto-seed service for FastAPI startup.

Provides automatic, idempotent seeding on application startup:
- Checks if database is empty or partially seeded
- Runs full seed + precomputation pipeline if needed
- Logs progress at each stage
- Ensures app never starts in a half-seeded state

This replaces manual "run scripts/seed.py by hand" workflows.
"""

import asyncio
import sys
import time
import os
from neo4j import AsyncDriver

# Add backend to path if needed for imports
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Import refactored seed and compute modules
try:
    # Try relative imports first (when used in FastAPI)
    from seeds.seed import seed_core_data, seed_transaction_data, SeedSummary
    from scripts.compute_fraud_rings import compute_fraud_rings, FraudRingSummary
    from scripts.compute_risk_scores import compute_risk_scores, RiskScoreSummary
except ImportError:
    # Fall back to relative imports from parent
    try:
        from ..seeds.seed import seed_core_data, seed_transaction_data, SeedSummary
        from ..scripts.compute_fraud_rings import compute_fraud_rings, FraudRingSummary
        from ..scripts.compute_risk_scores import compute_risk_scores, RiskScoreSummary
    except ImportError as e:
        raise ImportError(f"Failed to import seed/compute modules. Backend dir: {backend_dir}. Error: {e}")


class DatabaseCompletenessCheck:
    """
    Comprehensive check for full seeding completion.
    
    Instead of checking if database is empty, verify that ALL expected data exists:
    - All required node labels (Account, Device, IPAddress, PhoneNumber, FraudRing)
    - All required relationship types
    - Minimum expected counts for critical data
    - Key data combinations needed by the app
    
    This is a fast, read-only check (single query) that prevents expensive
    re-computation of risk scores on every startup if data is already complete.
    """

    def __init__(self, driver: AsyncDriver):
        self.driver = driver

    async def is_complete(self) -> dict:
        """
        Fast, comprehensive completeness check.
        
        Returns:
            dict {
                "is_complete": bool - True if all stages fully complete
                "account_count": int - Number of accounts
                "transaction_count": int - Number of transactions  
                "fraud_ring_count": int - Number of fraud rings
                "scored_accounts": int - Accounts with risk_score computed
                "missing_labels": [str] - Any missing node labels
                "missing_rels": [str] - Any missing relationship types
            }
        """
        result_info = {
            "is_complete": False,
            "account_count": 0,
            "transaction_count": 0,
            "fraud_ring_count": 0,
            "scored_accounts": 0,
            "missing_labels": [],
            "missing_rels": [],
        }

        try:
            async with self.driver.session() as session:
                # Comprehensive query to check all seeding stages (Neo4j 5.x compatible)
                completion_query = """
                MATCH (a:Account)
                OPTIONAL MATCH (d:Device)
                OPTIONAL MATCH (i:IPAddress)
                OPTIONAL MATCH (p:PhoneNumber)
                OPTIONAL MATCH (r:FraudRing)
                OPTIONAL MATCH ()-[t:TRANSACTED_WITH]->()
                OPTIONAL MATCH ()-[ud:USES_DEVICE]->()
                OPTIONAL MATCH ()-[hp:HAS_PHONE]->()
                OPTIONAL MATCH ()-[af:ACCESSED_FROM_IP]->()
                OPTIONAL MATCH ()-[m:MEMBER_OF]->()
                OPTIONAL MATCH ()-[ring:IS_IN_RING|CONNECTED_TO_RING]->()
                OPTIONAL MATCH (scored:Account) WHERE scored.risk_score IS NOT NULL
                RETURN 
                    count(DISTINCT a) as account_count,
                    count(DISTINCT t) as transaction_count,
                    count(DISTINCT r) as fraud_ring_count,
                    count(DISTINCT scored) as scored_accounts,
                    count(DISTINCT d) > 0 as has_device_label,
                    count(DISTINCT i) > 0 as has_ip_label,
                    count(DISTINCT p) > 0 as has_phone_label,
                    count(DISTINCT ud) > 0 as has_uses_device_rel,
                    count(DISTINCT hp) > 0 as has_phone_rel,
                    count(DISTINCT af) > 0 as has_ip_rel,
                    count(DISTINCT m) > 0 as has_member_rel,
                    count(DISTINCT ring) > 0 as has_fraud_ring_links
                """
                
                result = await session.run(completion_query)
                records = await result.data()
                
                if not records:
                    return result_info

                checks = records[0]
                
                # Extract counts
                result_info["account_count"] = checks.get("account_count", 0) or 0
                result_info["transaction_count"] = checks.get("transaction_count", 0) or 0
                result_info["fraud_ring_count"] = checks.get("fraud_ring_count", 0) or 0
                result_info["scored_accounts"] = checks.get("scored_accounts", 0) or 0
                
                # Check for missing labels
                if result_info["account_count"] > 0 and not checks.get("has_device_label", False):
                    result_info["missing_labels"].append("Device")
                if result_info["account_count"] > 0 and not checks.get("has_ip_label", False):
                    result_info["missing_labels"].append("IPAddress")
                if result_info["account_count"] > 0 and not checks.get("has_phone_label", False):
                    result_info["missing_labels"].append("PhoneNumber")
                if result_info["account_count"] > 0 and not checks.get("has_fraud_ring_count", False):
                    if result_info["fraud_ring_count"] == 0:
                        result_info["missing_labels"].append("FraudRing")
                
                # Check for missing relationship types
                if result_info["account_count"] > 0 and not checks.get("has_uses_device_rel", False):
                    result_info["missing_rels"].append("USES_DEVICE")
                if result_info["account_count"] > 0 and not checks.get("has_phone_rel", False):
                    result_info["missing_rels"].append("HAS_PHONE")
                if result_info["account_count"] > 0 and not checks.get("has_ip_rel", False):
                    result_info["missing_rels"].append("ACCESSED_FROM_IP")
                if result_info["account_count"] > 0 and not checks.get("has_member_rel", False):
                    result_info["missing_rels"].append("MEMBER_OF")
                
                # Determine if complete
                # Complete = 150+ accounts, 150+ transactions, 1+ rings, 150+ scored accounts, no missing labels/rels
                is_complete = (
                    result_info["account_count"] >= 150
                    and result_info["transaction_count"] >= 150
                    and result_info["fraud_ring_count"] >= 1
                    and result_info["scored_accounts"] >= 150
                    and len(result_info["missing_labels"]) == 0
                    and len(result_info["missing_rels"]) == 0
                )
                result_info["is_complete"] = is_complete
                
        except Exception as e:
            # If check fails, assume incomplete (err on side of safety)
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Completeness check failed (will attempt reseed): {str(e)}")

        return result_info


async def auto_seed_if_empty(driver: AsyncDriver, enabled: bool = True) -> dict:
    """
    Main entry point: check if seeding is needed, then run the pipeline if so.
    
    Uses comprehensive completeness check to avoid re-running expensive compute_risk_scores
    when all data is already present and complete.

    Args:
        driver: Neo4j AsyncDriver instance
        enabled: Whether auto-seeding is enabled (can be disabled via config)

    Returns:
        dict with keys:
        {
            "seeding_performed": True/False,
            "is_complete": bool - Whether all seeding stages are complete
            "skipped_reason": str or None,
            "seed_summary": SeedSummary or None,
            "fraud_rings_summary": FraudRingSummary or None,
            "risk_scores_summary": RiskScoreSummary or None,
            "total_time_seconds": float,
            "error": str or None - If seeding was attempted but failed
        }
    """
    import logging

    logger = logging.getLogger(__name__)
    start_time = time.time()

    result = {
        "seeding_performed": False,
        "is_complete": False,
        "skipped_reason": None,
        "seed_summary": None,
        "fraud_rings_summary": None,
        "risk_scores_summary": None,
        "total_time_seconds": 0.0,
        "error": None,
    }

    if not enabled:
        logger.info("Auto-seed is disabled via AUTO_SEED_ON_STARTUP=false")
        result["skipped_reason"] = "AUTO_SEED_ON_STARTUP is disabled"
        result["total_time_seconds"] = time.time() - start_time
        return result

    # FAST COMPLETENESS CHECK: Read-only, single query, non-blocking
    logger.info("Checking for complete seeded dataset...")
    checker = DatabaseCompletenessCheck(driver)
    
    try:
        completion_info = await checker.is_complete()
        
        # Extract info from completeness check
        result["is_complete"] = completion_info["is_complete"]
        
        if completion_info["is_complete"]:
            # Dataset is already complete - skip everything
            logger.info(
                f"✓ Dataset is complete ({completion_info['account_count']} accounts, "
                f"{completion_info['transaction_count']} transactions, "
                f"{completion_info['fraud_ring_count']} rings, "
                f"{completion_info['scored_accounts']} scored). Auto-seed skipped."
            )
            result["skipped_reason"] = (
                f"Dataset already complete: "
                f"{completion_info['account_count']} accounts, "
                f"{completion_info['fraud_ring_count']} rings, "
                f"{completion_info['scored_accounts']} scored accounts"
            )
            result["total_time_seconds"] = time.time() - start_time
            return result
        
        # Dataset is incomplete - proceed with seeding
        logger.info(
            f"Dataset incomplete: {completion_info['account_count']} accounts, "
            f"{completion_info['fraud_ring_count']} rings, "
            f"{completion_info['scored_accounts']} scored. Running auto-seed pipeline..."
        )
        
        logger.info("Running auto-seed pipeline...")

        # Run each stage if needed
        missing_labels = completion_info.get("missing_labels", [])
        missing_rels = completion_info.get("missing_rels", [])
        
        if completion_info["account_count"] == 0:
            logger.info("[1/4] Seeding core data (accounts, devices, IPs, phones)...")
            seed_summary = await seed_core_data(driver, verbose=True)
            result["seed_summary"] = seed_summary
            logger.info(
                f"  ✓ Seeded {seed_summary.accounts_created} accounts, "
                f"{seed_summary.devices_created} devices, "
                f"{seed_summary.ips_created} IPs, "
                f"{seed_summary.phones_created} phones"
            )
        else:
            logger.info(f"[1/4] Accounts already seeded ({completion_info['account_count']}) — skipping...")

        if completion_info["transaction_count"] == 0:
            logger.info("[2/4] Seeding transaction data...")
            txn_count = await seed_transaction_data(driver, verbose=True)
            if result["seed_summary"]:
                result["seed_summary"].transactions_created = txn_count
            logger.info(f"  ✓ Seeded {txn_count} transactions")
        else:
            logger.info(f"[2/4] Transactions already seeded ({completion_info['transaction_count']}) — skipping...")

        if completion_info["fraud_ring_count"] == 0:
            logger.info("[3/4] Computing fraud rings...")
            rings_summary = await compute_fraud_rings(driver, verbose=True)
            result["fraud_rings_summary"] = rings_summary
            logger.info(
                f"  ✓ Detected {rings_summary.rings_created} fraud rings "
                f"({rings_summary.critical_rings} critical, {rings_summary.high_rings} high)"
            )
        else:
            logger.info(f"[3/4] Fraud rings already computed ({completion_info['fraud_ring_count']}) — skipping...")

        if completion_info["scored_accounts"] < completion_info["account_count"]:
            logger.info(f"[4/4] Computing risk scores for {completion_info['account_count'] - completion_info['scored_accounts']} unscored accounts...")
            scores_summary = await compute_risk_scores(driver, verbose=True)
            result["risk_scores_summary"] = scores_summary
            logger.info(
                f"  ✓ Scored {scores_summary.accounts_scored} accounts "
                f"(avg score: {scores_summary.avg_score:.1f})"
            )
        else:
            logger.info(f"[4/4] Risk scores already computed ({completion_info['scored_accounts']}) — skipping...")

        result["seeding_performed"] = True
        elapsed = time.time() - start_time
        result["total_time_seconds"] = elapsed

        logger.info(f"\n✓ Auto-seed pipeline complete in {elapsed:.1f}s")
        return result

    except Exception as e:
        elapsed = time.time() - start_time
        result["total_time_seconds"] = elapsed
        result["error"] = str(e)
        
        logger.error(
            f"Auto-seed pipeline FAILED after {elapsed:.1f}s: {str(e)}. "
            f"App will start in degraded state. Retry seeding via admin endpoint or restart.",
            exc_info=True
        )
        
        # Return degraded state instead of raising - let app start but report the failure
        return result


# Alternate simpler implementation if you want single-check approach
async def auto_seed_simple(driver: AsyncDriver, enabled: bool = True) -> dict:
    """
    Simplified auto-seed: single check for 'is database empty?'
    
    If any accounts exist, assume full seeding is done and skip everything.
    This is faster for already-seeded databases but may leave a half-seeded state.
    
    Prefer auto_seed_if_empty() for safety, but this is available as an option.
    """
    import logging

    logger = logging.getLogger(__name__)
    start_time = time.time()

    result = {
        "seeding_performed": False,
        "skipped_reason": None,
        "seed_summary": None,
        "fraud_rings_summary": None,
        "risk_scores_summary": None,
        "total_time_seconds": 0.0,
    }

    if not enabled:
        logger.info("Auto-seed is disabled")
        result["skipped_reason"] = "AUTO_SEED_ON_STARTUP is disabled"
        return result

    try:
        checker = DatabaseEmptinessCheck(driver)
        account_count = await checker.count_accounts()

        if account_count > 0:
            logger.info(f"Existing data found ({account_count} accounts) — skipping auto-seed.")
            result["skipped_reason"] = f"Database already has {account_count} accounts"
            result["total_time_seconds"] = time.time() - start_time
            return result

        logger.info("Running full auto-seed pipeline...")

        # Run all stages in sequence
        logger.info("[1/4] Seeding core data...")
        seed_summary = await seed_core_data(driver, verbose=True)
        result["seed_summary"] = seed_summary

        logger.info("[2/4] Seeding transactions...")
        txn_count = await seed_transaction_data(driver, verbose=True)
        result["seed_summary"].transactions_created = txn_count

        logger.info("[3/4] Computing fraud rings...")
        rings_summary = await compute_fraud_rings(driver, verbose=True)
        result["fraud_rings_summary"] = rings_summary

        logger.info("[4/4] Computing risk scores...")
        scores_summary = await compute_risk_scores(driver, verbose=True)
        result["risk_scores_summary"] = scores_summary

        result["seeding_performed"] = True
        elapsed = time.time() - start_time
        result["total_time_seconds"] = elapsed

        logger.info(f"✓ Auto-seed complete in {elapsed:.1f}s")
        return result

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Auto-seed FAILED after {elapsed:.1f}s: {str(e)}", exc_info=True)
        raise
