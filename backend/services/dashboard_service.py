"""
Dashboard Service - Business Logic for Dashboard Metrics
Orchestrates repository calls and maps results to DTOs.
"""

import logging
from typing import Optional
from dto.dashboard import DashboardStatsDTO
from repositories.dashboard_repository import DashboardRepository

logger = logging.getLogger(__name__)


class DashboardService:
    """Service for dashboard statistics and metrics."""

    @staticmethod
    async def get_dashboard_stats() -> DashboardStatsDTO:
        """
        Get dashboard statistics as DTO.
        
        Returns:
            DashboardStatsDTO: Dashboard statistics with all metrics
        """
        try:
            stats = await DashboardRepository.get_dashboard_statistics()
            
            if stats:
                return DashboardStatsDTO(
                    total_accounts=stats.get("total_count", 0),
                    known_fraud_accounts=stats.get("fraud_count", 0),
                    detected_fraud_rings=stats.get("fraud_ring_count", 0),
                    medium_risk_accounts=stats.get("medium_risk_count", 0),
                    high_risk_accounts=stats.get("high_risk_count", 0),
                    critical_risk_accounts=stats.get("critical_risk_count", 0)
                )
            else:
                # Return default empty stats when database is unavailable
                return DashboardStatsDTO(
                    total_accounts=0,
                    known_fraud_accounts=0,
                    detected_fraud_rings=0,
                    medium_risk_accounts=0,
                    high_risk_accounts=0,
                    critical_risk_accounts=0
                )
        except Exception as e:
            logger.warning(f"Failed to fetch dashboard stats: {e}")
            # Return default empty stats on error
            return DashboardStatsDTO(
                total_accounts=0,
                known_fraud_accounts=0,
                detected_fraud_rings=0,
                medium_risk_accounts=0,
                high_risk_accounts=0,
                critical_risk_accounts=0
            )
