"""
Ultra-fast bulk seed data generator using batch Cypher statements.
"""

import asyncio
import os
import random
from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase

class FastBulkSeedGenerator:
    """Fast bulk seed generator - creates all items in minimal queries."""

    def __init__(self):
        """Initialize connection."""
        load_dotenv()
        
        uri = os.getenv("COGNODB_URI")
        user = os.getenv("COGNODB_USERNAME")
        password = os.getenv("COGNODB_PASSWORD")
        
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
        self.random = random.Random(42)

    async def close(self):
        """Close connection."""
        await self.driver.close()

    async def execute_query(self, query, params, description=""):
        """Execute single query with error handling."""
        try:
            async with self.driver.session() as session:
                result = await session.run(query, params)
                await result.consume()
            if description:
                print(f"  OK: {description}")
            return True
        except Exception as e:
            print(f"  ERROR: {description} - {str(e)[:80]}")
            raise

    async def clear_database(self):
        """Clear all existing data."""
        print("[1/6] Clearing database...")
        async with self.driver.session() as session:
            await session.run("MATCH (n) DETACH DELETE n")
        print("  OK")

    async def create_accounts_bulk(self):
        """Create all 10,000 accounts in bulk."""
        print("[2/6] Creating 10,000 accounts (bulk)...")
        
        # Create in large batches using Cypher UNWIND
        batch_size = 500
        all_accounts = []
        
        # 7,000 normal
        for i in range(1, 7001):
            all_accounts.append({
                "id": f"ACC_{i:05d}",
                "name": f"User {i}",
                "email": f"user{i}@example.com",
                "status": "ACTIVE",
                "risk_level": "LOW",
                "is_known_fraud": False
            })
        
        # 300 fraud
        for i in range(1, 301):
            all_accounts.append({
                "id": f"FRAUD_{i:05d}",
                "name": f"Fraud {i}",
                "email": f"fraud{i}@malicious.com",
                "status": "SUSPENDED",
                "risk_level": "CRITICAL",
                "is_known_fraud": True
            })
        
        # 2,700 suspicious
        for i in range(1, 2701):
            all_accounts.append({
                "id": f"SUSP_{i:05d}",
                "name": f"Suspect {i}",
                "email": f"suspect{i}@example.com",
                "status": "ACTIVE",
                "risk_level": "MEDIUM",
                "is_known_fraud": False
            })
        
        # Bulk insert in large batches
        for batch_start in range(0, len(all_accounts), batch_size):
            batch = all_accounts[batch_start:batch_start + batch_size]
            
            query = """
            UNWIND $accounts as acc
            CREATE (a:Account {
                account_id: acc.id,
                name: acc.name,
                email: acc.email,
                status: acc.status,
                risk_level: acc.risk_level,
                is_known_fraud: acc.is_known_fraud,
                created_at: datetime()
            })
            """
            await self.execute_query(query, {"accounts": batch}, 
                f"Batch {batch_start//batch_size + 1}")
        
        print(f"  OK - Created 10,000 accounts")

    async def create_cards_bulk(self):
        """Create payment cards."""
        print("[3/6] Creating 10,000 cards (bulk)...")
        
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
        
        # Bulk insert
        batch_size = 500
        for batch_start in range(0, len(cards_data), batch_size):
            batch = cards_data[batch_start:batch_start + batch_size]
            
            query = """
            UNWIND $cards as card
            MATCH (a:Account {account_id: card.account_id})
            CREATE (c:Card {
                card_number: card.card_number,
                card_type: card.card_type,
                status: 'ACTIVE',
                created_at: datetime()
            })
            CREATE (a)-[:HAS_CARD]->(c)
            """
            await self.execute_query(query, {"cards": batch}, 
                f"Batch {batch_start//batch_size + 1}/{len(cards_data)//batch_size + 1}")
        
        print(f"  OK - Created 10,000 cards")

    async def create_devices_bulk(self):
        """Create shared devices."""
        print("[4/6] Creating 500 devices (bulk)...")
        
        all_account_ids = (
            [f"ACC_{i:05d}" for i in range(1, 7001)] +
            [f"FRAUD_{i:05d}" for i in range(1, 301)] +
            [f"SUSP_{i:05d}" for i in range(1, 2701)]
        )
        
        device_ops = []
        device_id = 1
        
        # Suspicious devices (300)
        for i in range(1, 301):
            accounts = self.random.sample(all_account_ids, self.random.randint(2, 5))
            device_ops.append(({
                "device_id": f"DEV_{device_id:04d}",
                "device_name": f"Device_Suspicious_{i}",
                "accounts": accounts
            }))
            device_id += 1
        
        # Normal devices (200)
        for i in range(1, 201):
            count = 2 if self.random.random() < 0.3 else 1
            accounts = self.random.sample(all_account_ids, count)
            device_ops.append(({
                "device_id": f"DEV_{device_id:04d}",
                "device_name": f"Device_Normal_{i}",
                "accounts": accounts
            }))
            device_id += 1
        
        # Create devices and relationships
        query = """
        UNWIND $devices as dev
        CREATE (d:Device {device_id: dev.device_id, device_name: dev.device_name, created_at: datetime()})
        WITH d, dev
        UNWIND dev.accounts as account_id
        MATCH (a:Account {account_id: account_id})
        CREATE (a)-[:USES_DEVICE]->(d)
        """
        
        batch_size = 50
        for batch_start in range(0, len(device_ops), batch_size):
            batch = device_ops[batch_start:batch_start + batch_size]
            await self.execute_query(query, {"devices": batch}, 
                f"Batch {batch_start//batch_size + 1}/{len(device_ops)//batch_size + 1}")
        
        print(f"  OK - Created 500 devices")

    async def create_phones_bulk(self):
        """Create phone numbers."""
        print("[5/6] Creating 800 phone numbers (bulk)...")
        
        all_account_ids = (
            [f"ACC_{i:05d}" for i in range(1, 7001)] +
            [f"FRAUD_{i:05d}" for i in range(1, 301)] +
            [f"SUSP_{i:05d}" for i in range(1, 2701)]
        )
        
        phone_ops = []
        phone_id = 1
        
        # Suspicious phones (400)
        for i in range(1, 401):
            accounts = self.random.sample(all_account_ids, self.random.randint(2, 4))
            phone_ops.append({
                "phone_number": f"+1-555-{phone_id:05d}",
                "accounts": accounts
            })
            phone_id += 1
        
        # Individual phones (400)
        for i in range(1, 401):
            accounts = self.random.sample(all_account_ids, 1)
            phone_ops.append({
                "phone_number": f"+1-555-{phone_id:05d}",
                "accounts": accounts
            })
            phone_id += 1
        
        query = """
        UNWIND $phones as phone
        CREATE (p:PhoneNumber {phone_number: phone.phone_number, created_at: datetime()})
        WITH p, phone
        UNWIND phone.accounts as account_id
        MATCH (a:Account {account_id: account_id})
        CREATE (a)-[:HAS_PHONE]->(p)
        """
        
        batch_size = 50
        for batch_start in range(0, len(phone_ops), batch_size):
            batch = phone_ops[batch_start:batch_start + batch_size]
            await self.execute_query(query, {"phones": batch}, 
                f"Batch {batch_start//batch_size + 1}/{len(phone_ops)//batch_size + 1}")
        
        print(f"  OK - Created 800 phone numbers")

    async def create_ips_bulk(self):
        """Create IP addresses."""
        print("[6/6] Creating 600 IP addresses (bulk)...")
        
        all_account_ids = (
            [f"ACC_{i:05d}" for i in range(1, 7001)] +
            [f"FRAUD_{i:05d}" for i in range(1, 301)] +
            [f"SUSP_{i:05d}" for i in range(1, 2701)]
        )
        
        ip_ops = []
        ip_id = 1
        
        # Suspicious IPs (300)
        for i in range(1, 301):
            accounts = self.random.sample(all_account_ids, self.random.randint(2, 5))
            octet = (ip_id // 256) + 1
            host = ip_id % 256
            ip_ops.append({
                "ip_address": f"192.168.{octet}.{host}",
                "accounts": accounts
            })
            ip_id += 1
        
        # Individual IPs (300)
        for i in range(1, 301):
            accounts = self.random.sample(all_account_ids, 1)
            octet = (ip_id // 256) + 1
            host = ip_id % 256
            ip_ops.append({
                "ip_address": f"192.168.{octet}.{host}",
                "accounts": accounts
            })
            ip_id += 1
        
        query = """
        UNWIND $ips as ip
        CREATE (i:IPAddress {ip_address: ip.ip_address, created_at: datetime()})
        WITH i, ip
        UNWIND ip.accounts as account_id
        MATCH (a:Account {account_id: account_id})
        CREATE (a)-[:ACCESSED_FROM_IP]->(i)
        """
        
        batch_size = 50
        for batch_start in range(0, len(ip_ops), batch_size):
            batch = ip_ops[batch_start:batch_start + batch_size]
            await self.execute_query(query, {"ips": batch}, 
                f"Batch {batch_start//batch_size + 1}/{len(ip_ops)//batch_size + 1}")
        
        print(f"  OK - Created 600 IP addresses")

    async def generate_all(self):
        """Generate complete dataset."""
        print("\n" + "=" * 60)
        print("FAST BULK SEED DATA GENERATOR")
        print("=" * 60 + "\n")
        
        await self.clear_database()
        await self.create_accounts_bulk()
        await self.create_cards_bulk()
        await self.create_devices_bulk()
        await self.create_phones_bulk()
        await self.create_ips_bulk()
        
        print("\n" + "=" * 60)
        print("Seed Complete!")
        print("=" * 60 + "\n")

async def main():
    """Entry point."""
    generator = FastBulkSeedGenerator()
    try:
        await generator.generate_all()
    finally:
        await generator.close()

if __name__ == "__main__":
    asyncio.run(main())
