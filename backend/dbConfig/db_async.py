"""
Fraud Detection - Async CognoDB Connection Manager
Fully asynchronous database connection using AsyncGraphDatabase.
All operations are non-blocking via asyncio.
"""

from neo4j import AsyncGraphDatabase
import os
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load CognoDB credentials from environment variables
COGNODB_URI = os.getenv("COGNODB_URI")
COGNODB_USERNAME = os.getenv("COGNODB_USERNAME")
COGNODB_PASSWORD = os.getenv("COGNODB_PASSWORD")

# Validate required environment variables
if not COGNODB_URI:
    raise ValueError("COGNODB_URI environment variable is required")
if not COGNODB_USERNAME:
    raise ValueError("COGNODB_USERNAME environment variable is required")
if not COGNODB_PASSWORD:
    raise ValueError("COGNODB_PASSWORD environment variable is required")

# Initialize async Neo4j driver with resilience settings for managed remote instance (CognoDB)
# CRITICAL WINDOWS ISSUE: Pooled connections sit idle and are silently dropped by Windows socket
# timeouts (~20min) or managed instance idle disconnects. The driver doesn't detect this until
# the next query tries to use the connection, causing:
#   neo4j.exceptions.ServiceUnavailable: Failed to read from defunct connection ...
#   caused by OSError(22, 'The semaphore timeout period has expired', None, 121, None)
#
# Solution: Configure driver to proactively detect and replace stale connections.
# Do NOT pass conflicting encrypted= or trusted_certificates= settings.
# Reference: https://neo4j.com/docs/python-manual/5.14/configuration/
driver = AsyncGraphDatabase.driver(
    COGNODB_URI,
    auth=(COGNODB_USERNAME, COGNODB_PASSWORD),
    # === CONNECTION POOL RESILIENCE ===
    max_connection_pool_size=50,           # Max concurrent connections (reasonable for fraud dashboard)
    
    # === CONNECTION RECYCLING ===
    # Windows/managed instances drop idle connections after ~20min. Force refresh before that.
    # Also prevents accumulation of stale protocol state on very long-lived connections.
    max_connection_lifetime=15 * 60,       # 15min: recycle all connections proactively
                                           # (before ~20min idle-drop threshold)
    
    # === TIMEOUTS ===
    connection_timeout=30.0,               # 30s to establish initial connection (reasonable for internet)
    connection_acquisition_timeout=30.0,   # 30s: max wait for a connection from pool
                                           # (prevents indefinite hangs if pool saturated)
    
    # === TCP KEEPALIVE ===
    # keep_alive=True is enabled by default (connection_config feature in driver v5.14+)
    # Sends periodic TCP keepalive packets to detect dead peer sooner (OS-level detection)
    # Note: liveness_check_timeout is not supported in neo4j==5.14.1; use connection_acquisition_timeout
    #       and TCP keepalive for connection health monitoring
)


async def verify_connectivity() -> bool:
    """
    Verify async connection to CognoDB.
    
    Returns:
        True if connected, raises otherwise
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        await driver.verify_connectivity()
        logger.info("Successfully connected to CognoDB (async)")
        return True
    except Exception as e:
        raise RuntimeError(f"Failed to connect to CognoDB: {str(e)}")


def get_driver():
    """Return the async Neo4j driver instance."""
    return driver


async def close_driver():
    """Close the async Neo4j driver connection."""
    if driver:
        await driver.close()


async def run_query(query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Execute a Cypher query asynchronously with parameterized parameters.
    
    Args:
        query: Cypher query string with parameters
        parameters: Dictionary of parameters for the query
        
    Returns:
        Query result as list of records
        
    Raises:
        Exception: If query execution fails
    """
    if parameters is None:
        parameters = {}
    
    async with driver.session() as session:
        try:
            result = await session.run(query, parameters)
            data = await result.data()
            return data
        except Exception as e:
            raise RuntimeError(f"Query execution failed: {str(e)}")
