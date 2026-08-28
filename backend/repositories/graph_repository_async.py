"""
Graph Repository - Async Data Access Layer
Implements async multi-hop, variable-length path queries.
Uses asyncio.gather() for concurrent fraud detection queries.
"""

from typing import List, Dict, Any
from dbConfig.db_async import get_driver
from dto.graph import GraphResponseDTO, GraphNodeDTO, GraphEdgeDTO
from neo4j.exceptions import TransientError, ServiceUnavailable, SessionExpired
import asyncio
import logging

logger = logging.getLogger(__name__)


class GraphRepository:
    """Repository for async complex graph traversal and fraud detection queries."""

    @staticmethod
    async def _run_with_transient_retry(
        session,
        query: str,
        parameters: dict = None,
        timeout: float = 15.0,
        max_retries: int = 1
    ):
        """
        Execute a query with retry logic for transient errors only.
        
        Args:
            session: Neo4j async session
            query: Cypher query string
            parameters: Query parameters
            timeout: Per-query timeout in seconds
            max_retries: Number of retries on transient errors (0-2 recommended)
            
        Returns:
            Query result
            
        Raises:
            TransientError: On permanent failure after retries
            Exception: On non-transient errors (fails immediately)
        """
        for attempt in range(max_retries + 1):
            try:
                result = await session.run(query, parameters, timeout=timeout)
                return result
            except (TransientError, ServiceUnavailable, SessionExpired) as e:
                if attempt < max_retries:
                    wait_time = 1.0 * (attempt + 1)  # Linear backoff: 1s, 2s, 3s
                    logger.warning(
                        f"Transient error on attempt {attempt + 1}, retrying in {wait_time}s: {str(e)[:100]}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Transient error persisted after {max_retries + 1} attempts: {str(e)[:100]}")
                    raise

    @staticmethod
    async def get_account_graph(account_id: str, depth: int = 2) -> GraphResponseDTO:
        """
        Get the neighborhood graph around an account asynchronously.
        Returns all Account nodes and relationships within N hops as a typed DTO.
        
        Args:
            account_id: Account identifier
            depth: Maximum traversal depth (1-3 recommended)
            
        Returns:
            GraphResponseDTO with nodes and edges properly typed
        """
        driver = get_driver()
        
        # Cap depth at 3 to prevent excessive queries
        depth = min(max(depth, 1), 3)
        
        nodes_dict = {}
        relationships_set = set()
        node_id_to_account = {}  # Map: internal_node_id -> account_id
        
        async with driver.session() as session:
            # Step 1: Get the starting account
            start_result = await session.run(
                "MATCH (a:Account {account_id: $account_id}) RETURN a",
                {"account_id": account_id}
            )
            
            start_record = None
            async for record in start_result:
                start_record = record
                break
            
            if not start_record:
                return GraphResponseDTO(nodes=[], edges=[], hasMoreConnections=False)
            
            start_node = start_record["a"]
            nodes_dict[start_node.id] = {
                "id": start_node.id,
                "account_id": start_node.get("account_id"),
                "display_name": start_node.get("display_name") or start_node.get("name") or "",
                "is_known_fraud": start_node.get("is_known_fraud"),
                "risk_level": start_node.get("risk_level"),
                "risk_score": start_node.get("risk_score"),
                "status": start_node.get("status")
            }
            node_id_to_account[start_node.id] = start_node.get("account_id")
        
        # Step 2: Get neighbors and relationships within depth
        # CRITICAL FIX: Use specific relationship types (not wildcard), add LIMIT, add timeout
        # Relationship types: TRANSACTED_WITH (money), USES_DEVICE/HAS_PHONE/ACCESSED_FROM_IP (identity)
        async with driver.session() as session:
            # Use retry wrapper for expensive variable-length traversal query
            # Per-query timeout: 15 seconds (prevents hanging on dense graphs)
            # 1 retry on transient errors (total 2 attempts max)
            neighbor_result = await GraphRepository._run_with_transient_retry(
                session,
                f"""
                MATCH (a:Account {{account_id: $account_id}})
                      -[rel:TRANSACTED_WITH|USES_DEVICE|HAS_PHONE|ACCESSED_FROM_IP*1..{depth}]-
                      (b:Account)
                RETURN DISTINCT b, rel
                LIMIT 100
                """,
                {"account_id": account_id},
                timeout=15.0,
                max_retries=1  # 1 retry on transient errors
            )
            
            async for record in neighbor_result:
                neighbor = record.get("b")
                rel_path = record.get("rel")
                
                # Add neighbor node
                if neighbor:
                    nodes_dict[neighbor.id] = {
                        "id": neighbor.id,
                        "account_id": neighbor.get("account_id"),
                        "display_name": neighbor.get("display_name") or neighbor.get("name") or "",
                        "is_known_fraud": neighbor.get("is_known_fraud"),
                        "risk_level": neighbor.get("risk_level"),
                        "risk_score": neighbor.get("risk_score"),
                        "status": neighbor.get("status")
                    }
                    node_id_to_account[neighbor.id] = neighbor.get("account_id")
                
                # Extract individual relationships from the path
                if rel_path:
                    # rel_path is a list of relationships
                    for rel in rel_path:
                        rel_key = (rel.start_node.id, rel.end_node.id, rel.type)
                        relationships_set.add(rel_key)
        
        # Step 3: Convert raw data to DTOs
        graph_nodes = []
        for node_data in nodes_dict.values():
            node_dto = GraphNodeDTO(
                id=node_data["account_id"],
                type="ACCOUNT",
                label=node_data.get("display_name") or node_data.get("account_id", "Unknown"),
                riskLevel=node_data.get("risk_level"),
                riskScore=node_data.get("risk_score"),
                isKnownFraud=node_data.get("is_known_fraud"),
                metadata={"status": node_data.get("status")}
            )
            graph_nodes.append(node_dto)
        
        graph_edges = []
        edge_id_counter = 0
        for src_id, tgt_id, rel_type in relationships_set:
            # Only include edges where both endpoints are Account nodes
            src_account = node_id_to_account.get(src_id)
            tgt_account = node_id_to_account.get(tgt_id)
            
            # Skip edges with non-Account nodes (intermediate nodes in paths)
            if src_account and tgt_account:
                edge_dto = GraphEdgeDTO(
                    id=f"EDGE_{edge_id_counter}",
                    source=src_account,
                    target=tgt_account,
                    relationship=rel_type,
                    weight=None
                )
                graph_edges.append(edge_dto)
                edge_id_counter += 1
        
        return GraphResponseDTO(
            nodes=graph_nodes,
            edges=graph_edges,
            hasMoreConnections=False
        )

    @staticmethod
    async def detect_fraud_rings(limit: int = 10) -> List[Dict[str, Any]]:
        """
        Detect fraud rings asynchronously.
        Uses variable-length paths to find accounts connected through suspicious clusters.
        
        Args:
            limit: Maximum number of rings to return
            
        Returns:
            List of detected fraud rings with member accounts
        """
        driver = get_driver()
        
        query = """
        MATCH (a:Account)-[*2..4]->(b:Account)
        WHERE (a.is_known_fraud = true OR a.risk_level = 'HIGH')
        AND (b.is_known_fraud = true OR b.risk_level = 'HIGH')
        WITH a, b, length(shortestPath((a)-[*2..4]-(b))) as distance
        MATCH (a)-[:USES_DEVICE|HAS_PHONE|ACCESSED_FROM_IP|TRANSACTED_WITH*1..3]-(member:Account)
        WITH a, collect(DISTINCT member.account_id) as members, count(DISTINCT member) as ring_size
        WHERE ring_size >= 3
        RETURN {
            primary_account: a.account_id,
            primary_account_name: a.name,
            members: members,
            ring_size: ring_size,
            suspected_fraud_level: 'HIGH'
        } as fraud_ring
        LIMIT $limit
        """
        
        async with driver.session() as session:
            result = await session.run(query, {"limit": limit})
            records = await result.data()
            return [record["fraud_ring"] for record in records]

    @staticmethod
    async def detect_money_mule_paths(account_id: str, max_depth: int = 4) -> List[Dict[str, Any]]:
        """
        Detect money mule chains asynchronously.
        Variable-length TRANSACTED_WITH paths identify intermediary accounts.
        
        Args:
            account_id: Starting account (typically known fraud)
            max_depth: Maximum hops in the chain (1-4 recommended)
            
        Returns:
            List of detected mule chains
        """
        driver = get_driver()
        
        # Cap depth
        max_depth = min(max(max_depth, 1), 4)
        
        query = """
        MATCH p = (start:Account {account_id: $account_id})-[:TRANSACTED_WITH*1..""" + str(max_depth) + """]->(end:Account)
        WHERE length(p) >= 2
        RETURN {
            path_length: length(p),
            chain: [node in nodes(p) | {
                account_id: node.account_id,
                name: node.name,
                is_known_fraud: node.is_known_fraud,
                risk_level: node.risk_level
            }],
            total_hops: length(p)
        } as mule_chain
        ORDER BY path_length ASC
        LIMIT 50
        """
        
        async with driver.session() as session:
            result = await session.run(query, {"account_id": account_id})
            records = await result.data()
            return [record["mule_chain"] for record in records]

    @staticmethod
    async def get_fraud_proximity_scores(limit: int = 50) -> List[Dict[str, Any]]:
        """
        Calculate fraud proximity scores asynchronously.
        Returns accounts ranked by their relationship to known fraud accounts.
        
        Args:
            limit: Maximum accounts to score
            
        Returns:
            List of accounts with proximity scores
        """
        driver = get_driver()
        
        query = """
        MATCH (known_fraud:Account {is_known_fraud: true})
        MATCH (target:Account)
        WHERE target.account_id <> known_fraud.account_id
        MATCH paths = (target)-[*1..3]-(known_fraud)
        WITH target, count(DISTINCT paths) as path_count, min(length(paths)) as min_distance, 
             collect(DISTINCT type(relationships(paths[0])[0])) as connection_types
        RETURN {
            account_id: target.account_id,
            account_name: target.name,
            risk_level: target.risk_level,
            is_known_fraud: target.is_known_fraud,
            path_count: path_count,
            min_hops: min_distance,
            connection_types: connection_types,
            fraud_proximity_score: CASE 
                WHEN min_distance = 1 THEN 85
                WHEN min_distance = 2 THEN 60
                WHEN min_distance = 3 THEN 35
                ELSE 10
            END + (path_count * 5)
        } as proximity_result
        ORDER BY fraud_proximity_score DESC
        LIMIT $limit
        """
        
        async with driver.session() as session:
            result = await session.run(query, {"limit": limit})
            records = await result.data()
            return [record["proximity_result"] for record in records]

    @staticmethod
    async def get_investigation_paths(account_id: str, target_account_id: str) -> List[Dict[str, Any]]:
        """
        Get all paths between two accounts asynchronously.
        
        Args:
            account_id: Source account
            target_account_id: Target account
            
        Returns:
            List of connecting paths
        """
        driver = get_driver()
        
        query = """
        MATCH p = (source:Account {account_id: $account_id})-[*1..4]-(target:Account {account_id: $target_account_id})
        WITH p, length(p) as path_length
        RETURN {
            path_length: path_length,
            path_description: [node in nodes(p) | node.account_id],
            relationships: [rel in relationships(p) | type(rel)],
            explanation: CASE 
                WHEN path_length = 1 THEN "Direct connection"
                WHEN path_length = 2 THEN "Connected through one intermediary"
                ELSE "Connected through " + (path_length - 1) + " intermediaries"
            END
        } as investigation_path
        ORDER BY path_length ASC
        LIMIT 20
        """
        
        async with driver.session() as session:
            result = await session.run(query, {
                "account_id": account_id,
                "target_account_id": target_account_id
            })
            records = await result.data()
            return [record["investigation_path"] for record in records]

    @staticmethod
    async def get_suspicious_device_networks(limit: int = 20) -> List[Dict[str, Any]]:
        """
        Identify suspicious networks of accounts sharing the same device (async).
        
        Args:
            limit: Maximum networks to return
            
        Returns:
            List of device networks with member accounts
        """
        driver = get_driver()
        
        query = """
        MATCH (d:Device)
        MATCH (d)<-[:USES_DEVICE]-(a:Account)
        WITH d, collect({
            account_id: a.account_id,
            name: a.name,
            is_known_fraud: a.is_known_fraud
        }) as users, count(a) as user_count
        WHERE user_count > 1
        RETURN {
            device_id: d.device_id,
            device_name: d.device_name,
            user_count: user_count,
            users: users,
            has_fraud: any(user in users WHERE user.is_known_fraud = true)
        } as device_network
        ORDER BY user_count DESC
        LIMIT $limit
        """
        
        async with driver.session() as session:
            result = await session.run(query, {"limit": limit})
            records = await result.data()
            return [record["device_network"] for record in records]

    @staticmethod
    async def get_suspicious_ip_networks(limit: int = 20) -> List[Dict[str, Any]]:
        """
        Identify suspicious networks of accounts accessing from the same IP (async).
        
        Args:
            limit: Maximum networks to return
            
        Returns:
            List of IP networks with member accounts
        """
        driver = get_driver()
        
        query = """
        MATCH (ip:IPAddress)
        MATCH (ip)<-[:ACCESSED_FROM_IP]-(a:Account)
        WITH ip, collect({
            account_id: a.account_id,
            name: a.name,
            is_known_fraud: a.is_known_fraud
        }) as users, count(a) as user_count
        WHERE user_count > 1
        RETURN {
            ip_address: ip.ip_address,
            user_count: user_count,
            users: users,
            has_fraud: any(user in users WHERE user.is_known_fraud = true)
        } as ip_network
        ORDER BY user_count DESC
        LIMIT $limit
        """
        
        async with driver.session() as session:
            result = await session.run(query, {"limit": limit})
            records = await result.data()
            return [record["ip_network"] for record in records]

    @staticmethod
    async def execute_concurrent_fraud_checks(account_id: str) -> Dict[str, Any]:
        """
        Execute multiple fraud checks concurrently using asyncio.gather().
        Demonstrates non-blocking parallel query execution.
        
        Args:
            account_id: Account to check
            
        Returns:
            Dictionary with all fraud check results
        """
        # Execute all checks concurrently
        results = await asyncio.gather(
            GraphRepository.get_fraud_proximity_scores(limit=1),
            GraphRepository.detect_fraud_rings(limit=5),
            GraphRepository.detect_money_mule_paths(account_id, max_depth=4),
            GraphRepository.get_suspicious_device_networks(limit=10),
            GraphRepository.get_suspicious_ip_networks(limit=10),
            return_exceptions=True
        )
        
        return {
            "proximity_scores": results[0] if not isinstance(results[0], Exception) else [],
            "fraud_rings": results[1] if not isinstance(results[1], Exception) else [],
            "money_mule_paths": results[2] if not isinstance(results[2], Exception) else [],
            "device_networks": results[3] if not isinstance(results[3], Exception) else [],
            "ip_networks": results[4] if not isinstance(results[4], Exception) else [],
        }
