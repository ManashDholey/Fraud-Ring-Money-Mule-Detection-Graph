"""
Dashboard DTOs for public API contract.
Provides typed data transfer objects for dashboard metrics and statistics.
"""

from pydantic import BaseModel, Field, ConfigDict


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase"""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


class DashboardStatsDTO(BaseModel):
    """
    Public DTO for Dashboard Statistics.
    Provides KPI metrics for the fraud detection overview dashboard.
    """
    
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "totalAccounts": 10000,
                "knownFraudAccounts": 300,
                "detectedFraudRings": 150,
                "mediumRiskAccounts": 250,
                "highRiskAccounts": 500,
                "criticalRiskAccounts": 75
            }
        }
    )
    
    total_accounts: int = Field(..., description="Total number of accounts in the system")
    known_fraud_accounts: int = Field(..., description="Number of known fraudulent accounts")
    detected_fraud_rings: int = Field(..., description="Number of detected fraud rings")
    medium_risk_accounts: int = Field(..., description="Number of accounts with MEDIUM risk level")
    high_risk_accounts: int = Field(..., description="Number of accounts with HIGH risk level")
    critical_risk_accounts: int = Field(..., description="Number of accounts with CRITICAL risk level")
