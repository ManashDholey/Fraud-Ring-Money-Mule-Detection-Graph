"""
Synchronous Seed Data Generator - Creates synthetic fraud scenarios
Simpler sync version that avoids async/await connection pool issues
"""

import os
import random
from dotenv import load_dotenv
from neo4j import GraphDatabase


class SyncSeedDataGenerator:
    """Synchronously generates synthetic fraud scenarios."""

    def __init__(self):
        """Initialize sync graph database connection."""
        load_dotenv()
        
        uri = os.getenv("COGNODB_URI")
        user = os.getenv("COGNODB_USERNAME")
        password = os.getenv("COGNODB_PASSWORD")
        
        if not all([uri, user, password]):
            raise ValueError("Missing required environment variables")
        
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.random = random.Random(42)

    def close(self):
        """Close the database connection."""
        self.driver.close()

    def clear_database(self):
        """Clear all existing data."""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        print("✓ Database cleared")

    def create_accounts(self):
        """Create base accounts including known fraud."""
        with self.driver.session() as session:
            # Normal accounts
            for i in range(1, 71):
                session.run("""
                CREATE (a:Account {
                    account_id: $account_id,
                    name: $name,
                    email: $email,
                    status: 'ACTIVE',
                    risk_level: 'LOW',
                    is_known_fraud: false,
                    created_at: datetime()
                })
                """, {
                    "account_id": f"ACC_{i:04d}",
                    "name": f"User {i}",
                    "email": f"user{i}@example.com"
                })
            
            # Known fraud accounts
            fraud_names = ["Fraud Ring Leader", "Fraud Operator 1", "Fraud Operator 2"]
            for i, name in enumerate(fraud_names, 1):
                session.run("""
                CREATE (a:Account {
                    account_id: $account_id,
                    name: $name,
                    email: $email,
                    status: 'SUSPENDED',
                    risk_level: 'CRITICAL',
                    is_known_fraud: true,
                    created_at: datetime()
                })
                """, {
                    "account_id": f"FRAUD_{i:03d}",
                    "name": name,
                    "email": f"fraud{i}@malicious.com"
                })
            
            # Suspicious accounts
            for i in range(1, 28):
                session.run("""
                CREATE (a:Account {
                    account_id: $account_id,
                    name: $name,
                    email: $email,
                    status: 'ACTIVE',
                    risk_level: 'MEDIUM',
                    is_known_fraud: false,
                    created_at: datetime()
                })
                """, {
                    "account_id": f"SUSP_{i:03d}",
                    "name": f"Suspicious User {i}",
                    "email": f"suspect{i}@example.com"
                })
        
        print("✓ Created 100 accounts (70 normal, 3 known fraud, 27 suspicious)")

    def create_cards(self):
        """Create payment cards and associate with accounts."""
        with self.driver.session() as session:
            for i in range(1, 101):
                if i <= 70:
                    account_id = f"ACC_{i:04d}"
                elif i <= 73:
                    account_id = f"FRAUD_{((i - 70) % 3) + 1:03d}"
                else:
                    account_id = f"SUSP_{((i - 73) % 27) + 1:03d}"
                
                session.run("""
                MATCH (a:Account {account_id: $account_id})
                CREATE (c:Card {
                    card_number: $card_number,
                    card_type: $card_type,
                    status: 'ACTIVE'
                })
                CREATE (a)-[:HAS_CARD]->(c)
                """, {
                    "account_id": account_id,
                    "card_number": f"4532-{self.random.randint(1000, 9999)}-XXXX",
                    "card_type": self.random.choice(["VISA", "MASTERCARD", "AMEX"])
                })
        
        print("✓ Created 100 payment cards")

    def create_shared_devices(self):
        """Create devices and establish fraud ring relationships."""
        with self.driver.session() as session:
            device_id = 1
            
            # FRAUD RING 1
            for account_id in ["FRAUD_001", "SUSP_001", "SUSP_002", "SUSP_003"]:
                session.run("""
                MATCH (a:Account {account_id: $account_id})
                MERGE (d:Device {device_id: $device_id, device_name: $device_name})
                CREATE (a)-[:USES_DEVICE]->(d)
                """, {
                    "account_id": account_id,
                    "device_id": f"DEV_{device_id:04d}",
                    "device_name": "Device_Fraud_Ring_1"
                })
            device_id += 1
            
            # FRAUD RING 2
            for account_id in ["FRAUD_002", "SUSP_004", "SUSP_005", "SUSP_006"]:
                session.run("""
                MATCH (a:Account {account_id: $account_id})
                MERGE (d:Device {device_id: $device_id, device_name: $device_name})
                CREATE (a)-[:USES_DEVICE]->(d)
                """, {
                    "account_id": account_id,
                    "device_id": f"DEV_{device_id:04d}",
                    "device_name": "Device_Fraud_Ring_2"
                })
            device_id += 1
            
            # Additional devices
            for i in range(3, 51):
                accounts = self.random.sample(self._get_all_accounts(), 1 if self.random.random() > 0.3 else 2)
                for account_id in accounts:
                    session.run("""
                    MATCH (a:Account {account_id: $account_id})
                    MERGE (d:Device {device_id: $device_id, device_name: $device_name})
                    CREATE (a)-[:USES_DEVICE]->(d)
                    """, {
                        "account_id": account_id,
                        "device_id": f"DEV_{device_id:04d}",
                        "device_name": f"Device_{i}"
                    })
                device_id += 1
        
        print("✓ Created 50 devices with suspicious sharing patterns")

    def create_shared_phones(self):
        """Create phone numbers and establish relationships."""
        with self.driver.session() as session:
            phone_id = 1
            
            # Fraud ring phones
            fraud_phones = [
                (["FRAUD_001", "SUSP_001", "SUSP_002"], "+1-555-0001"),
                (["FRAUD_002", "SUSP_004", "SUSP_005"], "+1-555-0002"),
                (["FRAUD_003", "SUSP_007", "SUSP_008"], "+1-555-0003")
            ]
            
            for accounts, phone in fraud_phones:
                for account_id in accounts:
                    session.run("""
                    MATCH (a:Account {account_id: $account_id})
                    MERGE (p:PhoneNumber {phone: $phone})
                    CREATE (a)-[:HAS_PHONE]->(p)
                    """, {
                        "account_id": account_id,
                        "phone": phone
                    })
                phone_id += 1
            
            # Additional phones
            for i in range(4, 81):
                accounts = self.random.sample(self._get_all_accounts(), 1)
                for account_id in accounts:
                    session.run("""
                    MATCH (a:Account {account_id: $account_id})
                    MERGE (p:PhoneNumber {phone: $phone})
                    CREATE (a)-[:HAS_PHONE]->(p)
                    """, {
                        "account_id": account_id,
                        "phone": f"+1-555-{phone_id:04d}"
                    })
                phone_id += 1
        
        print("✓ Created 80 phone numbers with suspicious sharing patterns")

    def create_shared_ips(self):
        """Create IP addresses and establish relationships."""
        with self.driver.session() as session:
            ip_id = 1
            
            # Fraud ring IPs
            fraud_ips = [
                (["FRAUD_001", "SUSP_001", "SUSP_002", "SUSP_003"], "192.168.1.1"),
                (["FRAUD_002", "SUSP_004", "SUSP_005", "SUSP_006"], "192.168.2.1"),
                (["FRAUD_003", "SUSP_007", "SUSP_008"], "192.168.3.1")
            ]
            
            for accounts, ip in fraud_ips:
                for account_id in accounts:
                    session.run("""
                    MATCH (a:Account {account_id: $account_id})
                    MERGE (i:IPAddress {ip_address: $ip_address})
                    CREATE (a)-[:ACCESSED_FROM_IP]->(i)
                    """, {
                        "account_id": account_id,
                        "ip_address": ip
                    })
                ip_id += 1
            
            # Additional IPs
            for i in range(4, 61):
                accounts = self.random.sample(self._get_all_accounts(), 1)
                for account_id in accounts:
                    session.run("""
                    MATCH (a:Account {account_id: $account_id})
                    MERGE (i:IPAddress {ip_address: $ip_address})
                    CREATE (a)-[:ACCESSED_FROM_IP]->(i)
                    """, {
                        "account_id": account_id,
                        "ip_address": f"192.168.{ip_id}.1"
                    })
                ip_id += 1
        
        print("✓ Created 60 IP addresses with suspicious sharing patterns")

    def create_transactions(self):
        """Create transaction relationships."""
        with self.driver.session() as session:
            transaction_id = 1
            
            # Money-mule chain 1
            mule_chain = [
                ("FRAUD_001", "SUSP_009", 50000),
                ("SUSP_009", "SUSP_010", 45000),
                ("SUSP_010", "SUSP_011", 40000),
                ("SUSP_011", "ACC_001", 35000)
            ]
            
            for source, target, amount in mule_chain:
                session.run("""
                MATCH (s:Account {account_id: $source})
                MATCH (t:Account {account_id: $target})
                CREATE (s)-[:TRANSACTED_WITH {
                    transaction_id: $transaction_id,
                    amount: $amount,
                    timestamp: datetime()
                }]->(t)
                """, {
                    "source": source,
                    "target": target,
                    "transaction_id": f"TXN_{transaction_id:06d}",
                    "amount": amount
                })
                transaction_id += 1
            
            # Money-mule chain 2
            mule_chain_2 = [
                ("FRAUD_002", "SUSP_012", 60000),
                ("SUSP_012", "SUSP_013", 55000),
                ("SUSP_013", "ACC_002", 50000)
            ]
            
            for source, target, amount in mule_chain_2:
                session.run("""
                MATCH (s:Account {account_id: $source})
                MATCH (t:Account {account_id: $target})
                CREATE (s)-[:TRANSACTED_WITH {
                    transaction_id: $transaction_id,
                    amount: $amount,
                    timestamp: datetime()
                }]->(t)
                """, {
                    "source": source,
                    "target": target,
                    "transaction_id": f"TXN_{transaction_id:06d}",
                    "amount": amount
                })
                transaction_id += 1
            
            # Fraud ring transactions
            for source in ["FRAUD_001", "FRAUD_002", "FRAUD_003"]:
                for target in ["SUSP_001", "SUSP_002", "SUSP_004", "SUSP_005"]:
                    if source != target:
                        session.run("""
                        MATCH (s:Account {account_id: $source})
                        MATCH (t:Account {account_id: $target})
                        CREATE (s)-[:TRANSACTED_WITH {
                            transaction_id: $transaction_id,
                            amount: $amount,
                            timestamp: datetime()
                        }]->(t)
                        """, {
                            "source": source,
                            "target": target,
                            "transaction_id": f"TXN_{transaction_id:06d}",
                            "amount": self.random.randint(10000, 50000)
                        })
                        transaction_id += 1
            
            # Normal transactions
            for i in range(transaction_id, transaction_id + 400):
                source_acct = self.random.choice(self._get_all_accounts())
                target_acct = self.random.choice(self._get_all_accounts())
                if source_acct != target_acct:
                    session.run("""
                    MATCH (s:Account {account_id: $source})
                    MATCH (t:Account {account_id: $target})
                    CREATE (s)-[:TRANSACTED_WITH {
                        transaction_id: $transaction_id,
                        amount: $amount,
                        timestamp: datetime()
                    }]->(t)
                    """, {
                        "source": source_acct,
                        "target": target_acct,
                        "transaction_id": f"TXN_{i:06d}",
                        "amount": self.random.randint(100, 10000)
                    })
        
        print("✓ Created 500+ transactions including money-mule chains")

    def _get_all_accounts(self):
        """Get all account IDs."""
        accounts = [f"ACC_{i:04d}" for i in range(1, 71)]
        accounts += ["FRAUD_001", "FRAUD_002", "FRAUD_003"]
        accounts += [f"SUSP_{i:03d}" for i in range(1, 28)]
        return accounts

    def generate_all(self):
        """Generate complete seed dataset."""
        print("\n🌱 Starting seed data generation (Sync)...\n")
        try:
            self.clear_database()
            self.create_accounts()
            self.create_cards()
            self.create_shared_devices()
            self.create_shared_phones()
            self.create_shared_ips()
            self.create_transactions()
            print("\n✓ Seed data generation complete!\n")
        except Exception as e:
            print(f"\n✗ Error: {e}\n")
            raise


if __name__ == "__main__":
    generator = SyncSeedDataGenerator()
    try:
        generator.generate_all()
    finally:
        generator.close()
