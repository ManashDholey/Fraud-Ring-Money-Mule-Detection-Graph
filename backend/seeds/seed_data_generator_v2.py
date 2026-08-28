"""
Production-grade Seed Data Generator - Fixed Version
Generates 10,000 accounts with proper connection pool management and recovery.
"""

import asyncio
import os
import random
import sys
from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase

class ProductionSeedGenerator:
    """Production-grade seed generator with connection pool management."""

    def __init__(self):
        """Initialize async graph database connection."""
        load_dotenv()
        
        uri = os.getenv("COGNODB_URI")
        user = os.getenv("COGNODB_USERNAME")
        password = os.getenv("COGNODB_PASSWORD")
        
        if not all([uri, user, password]):
            raise ValueError("Missing required environment variables")
        
        self.driver = AsyncGraphDatabase.driver(
            uri, 
            auth=(user, password),
            connection_timeout=30.0
        )
        self.random = random.Random(42)

    async def close(self):
        """Close the database connection."""
        await self.driver.close()

    async def execute_with_retry(self, query, params, max_retries=5, batch_num=0):
        """Execute query with exponential backoff and fresh session each time."""
        for attempt in range(max_retries):
            try:
                async with self.driver.session() as session:
                    result = await session.run(query, params)
                    await result.consume()  # Ensure query completes
                    return True
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"  ERROR (batch {batch_num}): {str(e)[:100]}")
                    raise
                wait_time = 2 ** attempt
                print(f"  Retry {attempt + 1}/{max_retries} in {wait_time}s (batch {batch_num})...")
                await asyncio.sleep(wait_time)
        return False

    async def clear_database(self):
        """Clear all existing data."""
        print("[1/6] Clearing database...")
        async with self.driver.session() as session:
            await session.run("MATCH (n) DETACH DELETE n")
        print("  OK")

    async def create_accounts(self):
        """Create 10,000 accounts with proper batching."""
        print("[2/6] Creating 10,000 accounts...")
        
        accounts_data = []
        
        # 7,000 normal accounts
        for i in range(1, 7001):
            accounts_data.append({
                "id": f"ACC_{i:05d}",
                "name": f"User {i}",
                "email": f"user{i}@example.com",
                "status": "ACTIVE",
                "risk_level": "LOW",
                "is_known_fraud": False
            })
        
        # 300 known fraud accounts  
        for i in range(1, 301):
            accounts_data.append({
                "id": f"FRAUD_{i:05d}",
                "name": f"Fraud Operator {i}",
                "email": f"fraud{i}@malicious.com",
                "status": "SUSPENDED",
                "risk_level": "CRITICAL",
                "is_known_fraud": True
            })
        
        # 2,700 suspicious accounts
        for i in range(1, 2701):
            accounts_data.append({
                "id": f"SUSP_{i:05d}",
                "name": f"Suspicious User {i}",
                "email": f"suspect{i}@example.com",
                "status": "ACTIVE",
                "risk_level": "MEDIUM",
                "is_known_fraud": False
            })
        
        # Insert in small batches with fresh sessions
        batch_size = 10
        total_batches = len(accounts_data) // batch_size + (1 if len(accounts_data) % batch_size else 0)
        
        for batch_num, batch_start in enumerate(range(0, len(accounts_data), batch_size), 1):
            batch = accounts_data[batch_start:batch_start + batch_size]
            
            for acc in batch:
                query = """
                CREATE (a:Account {
                    account_id: $id,
                    name: $name,
                    email: $email,
                    status: $status,
                    risk_level: $risk_level,
                    is_known_fraud: $is_known_fraud,
                    created_at: datetime()
                })
                """
                await self.execute_with_retry(query, acc, batch_num=batch_num)
            
            print(f"  Batch {batch_num}/{total_batches}: {batch_num * batch_size}/{len(accounts_data)}")
            await asyncio.sleep(0.2)  # Longer delay between batches
        
        print(f"  OK - Created {len(accounts_data)} accounts")

    async def create_cards(self):
        """Create payment cards."""
        print("[3/6] Creating 10,000 payment cards...")
        
        cards_data = []
        for i in range(1, 10001):
            if i <= 7000:
                account_id = f"ACC_{i:05d}"
            elif i <= 7300:
                account_id = f"FRAUD_{((i - 7000) % 300) + 1:05d}"
            else:
                account_id = f"SUSP_{((i - 7300) % 2700) + 1:05d}"
            
            cards_data.append({
                "account_id": account_id,
                "card_number": f"4532-{self.random.randint(1000, 9999)}-XXXX",
                "card_type": self.random.choice(["VISA", "MASTERCARD", "AMEX"])
            })
        
        batch_size = 10
        total_batches = len(cards_data) // batch_size + (1 if len(cards_data) % batch_size else 0)
        
        for batch_num, batch_start in enumerate(range(0, len(cards_data), batch_size), 1):
            batch = cards_data[batch_start:batch_start + batch_size]
            
            for card in batch:
                query = """
                MATCH (a:Account {account_id: $account_id})
                CREATE (c:Card {
                    card_number: $card_number,
                    card_type: $card_type,
                    status: 'ACTIVE',
                    created_at: datetime()
                })
                CREATE (a)-[:HAS_CARD]->(c)
                """
                await self.execute_with_retry(query, card, batch_num=batch_num)
            
            if batch_num % 50 == 0:
                print(f"  Batch {batch_num}/{total_batches}: {batch_num * batch_size}/{len(cards_data)}")
            await asyncio.sleep(0.2)
        
        print(f"  OK - Created {len(cards_data)} cards")

    async def create_devices(self):
        """Create shared devices."""
        print("[4/6] Creating 500 devices...")
        
        device_id = 1
        device_ops = []
        
        # Suspicious devices
        for i in range(1, 301):
            accounts = self._pick_random_accounts(self.random.randint(2, 5))
            device_ops.append((device_id, accounts, f"Device_Suspicious_{i}"))
            device_id += 1
        
        # Normal devices
        for i in range(1, 201):
            count = 2 if self.random.random() < 0.3 else 1
            accounts = self._pick_random_accounts(count)
            device_ops.append((device_id, accounts, f"Device_Normal_{i}"))
            device_id += 1
        
        batch_size = 5
        total_batches = len(device_ops) // batch_size + (1 if len(device_ops) % batch_size else 0)
        
        for batch_num, batch_start in enumerate(range(0, len(device_ops), batch_size), 1):
            batch = device_ops[batch_start:batch_start + batch_size]
            
            for dev_id, accounts, device_name in batch:
                # Create device
                query1 = """
                MERGE (d:Device {device_id: $device_id, device_name: $device_name})
                ON CREATE SET d.created_at = datetime()
                """
                await self.execute_with_retry(query1, {
                    "device_id": f"DEV_{dev_id:04d}",
                    "device_name": device_name
                }, batch_num=batch_num)
                
                # Connect accounts
                for account_id in accounts:
                    query2 = """
                    MATCH (a:Account {account_id: $account_id})
                    MATCH (d:Device {device_id: $device_id})
                    CREATE (a)-[:USES_DEVICE]->(d)
                    """
                    await self.execute_with_retry(query2, {
                        "account_id": account_id,
                        "device_id": f"DEV_{dev_id:04d}"
                    }, batch_num=batch_num)
            
            if batch_num % 20 == 0:
                print(f"  Batch {batch_num}/{total_batches}")
            await asyncio.sleep(0.2)
        
        print(f"  OK - Created {len(device_ops)} devices")

    async def create_phones(self):
        """Create shared phone numbers."""
        print("[5/6] Creating 800 phone numbers...")
        
        phone_id = 1
        phone_ops = []
        
        # Suspicious shared phones
        for i in range(1, 401):
            accounts = self._pick_random_accounts(self.random.randint(2, 4))
            phone_ops.append((phone_id, accounts, f"+1-555-{phone_id:05d}"))
            phone_id += 1
        
        # Individual phones
        for i in range(1, 401):
            accounts = self._pick_random_accounts(1)
            phone_ops.append((phone_id, accounts, f"+1-555-{phone_id:05d}"))
            phone_id += 1
        
        batch_size = 10
        total_batches = len(phone_ops) // batch_size + (1 if len(phone_ops) % batch_size else 0)
        
        for batch_num, batch_start in enumerate(range(0, len(phone_ops), batch_size), 1):
            batch = phone_ops[batch_start:batch_start + batch_size]
            
            for ph_id, accounts, phone_number in batch:
                # Create phone
                query1 = """
                MERGE (p:PhoneNumber {phone_number: $phone_number})
                ON CREATE SET p.created_at = datetime()
                """
                await self.execute_with_retry(query1, {"phone_number": phone_number}, batch_num=batch_num)
                
                # Connect accounts
                for account_id in accounts:
                    query2 = """
                    MATCH (a:Account {account_id: $account_id})
                    MATCH (p:PhoneNumber {phone_number: $phone_number})
                    CREATE (a)-[:HAS_PHONE]->(p)
                    """
                    await self.execute_with_retry(query2, {
                        "account_id": account_id,
                        "phone_number": phone_number
                    }, batch_num=batch_num)
            
            if batch_num % 10 == 0:
                print(f"  Batch {batch_num}/{total_batches}")
            await asyncio.sleep(0.2)
        
        print(f"  OK - Created {len(phone_ops)} phone numbers")

    async def create_ips(self):
        """Create shared IP addresses."""
        print("[6/6] Creating 600 IP addresses...")
        
        ip_id = 1
        ip_ops = []
        
        # Suspicious shared IPs
        for i in range(1, 301):
            accounts = self._pick_random_accounts(self.random.randint(2, 5))
            octet = (ip_id // 256) + 1
            host = ip_id % 256
            ip_ops.append((ip_id, accounts, f"192.168.{octet}.{host}"))
            ip_id += 1
        
        # Individual IPs
        for i in range(1, 301):
            accounts = self._pick_random_accounts(1)
            octet = (ip_id // 256) + 1
            host = ip_id % 256
            ip_ops.append((ip_id, accounts, f"192.168.{octet}.{host}"))
            ip_id += 1
        
        batch_size = 10
        total_batches = len(ip_ops) // batch_size + (1 if len(ip_ops) % batch_size else 0)
        
        for batch_num, batch_start in enumerate(range(0, len(ip_ops), batch_size), 1):
            batch = ip_ops[batch_start:batch_start + batch_size]
            
            for ip_num, accounts, ip_address in batch:
                # Create IP
                query1 = """
                MERGE (ip:IPAddress {ip_address: $ip_address})
                ON CREATE SET ip.created_at = datetime()
                """
                await self.execute_with_retry(query1, {"ip_address": ip_address}, batch_num=batch_num)
                
                # Connect accounts
                for account_id in accounts:
                    query2 = """
                    MATCH (a:Account {account_id: $account_id})
                    MATCH (ip:IPAddress {ip_address: $ip_address})
                    CREATE (a)-[:ACCESSED_FROM_IP]->(ip)
                    """
                    await self.execute_with_retry(query2, {
                        "account_id": account_id,
                        "ip_address": ip_address
                    }, batch_num=batch_num)
            
            if batch_num % 10 == 0:
                print(f"  Batch {batch_num}/{total_batches}")
            await asyncio.sleep(0.2)
        
        print(f"  OK - Created {len(ip_ops)} IP addresses")

    async def create_transactions(self):
        """Create transaction relationships (deferred to next phase)."""
        print("[SKIP] Transactions deferred (Phase 2)")
        print("  Transactions will be added in Phase 2 after verification")

    def _pick_random_accounts(self, count):
        """Pick random account IDs."""
        all_accounts = (
            [f"ACC_{i:05d}" for i in range(1, 7001)] +
            [f"FRAUD_{i:05d}" for i in range(1, 301)] +
            [f"SUSP_{i:05d}" for i in range(1, 2701)]
        )
        return self.random.sample(all_accounts, min(count, len(all_accounts)))

    async def generate_all(self):
        """Generate complete seed dataset."""
        print("\n" + "=" * 60)
        print("PRODUCTION SEED DATA GENERATOR - Phase 1")
        print("=" * 60 + "\n")
        
        await self.clear_database()
        await self.create_accounts()
        await self.create_cards()
        await self.create_devices()
        await self.create_phones()
        await self.create_ips()
        await self.create_transactions()
        
        print("\n" + "=" * 60)
        print("Phase 1 Complete!")
        print("=" * 60 + "\n")

async def main():
    """Entry point."""
    generator = ProductionSeedGenerator()
    try:
        await generator.generate_all()
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        sys.exit(1)
    finally:
        await generator.close()

if __name__ == "__main__":
    asyncio.run(main())
