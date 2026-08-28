"""
Simple service to add fraud markers to existing accounts.
"""

from dotenv import load_dotenv
import asyncio
import logging

logger = logging.getLogger(__name__)

# Load env before importing db
load_dotenv()

from dbConfig.db_async import get_driver

async def add_fraud_markers():
    """Add fraud markers to a sample of existing accounts."""
    
    driver = get_driver()
    
    try:
        async with driver.session() as session:
            print("Adding fraud markers to existing accounts...\n")
            
            # Mark accounts ACC_00001 through ACC_00010 as known fraud
            for i in range(1, 11):
                acc_id = f"ACC_{i:05d}"
                result = await session.run("""
                    MATCH (a:Account {account_id: $id})
                    SET a.is_known_fraud = true,
                        a.risk_level = 'CRITICAL',
                        a.risk_score = 95.0
                    RETURN a.account_id as id
                """, {"id": acc_id})
                
                records = await result.data()
                if records:
                    print(f"✓ Marked {acc_id} as known fraud")
                else:
                    print(f"⚠ Account {acc_id} not found")
            
            # Create shared devices/IPs between fraud accounts
            print("\nCreating shared devices between fraud accounts...")
            
            # Fraud ring 1: ACC_00001 and ACC_00002 share a device and IP
            result = await session.run("""
                MATCH (a1:Account {account_id: 'ACC_00001'})
                MATCH (a2:Account {account_id: 'ACC_00002'})
                CREATE (d:Device {device_id: 'DEVICE_RING001', fingerprint: 'abc123xyz'})
                CREATE (a1)-[:USES_DEVICE]->(d)
                CREATE (a2)-[:USES_DEVICE]->(d)
                CREATE (ip:IPAddress {ip: '192.168.1.100', country: 'US'})
                CREATE (a1)-[:ACCESSED_FROM_IP]->(ip)
                CREATE (a2)-[:ACCESSED_FROM_IP]->(ip)
                RETURN d.device_id as device, ip.ip as ip_addr
            """)
            
            records = await result.data()
            if records:
                print(f"✓ Created shared device & IP for ring 1")
            
            # Fraud ring 2: ACC_00003, ACC_00004, ACC_00005 share a device
            result = await session.run("""
                MATCH (a1:Account {account_id: 'ACC_00003'})
                MATCH (a2:Account {account_id: 'ACC_00004'})
                MATCH (a3:Account {account_id: 'ACC_00005'})
                CREATE (d:Device {device_id: 'DEVICE_RING002', fingerprint: 'def456uvw'})
                CREATE (a1)-[:USES_DEVICE]->(d)
                CREATE (a2)-[:USES_DEVICE]->(d)
                CREATE (a3)-[:USES_DEVICE]->(d)
                RETURN d.device_id as device
            """)
            
            records = await result.data()
            if records:
                print(f"✓ Created shared device for ring 2")
            
            # Fraud ring 3: ACC_00006 and ACC_00007 share device and IP
            result = await session.run("""
                MATCH (a1:Account {account_id: 'ACC_00006'})
                MATCH (a2:Account {account_id: 'ACC_00007'})
                CREATE (d:Device {device_id: 'DEVICE_RING003', fingerprint: 'ghi789rst'})
                CREATE (a1)-[:USES_DEVICE]->(d)
                CREATE (a2)-[:USES_DEVICE]->(d)
                CREATE (ip:IPAddress {ip: '10.0.0.50', country: 'RU'})
                CREATE (a1)-[:ACCESSED_FROM_IP]->(ip)
                CREATE (a2)-[:ACCESSED_FROM_IP]->(ip)
                RETURN d.device_id as device
            """)
            
            records = await result.data()
            if records:
                print(f"✓ Created shared device & IP for ring 3")
            
            # Verification
            print("\n=== VERIFICATION ===")
            
            result = await session.run("""
                MATCH (a:Account) 
                WHERE a.is_known_fraud = true 
                RETURN count(a) as count
            """)
            records = await result.data()
            known_fraud_count = records[0]['count'] if records else 0
            print(f"Known fraud accounts: {known_fraud_count}")
            
            result = await session.run("""
                MATCH (a1:Account)-[:USES_DEVICE]->(d:Device)<-[:USES_DEVICE]-(a2:Account)
                WHERE a1.account_id < a2.account_id AND a1.is_known_fraud = true
                RETURN count(*) as count
            """)
            records = await result.data()
            ring_pairs = records[0]['count'] if records else 0
            print(f"Fraud account pairs with shared devices: {ring_pairs}")
            
            print("\n✅ Fraud rings should now be detectable!")
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(add_fraud_markers())
