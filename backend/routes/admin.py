"""
Admin Routes - Setup and maintenance endpoints
Use only in development/setup phase.
"""
import logging
import random
from fastapi import APIRouter, HTTPException
from seeds.seed_data_generator_async import SeedDataGenerator
from dbConfig.db_async import get_driver

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/admin",
    tags=["Admin"],
)


@router.post("/reseed")
async def reseed_database():
    """
    Re-seed the database with enhanced fraud patterns.
    Creates deliberate fraud rings and money-mule chains for demonstration.
    WARNING: Deletes all existing data - only use during development!
    """
    try:
        generator = SeedDataGenerator()
        try:
            await generator.generate_all()
            return {
                "status": "success",
                "message": "Database re-seeded with enhanced fraud patterns",
                "patterns_created": {
                    "fraud_rings": 5,
                    "money_mule_chains": 10,
                    "transactions_total": 3500,
                    "shared_devices": 515,
                    "shared_ips": 610
                }
            }
        finally:
            await generator.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Re-seeding failed: {str(e)}")


@router.get("/diagnose-fraud-rings")
async def diagnose_fraud_rings():
    """
    Run comprehensive diagnostic to identify root cause of empty fraud rings.
    Executes steps 1-5 of the investigation.
    """
    try:
        driver = get_driver()
        results = {}
        
        # STEP 1: Check known-fraud accounts
        try:
            async with driver.session() as session:
                # Sample query
                sample_result = await session.run(
                    "MATCH (a:Account) WHERE a.is_known_fraud = true RETURN a.account_id LIMIT 20"
                )
                sample_data = await sample_result.data()
                sample_ids = [r['a.account_id'] for r in sample_data]
                
                # Count query
                count_result = await session.run(
                    "MATCH (a:Account) WHERE a.is_known_fraud = true RETURN count(a) AS total"
                )
                count_data = await count_result.data()
                kf_total = count_data[0]['total'] if count_data else 0
            
            results['step_1_known_fraud_accounts'] = {
                "total": kf_total,
                "sample_ids": sample_ids[:5]
            }
        except Exception as e:
            logger.warning(f"Diagnostic Step 1 failed: {e}")
            results['step_1_known_fraud_accounts'] = {"error": str(e), "total": 0}
        
        # STEP 2: Check shared-attribute relationships
        try:
            async with driver.session() as session:
                # Device sharing
                device_result = await session.run(
                    "MATCH (a1:Account)-[:USES_DEVICE]->(d:Device)<-[:USES_DEVICE]-(a2:Account) RETURN count(*) AS count"
                )
                device_data = await device_result.data()
                device_count = device_data[0]['count'] if device_data else 0
                
                # IP sharing
                ip_result = await session.run(
                    "MATCH (a1:Account)-[:ACCESSED_FROM_IP]->(ip:IPAddress)<-[:ACCESSED_FROM_IP]-(a2:Account) RETURN count(*) AS count"
                )
                ip_data = await ip_result.data()
                ip_count = ip_data[0]['count'] if ip_data else 0
                
                # Phone sharing
                phone_result = await session.run(
                    "MATCH (a1:Account)-[:HAS_PHONE]->(p:PhoneNumber)<-[:HAS_PHONE]-(a2:Account) RETURN count(*) AS count"
                )
                phone_data = await phone_result.data()
                phone_count = phone_data[0]['count'] if phone_data else 0
            
            results['step_2_shared_attributes'] = {
                "device_shared": device_count,
                "ip_shared": ip_count,
                "phone_shared": phone_count
            }
        except Exception as e:
            logger.warning(f"Diagnostic Step 2 failed: {e}")
            results['step_2_shared_attributes'] = {"error": str(e)}
        
        # STEP 3: Check overlap
        try:
            async with driver.session() as session:
                overlap_result = await session.run("""
                    MATCH (f:Account) WHERE f.is_known_fraud = true
                    OPTIONAL MATCH (f)-[:USES_DEVICE]->(d:Device)<-[:USES_DEVICE]-(other:Account)
                    OPTIONAL MATCH (f)-[:ACCESSED_FROM_IP]->(ip:IPAddress)<-[:ACCESSED_FROM_IP]-(other2:Account)
                    OPTIONAL MATCH (f)-[:HAS_PHONE]->(p:PhoneNumber)<-[:HAS_PHONE]-(other3:Account)
                    WITH f, (CASE WHEN other IS NOT NULL THEN 1 ELSE 0 END + 
                             CASE WHEN other2 IS NOT NULL THEN 1 ELSE 0 END +
                             CASE WHEN other3 IS NOT NULL THEN 1 ELSE 0 END) as connection_count
                    WHERE connection_count > 0
                    RETURN count(DISTINCT f) AS known_fraud_with_connections
                """)
                overlap_data = await overlap_result.data()
                overlap_count = overlap_data[0]['known_fraud_with_connections'] if overlap_data else 0
            
            results['step_3_overlap'] = {
                "known_fraud_with_connections": overlap_count,
                "total_known_fraud": kf_total
            }
        except Exception as e:
            logger.warning(f"Diagnostic Step 3 failed: {e}")
            results['step_3_overlap'] = {"error": str(e)}
        
        # STEP 4: Check FraudRing nodes
        try:
            async with driver.session() as session:
                fr_result = await session.run(
                    "MATCH (r:FraudRing) RETURN count(r) AS total"
                )
                fr_data = await fr_result.data()
                fr_count = fr_data[0]['total'] if fr_data else 0
            
            results['step_4_fraudring_nodes'] = {
                "total_fraudring_nodes": fr_count
            }
        except Exception as e:
            logger.warning(f"Diagnostic Step 4 failed: {e}")
            results['step_4_fraudring_nodes'] = {"error": str(e)}
        
        # DIAGNOSE ROOT CAUSE (safely extract values)
        diagnosis = []
        
        kf_total = results.get('step_1_known_fraud_accounts', {}).get('total', 0)
        device_count = results.get('step_2_shared_attributes', {}).get('device_shared', 0)
        ip_count = results.get('step_2_shared_attributes', {}).get('ip_shared', 0)
        phone_count = results.get('step_2_shared_attributes', {}).get('phone_shared', 0)
        overlap_count = results.get('step_3_overlap', {}).get('known_fraud_with_connections', 0)
        fr_count = results.get('step_4_fraudring_nodes', {}).get('total_fraudring_nodes', 0)
        
        if kf_total == 0:
            diagnosis.append("ROOT_CAUSE_1: NO_KNOWN_FRAUD_ACCOUNTS")
        
        if device_count == 0 and ip_count == 0 and phone_count == 0:
            diagnosis.append("ROOT_CAUSE_2: NO_SHARED_ATTRIBUTE_RELATIONSHIPS")
        
        if kf_total > 0 and overlap_count == 0:
            diagnosis.append("ROOT_CAUSE_3: KNOWN_FRAUD_ISOLATED_FROM_SHARING")
        
        if fr_count == 0:
            diagnosis.append("ROOT_CAUSE_4: NO_FRAUDRING_NODES_COMPUTED")
        
        results['diagnosis'] = diagnosis
        
        return {
            "status": "diagnostic_complete",
            "diagnostic_results": results,
            "root_causes": diagnosis
        }
    
    except Exception as e:
        logger.error(f"Diagnostic failed: {e}")
        return {
            "status": "diagnostic_failed",
            "error": str(e),
            "root_causes": ["DATABASE_CONNECTION_ERROR"]
        }


