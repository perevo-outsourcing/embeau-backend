"""EMBEAU API - Color Psychology Research Backend."""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from embeau_api.api.v1 import router as api_v1_router
from embeau_api.config import get_settings
from embeau_api.core.exceptions import EmbeauException
from embeau_api.db.session import close_db, init_db

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    logger.info("Starting EMBEAU API...")
    await init_db()
    logger.info("Database initialized")

    # Initialize ML models if enabled
    if settings.use_local_models:
        try:
            from embeau_api.ml import initialize_models

            model_status = initialize_models()
            logger.info(f"ML models initialized: {model_status}")
        except Exception as e:
            logger.warning(f"ML model initialization failed: {e} (will use fallbacks)")

    yield
    # Shutdown
    logger.info("Shutting down EMBEAU API...")
    await close_db()
    logger.info("Database connections closed")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
EMBEAU API - Color Psychology Research Backend

This API powers the EMBEAU color therapy application, providing:
- Personal color analysis using AI
- Emotion tracking and analysis
- Healing color recommendations
- Weekly insights and reports

For research purposes, all user interactions are logged (with consent).
    """,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(EmbeauException)
async def embeau_exception_handler(request: Request, exc: EmbeauException) -> JSONResponse:
    """Handle custom EMBEAU exceptions."""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    if exc.code == "AUTH_ERROR":
        status_code = status.HTTP_401_UNAUTHORIZED
    elif exc.code == "FORBIDDEN":
        status_code = status.HTTP_403_FORBIDDEN
    elif exc.code == "NOT_FOUND":
        status_code = status.HTTP_404_NOT_FOUND
    elif exc.code == "VALIDATION_ERROR":
        status_code = status.HTTP_400_BAD_REQUEST
    elif exc.code in ("COLOR_ANALYSIS_ERROR", "EMOTION_ANALYSIS_ERROR"):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY

    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": "HTTP_ERROR",
                "message": exc.detail,
            },
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.exception("Unexpected error occurred")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
            },
        },
    )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.app_version,
    }


# Root endpoint
@app.get("/", tags=["Root"])
async def root() -> dict:
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "EMBEAU Color Psychology Research API",
        "docs": "/docs" if settings.debug else "Disabled in production",
        "health": "/health",
    }


# Include API routers
# Mount at /api for frontend compatibility
app.include_router(api_v1_router, prefix="/api")

# Also mount without prefix for direct access
app.include_router(api_v1_router, prefix="")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "embeau_api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
