"""
Accounts Router
Endpoints for individual account profiling, risk analysis, and direct node attributes.
All responses use DTOs for strict database abstraction.
"""

import asyncio
import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from neo4j.exceptions import TransientError, ServiceUnavailable, SessionExpired

from repositories.account_repository_async import AccountRepository
from repositories.account_repository_dto import AccountRepositoryDTO
from services.fraud_detection_service import FraudDetectionService
from dto.pagination import PaginatedResponse
from dto.account import AccountDTO, AccountConnectionsDTO
from dto.graph import GraphResponseDTO

router = APIRouter(
    prefix="/api/accounts",
    tags=["Accounts"],
    responses={404: {"description": "Account not found"}},
)


@router.get("", response_model=PaginatedResponse[AccountDTO])
async def search_accounts(
    query: Optional[str] = Query(None, min_length=1),
    limit: int = Query(25, ge=1, le=100),
    cursor: Optional[str] = Query(None, description="Opaque cursor for pagination")
):
    """
    Search accounts with cursor-based pagination.
    
    Query Parameters:
    - query: Search term (account name or ID)
    - limit: Items per page (default: 25, max: 100)
    - cursor: Cursor for next page (opaque, returned by previous response)
    
    Returns: PaginatedResponse with AccountDTOs
    """
    result = await AccountRepositoryDTO.search_accounts_paginated(
        search_term=query,
        limit=limit,
        cursor=cursor
    )
    return result


@router.get("/{account_id}", response_model=AccountDTO)
async def get_account_details(account_id: str):
    """
    Get detailed account information as DTO.
    
    Returns: AccountDTO
    """
    account = await AccountRepositoryDTO.get_account_by_id_dto(account_id)
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    return account


@router.get("/{account_id}/graph", response_model=GraphResponseDTO)
async def get_account_graph(
    account_id: str,
    depth: int = Query(2, ge=1, le=3)
):
    """
    Asynchronously get the graph neighborhood around an account for visualization.
    
    Query Parameters:
    - depth: Traversal depth (1-3, default: 2)
    
    Returns: GraphResponseDTO with nodes and edges properly typed
    
    Errors:
    - 404: Account not found
    - 504: Graph query timeout (too many connections for requested depth)
    """
    try:
        graph = await FraudDetectionService.get_account_graph_visualization(account_id, depth)
        return graph
    except (TransientError, ServiceUnavailable, SessionExpired) as e:
        # Neo4j transient errors: query timeout, temporary unavailability
        error_msg = str(e).lower()
        if "context deadline exceeded" in error_msg or "outoftime" in error_msg.lower():
            raise HTTPException(
                status_code=504,
                detail=f"Graph query timeout. Try a smaller depth (currently {depth}). Max connections for depth {depth} exceeded on server."
            )
        else:
            raise HTTPException(
                status_code=503,
                detail="Database temporarily unavailable. Try again in a moment."
            )


@router.get("/{account_id}/connections", response_model=AccountConnectionsDTO)
async def get_account_connections(account_id: str):
    """
    Get all account connections: cards, shared devices, phones, IPs.
    
    Returns: AccountConnectionsDTO
    """
    connections = await AccountRepositoryDTO.get_account_connections_dto(account_id)
    
    if not connections:
        raise HTTPException(status_code=404, detail="Account not found")
    
    return connections


@router.get("/{account_id}/fraud-proximity")
async def get_fraud_proximity(account_id: str):
    """
    Asynchronously get fraud proximity score: ranking of how close this account is to known fraud.
    """
    account = await AccountRepository.get_account_by_id(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    scores = await FraudDetectionService.compute_risk_score(account_id)
    return scores


@router.get("/{account_id}/risk-explanation")
async def get_risk_explanation(account_id: str):
    """
    Asynchronously get detailed explanation of why an account is flagged: risk factors and paths.
    """
    account = await AccountRepository.get_account_by_id(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Concurrently fetch risk score and shared identity analysis
    risk_score, shared_identity = await asyncio.gather(
        FraudDetectionService.compute_risk_score(account_id),
        FraudDetectionService.get_shared_identity_analysis(account_id),
        return_exceptions=False
    )
    
    return {
        "account_id": account_id,
        "account_name": account.get("name"),
        "risk_score": risk_score.get("risk_score"),
        "risk_level": risk_score.get("risk_level"),
        "risk_factors": risk_score.get("risk_factors"),
        "explanation": risk_score.get("explanation"),
        "shared_identities": shared_identity
    }


@router.get("/{account_id}/money-mule-paths")
async def get_money_mule_paths(account_id: str):
    """
    Asynchronously detect money-mule chains: multi-hop transaction paths from this account.
    """
    account = await AccountRepository.get_account_by_id(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    paths = await FraudDetectionService.get_money_mule_paths(account_id)
    return {
        "account_id": account_id,
        "mule_chains": paths,
        "chain_count": len([p for p in paths if "error" not in p])
    }
