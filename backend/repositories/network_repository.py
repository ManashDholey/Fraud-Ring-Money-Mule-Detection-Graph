"""
Network Repository - Fraud Ring and Money Mule Detection
Handles all CognoDB queries for fraud detection patterns.
Uses async/await throughout for non-blocking operations.
Implements efficient keyset (cursor-based) pagination.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dbConfig.db_async import get_driver
from dto.graph import FraudRingDTO, MoneyMuleChainDTO
from dto.pagination import PaginatedResponse
from utils.cursor_paginator import CursorPaginator
import base64

logger = logging.getLogger(__name__)


class NetworkRepository:
    """Repository for network analysis: fraud rings and money mules."""

    @staticmethod
    async def get_fraud_rings_paginated(
        limit: int = 25,
        cursor: Optional[str] = None
    ) -> PaginatedResponse[FraudRingDTO]:
        """
        Get fraud rings with keyset (cursor-based) pagination.
        Uses WHERE clause for efficient pagination instead of OFFSET.
        
        Args:
            limit: Items per page (max 100)
            cursor: Pagination cursor (opaque base64 token)
            
        Returns:
            PaginatedResponse with FraudRingDTOs
        """
        limit = min(limit, 100)
        
        # Decode cursor to get last_ring_id for keyset pagination
        last_ring_id = None
        if cursor:
            try:
                cursor_data = CursorPaginator.decode_cursor(cursor)
                if cursor_data:
                    last_ring_id = cursor_data.get("id")
            except ValueError as e:
                logger.debug(f"Invalid cursor value in get_fraud_rings_paginated: {e}")
                pass
        
        driver = get_driver()
        
        # Query to detect fraud rings (clusters of connected fraud accounts)
        # Finds Account pairs with 1+ shared identifiers (device, phone, IP, card)
        # Uses keyset pagination: WHERE ring_id > last_ring_id ORDER BY ring_id ASC
        if last_ring_id:
            query = """
            MATCH (a1:Account)-[:USES_DEVICE]->(d:Device)<-[:USES_DEVICE]-(a2:Account)
            WHERE a1.is_known_fraud = true AND a1.account_id < a2.account_id
            WITH a1, a2, 1 as device_shared
            OPTIONAL MATCH (a1)-[:HAS_PHONE]->(p:PhoneNumber)<-[:HAS_PHONE]-(a2)
            WITH a1, a2, device_shared + (CASE WHEN p IS NOT NULL THEN 1 ELSE 0 END) as shared_count
            OPTIONAL MATCH (a1)-[:ACCESSED_FROM_IP]->(ip:IPAddress)<-[:ACCESSED_FROM_IP]-(a2)
            WITH a1, a2, shared_count + (CASE WHEN ip IS NOT NULL THEN 1 ELSE 0 END) as shared_count
            WITH a1, a2, shared_count,
                 CASE 
                    WHEN a1.risk_level = 'CRITICAL' OR a2.risk_level = 'CRITICAL' THEN 'CRITICAL'
                    WHEN a1.risk_level = 'HIGH' OR a2.risk_level = 'HIGH' THEN 'HIGH'
                    ELSE 'MEDIUM'
                 END as risk_level,
                 (COALESCE(a1.risk_score, 0) + COALESCE(a2.risk_score, 0)) / 2 as risk_score,
                 CASE WHEN a1.is_known_fraud THEN 1 ELSE 0 END +
                 CASE WHEN a2.is_known_fraud THEN 1 ELSE 0 END as known_fraud_count
            WITH {
                ring_id: 'RING_' + toString(a1.account_id) + '_' + toString(a2.account_id),
                risk_level: risk_level,
                risk_score: risk_score,
                member_count: 2,
                known_fraud_count: known_fraud_count,
                detection_reason: 'Multiple shared identifiers between known/suspected fraud accounts',
                account_ids: [a1.account_id, a2.account_id]
            } as ring
            WHERE ring.ring_id > $last_ring_id
            RETURN ring
            ORDER BY ring.ring_id ASC
            LIMIT $limit
            """
            params = {"last_ring_id": last_ring_id, "limit": limit + 1}
        else:
            query = """
            MATCH (a1:Account)-[:USES_DEVICE]->(d:Device)<-[:USES_DEVICE]-(a2:Account)
            WHERE a1.is_known_fraud = true AND a1.account_id < a2.account_id
            WITH a1, a2, 1 as device_shared
            OPTIONAL MATCH (a1)-[:HAS_PHONE]->(p:PhoneNumber)<-[:HAS_PHONE]-(a2)
            WITH a1, a2, device_shared + (CASE WHEN p IS NOT NULL THEN 1 ELSE 0 END) as shared_count
            OPTIONAL MATCH (a1)-[:ACCESSED_FROM_IP]->(ip:IPAddress)<-[:ACCESSED_FROM_IP]-(a2)
            WITH a1, a2, shared_count + (CASE WHEN ip IS NOT NULL THEN 1 ELSE 0 END) as shared_count
            WITH a1, a2, shared_count,
                 CASE 
                    WHEN a1.risk_level = 'CRITICAL' OR a2.risk_level = 'CRITICAL' THEN 'CRITICAL'
                    WHEN a1.risk_level = 'HIGH' OR a2.risk_level = 'HIGH' THEN 'HIGH'
                    ELSE 'MEDIUM'
                 END as risk_level,
                 (COALESCE(a1.risk_score, 0) + COALESCE(a2.risk_score, 0)) / 2 as risk_score,
                 CASE WHEN a1.is_known_fraud THEN 1 ELSE 0 END +
                 CASE WHEN a2.is_known_fraud THEN 1 ELSE 0 END as known_fraud_count
            WITH {
                ring_id: 'RING_' + toString(a1.account_id) + '_' + toString(a2.account_id),
                risk_level: risk_level,
                risk_score: risk_score,
                member_count: 2,
                known_fraud_count: known_fraud_count,
                detection_reason: 'Multiple shared identifiers between known/suspected fraud accounts',
                account_ids: [a1.account_id, a2.account_id]
            } as ring
            RETURN ring
            ORDER BY ring.ring_id ASC
            LIMIT $limit
            """
            params = {"limit": limit + 1}
        
        # Use managed transaction for automatic retry on transient errors
        async def fetch_fraud_rings(tx):
            """Transaction function: execute query and return results."""
            result = await tx.run(query, params)
            return await result.data()
        
        async with driver.session() as session:
            records = await session.execute_read(fetch_fraud_rings)
        
        # Extract ring data
        rings_data = [record["ring"] for record in records]
        
        # Check if there are more records
        has_more = len(rings_data) > limit
        if has_more:
            rings_data = rings_data[:limit]
        
        # Create DTOs
        rings = [
            FraudRingDTO(
                ringId=ring.get('ring_id', f"RING_{i}"),
                riskLevel=ring.get('risk_level', 'MEDIUM'),
                riskScore=float(ring.get('risk_score', 0)),
                memberCount=ring.get('member_count', 2),
                knownFraudCount=ring.get('known_fraud_count', 0),
                detectionReason=ring.get('detection_reason', ''),
                accountIds=ring.get('account_ids', [])
            )
            for i, ring in enumerate(rings_data)
        ]
        
        # Generate next cursor using the last ring's ring_id
        next_cursor = None
        if has_more and rings_data:
            last_ring = rings_data[-1]
            next_cursor = CursorPaginator.encode_cursor(
                last_item_id=last_ring.get('ring_id'),
                last_item_key=last_ring.get('ring_id'),
                sort_field='ring_id'
            )
        
        return PaginatedResponse(
            items=rings,
            cursor=next_cursor,
            has_next_page=has_more,
            page_size=limit
        )

    @staticmethod
    async def get_money_mule_chains_paginated(
        limit: int = 25,
        cursor: Optional[str] = None
    ) -> PaginatedResponse[MoneyMuleChainDTO]:
        """
        Get money mule chains with keyset (cursor-based) pagination.
        Uses WHERE clause for efficient pagination instead of OFFSET.
        
        Args:
            limit: Items per page (max 100)
            cursor: Pagination cursor (opaque base64 token)
            
        Returns:
            PaginatedResponse with MoneyMuleChainDTOs
        """
        limit = min(limit, 100)
        
        # Decode cursor to get last_chain_id for keyset pagination
        last_chain_id = None
        if cursor:
            try:
                cursor_data = CursorPaginator.decode_cursor(cursor)
                if cursor_data:
                    last_chain_id = cursor_data.get("id")
            except ValueError as e:
                logger.debug(f"Invalid cursor value in get_money_mule_chains_paginated: {e}")
                pass
        
        driver = get_driver()
        
        # Query to detect money mule chains
        # (linear chains of accounts transacting with high risk/known fraud accounts)
        # Uses keyset pagination: WHERE chain_id > last_chain_id ORDER BY chain_id ASC
        if last_chain_id:
            query = """
            MATCH path = (a1:Account)-[:TRANSACTED_WITH]-(a2:Account)-[:TRANSACTED_WITH]-(a3:Account)
            WHERE (a1.is_known_fraud = true OR a2.risk_level = 'HIGH' OR a3.is_known_fraud = true)
            AND LENGTH(path) >= 2
            WITH a1, a2, a3, path,
                 CASE 
                    WHEN a1.risk_level = 'CRITICAL' OR a3.risk_level = 'CRITICAL' THEN 'CRITICAL'
                    ELSE 'HIGH'
                 END as risk_level,
                 (COALESCE(a1.risk_score, 0) + COALESCE(a2.risk_score, 0) + COALESCE(a3.risk_score, 0)) / 3 as risk_score
            WITH {
                chain_id: 'CHAIN_' + toString(a1.account_id) + '_' + toString(a3.account_id),
                risk_level: risk_level,
                risk_score: risk_score,
                chain_length: 3,
                account_ids: [a1.account_id, a2.account_id, a3.account_id],
                detection_reason: 'Linear transaction chain between fraud accounts (potential money laundering)'
            } as chain
            WHERE chain.chain_id > $last_chain_id
            RETURN chain
            ORDER BY chain.chain_id ASC
            LIMIT $limit
            """
            params = {"last_chain_id": last_chain_id, "limit": limit + 1}
        else:
            query = """
            MATCH path = (a1:Account)-[:TRANSACTED_WITH]-(a2:Account)-[:TRANSACTED_WITH]-(a3:Account)
            WHERE (a1.is_known_fraud = true OR a2.risk_level = 'HIGH' OR a3.is_known_fraud = true)
            AND LENGTH(path) >= 2
            WITH a1, a2, a3, path,
                 CASE 
                    WHEN a1.risk_level = 'CRITICAL' OR a3.risk_level = 'CRITICAL' THEN 'CRITICAL'
                    ELSE 'HIGH'
                 END as risk_level,
                 (COALESCE(a1.risk_score, 0) + COALESCE(a2.risk_score, 0) + COALESCE(a3.risk_score, 0)) / 3 as risk_score
            RETURN {
                chain_id: 'CHAIN_' + toString(a1.account_id) + '_' + toString(a3.account_id),
                risk_level: risk_level,
                risk_score: risk_score,
                chain_length: 3,
                account_ids: [a1.account_id, a2.account_id, a3.account_id],
                detection_reason: 'Linear transaction chain between fraud accounts (potential money laundering)'
            } as chain
            ORDER BY chain.chain_id ASC
            LIMIT $limit
            """
            params = {"limit": limit + 1}
        
        # Use managed transaction for automatic retry on transient errors
        async def fetch_money_mule_chains(tx):
            """Transaction function: execute query and return results."""
            result = await tx.run(query, params)
            return await result.data()
        
        async with driver.session() as session:
            records = await session.execute_read(fetch_money_mule_chains)
        
        # Extract chain data
        chains_data = [record["chain"] for record in records]
        
        # Check if there are more records
        has_more = len(chains_data) > limit
        if has_more:
            chains_data = chains_data[:limit]
        
        # Create DTOs
        chains = [
            MoneyMuleChainDTO(
                chainId=chain.get('chain_id', f"CHAIN_{i}"),
                riskLevel=chain.get('risk_level', 'HIGH'),
                riskScore=float(chain.get('risk_score', 0)),
                chainLength=chain.get('chain_length', 3),
                accountIds=chain.get('account_ids', []),
                detectionReason=chain.get('detection_reason', '')
            )
            for i, chain in enumerate(chains_data)
        ]
        
        # Generate next cursor using the last chain's chain_id
        next_cursor = None
        if has_more and chains_data:
            last_chain = chains_data[-1]
            next_cursor = CursorPaginator.encode_cursor(
                last_item_id=last_chain.get('chain_id'),
                last_item_key=last_chain.get('chain_id'),
                sort_field='chain_id'
            )
        
        return PaginatedResponse(
            items=chains,
            cursor=next_cursor,
            has_next_page=has_more,
            page_size=limit
        )
