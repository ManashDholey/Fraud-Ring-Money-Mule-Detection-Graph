"""
Improved seed data generator with deliberate fraud ring clusters.
Creates realistic graph structure where risk metrics can be meaningfully derived.
"""

import asyncio
import os
import random
from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase


class StructuredBulkSeedGenerator:
    """Generates seed data with deliberate fraud rings for meaningful graph analysis."""

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
        print("[1/9] Clearing database...")
        async with self.driver.session() as session:
            await session.run("MATCH (n) DETACH DELETE n")
        print("  OK")

    async def create_accounts_bulk(self):
        """Create all 10,000 accounts: 7K normal, 300 fraud, 2.7K suspicious."""
        print("[2/9] Creating 10,000 accounts (bulk)...")
        
        batch_size = 500
        all_accounts = []
        
        # 7,000 normal (no is_known_fraud, will compute risk from graph)
        for i in range(1, 7001):
            all_accounts.append({
                "id": f"ACC_{i:05d}",
                "name": f"User {i}",
                "email": f"user{i}@example.com",
                "status": "ACTIVE",
                "is_known_fraud": False
            })
        
        # 300 fraud (ground truth — these are KNOWN confirmed fraudsters)
        for i in range(1, 301):
            all_accounts.append({
                "id": f"FRAUD_{i:05d}",
                "name": f"Fraud {i}",
                "email": f"fraud{i}@malicious.com",
                "status": "SUSPENDED",
                "is_known_fraud": True
            })
        
        # 2,700 suspicious (unknown status — we will derive risk from connections to known fraud)
        for i in range(1, 2701):
            all_accounts.append({
                "id": f"SUSP_{i:05d}",
                "name": f"Suspect {i}",
                "email": f"suspect{i}@example.com",
                "status": "ACTIVE",
                "is_known_fraud": False
            })
        
        # Bulk insert without hardcoded risk_level — risk will be computed from graph
        for batch_start in range(0, len(all_accounts), batch_size):
            batch = all_accounts[batch_start:batch_start + batch_size]
            
            query = """
            UNWIND $accounts as acc
            CREATE (a:Account {
                account_id: acc.id,
                name: acc.name,
                email: acc.email,
                status: acc.status,
                is_known_fraud: acc.is_known_fraud,
                created_at: datetime()
            })
            """
            await self.execute_query(query, {"accounts": batch}, 
                f"Batch {batch_start//batch_size + 1}")
        
        print(f"  OK - Created 10,000 accounts")

    async def create_deliberate_fraud_rings(self):
        """Create 4 deliberately-constructed fraud rings for testing."""
        print("[3/9] Creating deliberate fraud rings (clusters)...")
        
        # RING 1: Device-based cluster — 2 known-fraud + 3 suspicious sharing one device
        ring1_accounts = ["FRAUD_00001", "FRAUD_00050", "SUSP_00100", "SUSP_00200", "SUSP_00300"]
        ring1_device = "DEV_RING1_SHARED"
        
        # RING 2: Phone-based cluster — 3 known-fraud + 2 suspicious sharing one phone
        ring2_accounts = ["FRAUD_00010", "FRAUD_00060", "FRAUD_00090", "SUSP_00400", "SUSP_00500"]
        ring2_phone = "+1-555-RING2-FRAUD"
        
        # RING 3: IP-based cluster — 1 known-fraud + 4 suspicious sharing one IP
        ring3_accounts = ["FRAUD_00020", "SUSP_00600", "SUSP_00700", "SUSP_00800", "SUSP_00900"]
        ring3_ip = "192.168.99.100"
        
        # RING 4: Multi-attribute — known-fraud shares device + phone + IP with different sets of accomplices
        ring4_accounts_device = ["FRAUD_00030", "SUSP_01000", "SUSP_01100"]
        ring4_accounts_phone = ["FRAUD_00030", "SUSP_01200", "SUSP_01300"]
        ring4_accounts_ip = ["FRAUD_00030", "SUSP_01400", "SUSP_01500"]
        
        # Create Ring 1 device
        async with self.driver.session() as session:
            await session.run("""
            CREATE (d:Device {device_id: $dev_id, device_name: $dev_name, created_at: datetime()})
            WITH d
            UNWIND $accounts as acc_id
            MATCH (a:Account {account_id: acc_id})
            CREATE (a)-[:USES_DEVICE]->(d)
            """, {"dev_id": ring1_device, "dev_name": ring1_device, "accounts": ring1_accounts})
        print("  OK: Ring 1 (device)")
        
        # Create Ring 2 phone
        async with self.driver.session() as session:
            await session.run("""
            CREATE (p:PhoneNumber {phone_number: $phone, created_at: datetime()})
            WITH p
            UNWIND $accounts as acc_id
            MATCH (a:Account {account_id: acc_id})
            CREATE (a)-[:HAS_PHONE]->(p)
            """, {"phone": ring2_phone, "accounts": ring2_accounts})
        print("  OK: Ring 2 (phone)")
        
        # Create Ring 3 IP
        async with self.driver.session() as session:
            await session.run("""
            CREATE (i:IPAddress {ip_address: $ip, created_at: datetime()})
            WITH i
            UNWIND $accounts as acc_id
            MATCH (a:Account {account_id: acc_id})
            CREATE (a)-[:ACCESSED_FROM_IP]->(i)
            """, {"ip": ring3_ip, "accounts": ring3_accounts})
        print("  OK: Ring 3 (IP)")
        
        # Create Ring 4 with multiple attributes
        async with self.driver.session() as session:
            # Device
            await session.run("""
            CREATE (d:Device {device_id: $dev_id, device_name: $dev_name, created_at: datetime()})
            WITH d
            UNWIND $accounts as acc_id
            MATCH (a:Account {account_id: acc_id})
            CREATE (a)-[:USES_DEVICE]->(d)
            """, {"dev_id": "DEV_RING4_A", "dev_name": "DEV_RING4_A", "accounts": ring4_accounts_device})
            
            # Phone
            await session.run("""
            CREATE (p:PhoneNumber {phone_number: $phone, created_at: datetime()})
            WITH p
            UNWIND $accounts as acc_id
            MATCH (a:Account {account_id: acc_id})
            CREATE (a)-[:HAS_PHONE]->(p)
            """, {"phone": "+1-555-RING4-PHONE", "accounts": ring4_accounts_phone})
            
            # IP
            await session.run("""
            CREATE (i:IPAddress {ip_address: $ip, created_at: datetime()})
            WITH i
            UNWIND $accounts as acc_id
            MATCH (a:Account {account_id: acc_id})
            CREATE (a)-[:ACCESSED_FROM_IP]->(i)
            """, {"ip": "192.168.99.200", "accounts": ring4_accounts_ip})
        print("  OK: Ring 4 (multi-attribute)")

    async def create_cards_bulk(self):
        """Create 10,000 cards with random assignments."""
        print("[4/9] Creating 10,000 cards (bulk)...")
        
        cards_data = []
        all_account_ids = (
            [f"ACC_{i:05d}" for i in range(1, 7001)] +
            [f"FRAUD_{i:05d}" for i in range(1, 301)] +
            [f"SUSP_{i:05d}" for i in range(1, 2701)]
        )
        
        for i, acc_id in enumerate(all_account_ids, 1):
            cards_data.append({
                "account_id": acc_id,
                "card_number": f"4532-{self.random.randint(1000, 9999)}-XXXX",
                "card_type": self.random.choice(["VISA", "MASTERCARD", "AMEX"])
            })
        
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
        """Create shared devices (excluding rings already created)."""
        print("[5/9] Creating 480 additional random devices...")
        
        all_account_ids = (
            [f"ACC_{i:05d}" for i in range(1, 7001)] +
            [f"FRAUD_{i:05d}" for i in range(51, 301)] +  # Exclude ring accounts
            [f"SUSP_{i:05d}" for i in range(1600, 2701)]   # Exclude ring accounts
        )
        
        device_ops = []
        device_id = 100  # Start after deliberately-created ring devices
        
        # Suspicious devices (300)
        for i in range(1, 301):
            accounts = self.random.sample(all_account_ids, self.random.randint(2, 5))
            device_ops.append({
                "device_id": f"DEV_{device_id:04d}",
                "device_name": f"Device_{i}",
                "accounts": accounts
            })
            device_id += 1
        
        # Normal devices (180)
        for i in range(1, 181):
            count = 2 if self.random.random() < 0.3 else 1
            accounts = self.random.sample(all_account_ids, count)
            device_ops.append({
                "device_id": f"DEV_{device_id:04d}",
                "device_name": f"Device_Normal_{i}",
                "accounts": accounts
            })
            device_id += 1
        
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
        
        print(f"  OK - Created 480 random devices")

    async def create_phones_bulk(self):
        """Create phone numbers (excluding rings already created)."""
        print("[6/9] Creating 750 additional phone numbers...")
        
        all_account_ids = (
            [f"ACC_{i:05d}" for i in range(1, 7001)] +
            [f"FRAUD_{i:05d}" for i in range(91, 301)] +   # Exclude ring accounts
            [f"SUSP_{i:05d}" for i in range(1600, 2701)]
        )
        
        phone_ops = []
        phone_id = 5000
        
        # Suspicious phones (375)
        for i in range(1, 376):
            accounts = self.random.sample(all_account_ids, self.random.randint(2, 4))
            phone_ops.append({
                "phone_number": f"+1-555-{phone_id:05d}",
                "accounts": accounts
            })
            phone_id += 1
        
        # Individual phones (375)
        for i in range(1, 376):
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
        
        print(f"  OK - Created 750 phone numbers")

    async def create_ips_bulk(self):
        """Create IP addresses (excluding rings already created)."""
        print("[7/9] Creating 550 additional IP addresses...")
        
        all_account_ids = (
            [f"ACC_{i:05d}" for i in range(1, 7001)] +
            [f"FRAUD_{i:05d}" for i in range(31, 301)] +
            [f"SUSP_{i:05d}" for i in range(1600, 2701)]
        )
        
        ip_ops = []
        ip_id = 1
        
        # Suspicious IPs (275)
        for i in range(1, 276):
            accounts = self.random.sample(all_account_ids, self.random.randint(2, 5))
            octet = (ip_id // 256) + 1
            host = ip_id % 256
            ip_ops.append({
                "ip_address": f"192.168.{octet}.{host}",
                "accounts": accounts
            })
            ip_id += 1
        
        # Individual IPs (275)
        for i in range(1, 276):
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
        
        print(f"  OK - Created 550 IP addresses")

    async def create_transaction_chains(self):
        """Create TRANSACTED_WITH relationships for money-mule chain detection."""
        print("[8/9] Creating transaction chains...")
        
        all_fraud_ids = [f"FRAUD_{i:05d}" for i in range(1, 301)]
        
        transactions = []
        
        # Create 3-5 transaction chains per fraud account (some fraud-to-fraud, some fraud-to-suspect)
        for fraud_id in all_fraud_ids[:100]:  # Create chains involving first 100 fraud accounts
            chain_length = self.random.randint(3, 5)
            
            # Build a chain: fraud -> (suspect|normal) -> suspect -> ...
            chain_accounts = [fraud_id]
            
            for hop in range(chain_length - 1):
                if self.random.random() < 0.3 and len(all_fraud_ids) > 1:
                    # Occasionally fraud-to-fraud
                    next_account = self.random.choice(all_fraud_ids)
                else:
                    # Usually fraud-to-suspect or suspect-to-suspect
                    if self.random.random() < 0.5:
                        next_account = f"SUSP_{self.random.randint(1, 2700):05d}"
                    else:
                        next_account = f"ACC_{self.random.randint(1, 7000):05d}"
                
                # Add edge from previous to current
                transactions.append({
                    "from_account": chain_accounts[-1],
                    "to_account": next_account
                })
                chain_accounts.append(next_account)
        
        if transactions:
            batch_size = 100
            for batch_start in range(0, len(transactions), batch_size):
                batch = transactions[batch_start:batch_start + batch_size]
                
                query = """
                UNWIND $txns as txn
                MATCH (from:Account {account_id: txn.from_account})
                MATCH (to:Account {account_id: txn.to_account})
                CREATE (from)-[:TRANSACTED_WITH]->(to)
                """
                await self.execute_query(query, {"txns": batch}, 
                    f"Batch {batch_start//batch_size + 1}/{len(transactions)//batch_size + 1}")
        
        print(f"  OK - Created {len(transactions)} transaction edges")

    async def generate_all(self):
        """Generate complete structured dataset."""
        print("\n" + "=" * 70)
        print("STRUCTURED BULK SEED DATA GENERATOR")
        print("Creates deliberate fraud clusters for meaningful graph analysis")
        print("=" * 70 + "\n")
        
        await self.clear_database()
        await self.create_accounts_bulk()
        await self.create_deliberate_fraud_rings()
        await self.create_cards_bulk()
        await self.create_devices_bulk()
        await self.create_phones_bulk()
        await self.create_ips_bulk()
        await self.create_transaction_chains()
        
        print("\n" + "=" * 70)
        print("Seed Complete! Database now contains:")
        print("  - 10,000 accounts (7K normal, 300 known-fraud, 2.7K suspicious)")
        print("  - 4 deliberate fraud rings with detectable clusters")
        print("  - ~14,000 shared-attribute relationships")
        print("  - ~300 transaction edges for money-mule detection")
        print("\nNext steps:")
        print("  1. python scripts/compute_risk_scores.py")
        print("  2. python scripts/compute_fraud_rings.py")
        print("=" * 70 + "\n")

async def main():
    """Entry point."""
    generator = StructuredBulkSeedGenerator()
    try:
        await generator.generate_all()
    finally:
        await generator.close()

if __name__ == "__main__":
    asyncio.run(main())
