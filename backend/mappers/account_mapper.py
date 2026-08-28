"""
Mapper functions: Database Results -> Domain Model -> DTO
Central location for database-to-API transformations.
"""

from typing import Dict, Any, Optional, List
from dto.account import (
    AccountDTO,
    CardDTO,
    SharedDeviceDTO,
    SharedPhoneDTO,
    SharedIPDTO,
    AccountConnectionsDTO
)
from dto.graph import GraphNodeDTO, GraphEdgeDTO, GraphResponseDTO


class AccountMapper:
    """Maps database account records to AccountDTO."""
    
    @staticmethod
    def to_dto(db_record: Dict[str, Any]) -> AccountDTO:
        """
        Convert database record to AccountDTO.
        Handles both snake_case (database) and camelCase (Cypher return) keys.
        
        Args:
            db_record: Dictionary with database properties (account_id, risk_level, etc.)
            
        Returns:
            AccountDTO with business-friendly property names
        """
        # Support both snake_case and camelCase keys
        account_id = db_record.get("account_id") or db_record.get("accountId", "")
        display_name = db_record.get("displayName") or db_record.get("name", "")
        risk_level = db_record.get("riskLevel") or db_record.get("risk_level", "LOW")
        risk_score = db_record.get("riskScore") or db_record.get("risk_score", 0.0)
        is_known_fraud = db_record.get("isKnownFraud") or db_record.get("is_known_fraud", False)
        created_at = db_record.get("createdAt") or db_record.get("created_at")
        
        return AccountDTO(
            accountId=account_id,
            displayName=display_name,
            email=db_record.get("email"),
            status=db_record.get("status", "ACTIVE"),
            riskLevel=risk_level,
            riskScore=float(risk_score),
            isKnownFraud=is_known_fraud,
            createdAt=str(created_at) if created_at else None
        )
    
    @staticmethod
    def to_dto_list(db_records: List[Dict[str, Any]]) -> List[AccountDTO]:
        """Convert list of database records to AccountDTOs."""
        return [AccountMapper.to_dto(record) for record in db_records]


class CardMapper:
    """Maps database card records to CardDTO."""
    
    @staticmethod
    def to_dto(db_record: Dict[str, Any]) -> CardDTO:
        """Convert database record to CardDTO."""
        return CardDTO(
            cardId=db_record.get("card_id", db_record.get("card_number", "")),
            cardNumber=db_record.get("card_number"),
            cardType=db_record.get("card_type", "VISA"),
            status=db_record.get("status", "ACTIVE")
        )
    
    @staticmethod
    def to_dto_list(db_records: List[Dict[str, Any]]) -> List[CardDTO]:
        """Convert list of database records to CardDTOs."""
        return [CardMapper.to_dto(record) for record in db_records]


class DeviceMapper:
    """Maps database device records to SharedDeviceDTO."""
    
    @staticmethod
    def to_dto(db_record: Dict[str, Any]) -> SharedDeviceDTO:
        """Convert database record to SharedDeviceDTO."""
        return SharedDeviceDTO(
            deviceId=db_record.get("device_id", ""),
            deviceName=db_record.get("device_name", ""),
            connectedAccountCount=db_record.get("account_count", 1)
        )
    
    @staticmethod
    def to_dto_list(db_records: List[Dict[str, Any]]) -> List[SharedDeviceDTO]:
        """Convert list of database records to SharedDeviceDTOs."""
        return [DeviceMapper.to_dto(record) for record in db_records]


class PhoneMapper:
    """Maps database phone records to SharedPhoneDTO."""
    
    @staticmethod
    def to_dto(db_record: Dict[str, Any]) -> SharedPhoneDTO:
        """Convert database record to SharedPhoneDTO."""
        return SharedPhoneDTO(
            phoneNumber=db_record.get("phone_number", ""),
            connectedAccountCount=db_record.get("account_count", 1)
        )
    
    @staticmethod
    def to_dto_list(db_records: List[Dict[str, Any]]) -> List[SharedPhoneDTO]:
        """Convert list of database records to SharedPhoneDTOs."""
        return [PhoneMapper.to_dto(record) for record in db_records]


