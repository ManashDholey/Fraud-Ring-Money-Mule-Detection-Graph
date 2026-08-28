"""
Health & Dashboard Router
Endpoints for system health, database connectivity, and dashboard metrics.
"""

import logging
from fastapi import APIRouter, HTTPException

from repositories.account_repository_async import AccountRepository
from services.fraud_detection_service import FraudDetectionService
from services.dashboard_service import DashboardService
from dto.dashboard import DashboardStatsDTO

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Health & System"],
)


@router.get("/api/health")
async def health_check():
    """
    Asynchronous health check endpoint.
    Returns service status and version information.
    """
    return {
        "status": "healthy",
        "service": "Fraud Detection API (Async)",
        "version": "1.0.0"
    }


@router.get("/api/dashboard")
async def get_dashboard() -> DashboardStatsDTO:
    """
    Asynchronously get dashboard metrics: account count, fraud ring count,
    risk distribution, and other KPIs for the fraud detection overview.
    
    Returns:
        DashboardStatsDTO: Dashboard statistics with typed fields
    """
    stats = await DashboardService.get_dashboard_stats()
    return stats


@router.get("/api/test-connection")
async def test_database_connection():
    """
    Asynchronously test database connectivity.
    Performs a simple query to verify Neo4j/CognoDB connection is active.
    """
    # Try a simple async query
    accounts = await AccountRepository.get_all_accounts(limit=1)
    return {
        "status": "connected",
        "message": "Database connection successful (async)"
    }
