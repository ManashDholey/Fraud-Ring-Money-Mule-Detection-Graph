"""
Dashboard Repository - Async Data Access Layer
Implements dashboard statistics queries for metrics and KPIs.
"""

from typing import Dict, Any, Optional
from dbConfig.db_async import get_driver
import logging

logger = logging.getLogger(__name__)


class DashboardRepository:
    """Repository for dashboard statistics queries."""

    @staticmethod
    async def get_dashboard_statistics() -> Optional[Dict[str, Any]]:
        """
        Get comprehensive dashboard statistics including account counts by risk level.
        
        Returns:
            Dictionary with total_count, fraud_count, medium_risk_count, high_risk_count, 
            critical_risk_count, and fraud_ring_count
        """
        try:
            driver = get_driver()
            
            async with driver.session() as session:
                # Query ALL accounts to get accurate counts (not biased sample)
                result = await session.run("""
                MATCH (a:Account)
                RETURN 
                  count(a) as total_count,
                  sum(CASE WHEN a.is_known_fraud = true THEN 1 ELSE 0 END) as fraud_count,
                  sum(CASE WHEN a.risk_level = 'MEDIUM' THEN 1 ELSE 0 END) as medium_risk_count,
                  sum(CASE WHEN a.risk_level = 'HIGH' THEN 1 ELSE 0 END) as high_risk_count,
                  sum(CASE WHEN a.risk_level = 'CRITICAL' THEN 1 ELSE 0 END) as critical_risk_count
                """)
                
                records = await result.data()
                account_stats = records[0] if records else {}
                
                # Query fraud rings (computed from shared device pairs with known-fraud accounts)
                result = await session.run("""
                MATCH (a1:Account)-[:USES_DEVICE]->(d:Device)<-[:USES_DEVICE]-(a2:Account)
                WHERE a1.is_known_fraud = true AND a1.account_id < a2.account_id
                RETURN count(*) as count
                """)
                records = await result.data()
                fraud_ring_count = records[0]["count"] if records else 0
                
                return {
                    "total_count": account_stats.get("total_count", 0),
                    "fraud_count": account_stats.get("fraud_count", 0),
                    "medium_risk_count": account_stats.get("medium_risk_count", 0),
                    "high_risk_count": account_stats.get("high_risk_count", 0),
                    "critical_risk_count": account_stats.get("critical_risk_count", 0),
                    "fraud_ring_count": fraud_ring_count
                }
        except Exception as e:
            logger.error(f"Error fetching dashboard statistics: {e}")
            return None
