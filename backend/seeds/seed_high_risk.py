#!/usr/bin/env python
"""
High Risk Account Seed Generator - Adds HIGH risk accounts to existing database
Does NOT delete existing data - only adds new HIGH risk accounts with patterns
"""
import asyncio
import os
import random
from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase

async def seed_high_risk():
    """Create HIGH risk accounts and associate them with transactions"""
    load_dotenv()
    
    uri = os.getenv("COGNODB_URI")
    user = os.getenv("COGNODB_USERNAME")
    password = os.getenv("COGNODB_PASSWORD")
    
    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    
    try:
        async with driver.session() as session:
            print("[1/4] Creating 50 HIGH risk accounts...")
            
            # Create 50 high-risk accounts
            for i in range(1, 51):
                await session.run("""
                CREATE (a:Account {
                    account_id: 'HIGH_' + toString($i),
                    display_name: 'High Risk Account ' + toString($i),
                    email: 'highrisk' + toString($i) + '@suspicious.com',
                    status: 'ACTIVE',
                    risk_level: 'HIGH',
                    is_known_fraud: false,
                    risk_score: 75.0,
                    created_at: datetime()
                })
                """, {"i": str(i).zfill(5)})
            
            print("  OK - Created 50 HIGH risk accounts")
            
            print("[2/4] Creating shared devices between HIGH risk accounts...")
            
            # Create devices and connect HIGH risk accounts to create patterns
            for dev_num in range(1, 6):
                await session.run("""
                MERGE (d:Device {device_id: 'DEVICE_HIGH_' + toString($dev)})
                ON CREATE SET d.device_name = 'High Risk Device ' + toString($dev)
                """, {"dev": str(dev_num).zfill(4)})
                
                # Connect 3 high-risk accounts to each device
                await session.run("""
                MATCH (d:Device {device_id: 'DEVICE_HIGH_' + toString($dev)})
                MATCH (h1:Account {account_id: 'HIGH_' + toString($h1_num)})
                MATCH (h2:Account {account_id: 'HIGH_' + toString($h2_num)})
                MATCH (h3:Account {account_id: 'HIGH_' + toString($h3_num)})
                CREATE (h1)-[:USES_DEVICE]->(d)
                CREATE (h2)-[:USES_DEVICE]->(d)
                CREATE (h3)-[:USES_DEVICE]->(d)
                """, {"dev": str(dev_num).zfill(4), 
                      "h1_num": str(dev_num).zfill(5),
                      "h2_num": str((dev_num + 10) % 50 + 1).zfill(5),
                      "h3_num": str((dev_num + 20) % 50 + 1).zfill(5)})
            
            print("  OK - Created device patterns for fraud detection")
            
            print("[3/4] Linking HIGH risk accounts to known fraud accounts...")
            
            # Create shared IPs between HIGH risk and FRAUD accounts
            for i in range(1, 11):
                await session.run("""
                MERGE (ip:IPAddress {ip_address: '192.168.100.' + toString($i)})
                ON CREATE SET ip.location = 'Suspicious Location ' + toString($i)
                WITH ip
                MATCH (f:Account {account_id: 'FRAUD_' + toString($f_num)})
                MATCH (h:Account {account_id: 'HIGH_' + toString($h_num)})
                CREATE (f)-[:ACCESSED_FROM_IP]->(ip)
                CREATE (h)-[:ACCESSED_FROM_IP]->(ip)
                """, {"i": str(i).zfill(2),
                      "f_num": str(i).zfill(5),
                      "h_num": str((i % 50) + 1).zfill(5)})
            
            print("  OK - Linked HIGH risk to known fraud accounts via shared IPs")
            
            print("[4/4] Creating transactions from HIGH risk accounts...")
            
            # Create transactions involving HIGH risk accounts
            txn_id = 1000  # Start high to avoid conflicts
            random.seed(42)
            
            # Create 100 transactions: HIGH -> SUSP -> HIGH patterns
            for chain_num in range(1, 51):
                high_src = f"HIGH_{(chain_num % 50 + 1):05d}"
                high_dst = f"HIGH_{((chain_num + 25) % 50 + 1):05d}"
                susp_mid = f"SUSP_{(chain_num % 40 + 1):05d}"
                
                # Create 2-hop chain: HIGH -> SUSP -> HIGH
                amounts = [75000 - (chain_num * 100), 65000 - (chain_num * 100)]
                chain_hops = [
                    (high_src, susp_mid, amounts[0]),
                    (susp_mid, high_dst, amounts[1])
                ]
                
                for from_id, to_id, amount in chain_hops:
                    try:
                        await session.run("""
                        MATCH (a1:Account {account_id: $from_id})
                        MATCH (a2:Account {account_id: $to_id})
                        CREATE (a1)-[:TRANSACTED_WITH {
                            transaction_id: 'TXN_HIGH_' + toString($txn_id),
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
            
            # Create transactions between HIGH risk accounts and normal accounts
            for i in range(50):
                high_acc = f"HIGH_{(i % 50 + 1):05d}"
                normal_acc = f"ACC_{(i + 1):05d}"
                
                try:
                    await session.run("""
                    MATCH (a1:Account {account_id: $high_id})
                    MATCH (a2:Account {account_id: $normal_id})
                    CREATE (a1)-[:TRANSACTED_WITH {
                        transaction_id: 'TXN_HIGH_' + toString($txn_id),
                        amount: $amount,
                        timestamp: datetime()
                    }]->(a2)
                    """, {
                        "high_id": high_acc,
                        "normal_id": normal_acc,
                        "txn_id": str(txn_id).zfill(6),
                        "amount": random.randint(10000, 50000)
                    })
                    txn_id += 1
                except Exception as e:
                    print(f"    Warning: Failed transaction {txn_id}: {e}")
                    continue
            
            print(f"  OK - Created {txn_id - 1000} HIGH risk transactions")
            
        print("\n" + "="*60)
        print("SUCCESS: High Risk Account Seed Data Generated!")
        print("="*60)
        print("\nDatabase now contains:")
        print("  * 50 HIGH risk accounts (risk_level = 'HIGH', risk_score = 75.0)")
        print("  * 5 shared devices connecting HIGH risk accounts")
        print("  * 10 shared IPs between HIGH and FRAUD accounts")
        print("  * 150+ transactions from/to HIGH risk accounts")
        print("\nThese accounts will be detected as high-risk in fraud analysis")
        
    finally:
        await driver.close()

if __name__ == "__main__":
    asyncio.run(seed_high_risk())
