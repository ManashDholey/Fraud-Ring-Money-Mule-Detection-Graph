#!/usr/bin/env python3
"""
Quick script to add fraud markers and fraud ring relationships to existing accounts.
Marks some accounts as known fraud and creates shared device/IP relationships.
"""

from dotenv import load_dotenv
import asyncio
from neo4j import AsyncGraphDatabase
import os

load_dotenv()

async def add_fraud_rings():
    """Add fraud markers and relationships to create detectable fraud rings."""
    
    driver = AsyncGraphDatabase.driver(
        os.getenv("COGNODB_URI"),
        auth=(os.getenv("COGNODB_USERNAME"), os.getenv("COGNODB_PASSWORD"))
    )
    
    try:
        async with driver.session() as session:
            print("Adding fraud markers and relationships...\n")
            
            # Step 1: Mark some accounts as known fraud
            # Select accounts ACC_00001 through ACC_00010 as known fraud
            for i in range(1, 11):
                acc_id = f"ACC_{i:05d}"
                result = await session.run("""
                    MATCH (a:Account {account_id: $id})
                    SET a.is_known_fraud = true,
                        a.risk_level = 'CRITICAL',
                        a.risk_score = 95.0
                    RETURN a.account_id
                """, {"id": acc_id})
                records = await result.data()
                if records:
                    print(f"✓ Marked {acc_id} as known fraud")
            
            # Step 2: Create devices shared between fraud accounts (fraud ring 1)
            # ACC_00001 and ACC_00002 share a device
            result = await session.run("""
                MATCH (a1:Account {account_id: 'ACC_00001'})
                MATCH (a2:Account {account_id: 'ACC_00002'})
                CREATE (d:Device {device_id: 'DEVICE_FRAUD_001', fingerprint: 'abc123xyz'})
                CREATE (a1)-[:USES_DEVICE]->(d)
                CREATE (a2)-[:USES_DEVICE]->(d)
                RETURN d.device_id
            """)
            records = await result.data()
            if records:
                print(f"✓ Created shared device between ACC_00001 and ACC_00002")
            
            # Step 3: Create another shared device (fraud ring 1, stronger connection)
            result = await session.run("""
                MATCH (a1:Account {account_id: 'ACC_00001'})
                MATCH (a2:Account {account_id: 'ACC_00002'})
                CREATE (ip:IPAddress {ip: '192.168.1.100', country: 'US'})
                CREATE (a1)-[:ACCESSED_FROM_IP]->(ip)
                CREATE (a2)-[:ACCESSED_FROM_IP]->(ip)
                RETURN ip.ip
            """)
            records = await result.data()
            if records:
                print(f"✓ Created shared IP between ACC_00001 and ACC_00002")
            
            # Step 4: Create fraud ring 2 (ACC_00003, ACC_00004, ACC_00005)
            result = await session.run("""
                MATCH (a1:Account {account_id: 'ACC_00003'})
                MATCH (a2:Account {account_id: 'ACC_00004'})
                MATCH (a3:Account {account_id: 'ACC_00005'})
                CREATE (d:Device {device_id: 'DEVICE_FRAUD_002', fingerprint: 'def456uvw'})
                CREATE (a1)-[:USES_DEVICE]->(d)
                CREATE (a2)-[:USES_DEVICE]->(d)
                CREATE (a3)-[:USES_DEVICE]->(d)
                RETURN d.device_id
            """)
            records = await result.data()
            if records:
                print(f"✓ Created shared device for fraud ring 2 (ACC_00003, ACC_00004, ACC_00005)")
            
            # Step 5: Create fraud ring 3 (ACC_00006, ACC_00007)
            result = await session.run("""
                MATCH (a1:Account {account_id: 'ACC_00006'})
                MATCH (a2:Account {account_id: 'ACC_00007'})
                CREATE (d:Device {device_id: 'DEVICE_FRAUD_003', fingerprint: 'ghi789rst'})
                CREATE (a1)-[:USES_DEVICE]->(d)
                CREATE (a2)-[:USES_DEVICE]->(d)
                CREATE (ip:IPAddress {ip: '10.0.0.50', country: 'RU'})
                CREATE (a1)-[:ACCESSED_FROM_IP]->(ip)
                CREATE (a2)-[:ACCESSED_FROM_IP]->(ip)
                RETURN d.device_id
            """)
            records = await result.data()
            if records:
                print(f"✓ Created shared device/IP for fraud ring 3 (ACC_00006, ACC_00007)")
            
            # Step 6: Verify results
            print("\n=== VERIFICATION ===")
            result = await session.run("""
                MATCH (a:Account) 
                WHERE a.is_known_fraud = true 
                RETURN count(a) as count
            """)
            records = await result.data()
            print(f"✓ Known fraud accounts: {records[0]['count'] if records else 0}")
            
            result = await session.run("""
                MATCH (a1:Account)-[:USES_DEVICE]->(d:Device)<-[:USES_DEVICE]-(a2:Account)
                WHERE a1.account_id < a2.account_id AND a1.is_known_fraud = true
                RETURN count(*) as count
            """)
            records = await result.data()
            print(f"✓ Fraud account pairs with shared devices: {records[0]['count'] if records else 0}")
            
            print("\n✅ Fraud rings should now be detectable!")
    
    finally:
        await driver.close()

if __name__ == "__main__":
    asyncio.run(add_fraud_rings())
