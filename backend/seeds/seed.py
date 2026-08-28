"""
Core seed data generation module - importable functions for both CLI and startup auto-seed

Implements idempotent seeding using MERGE operations to avoid duplicates.
All functions are async and return dataclass summaries with counts.

Ensures unique account_id constraints at both application and database levels.
Validates seed data before insertion and verifies uniqueness after completion.
"""

import asyncio
import random
import logging
from dataclasses import dataclass
from typing import Optional, Set, Dict, List
from neo4j import AsyncDriver

logger = logging.getLogger(__name__)


@dataclass
class SeedSummary:
    """Summary of seed operation results"""
    accounts_created: int
    devices_created: int
    ips_created: int
    phones_created: int
    transactions_created: int
    total_time_seconds: float


async def _create_uniqueness_constraint(driver: AsyncDriver, verbose: bool = True) -> bool:
    """
    Create a unique constraint on Account.account_id in the database.
    
    Args:
        driver: Neo4j AsyncDriver instance
        verbose: Whether to print progress messages
    
    Returns:
        True if constraint created or already exists, False on error
    
    This ensures database-level enforcement of account_id uniqueness.
    If the constraint already exists, this is a no-op (safe to call multiple times).
    """
    try:
        async with driver.session() as session:
            # Check if constraint already exists
            result = await session.run(
                """
                SHOW CONSTRAINTS
                YIELD name, type
                WHERE type = 'UNIQUENESS' AND name CONTAINS 'account_id'
                RETURN COUNT(*) as count
                """
            )
            records = await result.data()
            existing_count = records[0]['count'] if records else 0
            
            if existing_count > 0:
                if verbose:
                    logger.info("✓ Unique constraint on Account.account_id already exists")
                return True
            
            # Create the constraint
            await session.run(
                "CREATE CONSTRAINT account_id_uniqueness IF NOT EXISTS "
                "FOR (a:Account) REQUIRE a.account_id IS UNIQUE"
            )
            
            if verbose:
                logger.info("✓ Created unique constraint on Account.account_id")
            return True
            
    except Exception as e:
        # Some Neo4j versions use different constraint syntax
        try:
            async with driver.session() as session:
                await session.run(
                    "CREATE CONSTRAINT account_id_uniqueness IF NOT EXISTS "
                    "ON (a:Account) ASSERT a.account_id IS UNIQUE"
                )
                if verbose:
                    logger.info("✓ Created unique constraint on Account.account_id (legacy syntax)")
                return True
        except Exception as e2:
            logger.warning(
                f"⚠ Could not create unique constraint on Account.account_id. "
                f"Database may not support constraints or constraint already exists. "
                f"Errors: {str(e)}, {str(e2)}"
            )
            return False


async def _validate_seed_data(seed_config: dict, verbose: bool = True) -> Dict[str, List[str]]:
    """
    Validate the seed dataset for duplicate account IDs.
    
    Args:
        seed_config: Configuration dict with count parameters
        verbose: Whether to print progress messages
    
    Returns:
        Dictionary with any detected duplicates and validation results
    
    Generates all account IDs that will be created and checks for duplicates
    within the seed data itself.
    """
    seen_ids: Set[str] = set()
    duplicates: Set[str] = set()
    validation_report = {
        "total_seed_accounts": 0,
        "duplicates_found": [],
        "unique_accounts": 0
    }
    
    # Generate all expected account IDs
    account_ids: List[str] = []
    
    # Fraud accounts
    for i in range(1, seed_config["fraud_count"] + 1):
        account_ids.append(f"FRAUD_{i:05d}")
    
    # Suspicious accounts
    for i in range(1, seed_config["suspicious_count"] + 1):
        account_ids.append(f"SUSP_{i:05d}")
    
    # Normal accounts
    for i in range(1, seed_config["normal_count"] + 1):
        account_ids.append(f"ACC_{i:05d}")
    
    # High risk accounts
    for i in range(1, seed_config["high_risk_count"] + 1):
        account_ids.append(f"HIGH_{i:05d}")
    
    # Check for duplicates
    validation_report["total_seed_accounts"] = len(account_ids)
    
    for account_id in account_ids:
        if account_id in seen_ids:
            duplicates.add(account_id)
            validation_report["duplicates_found"].append(account_id)
        else:
            seen_ids.add(account_id)
    
    validation_report["unique_accounts"] = len(seen_ids)
    
    if verbose:
        if duplicates:
            logger.warning(
                f"⚠ VALIDATION ERROR: Found {len(duplicates)} duplicate account IDs in seed data: "
                f"{sorted(list(duplicates))}"
            )
        else:
            logger.info(
                f"✓ Seed data validation passed: "
                f"{len(seen_ids)} unique accounts (expected {validation_report['total_seed_accounts']})"
            )
    
    return validation_report