@router.post("/add-fraud-markers")
async def add_fraud_markers():
    """
    Quick operation: Mark existing accounts as known fraud and create shared devices/IPs.
    This creates 3 detectable fraud rings without full re-seeding.
    """
    try:
        driver = get_driver()
        
        async with driver.session() as session:
            # Mark accounts ACC_00001 through ACC_00010 as known fraud
            await session.run("""
                UNWIND ['ACC_00001', 'ACC_00002', 'ACC_00003', 'ACC_00004', 'ACC_00005',
                        'ACC_00006', 'ACC_00007', 'ACC_00008', 'ACC_00009', 'ACC_00010'] as acc_id
                MATCH (a:Account {account_id: acc_id})
                SET a.is_known_fraud = true,
                    a.risk_level = 'CRITICAL',
                    a.risk_score = 95.0
                RETURN count(a) as updated
            """)
            
            # Create fraud ring 1: ACC_00001 and ACC_00002 share a device and IP
            await session.run("""
                MATCH (a1:Account {account_id: 'ACC_00001'})
                MATCH (a2:Account {account_id: 'ACC_00002'})
                MERGE (d:Device {device_id: 'DEVICE_RING001', fingerprint: 'abc123xyz'})
                MERGE (a1)-[:USES_DEVICE]->(d)
                MERGE (a2)-[:USES_DEVICE]->(d)
                MERGE (ip:IPAddress {ip: '192.168.1.100', country: 'US'})
                MERGE (a1)-[:ACCESSED_FROM_IP]->(ip)
                MERGE (a2)-[:ACCESSED_FROM_IP]->(ip)
            """)
            
            # Create fraud ring 2: ACC_00003, ACC_00004, ACC_00005 share a device
            await session.run("""
                MATCH (a1:Account {account_id: 'ACC_00003'})
                MATCH (a2:Account {account_id: 'ACC_00004'})
                MATCH (a3:Account {account_id: 'ACC_00005'})
                MERGE (d:Device {device_id: 'DEVICE_RING002', fingerprint: 'def456uvw'})
                MERGE (a1)-[:USES_DEVICE]->(d)
                MERGE (a2)-[:USES_DEVICE]->(d)
                MERGE (a3)-[:USES_DEVICE]->(d)
            """)
            
            # Create fraud ring 3: ACC_00006 and ACC_00007 share device and IP
            await session.run("""
                MATCH (a1:Account {account_id: 'ACC_00006'})
                MATCH (a2:Account {account_id: 'ACC_00007'})
                MERGE (d:Device {device_id: 'DEVICE_RING003', fingerprint: 'ghi789rst'})
                MERGE (a1)-[:USES_DEVICE]->(d)
                MERGE (a2)-[:USES_DEVICE]->(d)
                MERGE (ip:IPAddress {ip: '10.0.0.50', country: 'RU'})
                MERGE (a1)-[:ACCESSED_FROM_IP]->(ip)
                MERGE (a2)-[:ACCESSED_FROM_IP]->(ip)
            """)
            
            # Get verification stats
            result = await session.run("""
                MATCH (a:Account) 
                WHERE a.is_known_fraud = true 
                RETURN count(a) as known_fraud_count
            """)
            kf_data = await result.data()
            known_fraud_count = kf_data[0]['known_fraud_count'] if kf_data else 0
            
            result = await session.run("""
                MATCH (a1:Account)-[:USES_DEVICE]->(d:Device)<-[:USES_DEVICE]-(a2:Account)
                WHERE a1.account_id < a2.account_id AND a1.is_known_fraud = true
                RETURN count(*) as ring_pairs
            """)
            ring_data = await result.data()
            ring_pairs = ring_data[0]['ring_pairs'] if ring_data else 0
        
        return {
            "status": "success",
            "message": "Fraud markers added to database",
            "changes": {
                "known_fraud_accounts": 10,
                "fraud_rings_created": 3,
                "total_known_fraud_in_db": known_fraud_count,
                "fraud_account_pairs_with_shared_devices": ring_pairs
            }
        }
    
    except Exception as e:
        logger.error(f"Failed to add fraud markers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add fraud markers: {str(e)}")


