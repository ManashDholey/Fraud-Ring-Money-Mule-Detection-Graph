"""
Account DTOs for public API contract.
Business-friendly naming and abstraction from database schema.
"""

from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class AccountDTO(BaseModel):
    """
    Public DTO for Account.
    Uses business-friendly names, never exposes database property names.
    """
    
    accountId: str = Field(..., description="Unique account identifier")
    displayName: str = Field(..., description="Account holder name")
    email: Optional[str] = Field(None, description="Account email")
    status: str = Field("ACTIVE", description="Account status")
    riskLevel: str = Field("LOW", description="Risk assessment: LOW | MEDIUM | HIGH | CRITICAL")
    riskScore: float = Field(0.0, description="Computed risk score (0-100)")
    isKnownFraud: bool = Field(False, description="Whether account is known fraud")
    createdAt: Optional[str] = Field(None, description="Account creation timestamp (ISO 8601)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "accountId": "ACC_00001",
                "displayName": "John Doe",
                "email": "john@example.com",
                "status": "ACTIVE",
                "riskLevel": "LOW",
                "riskScore": 15.5,
                "isKnownFraud": False,
                "createdAt": "2026-01-15T10:30:00Z"
            }
        }


class CardDTO(BaseModel):
    """Public DTO for Payment Card."""
    
    cardId: str = Field(..., description="Unique card identifier")
    cardNumber: Optional[str] = Field(None, description="Masked card number (last 4 digits shown)")
    cardType: str = Field("VISA", description="Card type: VISA | MASTERCARD | AMEX")
    status: str = Field("ACTIVE", description="Card status")
    
    class Config:
        json_schema_extra = {
            "example": {
                "cardId": "CARD_001",
                "cardNumber": "4532-XXXX-XXXX-1234",
                "cardType": "VISA",
                "status": "ACTIVE"
            }
        }


class SharedDeviceDTO(BaseModel):
    """Public DTO for Shared Device connection."""
    
    deviceId: str = Field(..., description="Unique device identifier")
    deviceName: str = Field(..., description="Human-readable device name")
    connectedAccountCount: int = Field(..., description="Number of accounts using this device")
    
    class Config:
        json_schema_extra = {
            "example": {
                "deviceId": "DEV_0001",
                "deviceName": "Device_Suspicious_001",
                "connectedAccountCount": 5
            }
        }


class SharedPhoneDTO(BaseModel):
    """Public DTO for Shared Phone connection."""
    
    phoneNumber: str = Field(..., description="Phone number (potentially masked)")
    connectedAccountCount: int = Field(..., description="Number of accounts using this phone")
    
    class Config:
        json_schema_extra = {
            "example": {
                "phoneNumber": "+1-555-00001",
                "connectedAccountCount": 3
            }
        }


class SharedIPDTO(BaseModel):
    """Public DTO for Shared IP connection."""
    
    ipAddress: str = Field(..., description="IP address")
    connectedAccountCount: int = Field(..., description="Number of accounts accessed from this IP")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ipAddress": "192.168.1.50",
                "connectedAccountCount": 4
            }
        }


class AccountConnectionsDTO(BaseModel):
    """
    Public DTO for account connections/relationships.
    Aggregates cards, devices, phones, IPs.
    """
    
    accountId: str = Field(..., description="Account identifier")
    displayName: str = Field(..., description="Account name")
    cards: list[CardDTO] = Field(default_factory=list, description="Associated payment cards")
    sharedDevices: list[SharedDeviceDTO] = Field(default_factory=list, description="Devices shared with other accounts")
    sharedPhones: list[SharedPhoneDTO] = Field(default_factory=list, description="Phone numbers shared with other accounts")
    sharedIPs: list[SharedIPDTO] = Field(default_factory=list, description="IP addresses shared with other accounts")
    
    class Config:
        json_schema_extra = {
            "example": {
                "accountId": "ACC_00001",
                "displayName": "John Doe",
                "cards": [],
                "sharedDevices": [],
                "sharedPhones": [],
                "sharedIPs": []
            }
        }
