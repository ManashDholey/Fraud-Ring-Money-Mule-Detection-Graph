"""
Networks Router
Endpoints for fraud detection: fraud rings and money-mule chains.
All responses use DTOs for strict database abstraction.
Routes delegate to Repository layer for all database operations.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from dto.pagination import PaginatedResponse
from dto.graph import FraudRingDTO, MoneyMuleChainDTO
from repositories.network_repository import NetworkRepository
from services.fraud_detection_service import FraudDetectionService

router = APIRouter(
    prefix="/api/networks",
    tags=["Networks"],
    responses={500: {"description": "Internal server error"}},
)


@router.get("/fraud-rings", response_model=PaginatedResponse[FraudRingDTO])
async def get_fraud_rings(
    limit: int = Query(25, ge=1, le=100),
    cursor: Optional[str] = Query(None, description="Opaque cursor for pagination")
):
    """
    Get detected fraud rings with cursor-based pagination.
    
    Query Parameters:
    - limit: Items per page (default: 25, max: 100)
    - cursor: Cursor for next page
    
    Returns: PaginatedResponse with FraudRingDTOs
    """
    result = await NetworkRepository.get_fraud_rings_paginated(limit, cursor)
    return result


@router.get("/money-mule-chains", response_model=PaginatedResponse[MoneyMuleChainDTO])
async def get_money_mule_chains(
    limit: int = Query(25, ge=1, le=100),
    cursor: Optional[str] = Query(None, description="Opaque cursor for pagination")
):
    """
    Get detected money-mule chains with cursor-based pagination.
    
    Query Parameters:
    - limit: Items per page (default: 25, max: 100)
    - cursor: Cursor for next page
    
    Returns: PaginatedResponse with MoneyMuleChainDTOs
    """
    result = await NetworkRepository.get_money_mule_chains_paginated(limit, cursor)
    return result

@router.get("/suspicious-devices")
async def get_suspicious_devices():
    """
    Asynchronously get suspicious device networks: device fingerprints
    accessed by multiple accounts.
    
    Note: This endpoint is deprecated. Use account connections instead.
    """
    devices = await FraudDetectionService.get_suspicious_devices()
    return {
        "device_networks": devices,
        "network_count": len([d for d in devices if "error" not in d])
    }


@router.get("/suspicious-ips")
async def get_suspicious_ips():
    """
    Asynchronously get suspicious IP networks: IP addresses accessed by multiple accounts,
    signaling coordinated fraud or shared network infrastructure.
    """
    ips = await FraudDetectionService.get_suspicious_ips()
    return {
        "ip_networks": ips,
        "network_count": len([ip for ip in ips if "error" not in ip])
    }