async def _verify_account_uniqueness(driver: AsyncDriver, expected_count: int, verbose: bool = True) -> Dict[str, any]:
    """
    Verify that all account IDs in the database are unique.
    
    Args:
        driver: Neo4j AsyncDriver instance
        expected_count: Expected number of unique accounts
        verbose: Whether to print progress messages
    
    Returns:
        Verification report with results
    
    Queries the database to ensure no duplicate account_ids exist.
    """
    verification_report = {
        "total_accounts": 0,
        "unique_account_ids": 0,
        "duplicates_found": [],
        "is_valid": True,
    }
    
    try:
        async with driver.session() as session:
            # Count total accounts
            result = await session.run("MATCH (a:Account) RETURN COUNT(a) as count")
            records = await result.data()
            total_accounts = records[0]["count"] if records else 0
            verification_report["total_accounts"] = total_accounts
            
            # Count unique account IDs
            result = await session.run(
                "MATCH (a:Account) RETURN COUNT(DISTINCT a.account_id) as unique_count"
            )
            records = await result.data()
            unique_count = records[0]["unique_count"] if records else 0
            verification_report["unique_account_ids"] = unique_count
            
            # Find any duplicates (if total > unique)
            if total_accounts != unique_count:
                result = await session.run(
                    """
                    MATCH (a:Account)
                    WITH a.account_id as account_id, COUNT(*) as count
                    WHERE count > 1
                    RETURN account_id, count
                    ORDER BY count DESC
                    """
                )
                records = await result.data()
                for record in records:
                    verification_report["duplicates_found"].append({
                        "account_id": record["account_id"],
                        "count": record["count"]
                    })
                verification_report["is_valid"] = False
            
            if verbose:
                if verification_report["is_valid"]:
                    logger.info(
                        f"✓ Uniqueness verification passed: "
                        f"{unique_count} unique account IDs, "
                        f"{total_accounts} total accounts"
                    )
                else:
                    logger.error(
                        f"✗ UNIQUENESS VIOLATION: Found {len(verification_report['duplicates_found'])} "
                        f"duplicate account IDs: {verification_report['duplicates_found']}"
                    )
    
    except Exception as e:
        logger.error(f"✗ Verification query failed: {str(e)}")
        verification_report["is_valid"] = False
    
    return verification_report


