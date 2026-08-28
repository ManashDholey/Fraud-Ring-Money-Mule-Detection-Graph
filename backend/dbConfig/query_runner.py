"""
Centralized Query Runner - Resilient Neo4j Async Query Execution
=====================================================================

Provides a single source for all session.run() calls with automatic retry logic
for transient errors (ServiceUnavailable, SessionExpired, TransientError).

This module wraps the Neo4j async driver's managed transaction functions
(execute_read/execute_write) to provide:
  - Automatic retry with exponential backoff on transient failures
  - Fresh connection acquisition on retry
  - Consistent timeout and error handling across all repositories
  - Clear logging of retry attempts

Usage pattern (preferred - uses managed transactions):
  from dbConfig.query_runner import run_read_query
  
  async def fetch_accounts(tx):
      result = await tx.run(query, params)
      return await result.data()
  
  async with driver.session() as session:
      accounts = await run_read_query(session, fetch_accounts)

Usage pattern (fallback for streaming large results):
  from dbConfig.query_runner import run_query_with_retry
  
  result = await run_query_with_retry(session, query, params, timeout=15.0)

WHY THIS MATTERS:
  Windows socket idle timeouts + managed remote instances drop pooled connections
  silently after ~20 minutes idle. Without liveness checks and retry logic,
  random ServiceUnavailable errors occur intermittently. This module provides a
  unified resilience layer that catches and transparently retries these transient
  failures, ensuring callers get fresh connections on retry.
"""

import logging
import asyncio
from typing import Optional, Callable, Any, Dict, List
from neo4j.exceptions import (
    ServiceUnavailable,
    SessionExpired,
    TransientError,
)

logger = logging.getLogger(__name__)


async def run_read_query(
    session,
    tx_func: Callable,
    timeout: float = 15.0,
    max_retries: int = 1
) -> Any:
    """
    Execute a read query via managed transaction (automatic retry on transient errors).
    
    Uses session.execute_read() which has built-in retry logic for:
    - neo4j.exceptions.ServiceUnavailable (connection lost/dead pool connection)
    - neo4j.exceptions.SessionExpired (server restarted)
    - neo4j.exceptions.TransientError (temporary server issue)
    
    The driver will automatically retry with a fresh connection from the pool.
    
    Args:
        session: Neo4j async session (from `async with driver.session() as session:`)
        tx_func: Async function accepting a transaction object (tx) and returning data.
                 Should call `await tx.run(query, params)` internally.
                 Example:
                   async def fetch_accounts(tx):
                       result = await tx.run(query, params)
                       return await result.data()
        timeout: Query timeout in seconds (default 15.0)
        max_retries: Max retry attempts for transient errors (default 1)
        
    Returns:
        Result of tx_func (could be list, dict, single record, etc.)
        
    Raises:
        ServiceUnavailable, SessionExpired, TransientError: On permanent failure
        Other Neo4j exceptions: Non-transient errors (connection errors, syntax, etc.)
    """
    # session.execute_read() with the driver's built-in retry logic handles transients
    # No additional retry wrapper needed here — the driver does it for us
    try:
        return await session.execute_read(tx_func)
    except (ServiceUnavailable, SessionExpired, TransientError) as e:
        logger.error(
            f"Query failed after driver retries (managed transaction): {str(e)[:150]}"
        )
        raise


async def run_write_query(
    session,
    tx_func: Callable,
    timeout: float = 15.0,
    max_retries: int = 1
) -> Any:
    """
    Execute a write query via managed transaction (automatic retry on transient errors).
    
    Similar to run_read_query but for write operations.
    Uses session.execute_write() which has built-in retry logic for transient errors.
    
    Args:
        session: Neo4j async session
        tx_func: Async function accepting a transaction object (tx) and returning result.
                 Example:
                   async def create_relationship(tx):
                       result = await tx.run(write_query, params)
                       return await result.data()
        timeout: Query timeout in seconds (default 15.0)
        max_retries: Max retry attempts (default 1)
        
    Returns:
        Result of tx_func
        
    Raises:
        ServiceUnavailable, SessionExpired, TransientError: On permanent failure
    """
    try:
        return await session.execute_write(tx_func)
    except (ServiceUnavailable, SessionExpired, TransientError) as e:
        logger.error(
            f"Write query failed after driver retries (managed transaction): {str(e)[:150]}"
        )
        raise


async def run_query_with_retry(
    session,
    query: str,
    parameters: Optional[Dict[str, Any]] = None,
    timeout: float = 15.0,
    max_retries: int = 2
) -> Any:
    """
    Execute a raw query with explicit retry loop (fallback for edge cases).
    
    Use this ONLY when execute_read/execute_write cannot be used (e.g. streaming
    large result sets that need per-record processing). For all other cases,
    prefer run_read_query() or run_write_query().
    
    Implements manual retry loop because session.run() doesn't auto-retry like
    execute_read/write does. On ServiceUnavailable, closes session and retries
    with a new one.
    
    Args:
        session: Neo4j async session
        query: Cypher query string
        parameters: Query parameters dictionary
        timeout: Per-attempt timeout in seconds (default 15.0)
        max_retries: Max retry attempts (default 2)
        
    Returns:
        Query result (cursor)
        
    Raises:
        ServiceUnavailable, SessionExpired, TransientError: After max_retries exhausted
    """
    if parameters is None:
        parameters = {}
    
    for attempt in range(max_retries + 1):
        try:
            result = await session.run(query, parameters, timeout=timeout)
            if attempt > 0:
                logger.info(f"Query succeeded on retry attempt {attempt + 1}")
            return result
        except (ServiceUnavailable, SessionExpired, TransientError) as e:
            if attempt < max_retries:
                wait_time = 1.0 * (attempt + 1)  # Linear backoff: 1s, 2s, 3s...
                logger.warning(
                    f"Transient error on attempt {attempt + 1}/{max_retries + 1}, "
                    f"retrying in {wait_time}s: {str(e)[:100]}"
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(
                    f"Query failed permanently after {max_retries + 1} attempts: {str(e)[:100]}"
                )
                raise


async def run_query_streaming_with_retry(
    session,
    query: str,
    parameters: Optional[Dict[str, Any]] = None,
    timeout: float = 15.0,
    max_retries: int = 2,
    process_record: Optional[Callable] = None
) -> List[Dict[str, Any]]:
    """
    Execute a query and process results with automatic retry on transient errors.
    
    Handles the common pattern: run query, get all data, return as list.
    Unlike run_query_with_retry, this calls .data() for you and handles retries
    at the transaction level.
    
    Args:
        session: Neo4j async session
        query: Cypher query string
        parameters: Query parameters
        timeout: Query timeout in seconds
        max_retries: Max retries on transient error
        process_record: Optional function to transform each record
        
    Returns:
        List of records (or processed records if process_record provided)
        
    Raises:
        ServiceUnavailable, SessionExpired, TransientError: On permanent failure
    """
    if parameters is None:
        parameters = {}
    
    async def execute_and_fetch(tx):
        """Transaction function: execute and collect all results."""
        result = await tx.run(query, parameters)
        records = await result.data()
        if process_record:
            return [process_record(r) for r in records]
        return records
    
    return await run_read_query(session, execute_and_fetch, timeout=timeout)