@router.get("/diagnose-transactions")
async def diagnose_transactions():
    """
    Diagnose transaction data in the database.
    """
    try:
        driver = get_driver()
        results = {}
        
        # Check TRANSACTED_WITH relationships
        try:
            async with driver.session() as session:
                # Count all TRANSACTED_WITH relationships
                result = await session.run(
                    "MATCH ()-[t:TRANSACTED_WITH]->() RETURN count(t) AS total"
                )
                data = await result.data()
                txn_count = data[0]['total'] if data else 0
                
                # Sample transactions
                sample_result = await session.run("""
                MATCH (a1:Account)-[t:TRANSACTED_WITH]->(a2:Account)
                RETURN a1.account_id, a2.account_id, t.amount, t.transaction_id LIMIT 10
                """)
                samples = await sample_result.data()
                
            results['transacted_with_relationships'] = {
                "total_count": txn_count,
                "sample_count": len(samples),
                "samples": [
                    {
                        "from": s.get('a1.account_id'),
                        "to": s.get('a2.account_id'),
                        "amount": s.get('t.amount'),
                        "transaction_id": s.get('t.transaction_id')
                    }
                    for s in samples
                ]
            }
        except Exception as e:
            logger.warning(f"Transaction check failed: {e}")
            results['transacted_with_relationships'] = {"error": str(e)}
        
        # Check 3-hop money-mule patterns
        try:
            async with driver.session() as session:
                # Count 3-account chains
                result = await session.run("""
                MATCH (a1:Account)-[:TRANSACTED_WITH]-(a2:Account)-[:TRANSACTED_WITH]-(a3:Account)
                RETURN count(*) AS total
                """)
                data = await result.data()
                chain_count = data[0]['total'] if data else 0
                
                # Count chains involving known-fraud accounts
                result = await session.run("""
                MATCH (a1:Account)-[:TRANSACTED_WITH]-(a2:Account)-[:TRANSACTED_WITH]-(a3:Account)
                WHERE a1.is_known_fraud = true OR a2.is_known_fraud = true OR a3.is_known_fraud = true
                RETURN count(*) AS total
                """)
                data = await result.data()
                fraud_chain_count = data[0]['total'] if data else 0
                
            results['money_mule_chains'] = {
                "total_3_hop_chains": chain_count,
                "chains_with_known_fraud": fraud_chain_count
            }
        except Exception as e:
            logger.warning(f"Chain check failed: {e}")
            results['money_mule_chains'] = {"error": str(e)}
        
        # Check account properties
        try:
            async with driver.session() as session:
                # Check is_known_fraud property
                result = await session.run(
                    "MATCH (a:Account) WHERE a.is_known_fraud = true RETURN count(a) AS total"
                )
                data = await result.data()
                known_fraud_with_property = data[0]['total'] if data else 0
                
                # Check isKnownFraud property (camelCase)
                result = await session.run(
                    "MATCH (a:Account) WHERE a.isKnownFraud = true RETURN count(a) AS total"
                )
                data = await result.data()
                known_fraud_camel = data[0]['total'] if data else 0
                
            results['account_properties'] = {
                "is_known_fraud_snake_case": known_fraud_with_property,
                "isKnownFraud_camel_case": known_fraud_camel
            }
        except Exception as e:
            logger.warning(f"Account property check failed: {e}")
            results['account_properties'] = {"error": str(e)}
        
        return {
            "status": "diagnostic_complete",
            "diagnosis": results
        }
    
    except Exception as e:
        logger.error(f"Diagnostic failed: {e}")
        raise HTTPException(status_code=500, detail=f"Diagnostic failed: {str(e)}")