async def seed_core_data(
    driver: AsyncDriver, 
    seed_config: Optional[dict] = None,
    verbose: bool = True
) -> SeedSummary:
    """
    Seed core account and attribute data (MERGE-based, idempotent).
    
    Args:
        driver: Neo4j AsyncDriver instance
        seed_config: Optional config dict with keys like 'fraud_count', 'suspicious_count', etc.
        verbose: Whether to print progress messages
    
    Returns:
        SeedSummary with creation counts
    
    This operation is safe to run multiple times — MERGE ensures no duplicates.
    Existing accounts with the same account_id will be skipped.
    
    Process:
      1. Create unique constraint on account_id (if not exists)
      2. Validate seed data for duplicates
      3. Create accounts using MERGE (idempotent)
      4. Verify uniqueness after seeding
    """
    import time
    start_time = time.time()
    
    # Default seed configuration
    config = {
        "fraud_count": 10,
        "suspicious_count": 40,
        "normal_count": 50,
        "high_risk_count": 50,
        "devices_per_fraud_pair": 5,
        "ips_per_high_risk": 10,
    }
    if seed_config:
        config.update(seed_config)
    
    # Step 1: Create unique constraint on account_id
    if verbose:
        logger.info("[Seed] Ensuring unique constraint on account_id...")
    await _create_uniqueness_constraint(driver, verbose=verbose)
    
    # Step 2: Validate seed data for duplicates
    if verbose:
        logger.info("[Seed] Validating seed data...")
    validation_report = await _validate_seed_data(config, verbose=verbose)
    
    if validation_report["duplicates_found"]:
        raise ValueError(
            f"Seed data contains {len(validation_report['duplicates_found'])} duplicate account IDs: "
            f"{validation_report['duplicates_found']}. Cannot proceed with seeding."
        )
    
    # Step 3: Seed accounts
    async with driver.session() as session:
        # Stage 1: Create fraud accounts (MERGE - idempotent)
        if verbose:
            logger.info(f"[Seed] Creating {config['fraud_count']} fraud accounts...")
        
        fraud_count_created = 0
        for i in range(1, config["fraud_count"] + 1):
            account_id = f"FRAUD_{i:05d}"
            try:
                result = await session.run(
                    """
                    MERGE (a:Account {account_id: $account_id})
                    ON CREATE SET
                        a.display_name = $display_name,
                        a.email = $email,
                        a.status = 'SUSPENDED',
                        a.risk_level = 'CRITICAL',
                        a.is_known_fraud = true,
                        a.risk_score = 95.0,
                        a.created_at = datetime()
                    RETURN a.account_id as id
                    """,
                    {
                        "account_id": account_id,
                        "display_name": f"Fraud Account {i:05d}",
                        "email": f"fraud{i:05d}@test.com",
                    },
                )
                record = await result.single()
                if record:
                    fraud_count_created += 1
            except Exception as e:
                logger.error(f"✗ Error creating fraud account {account_id}: {str(e)}")
                raise
        
        fraud_count = config["fraud_count"]
        if verbose:
            logger.info(f"  ✓ Processed {fraud_count_created}/{fraud_count} fraud accounts")
        
        # Stage 2: Create suspicious accounts (MERGE - idempotent)
        if verbose:
            logger.info(f"[Seed] Creating {config['suspicious_count']} suspicious accounts...")
        
        susp_count_created = 0
        for i in range(1, config["suspicious_count"] + 1):
            account_id = f"SUSP_{i:05d}"
            try:
                result = await session.run(
                    """
                    MERGE (a:Account {account_id: $account_id})
                    ON CREATE SET
                        a.display_name = $display_name,
                        a.email = $email,
                        a.status = 'ACTIVE',
                        a.risk_level = 'MEDIUM',
                        a.is_known_fraud = false,
                        a.risk_score = 50.0,
                        a.created_at = datetime()
                    RETURN a.account_id as id
                    """,
                    {
                        "account_id": account_id,
                        "display_name": f"Suspicious Account {i:05d}",
                        "email": f"susp{i:05d}@test.com",
                    },
                )
                record = await result.single()
                if record:
                    susp_count_created += 1
            except Exception as e:
                logger.error(f"✗ Error creating suspicious account {account_id}: {str(e)}")
                raise
        
        suspicious_count = config["suspicious_count"]
        if verbose:
            logger.info(f"  ✓ Processed {susp_count_created}/{suspicious_count} suspicious accounts")
        # Stage 3: Create normal accounts (MERGE - idempotent)
        if verbose:
            logger.info(f"[Seed] Creating {config['normal_count']} normal accounts...")
        
        normal_count_created = 0
        for i in range(1, config["normal_count"] + 1):
            account_id = f"ACC_{i:05d}"
            try:
                result = await session.run(
                    """
                    MERGE (a:Account {account_id: $account_id})
                    ON CREATE SET
                        a.display_name = $display_name,
                        a.email = $email,
                        a.status = 'ACTIVE',
                        a.risk_level = 'LOW',
                        a.is_known_fraud = false,
                        a.risk_score = 0.0,
                        a.created_at = datetime()
                    RETURN a.account_id as id
                    """,
                    {
                        "account_id": account_id,
                        "display_name": f"User {i:05d}",
                        "email": f"user{i:05d}@test.com",
                    },
                )
                record = await result.single()
                if record:
                    normal_count_created += 1
            except Exception as e:
                logger.error(f"✗ Error creating normal account {account_id}: {str(e)}")
                raise
        
        normal_count = config["normal_count"]
        if verbose:
            logger.info(f"  ✓ Processed {normal_count_created}/{normal_count} normal accounts")
        
        # Stage 4: Create HIGH risk accounts (MERGE - idempotent)
        if verbose:
            logger.info(f"[Seed] Creating {config['high_risk_count']} HIGH risk accounts...")
        
        high_count_created = 0
        for i in range(1, config["high_risk_count"] + 1):
            account_id = f"HIGH_{i:05d}"
            try:
                result = await session.run(
                    """
                    MERGE (a:Account {account_id: $account_id})
                    ON CREATE SET
                        a.display_name = $display_name,
                        a.email = $email,
                        a.status = 'ACTIVE',
                        a.risk_level = 'HIGH',
                        a.is_known_fraud = false,
                        a.risk_score = 75.0,
                        a.created_at = datetime()
                    RETURN a.account_id as id
                    """,
                    {
                        "account_id": account_id,
                        "display_name": f"High Risk Account {i:05d}",
                        "email": f"high{i:05d}@test.com",
                    },
                )
                record = await result.single()
                if record:
                    high_count_created += 1
            except Exception as e:
                logger.error(f"✗ Error creating high risk account {account_id}: {str(e)}")
                raise
        
        high_count = config["high_risk_count"]
        if verbose:
            logger.info(f"  ✓ Processed {high_count_created}/{high_count} HIGH risk accounts")
        
        total_accounts = fraud_count + suspicious_count + normal_count + high_count
        
        # Stage 5: Create shared devices connecting fraud accounts (MERGE - idempotent)
        if verbose:
            logger.info(f"[Seed] Creating {config['devices_per_fraud_pair']} shared devices...")
        
        devices_created = 0
        for dev_num in range(1, config["devices_per_fraud_pair"] + 1):
            device_id = f"DEV_{dev_num:04d}"
            
            # MERGE device node
            await session.run(
                """
                MERGE (d:Device {device_id: $device_id})
                ON CREATE SET d.device_name = $device_name
                """,
                {
                    "device_id": device_id,
                    "device_name": f"Device {dev_num:04d}",
                },
            )
            
            # Connect pairs of fraud accounts to the device
            f1_num = dev_num % fraud_count
            if f1_num == 0:
                f1_num = fraud_count
            f2_num = (dev_num + 1) % fraud_count
            if f2_num == 0:
                f2_num = fraud_count
            
            f1_id = f"FRAUD_{f1_num:05d}"
            f2_id = f"FRAUD_{f2_num:05d}"
            
            # MERGE relationships
            await session.run(
                """
                MATCH (d:Device {device_id: $device_id})
                MATCH (f1:Account {account_id: $f1_id})
                MERGE (f1)-[:USES_DEVICE]->(d)
                """,
                {
                    "device_id": device_id,
                    "f1_id": f1_id,
                },
            )
            
            await session.run(
                """
                MATCH (d:Device {device_id: $device_id})
                MATCH (f2:Account {account_id: $f2_id})
                MERGE (f2)-[:USES_DEVICE]->(d)
                """,
                {
                    "device_id": device_id,
                    "f2_id": f2_id,
                },
            )
            
            devices_created += 1
        
        if verbose:
            logger.info(f"  ✓ Created {devices_created} shared devices with fraud account connections")
        
        # Stage 6: Create shared IPs (similar pattern - MERGE-based)
        if verbose:
            logger.info(f"[Seed] Creating {config['ips_per_high_risk']} shared IPs...")
        
        ips_created = 0
        for ip_num in range(1, config["ips_per_high_risk"] + 1):
            ip_id = f"IP_{ip_num:04d}"
            ip_address = f"192.168.{ip_num // 256}.{ip_num % 256}"
            
            # MERGE IP node
            await session.run(
                """
                MERGE (i:IPAddress {ip_id: $ip_id})
                ON CREATE SET i.ip_address = $ip_address
                """,
                {
                    "ip_id": ip_id,
                    "ip_address": ip_address,
                },
            )
            
            # Connect HIGH accounts to IPs, plus one FRAUD account for variety
            high_num = (ip_num % high_count) + 1
            fraud_num = (ip_num % fraud_count) + 1
            
            high_id = f"HIGH_{high_num:05d}"
            fraud_id = f"FRAUD_{fraud_num:05d}"
            
            await session.run(
                """
                MATCH (i:IPAddress {ip_id: $ip_id})
                MATCH (h:Account {account_id: $high_id})
                MERGE (h)-[:ACCESSED_FROM_IP]->(i)
                """,
                {
                    "ip_id": ip_id,
                    "high_id": high_id,
                },
            )
            
            await session.run(
                """
                MATCH (i:IPAddress {ip_id: $ip_id})
                MATCH (f:Account {account_id: $fraud_id})
                MERGE (f)-[:ACCESSED_FROM_IP]->(i)
                """,
                {
                    "ip_id": ip_id,
                    "fraud_id": fraud_id,
                },
            )
            
            ips_created += 1
        
        if verbose:
            logger.info(f"  ✓ Created {ips_created} shared IPs")
        
        # Stage 7: Create phone numbers (simple - MERGE-based)
        if verbose:
            logger.info(f"[Seed] Creating phone numbers...")
        
        phones_created = 0
        for phone_num in range(1, min(20, total_accounts)):
            phone_id = f"PHONE_{phone_num:04d}"
            phone_number = f"+1-555-{1000 + phone_num:04d}"
            
            await session.run(
                """
                MERGE (p:PhoneNumber {phone_id: $phone_id})
                ON CREATE SET p.phone_number = $phone_number
                """,
                {
                    "phone_id": phone_id,
                    "phone_number": phone_number,
                },
            )
            
            # Assign to random accounts
            account_types = ["FRAUD", "SUSP", "ACC", "HIGH"]
            account_type = random.choice(account_types)
            account_num = random.randint(1, 50)
            account_id = f"{account_type}_{account_num:05d}"
            
            await session.run(
                """
                MATCH (p:PhoneNumber {phone_id: $phone_id})
                MATCH (a:Account {account_id: $account_id})
                MERGE (a)-[:HAS_PHONE]->(p)
                """,
                {
                    "phone_id": phone_id,
                    "account_id": account_id,
                },
            )
            
            phones_created += 1
        
        if verbose:
            logger.info(f"  ✓ Created {phones_created} phone numbers")
    
    # Step 4: Verify uniqueness after seeding
    if verbose:
        logger.info("[Seed] Verifying account uniqueness...")
    verification_report = await _verify_account_uniqueness(driver, total_accounts, verbose=verbose)
    
    if not verification_report["is_valid"]:
        logger.warning(
            f"✗ UNIQUENESS VERIFICATION FAILED: {len(verification_report['duplicates_found'])} "
            f"duplicate account IDs found after seeding"
        )
    else:
        if verbose:
            logger.info("✓ Seed operation completed with uniqueness constraint satisfied")
    
    elapsed = time.time() - start_time
    
    return SeedSummary(
        accounts_created=total_accounts,
        devices_created=devices_created,
        ips_created=ips_created,
        phones_created=phones_created,
        transactions_created=0,  # Filled in by seed_transaction_data
        total_time_seconds=elapsed,
    )


