"""
Seed Data Generator - Asynchronously creates synthetic fraud scenarios
Generates 100 accounts with 3 fraud rings and 2 money-mule chains for testing.
Uses AsyncGraphDatabase for non-blocking operations.
"""

import asyncio
import os
import random
import time
from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase


class SeedDataGenerator:
    """Asynchronously generates synthetic fraud scenarios with AsyncGraphDatabase."""

    def __init__(self):
        """Initialize async graph database connection."""
        load_dotenv()
        
        uri = os.getenv("COGNODB_URI")
        user = os.getenv("COGNODB_USERNAME")
        password = os.getenv("COGNODB_PASSWORD")
        
        if not all([uri, user, password]):
            raise ValueError("Missing required environment variables: COGNODB_URI, COGNODB_USERNAME, COGNODB_PASSWORD")
        
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
        self.random = random.Random(42)  # Consistent random state

    async def close(self):
        """Asynchronously close the database connection."""
        await self.driver.close()

    async def _run_with_retry(self, session, query, params, max_retries=3):
        """Run a query with exponential backoff retry logic."""
        for attempt in range(max_retries):
            try:
                return await session.run(query, params)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                print(f"[WARN] Attempt {attempt + 1} failed, retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)

    async def clear_database(self):
        """Asynchronously clear all existing data."""
        async with self.driver.session() as session:
            await self._run_with_retry(session, "MATCH (n) DETACH DELETE n", {})
            print("[OK] Database cleared")

    async def create_accounts(self):
        """Asynchronously create base accounts including known fraud."""
        # Create normal accounts (7000)
        accounts_data = []
        for i in range(1, 7001):
            accounts_data.append({
                "id": f"ACC_{i:05d}",
                "name": f"User {i}",
                "email": f"user{i}@example.com",
                "status": "ACTIVE",
                "risk_level": "LOW",
                "is_known_fraud": False
            })
        
        # Create known fraud accounts (300)
        for i in range(1, 301):
            accounts_data.append({
                "id": f"FRAUD_{i:05d}",
                "name": f"Fraud Operator {i}",
                "email": f"fraud{i}@malicious.com",
                "status": "SUSPENDED",
                "risk_level": "CRITICAL",
                "is_known_fraud": True
            })
        
        # Create suspicious accounts (2700)
        for i in range(1, 2701):
            accounts_data.append({
                "id": f"SUSP_{i:05d}",
                "name": f"Suspicious User {i}",
                "email": f"suspect{i}@example.com",
                "status": "ACTIVE",
                "risk_level": "MEDIUM",
                "is_known_fraud": False
            })
        
        # Execute sequentially with new session per batch
        batch_size = 50
        for batch_start in range(0, len(accounts_data), batch_size):
            batch = accounts_data[batch_start:batch_start + batch_size]
            async with self.driver.session() as session:
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
                    await self._run_with_retry(session, query, acc)
                    await asyncio.sleep(0.01)  # Small delay to prevent connection pool saturation
        
        print("[OK] Created 10,000 accounts (7000 normal, 300 known fraud, 2700 suspicious)")

    async def create_cards(self):
        """Asynchronously create payment cards and associate with accounts."""
        cards_data = []
        for i in range(1, 10001):
            account_id = None
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
        
        # Execute in batches sequentially with new session per batch
        batch_size = 50
        for batch_start in range(0, len(cards_data), batch_size):
            batch = cards_data[batch_start:batch_start + batch_size]
            async with self.driver.session() as session:
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
                    await self._run_with_retry(session, query, card)
                    await asyncio.sleep(0.01)
        
        print("[OK] Created 10,000 payment cards")

    async def create_shared_devices(self):
        """Asynchronously create devices and establish suspicious shared device relationships."""
        device_tasks = []
        device_id = 1
        
        # DELIBERATE FRAUD RINGS (5 rings × 3 devices per ring = 15 devices)
        # Each ring connects known-fraud + suspicious accounts on shared devices
        print("[*] Creating deliberate fraud ring shared devices...")
        for ring_num in range(1, 6):
            # Get known-fraud anchor accounts for this ring
            known_fraud_accounts = [f"FRAUD_{i:05d}" for i in range((ring_num-1)*50 + 1, (ring_num-1)*50 + 3)]
            # Get suspicious accounts for this ring
            suspicious_accounts = [f"SUSP_{i:05d}" for i in range((ring_num-1)*200 + 1, (ring_num-1)*200 + 5)]
            
            ring_members = known_fraud_accounts + suspicious_accounts
            
            # Create 3 shared devices, each connecting all ring members
            for dev_num in range(1, 4):
                device_name = f"Device_FraudRing{ring_num}_{dev_num}"
                device_tasks.append((device_id, ring_members, device_name))
                device_id += 1
        
        # Suspicious devices (300) - regular random selection
        for i in range(1, 301):
            accounts = self._pick_random_accounts(self.random.randint(2, 5))
            device_tasks.append((device_id, accounts, f"Device_Suspicious_{i}"))
            device_id += 1
        
        # Normal devices (200)
        for i in range(1, 201):
            if self.random.random() < 0.3:
                accounts = self._pick_random_accounts(2)
            else:
                accounts = self._pick_random_accounts(1)
            device_tasks.append((device_id, accounts, f"Device_Normal_{i}"))
            device_id += 1
        
        print(f"[*] Created {len(device_tasks)} total devices including deliberate fraud ring patterns")
        
        # Execute with new session per batch
        batch_size = 10
        for batch_start in range(0, len(device_tasks), batch_size):
            batch = device_tasks[batch_start:batch_start + batch_size]
            async with self.driver.session() as session:
                for dev_id, accounts, device_name in batch:
                    await self._create_shared_device_async(session, dev_id, accounts, device_name)
                    await asyncio.sleep(0.01)
        
        print("[OK] Devices created successfully with deliberate fraud ring patterns")

    async def create_shared_phone_numbers(self):
        """Asynchronously create phone numbers and establish shared phone relationships."""
        phone_tasks = []
        phone_id = 1
        
        # Suspicious shared phones (400)
        for i in range(1, 401):
            accounts = self._pick_random_accounts(self.random.randint(2, 4))
            phone_tasks.append((phone_id, accounts, f"+1-555-{phone_id:05d}"))
            phone_id += 1
        
        # Individual phones for remaining accounts (400)
        for i in range(1, 401):
            accounts = self._pick_random_accounts(1)
            phone_tasks.append((phone_id, accounts, f"+1-555-{phone_id:05d}"))
            phone_id += 1
        
        # Execute with new session per batch
        batch_size = 20
        for batch_start in range(0, len(phone_tasks), batch_size):
            batch = phone_tasks[batch_start:batch_start + batch_size]
            async with self.driver.session() as session:
                for phone_id, accounts, phone_number in batch:
                    await self._create_shared_phone_async(session, phone_id, accounts, phone_number)
                    await asyncio.sleep(0.01)
        
        print("[OK] Created 800 phone numbers with suspicious sharing patterns")

    async def create_shared_ip_addresses(self):
        """Asynchronously create IP addresses and establish shared IP relationships."""
        ip_tasks = []
        ip_id = 1
        
        # DELIBERATE FRAUD RINGS (5 rings × 2 IPs per ring = 10 IPs)
        # Each ring connects known-fraud + suspicious accounts on shared IPs
        print("[*] Creating deliberate fraud ring shared IPs...")
        for ring_num in range(1, 6):
            # Get known-fraud anchor accounts for this ring
            known_fraud_accounts = [f"FRAUD_{i:05d}" for i in range((ring_num-1)*50 + 1, (ring_num-1)*50 + 3)]
            # Get suspicious accounts for this ring
            suspicious_accounts = [f"SUSP_{i:05d}" for i in range((ring_num-1)*200 + 1, (ring_num-1)*200 + 5)]
            
            ring_members = known_fraud_accounts + suspicious_accounts
            
            # Create 2 shared IPs, each connecting all ring members
            for ip_num in range(1, 3):
                ip_address = f"192.168.{100 + ring_num}.{ip_num * 100}"
                ip_tasks.append((ip_id, ring_members, ip_address))
                ip_id += 1
        
        # Suspicious shared IPs (300) - regular random selection
        for i in range(1, 301):
            accounts = self._pick_random_accounts(self.random.randint(2, 5))
            octet = (ip_id // 256) + 1
            host = (ip_id % 256)
            ip_tasks.append((ip_id, accounts, f"192.168.{octet}.{host}"))
            ip_id += 1
        
        # Individual IPs for remaining accounts (300)
        for i in range(1, 301):
            accounts = self._pick_random_accounts(1)
            octet = (ip_id // 256) + 1
            host = (ip_id % 256)
            ip_tasks.append((ip_id, accounts, f"192.168.{octet}.{host}"))
            ip_id += 1
        
        print(f"[*] Created {len(ip_tasks)} total IPs including deliberate fraud ring patterns")
        
        # Execute with new session per batch
        batch_size = 10
        for batch_start in range(0, len(ip_tasks), batch_size):
            batch = ip_tasks[batch_start:batch_start + batch_size]
            async with self.driver.session() as session:
                for ip_id, accounts, ip_address in batch:
                    await self._create_shared_ip_async(session, ip_id, accounts, ip_address)
                    await asyncio.sleep(0.01)
        
        print("[OK] Created 600 IP addresses with suspicious sharing patterns")

    async def create_transactions(self):
        """Asynchronously create transaction relationships between accounts."""
        transaction_id = 1
        transactions = []
        
        # DELIBERATE MONEY-MULE CHAINS (10 chains with known-fraud anchors)
        # Each chain: known-fraud -> suspicious -> suspicious -> known-fraud
        print("[*] Creating deliberate money-mule chains with known-fraud involvement...")
        for chain_num in range(1, 11):
            source = f"FRAUD_{100 + chain_num:05d}"
            intermediary1 = f"SUSP_{3000 + chain_num * 10:05d}"
            intermediary2 = f"SUSP_{3000 + chain_num * 10 + 1:05d}"
            destination = f"FRAUD_{200 + chain_num:05d}"
            
            chain_accounts = [source, intermediary1, intermediary2, destination]
            base_amount = 50000
            
            for i in range(len(chain_accounts) - 1):
                from_acc = chain_accounts[i]
                to_acc = chain_accounts[i + 1]
                amount = max(5000, base_amount - (i * 5000))
                transactions.append((transaction_id, from_acc, to_acc, amount))
                transaction_id += 1
        
        # Regular money-mule chains (490 chains × 4 hops = 1960 transactions)
        for chain_num in range(11, 501):
            accounts = self._pick_random_accounts(5)
            amount = self.random.randint(20000, 100000)
            for i in range(len(accounts) - 1):
                transactions.append((transaction_id, accounts[i], accounts[i+1], amount - (i * 1000)))
                transaction_id += 1
        
        # Fraud ring internal transactions (100 × 10 = 1000 transactions)
        for ring_num in range(1, 101):
            accounts = self._pick_random_accounts(10)
            for i, source in enumerate(accounts):
                for target in accounts[i+1:]:
                    if source != target and self.random.random() < 0.3:
                        amount = self.random.randint(5000, 30000)
                        transactions.append((transaction_id, source, target, amount))
                        transaction_id += 1
        
        # Normal legitimate transactions (2000 more)
        for i in range(2000):
            source = self._pick_random_account()
            target = self._pick_random_account()
            if source != target:
                amount = self.random.randint(50, 5000)
                transactions.append((transaction_id, source, target, amount))
                transaction_id += 1
        
        print(f"[*] Created {len(transactions)} total transactions")
        
        # Execute with new session per batch
        batch_size = 50
        for batch_start in range(0, len(transactions), batch_size):
            batch = transactions[batch_start:batch_start + batch_size]
            async with self.driver.session() as session:
                for txn_id, source, target, amount in batch:
                    await self._create_transaction_async(session, txn_id, source, target, amount)
                    await asyncio.sleep(0.01)
        
        print("[OK] Created 5,000+ transactions including money-mule chains")

    # ========================================================================
    # ASYNC HELPER METHODS
    # ========================================================================

    async def _create_shared_device_async(self, session, device_id, account_ids, device_name):
        """Asynchronously create a device and connect accounts to it."""
        # Create the device
        await self._run_with_retry(session, """
        MERGE (d:Device {
            device_id: $device_id,
            device_name: $device_name
        })
        ON CREATE SET d.created_at = datetime()
        """, {"device_id": f"DEV_{device_id:04d}", "device_name": device_name})
        
        # Connect accounts to device
        for account_id in account_ids:
            await self._run_with_retry(session, """
            MATCH (a:Account {account_id: $account_id})
            MATCH (d:Device {device_id: $device_id})
            CREATE (a)-[:USES_DEVICE]->(d)
            """, {
                "account_id": account_id,
                "device_id": f"DEV_{device_id:04d}"
            })

    async def _create_shared_phone_async(self, session, phone_id, account_ids, phone_number):
        """Asynchronously create a phone number and connect accounts to it."""
        # Create the phone
        await self._run_with_retry(session, """
        MERGE (p:PhoneNumber {
            phone_number: $phone_number
        })
        ON CREATE SET p.created_at = datetime()
        """, {"phone_number": phone_number})
        
        # Connect accounts to phone
        for account_id in account_ids:
            await self._run_with_retry(session, """
            MATCH (a:Account {account_id: $account_id})
            MATCH (p:PhoneNumber {phone_number: $phone_number})
            CREATE (a)-[:HAS_PHONE]->(p)
            """, {
                "account_id": account_id,
                "phone_number": phone_number
            })

    async def _create_shared_ip_async(self, session, ip_id, account_ids, ip_address):
        """Asynchronously create an IP address and connect accounts to it."""
        # Create the IP
        await self._run_with_retry(session, """
        MERGE (ip:IPAddress {
            ip_address: $ip_address
        })
        ON CREATE SET ip.created_at = datetime()
        """, {"ip_address": ip_address})
        
        # Connect accounts to IP
        for account_id in account_ids:
            await self._run_with_retry(session, """
            MATCH (a:Account {account_id: $account_id})
            MATCH (ip:IPAddress {ip_address: $ip_address})
            CREATE (a)-[:ACCESSED_FROM_IP]->(ip)
            """, {
                "account_id": account_id,
                "ip_address": ip_address
            })

    async def _create_transaction_async(self, session, transaction_id, source_id, target_id, amount):
        """Asynchronously create a transaction relationship between two accounts."""
        await self._run_with_retry(session, """
        MATCH (source:Account {account_id: $source_id})
        MATCH (target:Account {account_id: $target_id})
        CREATE (source)-[:TRANSACTED_WITH {
            transaction_id: $transaction_id,
            amount: $amount,
            transaction_count: 1,
            total_amount: $amount,
            timestamp: datetime()
        }]->(target)
        """, {
            "source_id": source_id,
            "target_id": target_id,
            "transaction_id": f"TXN_{transaction_id:06d}",
            "amount": amount
        })

    # ========================================================================
    # SYNCHRONOUS HELPERS (no async/await needed)
    # ========================================================================

    def _pick_random_accounts(self, count):
        """Pick random account IDs."""
        all_accounts = (
            [f"ACC_{i:05d}" for i in range(1, 7001)] +
            [f"FRAUD_{i:05d}" for i in range(1, 301)] +
            [f"SUSP_{i:05d}" for i in range(1, 2701)]
        )
        return self.random.sample(all_accounts, min(count, len(all_accounts)))

    def _pick_random_account(self):
        """Pick a random account ID."""
        return self._pick_random_accounts(1)[0]

    async def generate_all(self):
        """Asynchronously generate complete seed dataset."""
        print("\n[*] Starting seed data generation (Async)...\n")
        await self.clear_database()
        await self.create_accounts()
        await self.create_cards()
        await self.create_shared_devices()
        await self.create_shared_phone_numbers()
        await self.create_shared_ip_addresses()
        await self.create_transactions()
        print("\n[OK] Seed data generation complete!\n")


async def main():
    """Async entry point for seed generation."""
    generator = SeedDataGenerator()
    try:
        await generator.generate_all()
    finally:
        await generator.close()


if __name__ == "__main__":
    asyncio.run(main())
