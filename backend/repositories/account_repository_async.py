"""
Account Repository - Async Data Access Layer with Resilient Query Execution
Implements parameterized async Cypher queries with automatic retry on transient failures.

ALL queries now use session.execute_read() for automatic retry on:
  - neo4j.exceptions.ServiceUnavailable (stale pooled connection)
  - neo4j.exceptions.SessionExpired (server restart)
  - neo4j.exceptions.TransientError (temporary server issue)

This prevents intermittent ServiceUnavailable errors from Windows socket timeouts.
"""

from typing import List, Dict, Any, Optional
from dbConfig.db_async import get_driver
import asyncio


class AccountRepository:
    """Repository for Account-related async graph queries."""

    @staticmethod
    async def search_accounts(search_term: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search for accounts by name or ID (async).
        Uses execute_read() for automatic retry on transient errors.
        
        Args:
            search_term: Account name or ID to search for
            limit: Maximum number of results
            
        Returns:
            List of matching accounts
        """
        driver = get_driver()
        
        query = """
        MATCH (a:Account)
        WHERE a.account_id CONTAINS $search_term OR a.name CONTAINS $search_term
        RETURN {
            account_id: a.account_id,
            name: a.name,
            email: a.email,
            status: a.status,
            risk_level: a.risk_level,
            is_known_fraud: a.is_known_fraud
        } as account
        LIMIT $limit
        """
        
        # Use managed transaction for automatic retry on transient errors
        async def fetch_accounts(tx):
            """Transaction function: execute query and return results."""
            result = await tx.run(query, {"search_term": search_term, "limit": limit})
            return await result.data()
        
        async with driver.session() as session:
            records = await session.execute_read(fetch_accounts)
            return [record["account"] for record in records]

    @staticmethod
    async def get_account_by_id(account_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed account information (async).
        Uses execute_read() for automatic retry on transient errors.
        
        Args:
            account_id: Unique account identifier
            
        Returns:
            Account details or None if not found
        """
        driver = get_driver()
        
        query = """
        MATCH (a:Account {account_id: $account_id})
        RETURN {
            account_id: a.account_id,
            name: a.name,
            email: a.email,
            status: a.status,
            risk_level: a.risk_level,
            is_known_fraud: a.is_known_fraud,
            created_at: a.created_at
        } as account
        """
        
        # Use managed transaction for automatic retry on transient errors
        async def fetch_account(tx):
            """Transaction function: execute query and return single result."""
            result = await tx.run(query, {"account_id": account_id})
            return await result.single()
        
        async with driver.session() as session:
            record = await session.execute_read(fetch_account)
            return record["account"] if record else None

    @staticmethod
    async def get_account_cards(account_id: str) -> List[Dict[str, Any]]:
        """
        Get all cards associated with an account (async).
        Uses execute_read() for automatic retry on transient errors.
        
        Args:
            account_id: Account identifier
            
        Returns:
            List of card details
        """
        driver = get_driver()
        
        query = """
        MATCH (a:Account {account_id: $account_id})-[:HAS_CARD]->(c:Card)
        RETURN {
            card_number: c.card_number,
            card_type: c.card_type,
            status: c.status
        } as card
        """
        
        # Use managed transaction for automatic retry on transient errors
        async def fetch_cards(tx):
            """Transaction function: execute query and return results."""
            result = await tx.run(query, {"account_id": account_id})
            return await result.data()
        
        async with driver.session() as session:
            records = await session.execute_read(fetch_cards)
            return [record["card"] for record in records]

    @staticmethod
    async def get_shared_devices(account_id: str) -> List[Dict[str, Any]]:
        """
        Find other accounts sharing a device with the given account (async).
        Uses execute_read() for automatic retry on transient errors.
        
        Args:
            account_id: Account identifier
            
        Returns:
            List of co-users on shared devices
        """
        driver = get_driver()
        
        query = """
        MATCH (a:Account {account_id: $account_id})-[:USES_DEVICE]->(d:Device)
        MATCH (d)<-[:USES_DEVICE]-(other:Account)
        WHERE other.account_id <> a.account_id
        RETURN {
            account_id: other.account_id,
            name: other.name,
            device_id: d.device_id,
            device_name: d.device_name,
            is_known_fraud: other.is_known_fraud
        } as shared_device_user
        """
        
        # Use managed transaction for automatic retry on transient errors
        async def fetch_devices(tx):
            """Transaction function: execute query and return results."""
            result = await tx.run(query, {"account_id": account_id})
            return await result.data()
        
        async with driver.session() as session:
            records = await session.execute_read(fetch_devices)
            return [record["shared_device_user"] for record in records]

    @staticmethod
    async def get_shared_phone_numbers(account_id: str) -> List[Dict[str, Any]]:
        """
        Find other accounts sharing a phone number with the given account (async).
        Uses execute_read() for automatic retry on transient errors.
        
        Args:
            account_id: Account identifier
            
        Returns:
            List of accounts with shared phone numbers
        """
        driver = get_driver()
        
        query = """
        MATCH (a:Account {account_id: $account_id})-[:HAS_PHONE]->(p:PhoneNumber)
        MATCH (p)<-[:HAS_PHONE]-(other:Account)
        WHERE other.account_id <> a.account_id
        RETURN {
            account_id: other.account_id,
            name: other.name,
            phone: p.phone_number,
            is_known_fraud: other.is_known_fraud
        } as shared_phone_user
        """
        
        # Use managed transaction for automatic retry on transient errors
        async def fetch_phones(tx):
            """Transaction function: execute query and return results."""
            result = await tx.run(query, {"account_id": account_id})
            return await result.data()
        
        async with driver.session() as session:
            records = await session.execute_read(fetch_phones)
            return [record["shared_phone_user"] for record in records]

    @staticmethod
    async def get_shared_ip_addresses(account_id: str) -> List[Dict[str, Any]]:
        """
        Find other accounts accessing from the same IP address (async).
        Uses execute_read() for automatic retry on transient errors.
        
        Args:
            account_id: Account identifier
            
        Returns:
            List of accounts with shared IP addresses
        """
        driver = get_driver()
        
        query = """
        MATCH (a:Account {account_id: $account_id})-[:ACCESSED_FROM_IP]->(ip:IPAddress)
        MATCH (ip)<-[:ACCESSED_FROM_IP]-(other:Account)
        WHERE other.account_id <> a.account_id
        RETURN {
            account_id: other.account_id,
            name: other.name,
            ip_address: ip.ip_address,
            is_known_fraud: other.is_known_fraud
        } as shared_ip_user
        """
        
        # Use managed transaction for automatic retry on transient errors
        async def fetch_ips(tx):
            """Transaction function: execute query and return results."""
            result = await tx.run(query, {"account_id": account_id})
            return await result.data()
        
        async with driver.session() as session:
            records = await session.execute_read(fetch_ips)
            return [record["shared_ip_user"] for record in records]

    @staticmethod
    async def get_direct_transactions(account_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get direct transactions with other accounts (async).
        Uses execute_read() for automatic retry on transient errors.
        
        Args:
            account_id: Account identifier
            limit: Maximum results
            
        Returns:
            List of transaction relationships
        """
        driver = get_driver()
        
        query = """
        MATCH (a:Account {account_id: $account_id})-[t:TRANSACTED_WITH]->(other:Account)
        RETURN {
            other_account_id: other.account_id,
            other_account_name: other.name,
            transaction_count: t.transaction_count,
            total_amount: t.total_amount,
            is_known_fraud: other.is_known_fraud
        } as transaction
        LIMIT $limit
        """
        
        # Use managed transaction for automatic retry on transient errors
        async def fetch_transactions(tx):
            """Transaction function: execute query and return results."""
            result = await tx.run(query, {"account_id": account_id, "limit": limit})
            return await result.data()
        
        async with driver.session() as session:
            records = await session.execute_read(fetch_transactions)
            return [record["transaction"] for record in records]

    @staticmethod
    async def get_all_accounts(limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get all accounts (for dashboard listing) (async).
        Uses execute_read() for automatic retry on transient errors.
        
        Args:
            limit: Maximum results
            
        Returns:
            List of accounts
        """
        driver = get_driver()
        
        query = """
        MATCH (a:Account)
        RETURN {
            account_id: a.account_id,
            name: a.name,
            email: a.email,
            risk_level: a.risk_level,
            is_known_fraud: a.is_known_fraud,
            status: a.status
        } as account
        LIMIT $limit
        """
        
        # Use managed transaction for automatic retry on transient errors
        async def fetch_all_accounts(tx):
            """Transaction function: execute query and return results."""
            result = await tx.run(query, {"limit": limit})
            return await result.data()
        
        async with driver.session() as session:
            records = await session.execute_read(fetch_all_accounts)
            return [record["account"] for record in records]