async def seed_transaction_data(
    driver: AsyncDriver,
    transaction_config: Optional[dict] = None,
    verbose: bool = True,
) -> int:
    """
    Seed transaction (money-mule) data - idempotent MERGE-based operations.
    
    Args:
        driver: Neo4j AsyncDriver instance
        transaction_config: Optional config dict
        verbose: Whether to print progress messages
    
    Returns:
        Count of transactions created
    
    Creates TRANSACTED_WITH relationships between accounts, designed to form
    realistic money-mule chains from fraud to fraud through intermediaries.
    """
    import time
    start_time = time.time()
    
    config = {
        "chains_count": 50,
        "noise_transactions": 50,
    }
    if transaction_config:
        config.update(transaction_config)
    
    if verbose:
        logger.info(f"[Seed] Creating money-mule transaction chains...")
    
    txn_count = 0
    random.seed(42)
    
    async with driver.session() as session:
        # Create money-mule chains: FRAUD -> SUSP -> SUSP -> FRAUD
        for chain_num in range(1, config["chains_count"] + 1):
            fraud_src = f"FRAUD_{(chain_num % 10 + 1):05d}"
            fraud_dst = f"FRAUD_{((chain_num + 5) % 10 + 1):05d}"
            susp_mid1 = f"SUSP_{(chain_num * 2 % 40 + 1):05d}"
            susp_mid2 = f"SUSP_{((chain_num * 2 + 1) % 40 + 1):05d}"
            
            amounts = [
                50000 - (chain_num * 100),
                40000 - (chain_num * 100),
                30000 - (chain_num * 100),
            ]
            
            hops = [
                (fraud_src, susp_mid1, amounts[0]),
                (susp_mid1, susp_mid2, amounts[1]),
                (susp_mid2, fraud_dst, amounts[2]),
            ]
            
            for from_id, to_id, amount in hops:
                txn_id = f"TXN_{(chain_num * 3 + hops.index((from_id, to_id, amount))):08d}"
                
                try:
                    await session.run(
                        """
                        MATCH (a1:Account {account_id: $from_id})
                        MATCH (a2:Account {account_id: $to_id})
                        MERGE (a1)-[r:TRANSACTED_WITH {transaction_id: $txn_id}]->(a2)
                        ON CREATE SET
                            r.amount = $amount,
                            r.timestamp = datetime()
                        """,
                        {
                            "from_id": from_id,
                            "to_id": to_id,
                            "txn_id": txn_id,
                            "amount": amount,
                        },
                    )
                    txn_count += 1
                except Exception as e:
                    logger.warning(f"  ⚠ Warning: Failed to create transaction {txn_id}: {e}")
        
        # Add noise transactions: normal accounts to suspicious accounts
        for i in range(1, config["noise_transactions"] + 1):
            acc_from = f"ACC_{i:05d}"
            acc_to = f"SUSP_{((i * 3) % 40 + 1):05d}"
            txn_id = f"TXN_{(1000000 + i):08d}"
            amount = random.randint(1000, 10000)
            
            try:
                await session.run(
                    """
                    MATCH (a1:Account {account_id: $from_id})
                    MATCH (a2:Account {account_id: $to_id})
                    MERGE (a1)-[r:TRANSACTED_WITH {transaction_id: $txn_id}]->(a2)
                    ON CREATE SET
                        r.amount = $amount,
                        r.timestamp = datetime()
                    """,
                    {
                        "from_id": acc_from,
                        "to_id": acc_to,
                        "txn_id": txn_id,
                        "amount": amount,
                    },
                )
                txn_count += 1
            except Exception as e:
                logger.warning(f"  ⚠ Warning: Failed to create noise transaction {txn_id}: {e}")
        
        if verbose:
            elapsed = time.time() - start_time
            logger.info(
                f"  ✓ Created {txn_count} transactions (chains + noise) in {elapsed:.1f}s"
            )
    
    return txn_count


