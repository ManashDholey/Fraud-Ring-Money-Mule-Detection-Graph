"""
Fraud Detection API - Fully Asynchronous FastAPI Backend
Uses AsyncGraphDatabase for non-blocking Neo4j operations

Application structure follows clean architecture with modularized routers:
- routes/accounts.py: Account profiling and risk analysis
- routes/networks.py: Fraud ring detection and network analysis
- routes/health.py: Health checks and dashboard metrics
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import logging
from dotenv import load_dotenv
from typing import AsyncGenerator
from collections import defaultdict
from time import time
import asyncio

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get CORS origins from environment
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")

from config.settings import settings
from dbConfig.db_async import close_driver, verify_connectivity, get_driver
from routes import accounts_router, networks_router, health_router
from routes.admin import router as admin_router
from services.auto_seed import auto_seed_if_empty
from utils.exception_handlers import (
    general_exception_handler,
    neo4j_exception_handler,
    custom_exception_handler,
    value_error_handler
)
from dto.error import CustomException
from neo4j.exceptions import Neo4jError

# Rate limiting configuration: 100 requests per minute per IP
RATE_LIMIT_REQUESTS = 100
RATE_LIMIT_WINDOW_SECONDS = 60

# Track requests per IP
request_tracker = defaultdict(list)


async def rate_limit_middleware(request: Request, call_next):
    """
    Rate limiting middleware - enforces 100 requests per minute per IP.
    Protects against runaway request loops and connection pool exhaustion.
    """
    client_ip = request.client.host
    current_time = time()
    
    # Get request history for this IP
    request_times = request_tracker[client_ip]
    
    # Remove timestamps older than the rate limit window
    request_times[:] = [t for t in request_times if current_time - t < RATE_LIMIT_WINDOW_SECONDS]
    
    # Check if limit exceeded
    if len(request_times) >= RATE_LIMIT_REQUESTS:
        return JSONResponse(
            status_code=429,
            content={
                "error": "Too Many Requests",
                "detail": f"Rate limit exceeded: {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW_SECONDS} seconds",
                "retry_after": RATE_LIMIT_WINDOW_SECONDS
            }
        )
    
    # Add current request timestamp
    request_times.append(current_time)
    
    # Warn if approaching limit (80% = 80 requests per minute)
    if len(request_times) > RATE_LIMIT_REQUESTS * 0.8:
        print(f"⚠️  Rate limit warning: {len(request_times)} requests from {client_ip} in the last minute. " +
              f"Limit is {RATE_LIMIT_REQUESTS}/min. This may indicate a request loop bug.")
    
    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT_REQUESTS)
    response.headers["X-RateLimit-Remaining"] = str(RATE_LIMIT_REQUESTS - len(request_times))
    response.headers["X-RateLimit-Reset"] = str(int(current_time) + RATE_LIMIT_WINDOW_SECONDS)
    
    return response


async def _run_background_seeding():
    """
    Background task to run database seeding without blocking app startup.
    Called via asyncio.create_task() after app is ready to serve requests.
    This prevents 502 Bad Gateway errors from startup timeout during health checks.
    """
    logger_bg = logging.getLogger(__name__)
    try:
        if not settings.AUTO_SEED_ON_STARTUP:
            logger_bg.info("Auto-seed is disabled via AUTO_SEED_ON_STARTUP=false")
            return
        
        logger_bg.info("🔄 [Background] Auto-seed pipeline starting...")
        driver = get_driver()
        
        # Run seeding in background without blocking startup
        seed_result = await auto_seed_if_empty(driver, enabled=True)
        
        if seed_result["is_complete"]:
            logger_bg.info(
                f"✓ [Background] Database seeding confirmed complete: "
                f"{seed_result['seeding_performed'] and 'pipeline ran' or 'data already present'}"
            )
        elif seed_result["seeding_performed"]:
            # Build summary from available results
            summary_parts = []
            if seed_result["seed_summary"]:
                summary_parts.append(f"{seed_result['seed_summary'].accounts_created} accounts")
            if seed_result["fraud_rings_summary"]:
                summary_parts.append(f"{seed_result['fraud_rings_summary'].rings_created} fraud rings")
            if seed_result["risk_scores_summary"]:
                summary_parts.append(f"{seed_result['risk_scores_summary'].accounts_scored} scored")
            
            summary_str = ", ".join(summary_parts) if summary_parts else "partial stages"
            logger_bg.info(
                f"✓ [Background] Auto-seed completed ({summary_str}, "
                f"in {seed_result['total_time_seconds']:.1f}s)"
            )
        elif seed_result["skipped_reason"]:
            logger_bg.info(f"✓ [Background] Auto-seed skipped: {seed_result['skipped_reason']}")
        
        if seed_result["error"]:
            logger_bg.warning(
                f"⚠ [Background] Auto-seed encountered error: "
                f"{seed_result['error']}. Retry via /admin/reseed"
            )
    except Exception as e:
        logger_bg.error(f"✗ [Background] Auto-seed pipeline failed: {str(e)}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage application lifespan using async context manager.
    Replaces deprecated @app.on_event decorators.
    
    Startup (NON-BLOCKING): 
      - Verify database connectivity only (~1-2 seconds)
      - Schedule seeding as background task (does NOT block startup)
      - App is ready to serve requests immediately
    
    Background:
      - Auto-seed pipeline runs asynchronously if configured
    
    Shutdown: 
      - Close database connection gracefully
    """
    logger = logging.getLogger(__name__)
    
    # Startup phase - FAST and NON-BLOCKING
    try:
        logger.info("⏱️  Starting application startup sequence...")
        
        # 1. Verify database connectivity (should be < 2 seconds)
        await verify_connectivity()
        logger.info("✓ Database connectivity verified")
        
        # 2. Schedule auto-seed as background task (does NOT await/block)
        if settings.AUTO_SEED_ON_STARTUP:
            logger.info("📌 Auto-seed is enabled - scheduling as background task")
            # Create background task that runs WITHOUT blocking startup
            asyncio.create_task(_run_background_seeding())
            logger.info("   (App is ready to serve requests immediately)")
        else:
            logger.info("Auto-seed is disabled via AUTO_SEED_ON_STARTUP=false")
        
        logger.info("✓ Application startup complete and ready to serve requests")
        
    except Exception as e:
        logger.error(f"✗ Database startup FAILED: {str(e)}", exc_info=True)
        # Don't raise - let app start in degraded state
    
    yield  # Application runs here and serves requests
    
    # Shutdown phase - execute after app stops
    try:
        await close_driver()
        logger.info("✓ Database lifespan shutdown complete")
    except Exception as e:
        logger.warning(f"⚠ Database shutdown warning: {str(e)}")


