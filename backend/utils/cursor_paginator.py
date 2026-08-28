"""
Cursor pagination utility.
Handles opaque cursor encoding/decoding for server-side pagination.
"""

import base64
import json
import logging
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)


class CursorPaginator:
    """
    Manages cursor-based pagination.
    Cursors are opaque to the client - they encode ordering and position internally.
    """
    
    @staticmethod
    def encode_cursor(
        last_item_id: str, 
        last_item_key: Any, 
        sort_field: str = "account_id"
    ) -> str:
        """
        Encode a cursor from the last item's position.
        
        Args:
            last_item_id: ID of the last returned item
            last_item_key: Sort key value (for deterministic ordering).
                          Can be Any comparable type (str, int, datetime, etc.)
                          Converted to string for JSON serialization.
            sort_field: Field used for sorting
            
        Returns:
            Opaque cursor string (base64 encoded)
        """
        cursor_data = {
            "id": last_item_id,
            "key": str(last_item_key),
            "sort_field": sort_field
        }
        cursor_json = json.dumps(cursor_data)
        cursor_bytes = cursor_json.encode('utf-8')
        cursor_b64 = base64.b64encode(cursor_bytes).decode('utf-8')
        return cursor_b64
    
    @staticmethod
    def decode_cursor(cursor: str) -> Optional[Dict[str, Any]]:
        """
        Decode an opaque cursor.
        Silently returns None on any decode error to support graceful degradation
        (invalid/expired cursors treated as "first page" request).
        
        Args:
            cursor: Cursor string from client
            
        Returns:
            Dictionary with cursor data or None if invalid
        """
        try:
            cursor_bytes = base64.b64decode(cursor.encode('utf-8'))
            cursor_json = cursor_bytes.decode('utf-8')
            return json.loads(cursor_json)
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as e:
            # Broad exception catch justified: client can send malformed cursors
            # Log at debug level to aid troubleshooting without alerting on normal user errors
            logger.debug(f"Invalid cursor format, treating as first-page request: {type(e).__name__}")
            return None
    
    @staticmethod
    def paginate_records(
        records: List[Dict[str, Any]],
        page_size: int = 25,
        cursor: Optional[str] = None,
        sort_key: str = "account_id"
    ) -> Tuple[List[Dict[str, Any]], Optional[str], bool]:
        """
        Apply cursor-based pagination to a list of records.
        
        Args:
            records: All records from database query (must be pre-sorted)
            page_size: Items per page
            cursor: Cursor from client (None for first page)
            sort_key: Database field used for sorting
            
        Returns:
            Tuple of (paginated_records, next_cursor, has_next_page)
        """
        if not records:
            return [], None, False
        
        # Find starting position
        start_idx = 0
        if cursor:
            cursor_data = CursorPaginator.decode_cursor(cursor)
            if cursor_data:
                cursor_id = cursor_data.get("id")
                # Find the index of the item after the cursor
                for i, record in enumerate(records):
                    if record.get(sort_key) == cursor_id or record.get("account_id") == cursor_id:
                        start_idx = i + 1
                        break
        
        # Extract page
        page_end = start_idx + page_size
        page_records = records[start_idx:page_end]
        
        # Check if more records exist
        has_next = len(records) > page_end
        
        # Generate next cursor
        next_cursor = None
        if has_next and page_records:
            last_record = page_records[-1]
            last_id = last_record.get("account_id", "")
            last_key = last_record.get(sort_key, "")
            next_cursor = CursorPaginator.encode_cursor(last_id, last_key, sort_key)
        
        return page_records, next_cursor, has_next
    
    @staticmethod
    def get_cursor_offset(cursor: Optional[str], default_offset: int = 0) -> int:
        """
        Get numeric offset from cursor (for cases needing both).
        This is primarily for backend internal use.
        
        Args:
            cursor: Cursor string
            default_offset: Default offset if cursor invalid
            
        Returns:
            Numeric offset
        """
        if not cursor:
            return default_offset
        
        cursor_data = CursorPaginator.decode_cursor(cursor)
        if cursor_data and "offset" in cursor_data:
            return cursor_data.get("offset", default_offset)
        
        return default_offset
