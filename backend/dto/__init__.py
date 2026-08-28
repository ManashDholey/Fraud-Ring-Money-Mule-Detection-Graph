"""
Data Transfer Objects (DTOs) for public API contracts.
Defines stable interfaces independent of database schema.
"""

from .pagination import PaginatedResponse, PaginationCursor
from .account import (
    AccountDTO,
    CardDTO,
    SharedDeviceDTO,
    SharedPhoneDTO,
    SharedIPDTO,
    AccountConnectionsDTO
)
from .graph import (
    GraphNodeDTO,
    GraphEdgeDTO,
    GraphResponseDTO,
    FraudRingDTO,
    MoneyMuleChainDTO
)

__all__ = [
    "PaginatedResponse",
    "PaginationCursor",
    "AccountDTO",
    "CardDTO",
    "SharedDeviceDTO",
    "SharedPhoneDTO",
    "SharedIPDTO",
    "AccountConnectionsDTO",
    "GraphNodeDTO",
    "GraphEdgeDTO",
    "GraphResponseDTO",
    "FraudRingDTO",
    "MoneyMuleChainDTO",
]
