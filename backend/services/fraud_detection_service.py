"""
Fraud Detection Service - Asynchronous business logic for fraud investigation.
Orchestrates repository calls and computes risk scores with transparent factors.
Uses asyncio.gather() for concurrent operations.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from repositories.account_repository_async import AccountRepository
from repositories.graph_repository_async import GraphRepository

logger = logging.getLogger(__name__)


class FraudDetectionService:
    """Service for fraud detection and risk analysis (async)."""

    @staticmethod
    async def compute_risk_score(account_id: str) -> Dict[str, Any]:
        """
        Asynchronously compute fraud risk score for an account based on graph relationships.
        Returns transparent scoring with factors.
        
        Args:
            account_id: Account to score
            
        Returns:
            Risk score dictionary with factors and explanation
        """
        account = await AccountRepository.get_account_by_id(account_id)
        if not account:
            return {"error": "Account not found", "risk_score": 0, "risk_level": "UNKNOWN"}

        risk_score = 0
        risk_factors = []

        # Factor 1: Known fraud status (40 points)
        if account.get("is_known_fraud"):
            risk_score += 40
            risk_factors.append({
                "factor": "Known fraud account",
                "weight": 40,
                "description": "This account is in the known-fraud database"
            })

        # Fetch shared identity data concurrently using asyncio.gather()
        try:
            shared_devices, shared_phones, shared_ips = await asyncio.gather(
                AccountRepository.get_shared_devices(account_id),
                AccountRepository.get_shared_phone_numbers(account_id),
                AccountRepository.get_shared_ip_addresses(account_id),
                return_exceptions=False
            )
        except Exception as e:
            logger.warning(f"Failed to retrieve shared identity data for {account_id}: {e}")
            shared_devices = []
            shared_phones = []
            shared_ips = []

        # Factor 2: Direct connection to known fraud (35 points per connection)
        try:
            proximity_results = await GraphRepository.get_fraud_proximity_scores()
            for item in proximity_results:
                if item["account_id"] == account_id and item["min_hops"] == 1:
                    risk_score += 35
                    risk_factors.append({
                        "factor": "Direct connection to known fraud",
                        "weight": 35,
                        "description": f"Connected to {item['path_count']} fraud account(s)"
                    })
                    break
        except Exception as e:
            logger.warning(f"Failed to compute fraud proximity for {account_id}: {e}")

        # Factor 3: Shared device with fraud (20 points per device)
        fraud_device_count = sum(1 for d in shared_devices if d.get("is_known_fraud"))
        if fraud_device_count > 0:
            device_score = min(fraud_device_count * 20, 40)
            risk_score += device_score
            risk_factors.append({
                "factor": "Shared device with fraud account(s)",
                "weight": device_score,
                "description": f"Shares device with {fraud_device_count} known-fraud account(s)"
            })

        # Factor 4: Shared phone number with fraud (15 points)
        fraud_phone_count = sum(1 for p in shared_phones if p.get("is_known_fraud"))
        if fraud_phone_count > 0:
            phone_score = min(fraud_phone_count * 15, 30)
            risk_score += phone_score
            risk_factors.append({
                "factor": "Shared phone number with fraud account(s)",
                "weight": phone_score,
                "description": f"Shares phone with {fraud_phone_count} known-fraud account(s)"
            })

        # Factor 5: Shared IP address with fraud (10 points)
        fraud_ip_count = sum(1 for ip in shared_ips if ip.get("is_known_fraud"))
        if fraud_ip_count > 0:
            ip_score = min(fraud_ip_count * 10, 20)
            risk_score += ip_score
            risk_factors.append({
                "factor": "Shared IP address with fraud account(s)",
                "weight": ip_score,
                "description": f"Accesses from IP shared with {fraud_ip_count} known-fraud account(s)"
            })

        # Factor 6: Multi-hop fraud connection (up to 10 points)
        try:
            proximity = await GraphRepository.get_fraud_proximity_scores()
            for item in proximity:
                if item["account_id"] == account_id and item["min_hops"] > 1:
                    multi_hop_score = max(0, 15 - (item["min_hops"] * 5))
                    if multi_hop_score > 0:
                        risk_score += multi_hop_score
                        risk_factors.append({
                            "factor": f"Connected to fraud through {item['min_hops']} intermediaries",
                            "weight": multi_hop_score,
                            "description": f"{item['path_count']} indirect path(s) to fraud account(s)"
                        })
                    break
        except Exception as e:
            logger.warning(f"Failed to compute multi-hop fraud connections for {account_id}: {e}")

        # Determine risk level
        if risk_score >= 75:
            risk_level = "CRITICAL"
        elif risk_score >= 50:
            risk_level = "HIGH"
        elif risk_score >= 30:
            risk_level = "MEDIUM"
        elif risk_score >= 10:
            risk_level = "LOW"
        else:
            risk_level = "MINIMAL"

        return {
            "account_id": account_id,
            "account_name": account.get("name"),
            "risk_score": min(risk_score, 100),  # Cap at 100
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "is_known_fraud": account.get("is_known_fraud"),
            "explanation": FraudDetectionService._generate_explanation(risk_factors, risk_level)
        }

    @staticmethod
    def _generate_explanation(risk_factors: List[Dict[str, Any]], risk_level: str) -> str:
        """Generate natural language explanation for risk score."""
        if not risk_factors:
            return "No risk factors detected."
        
        factor_descriptions = [f["description"] for f in risk_factors[:3]]
        explanation = f"Risk Level: {risk_level}. "
        explanation += " ".join(factor_descriptions)
        if len(risk_factors) > 3:
            explanation += f" Plus {len(risk_factors) - 3} additional risk factor(s)."
        return explanation

    @staticmethod
    async def get_fraud_rings() -> List[Dict[str, Any]]:
        """Asynchronously get detected fraud rings."""
        try:
            return await GraphRepository.detect_fraud_rings(limit=10)
        except Exception as e:
            return [{"error": str(e)}]

    @staticmethod
    async def get_money_mule_paths(account_id: str) -> List[Dict[str, Any]]:
        """Asynchronously get detected money-mule chains from an account."""
        try:
            return await GraphRepository.detect_money_mule_paths(account_id, max_depth=4)
        except Exception as e:
            return [{"error": str(e)}]

    @staticmethod
    async def get_shared_identity_analysis(account_id: str) -> Dict[str, Any]:
        """Asynchronously get comprehensive shared identity analysis for an account."""
        try:
            # Concurrently fetch all shared identity data
            shared_devices, shared_phones, shared_ips = await asyncio.gather(
                AccountRepository.get_shared_devices(account_id),
                AccountRepository.get_shared_phone_numbers(account_id),
                AccountRepository.get_shared_ip_addresses(account_id),
                return_exceptions=False
            )
            
            return {
                "account_id": account_id,
                "shared_devices": shared_devices,
                "shared_device_count": len(shared_devices),
                "shared_phones": shared_phones,
                "shared_phone_count": len(shared_phones),
                "shared_ips": shared_ips,
                "shared_ip_count": len(shared_ips),
                "total_shared_identity_connections": len(shared_devices) + len(shared_phones) + len(shared_ips)
            }
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    async def get_account_graph_visualization(account_id: str, depth: int = 2):
        """
        Asynchronously get account graph for visualization.
        Returns typed GraphResponseDTO.
        """
        return await GraphRepository.get_account_graph(account_id, depth)

    @staticmethod
    async def get_investigation_explanation(account_id: str, target_account_id: str) -> Dict[str, Any]:
        """Asynchronously get explanation paths between two accounts."""
        try:
            paths = await GraphRepository.get_investigation_paths(account_id, target_account_id)
            return {
                "source_account": account_id,
                "target_account": target_account_id,
                "paths": paths,
                "path_count": len(paths),
                "explanation": f"Found {len(paths)} path(s) connecting these accounts"
            }
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    async def get_suspicious_devices() -> List[Dict[str, Any]]:
        """Asynchronously get suspicious device networks."""
        try:
            return await GraphRepository.get_suspicious_device_networks(limit=20)
        except Exception as e:
            return [{"error": str(e)}]

    @staticmethod
    async def get_suspicious_ips() -> List[Dict[str, Any]]:
        """Asynchronously get suspicious IP networks."""
        try:
            return await GraphRepository.get_suspicious_ip_networks(limit=20)
        except Exception as e:
            return [{"error": str(e)}]
