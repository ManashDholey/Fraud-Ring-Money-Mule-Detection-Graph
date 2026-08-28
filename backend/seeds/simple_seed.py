#!/usr/bin/env python
"""
Ultra-simple direct seed generator - directly creates essential test data
"""
import asyncio
import os
import random
from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase

async def seed_database():
    """Create essential test data directly"""
    load_dotenv()
    
    uri = os.getenv("COGNODB_URI")
    user = os.getenv("COGNODB_USERNAME")
    password = os.getenv("COGNODB_PASSWORD")
    
    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    
    try:
        async with driver.session() as session:
            print("[1/3] Creating 100 test accounts...")
            
            # Create 10 fraud accounts
            for i in range(1, 11):
                await session.run("""
                CREATE (a:Account {
                    account_id: 'FRAUD_' + toString($i),
                    display_name: 'Fraud Account ' + toString($i),
                    email: 'fraud' + toString($i) + '@test.com',
                    status: 'SUSPENDED',
                    risk_level: 'CRITICAL',
                    is_known_fraud: true,
                    risk_score: 95.0,
                    created_at: datetime()
                })
                """, {"i": str(i).zfill(5)})
            
            # Create 40 suspicious accounts
            for i in range(1, 41):
                await session.run("""
                CREATE (a:Account {
                    account_id: 'SUSP_' + toString($i),
                    display_name: 'Suspicious Account ' + toString($i),
                    email: 'susp' + toString($i) + '@test.com',
                    status: 'ACTIVE',
                    risk_level: 'MEDIUM',
                    is_known_fraud: false,
                    risk_score: 50.0,
                    created_at: datetime()
                })
                """, {"i": str(i).zfill(5)})
            
            # Create 50 normal accounts
            for i in range(1, 51):
                await session.run("""
                CREATE (a:Account {
                    account_id: 'ACC_' + toString($i),
                    display_name: 'User Account ' + toString($i),
                    email: 'user' + toString($i) + '@test.com',
                    status: 'ACTIVE',
                    risk_level: 'LOW',
                    is_known_fraud: false,
                    risk_score: 0.0,
                    created_at: datetime()
                })
                """, {"i": str(i).zfill(5)})
            
            print("  OK - Created 100 accounts")
            
            print("[2/3] Creating shared devices for fraud rings...")
            
            # Create devices and connect fraud accounts
            for dev_num in range(1, 6):
                await session.run("""
                MERGE (d:Device {device_id: 'DEV_' + toString($dev)})
                ON CREATE SET d.device_name = 'Device ' + toString($dev)
                """, {"dev": str(dev_num).zfill(4)})
                
                # Connect 2 fraud accounts to each device
                await session.run("""
                MATCH (d:Device {device_id: 'DEV_' + toString($dev)})
                MATCH (f1:Account {account_id: 'FRAUD_' + toString($f1_num)})
                MATCH (f2:Account {account_id: 'FRAUD_' + toString($f2_num)})
                CREATE (f1)-[:USES_DEVICE]->(d)
                CREATE (f2)-[:USES_DEVICE]->(d)
                """, {"dev": str(dev_num).zfill(4), 
                      "f1_num": str(dev_num).zfill(5),
                      "f2_num": str((dev_num % 10) + 1).zfill(5)})
            
            print("  OK - Created fraud ring patterns")
            
            print("[3/3] Creating TRANSACTED_WITH relationships...")
            
            # Create 100+ money-mule chains: FRAUD -> SUSP -> SUSP -> FRAUD
            txn_id = 1
            random.seed(42)
            
            for chain_num in range(1, 51):
                # Get fraud source and destination
                fraud_src = f"FRAUD_{(chain_num % 10 + 1):05d}"
                fraud_dst = f"FRAUD_{((chain_num + 5) % 10 + 1):05d}"
                susp_mid1 = f"SUSP_{(chain_num * 2 % 40 + 1):05d}"
                susp_mid2 = f"SUSP_{((chain_num * 2 + 1) % 40 + 1):05d}"
                
                # Create 3-hop chain
                amounts = [50000 - (chain_num * 100), 40000 - (chain_num * 100), 30000 - (chain_num * 100)]
                chain_hops = [
                    (fraud_src, susp_mid1, amounts[0]),
                    (susp_mid1, susp_mid2, amounts[1]),
                    (susp_mid2, fraud_dst, amounts[2])
                ]
                
                for from_id, to_id, amount in chain_hops:
                    try:
                        await session.run("""
                        MATCH (a1:Account {account_id: $from_id})
                        MATCH (a2:Account {account_id: $to_id})
                        CREATE (a1)-[:TRANSACTED_WITH {
                            transaction_id: 'TXN_' + toString($txn_id),
                            amount: $amount,
                            timestamp: datetime()
                        }]->(a2)
                        """, {
                            "from_id": from_id,
                            "to_id": to_id,
                            "txn_id": str(txn_id).zfill(6),
                            "amount": amount
                        })
                        txn_id += 1
                    except Exception as e:
                        print(f"    Warning: Failed transaction {txn_id}: {e}")
                        continue
            
            # Add 50 random noise transactions
            for i in range(50):
                acc_ids = [f"ACC_{(i+1):05d}", f"SUSP_{((i*3) % 40 + 1):05d}"]
                try:
                    await session.run("""
                    MATCH (a1:Account {account_id: $from_id})
                    MATCH (a2:Account {account_id: $to_id})
                    CREATE (a1)-[:TRANSACTED_WITH {
                        transaction_id: 'TXN_' + toString($txn_id),
                        amount: $amount,
                        timestamp: datetime()
                    }]->(a2)
                    """, {
                        "from_id": acc_ids[0],
                        "to_id": acc_ids[1],
                        "txn_id": str(txn_id).zfill(6),
                        "amount": random.randint(1000, 10000)
                    })
                    txn_id += 1
                except Exception as e:
                    print(f"    Warning: Failed noise transaction {txn_id}: {e}")
                    continue
            
            print(f"  OK - Created {txn_id - 1} transactions")
            
        print("\n" + "="*60)
        print("SUCCESS: Seed data generated!")
        print("="*60)
        print("\nDatabase now contains:")
        print("  * 100 accounts (10 fraud, 40 suspicious, 50 normal)")
        print("  * Fraud ring patterns (shared devices)")
        print("  * 150+ money-mule transactions")
        
    finally:
        await driver.close()

if __name__ == "__main__":
    asyncio.run(seed_database())
