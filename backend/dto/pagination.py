"""
Pagination DTOs for cursor-based pagination.
"""

from typing import List, TypeVar, Generic, Optional
from pydantic import BaseModel, Field, ConfigDict

T = TypeVar('T')


class PaginationCursor(BaseModel):
    """Cursor for opaque pagination."""
    
    cursor: Optional[str] = Field(None, description="Opaque cursor for next page")
    has_next_page: bool = Field(False, alias="hasNextPage", description="Whether more results exist")
    page_size: int = Field(25, alias="pageSize", description="Number of items per page")
    
    model_config = ConfigDict(populate_by_name=True)


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""
    
    items: List[T] = Field(..., description="Items on this page")
    cursor: Optional[str] = Field(None, description="Cursor for next page")
    has_next_page: bool = Field(False, alias="hasNextPage", description="Whether more results exist")
    page_size: int = Field(25, alias="pageSize", description="Number of items per page")
    
    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)