app = FastAPI(
    title="Fraud Detection API (Async)",
    description="Asynchronous graph-based fraud ring and money-mule detection",
    version="1.0.0",
    lifespan=lifespan
)

# Register centralized exception handlers (must be before middleware/routers)
app.add_exception_handler(CustomException, custom_exception_handler)
app.add_exception_handler(Neo4jError, neo4j_exception_handler)
app.add_exception_handler(ValueError, value_error_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Enable CORS for React frontend (add first so it runs last in the middleware stack)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware (100 requests per minute per IP)
# This protects against runaway request loops and connection pool exhaustion
app.middleware("http")(rate_limit_middleware)

# Register modularized routers
app.include_router(health_router)
app.include_router(accounts_router)
app.include_router(networks_router)
app.include_router(admin_router)

# Serve React static files (mounted AFTER API routes so /api/* routes take precedence)
# This allows serving the React app from the same origin as the backend
import os
from fastapi.staticfiles import StaticFiles

# Check if static directory exists (created during Docker build from frontend/dist)
static_dir = os.path.join(os.path.dirname(__file__), 'static')
if os.path.exists(static_dir) and os.listdir(static_dir):
    logger.info(f"✓ Mounting static files from {static_dir}")
    app.mount('/', StaticFiles(directory=static_dir, html=True), name='frontend')
else:
    logger.warning(f"⚠ Static files directory not found or empty: {static_dir}")
    logger.info("  For local development, this is normal. For production, rebuild with frontend included.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
