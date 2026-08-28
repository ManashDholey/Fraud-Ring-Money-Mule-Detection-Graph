"""
Graph DTOs for network visualization.
Abstracts CognoDB graph structure behind clean API contract.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class GraphNodeDTO(BaseModel):
    """
    Public DTO for a graph node.
    Never exposes raw database node properties.
    """
    
    id: str = Field(..., description="Unique node identifier")
    type: str = Field(..., description="Node type: ACCOUNT | CARD | DEVICE | PHONE_NUMBER | IP_ADDRESS")
    label: str = Field(..., description="Human-readable label")
    riskLevel: Optional[str] = Field(None, description="Risk level if applicable (LOW | MEDIUM | HIGH | CRITICAL)")
    riskScore: Optional[float] = Field(None, description="Risk score if applicable (0-100)")
    isKnownFraud: Optional[bool] = Field(None, description="Whether node is known fraud (for ACCOUNT nodes)")
    metadata: dict = Field(default_factory=dict, description="Non-sensitive metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "ACC_00001",
                "type": "ACCOUNT",
                "label": "John Doe",
                "riskLevel": "LOW",
                "riskScore": 15.5,
                "isKnownFraud": False,
                "metadata": {}
            }
        }


class GraphEdgeDTO(BaseModel):
    """
    Public DTO for a graph edge/relationship.
    Never exposes raw database relationship objects.
    """
    
    id: str = Field(..., description="Unique edge identifier")
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    relationship: str = Field(..., description="Relationship type: HAS_CARD | USES_DEVICE | HAS_PHONE | ACCESSED_FROM_IP | TRANSACTED_WITH")
    weight: Optional[float] = Field(None, description="Optional weight/strength")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "EDGE_001",
                "source": "ACC_00001",
                "target": "CARD_001",
                "relationship": "HAS_CARD",
                "weight": None
            }
        }


class GraphResponseDTO(BaseModel):
    """
    Public DTO for complete graph response.
    Aggregates nodes and edges for visualization.
    Supports cursor-based expansion.
    """
    
    nodes: List[GraphNodeDTO] = Field(..., description="Graph nodes")
    edges: List[GraphEdgeDTO] = Field(..., description="Graph edges/relationships")
    cursor: Optional[str] = Field(None, description="Cursor for expanding graph further")
    hasMoreConnections: bool = Field(False, description="Whether more connections exist beyond current depth")
    
    class Config:
        json_schema_extra = {
            "example": {
                "nodes": [],
                "edges": [],
                "cursor": None,
                "hasMoreConnections": False
            }
        }


class FraudRingDTO(BaseModel):
    """
    Public DTO for detected fraud ring.
    Summary information for investigation queue.
    """
    
    ringId: str = Field(..., description="Unique fraud ring identifier")
    riskLevel: str = Field("HIGH", description="Ring risk level")
    riskScore: float = Field(..., description="Aggregated risk score")
    memberCount: int = Field(..., description="Total members in ring")
    knownFraudCount: int = Field(..., description="Count of known fraud accounts")
    detectionReason: str = Field(..., description="Why this ring was detected")
    accountIds: List[str] = Field(..., description="Account IDs in ring (summary)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ringId": "RING_001",
                "riskLevel": "CRITICAL",
                "riskScore": 85.0,
                "memberCount": 5,
                "knownFraudCount": 2,
                "detectionReason": "Shared device network connecting known fraud",
                "accountIds": ["ACC_00001", "ACC_00002"]
            }
        }


class MoneyMuleChainDTO(BaseModel):
    """
    Public DTO for detected money-mule chain.
    Represents potential fund transfer pattern.
    """
    
    chainId: str = Field(..., description="Unique chain identifier")
    riskLevel: str = Field("HIGH", description="Chain risk level")
    riskScore: float = Field(..., description="Aggregated risk score")
    chainLength: int = Field(..., description="Number of hops in chain")
    accountIds: List[str] = Field(..., description="Account sequence in chain")
    detectionReason: str = Field(..., description="Why this chain was flagged")
    
    class Config:
        json_schema_extra = {
            "example": {
                "chainId": "CHAIN_001",
                "riskLevel": "CRITICAL",
                "riskScore": 90.0,
                "chainLength": 4,
                "accountIds": ["FRAUD_001", "ACC_00100", "ACC_00200", "ACC_00300"],
                "detectionReason": "Transaction chain from known fraud to unknown accounts"
            }
        }