if __name__ == "__main__":
    # CLI entry point for manual seeding
    import os
    from dotenv import load_dotenv
    from neo4j import AsyncGraphDatabase
    
    # Configure logging for CLI usage
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    async def main():
        load_dotenv()
        
        driver = AsyncGraphDatabase.driver(
            os.getenv("COGNODB_URI"),
            auth=(os.getenv("COGNODB_USERNAME"), os.getenv("COGNODB_PASSWORD")),
        )
        
        try:
            print("\n" + "=" * 70)
            print("MANUAL SEED DATA GENERATION WITH UNIQUENESS VALIDATION")
            print("=" * 70 + "\n")
            
            summary = await seed_core_data(driver, verbose=True)
            txn_count = await seed_transaction_data(driver, verbose=True)
            
            print("\n" + "=" * 70)
            print("SEED COMPLETE")
            print("=" * 70)
            print(f"  Accounts created: {summary.accounts_created}")
            print(f"  Devices created: {summary.devices_created}")
            print(f"  IPs created: {summary.ips_created}")
            print(f"  Phones created: {summary.phones_created}")
            print(f"  Transactions created: {txn_count}")
            print(f"  Total time: {summary.total_time_seconds:.1f}s\n")
            
        finally:
            await driver.close()
    
    asyncio.run(main())
