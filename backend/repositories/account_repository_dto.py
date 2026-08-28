"""
Account Repository - Enhanced with DTO Support
Implements cursor-based pagination and DTO mapping.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dbConfig.db_async import get_driver
from dto.account import AccountDTO, AccountConnectionsDTO
from dto.pagination import PaginatedResponse
from mappers.account_mapper import (
    AccountMapper,
    CardMapper,
    DeviceMapper,
    PhoneMapper,
    IPMapper,
    ConnectionMapper
)
from utils.cursor_paginator import CursorPaginator
import base64
import json

logger = logging.getLogger(__name__)


class AccountRepositoryDTO:
    """Repository for Account queries returning DTOs."""
    
    @staticmethod
    async def search_accounts_paginated(
        search_term: Optional[str] = None,
        limit: int = 25,
        cursor: Optional[str] = None
    ) -> PaginatedResponse[AccountDTO]:
        """
        Search accounts with keyset (cursor-based) pagination.
        Uses WHERE clause for efficient pagination instead of OFFSET.
        
        Args:
            search_term: Optional search query
            limit: Items per page (max 100)
            cursor: Cursor for pagination (base64 encoded {id, key})
            
        Returns:
            PaginatedResponse with AccountDTOs
        """
        limit = min(limit, 100)
        driver = get_driver()
        
        # Decode cursor to get last_id for keyset pagination
        last_id = None
        if cursor:
            try:
                cursor_data = CursorPaginator.decode_cursor(cursor)
                if cursor_data:
                    last_id = cursor_data.get("id")
            except ValueError as e:
                logger.debug(f"Invalid cursor value: {e}, treating as first-page request")
                pass
        
        # Build keyset pagination query (WHERE id > last_cursor ORDER BY id ASC)
        if search_term:
            if last_id:
                query = """
                MATCH (a:Account)
                WHERE (a.account_id CONTAINS $search_term OR a.display_name CONTAINS $search_term)
                AND a.account_id > $last_id
                RETURN {
                    account_id: a.account_id,
                    displayName: a.display_name,
                    email: a.email,
                    status: a.status,
                    riskLevel: a.risk_level,
                    isKnownFraud: a.is_known_fraud,
                    riskScore: COALESCE(a.risk_score, 0),
                    createdAt: a.created_at
                } as account
                ORDER BY a.account_id ASC
                LIMIT $limit
                """
                params = {"search_term": search_term, "last_id": last_id, "limit": limit + 1}
            else:
                query = """
                MATCH (a:Account)
                WHERE a.account_id CONTAINS $search_term OR a.display_name CONTAINS $search_term
                RETURN {
                    account_id: a.account_id,
                    displayName: a.display_name,
                    email: a.email,
                    status: a.status,
                    riskLevel: a.risk_level,
                    isKnownFraud: a.is_known_fraud,
                    riskScore: COALESCE(a.risk_score, 0),
                    createdAt: a.created_at
                } as account
                ORDER BY a.account_id ASC
                LIMIT $limit
                """
                params = {"search_term": search_term, "limit": limit + 1}
        else:
            if last_id:
                query = """
                MATCH (a:Account)
                WHERE a.account_id > $last_id
                RETURN {
                    account_id: a.account_id,
                    displayName: a.display_name,
                    email: a.email,
                    status: a.status,
                    riskLevel: a.risk_level,
                    isKnownFraud: a.is_known_fraud,
                    riskScore: COALESCE(a.risk_score, 0),
                    createdAt: a.created_at
                } as account
                ORDER BY a.account_id ASC
                LIMIT $limit
                """
                params = {"last_id": last_id, "limit": limit + 1}
            else:
                query = """
                MATCH (a:Account)
                RETURN {
                    account_id: a.account_id,
                    displayName: a.display_name,
                    email: a.email,
                    status: a.status,
                    riskLevel: a.risk_level,
                    isKnownFraud: a.is_known_fraud,
                    riskScore: COALESCE(a.risk_score, 0),
                    createdAt: a.created_at
                } as account
                ORDER BY a.account_id ASC
                LIMIT $limit
                """
                params = {"limit": limit + 1}
        
        # Use managed transaction (execute_read) for automatic retry on transient failures
        # This catches ServiceUnavailable, SessionExpired, TransientError and retries with backoff
        async def fetch_paginated_accounts(tx):
            """Transaction function: execute query and return results."""
            result = await tx.run(query, params)
            return await result.data()
        
        async with driver.session() as session:
            records_list = await session.execute_read(fetch_paginated_accounts)
        
        page_records = [record["account"] for record in records_list]
        
        # Check if there are more records
        has_more = len(page_records) > limit
        if has_more:
            page_records = page_records[:limit]
        
        # Generate next cursor using the last item's account_id
        next_cursor = None
        if has_more and page_records:
            last_account = page_records[-1]
            next_cursor = CursorPaginator.encode_cursor(
                last_item_id=last_account.get("account_id"),
                last_item_key=last_account.get("account_id"),
                sort_field="account_id"
            )
        
        # Map to DTOs
        account_dtos = AccountMapper.to_dto_list(page_records)
        
        return PaginatedResponse(
            items=account_dtos,
            cursor=next_cursor,
            has_next_page=has_more,
            page_size=limit
        )
    
    @staticmethod
    async def get_account_by_id_dto(account_id: str) -> Optional[AccountDTO]:
        """
        Get account details as DTO.
        
        Args:
            account_id: Account identifier
            
        Returns:
            AccountDTO or None if not found
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
            risk_score: COALESCE(a.risk_score, 0),
            created_at: a.created_at
        } as account
        """
        
        # Use managed transaction for automatic retry on transient failures
        async def fetch_account(tx):
            """Transaction function: execute query and return single result."""
            result = await tx.run(query, {"account_id": account_id})
            return await result.single()
        
        async with driver.session() as session:
            record = await session.execute_read(fetch_account)
            
            if not record:
                return None
            
            return AccountMapper.to_dto(record["account"])
    
    @staticmethod
    async def get_account_connections_dto(account_id: str) -> Optional[AccountConnectionsDTO]:
        """
        Get account with all its connections as DTO.
        
        Args:
            account_id: Account identifier
            
        Returns:
            AccountConnectionsDTO or None
        """
        driver = get_driver()
        
        # Get account + aggregated connections in single query
        query = """
        MATCH (a:Account {account_id: $account_id})
        OPTIONAL MATCH (a)-[:HAS_CARD]->(c:Card)
        OPTIONAL MATCH (a)-[:USES_DEVICE]->(d:Device)
        OPTIONAL MATCH (a)-[:HAS_PHONE]->(p:PhoneNumber)
        OPTIONAL MATCH (a)-[:ACCESSED_FROM_IP]->(ip:IPAddress)
        
        // Count connections for each shared resource
        OPTIONAL MATCH (d)<-[:USES_DEVICE]-(other_acct:Account)
        OPTIONAL MATCH (p)<-[:HAS_PHONE]-(other_phone:Account)
        OPTIONAL MATCH (ip)<-[:ACCESSED_FROM_IP]-(other_ip:Account)
        
        RETURN DISTINCT
            {
                account_id: a.account_id,
                name: a.name,
                email: a.email,
                status: a.status,
                risk_level: a.risk_level,
                is_known_fraud: a.is_known_fraud,
                created_at: a.created_at
            } as account,
            COLLECT(DISTINCT {
                card_id: c.card_number,
                card_number: c.card_number,
                card_type: c.card_type,
                status: c.status
            }) as cards,
            COLLECT(DISTINCT {
                device_id: d.device_id,
                device_name: d.device_name,
                account_count: COUNT(DISTINCT other_acct)
            }) as devices,
            COLLECT(DISTINCT {
                phone_number: p.phone_number,
                account_count: COUNT(DISTINCT other_phone)
            }) as phones,
            COLLECT(DISTINCT {
                ip_address: ip.ip_address,
                account_count: COUNT(DISTINCT other_ip)
            }) as ips
        """
        
        # Use managed transaction for automatic retry on transient failures
        async def fetch_connections(tx):
            """Transaction function: execute query and return single result."""
            result = await tx.run(query, {"account_id": account_id})
            return await result.single()
        
        async with driver.session() as session:
            record = await session.execute_read(fetch_connections)
            
            if not record:
                return None
            
            acct_data = record["account"]
            cards_data = [c for c in record.get("cards", []) if c.get("card_number")]
            devices_data = [d for d in record.get("devices", []) if d.get("device_id")]
            phones_data = [p for p in record.get("phones", []) if p.get("phone_number")]
            ips_data = [ip for ip in record.get("ips", []) if ip.get("ip_address")]
        
        # Map to DTO
        return ConnectionMapper.to_dto(
            acct_data,
            cards_data,
            devices_data,
            phones_data,
            ips_data
        )
