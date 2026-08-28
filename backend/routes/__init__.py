"""
FastAPI Routes Package
Modularized router definitions for the Fraud Detection API.
"""

from .accounts import router as accounts_router
from .networks import router as networks_router
from .health import router as health_router

__all__ = ["accounts_router", "networks_router", "health_router"]