@router.post("/generate-transactions")
async def generate_transactions():
    """
    Generate transaction relationships (TRANSACTED_WITH) in the database.
    Creates money-mule chains anchored on known-fraud accounts.
    Does NOT delete existing data - only adds transactions.
    """
    try:
        driver = get_driver()
        transactions_created = 0
        
        async with driver.session() as session:
            # Get list of known-fraud accounts
            fraud_accounts_result = await session.run(
                "MATCH (a:Account) WHERE a.is_known_fraud = true RETURN a.account_id"
            )
            fraud_accounts = [r['a.account_id'] for r in await fraud_accounts_result.data()]
            
            if not fraud_accounts:
                return {
                    "status": "error",
                    "message": "No known-fraud accounts found in database",
                    "transactions_created": 0
                }
            
            # Get list of all suspicious accounts
            susp_accounts_result = await session.run(
                "MATCH (a:Account) WHERE a.account_id LIKE 'SUSP_%' RETURN a.account_id"
            )
            susp_accounts = [r['a.account_id'] for r in await susp_accounts_result.data()]
            
            # Create deliberate money-mule chains: FRAUD -> SUSP -> SUSP -> FRAUD
            random.seed(42)
            
            for i, fraud_source in enumerate(fraud_accounts[:50]):  # Use first 50 fraud accounts
                try:
                    # Pick 2 suspicious accounts for the chain
                    if len(susp_accounts) >= 2:
                        chain = random.sample(susp_accounts, 2)
                        fraud_dest = random.choice([a for a in fraud_accounts if a != fraud_source])
                        
                        # Create 3-hop chain: fraud_source -> chain[0] -> chain[1] -> fraud_dest
                        hops = [
                            (fraud_source, chain[0], 50000 - (i * 100)),
                            (chain[0], chain[1], 40000 - (i * 100)),
                            (chain[1], fraud_dest, 30000 - (i * 100))
                        ]
                        
                        for from_acc, to_acc, amount in hops:
                            txn_id = f"TXN_{transactions_created:06d}"
                            await session.run("""
                            MATCH (a1:Account {account_id: $from_id})
                            MATCH (a2:Account {account_id: $to_id})
                            CREATE (a1)-[:TRANSACTED_WITH {
                                transaction_id: $txn_id,
                                amount: $amount,
                                timestamp: datetime()
                            }]->(a2)
                            """, {
                                "from_id": from_acc,
                                "to_id": to_acc,
                                "txn_id": txn_id,
                                "amount": amount
                            })
                            transactions_created += 1
                except Exception as e:
                    logger.warning(f"Failed to create chain starting at {fraud_source}: {e}")
                    continue
            
            # Create additional noise transactions (non-mule chains)
            all_accounts_result = await session.run(
                "MATCH (a:Account) RETURN a.account_id LIMIT 500"
            )
            all_accounts = [r['a.account_id'] for r in await all_accounts_result.data()]
            
            for i in range(100):
                try:
                    from_acc = random.choice(all_accounts)
                    to_acc = random.choice([a for a in all_accounts if a != from_acc])
                    amount = random.randint(1000, 10000)
                    txn_id = f"TXN_{transactions_created:06d}"
                    
                    await session.run("""
                    MATCH (a1:Account {account_id: $from_id})
                    MATCH (a2:Account {account_id: $to_id})
                    CREATE (a1)-[:TRANSACTED_WITH {
                        transaction_id: $txn_id,
                        amount: $amount,
                        timestamp: datetime()
                    }]->(a2)
                    """, {
                        "from_id": from_acc,
                        "to_id": to_acc,
                        "txn_id": txn_id,
                        "amount": amount
                    })
                    transactions_created += 1
                except Exception as e:
                    logger.warning(f"Failed to create noise transaction {i}: {e}")
                    continue
        
        return {
            "status": "success",
            "message": f"Generated {transactions_created} transaction relationships",
            "transactions_created": transactions_created,
            "details": {
                "money_mule_chains": min(150, transactions_created // 3),
                "noise_transactions": transactions_created % 3
            }
        }
    
    except Exception as e:
        logger.error(f"Failed to generate transactions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate transactions: {str(e)}")