class IPMapper:
    """Maps database IP records to SharedIPDTO."""
    
    @staticmethod
    def to_dto(db_record: Dict[str, Any]) -> SharedIPDTO:
        """Convert database record to SharedIPDTO."""
        return SharedIPDTO(
            ipAddress=db_record.get("ip_address", ""),
            connectedAccountCount=db_record.get("account_count", 1)
        )
    
    @staticmethod
    def to_dto_list(db_records: List[Dict[str, Any]]) -> List[SharedIPDTO]:
        """Convert list of database records to SharedIPDTOs."""
        return [IPMapper.to_dto(record) for record in db_records]


class ConnectionMapper:
    """Maps account connections to AccountConnectionsDTO."""
    
    @staticmethod
    def to_dto(
        account_record: Dict[str, Any],
        cards: List[Dict[str, Any]],
        devices: List[Dict[str, Any]],
        phones: List[Dict[str, Any]],
        ips: List[Dict[str, Any]]
    ) -> AccountConnectionsDTO:
        """Convert database records to AccountConnectionsDTO."""
        return AccountConnectionsDTO(
            accountId=account_record.get("account_id", ""),
            displayName=account_record.get("name", ""),
            cards=CardMapper.to_dto_list(cards),
            sharedDevices=DeviceMapper.to_dto_list(devices),
            sharedPhones=PhoneMapper.to_dto_list(phones),
            sharedIPs=IPMapper.to_dto_list(ips)
        )


class GraphNodeMapper:
    """Maps database nodes to GraphNodeDTO."""
    
    @staticmethod
    def from_account(db_record: Dict[str, Any]) -> GraphNodeDTO:
        """Convert Account node to GraphNodeDTO."""
        return GraphNodeDTO(
            id=db_record.get("account_id", ""),
            type="ACCOUNT",
            label=db_record.get("name", ""),
            riskLevel=db_record.get("risk_level"),
            riskScore=float(db_record.get("risk_score", 0.0)) if db_record.get("risk_score") else None,
            isKnownFraud=db_record.get("is_known_fraud", False),
            metadata={
                "status": db_record.get("status"),
                "email": db_record.get("email")
            }
        )
    
    @staticmethod
    def from_card(db_record: Dict[str, Any]) -> GraphNodeDTO:
        """Convert Card node to GraphNodeDTO."""
        return GraphNodeDTO(
            id=db_record.get("card_number", ""),
            type="CARD",
            label=f"Card {db_record.get('card_number', '')[0:8]}...",
            metadata={
                "cardType": db_record.get("card_type"),
                "status": db_record.get("status")
            }
        )
    
    @staticmethod
    def from_device(db_record: Dict[str, Any]) -> GraphNodeDTO:
        """Convert Device node to GraphNodeDTO."""
        return GraphNodeDTO(
            id=db_record.get("device_id", ""),
            type="DEVICE",
            label=db_record.get("device_name", ""),
            metadata={}
        )
    
    @staticmethod
    def from_phone(db_record: Dict[str, Any]) -> GraphNodeDTO:
        """Convert Phone node to GraphNodeDTO."""
        return GraphNodeDTO(
            id=db_record.get("phone_number", ""),
            type="PHONE_NUMBER",
            label=db_record.get("phone_number", ""),
            metadata={}
        )
    
    @staticmethod
    def from_ip(db_record: Dict[str, Any]) -> GraphNodeDTO:
        """Convert IP node to GraphNodeDTO."""
        return GraphNodeDTO(
            id=db_record.get("ip_address", ""),
            type="IP_ADDRESS",
            label=db_record.get("ip_address", ""),
            metadata={}
        )


class GraphEdgeMapper:
    """Maps database relationships to GraphEdgeDTO."""
    
    @staticmethod
    def to_dto(
        source: str,
        target: str,
        relationship: str,
        weight: Optional[float] = None
    ) -> GraphEdgeDTO:
        """Convert relationship to GraphEdgeDTO."""
        return GraphEdgeDTO(
            id=f"{source}-{relationship}-{target}",
            source=source,
            target=target,
            relationship=relationship,
            weight=weight
        )


class GraphResponseMapper:
    """Maps database graph results to GraphResponseDTO."""
    
    @staticmethod
    def to_dto(
        nodes: List[GraphNodeDTO],
        edges: List[GraphEdgeDTO],
        cursor: Optional[str] = None,
        has_more: bool = False
    ) -> GraphResponseDTO:
        """Convert graph components to GraphResponseDTO."""
        return GraphResponseDTO(
            nodes=nodes,
            edges=edges,
            cursor=cursor,
            hasMoreConnections=has_more
        )
