"""
SafeChat API Gateway — Complete Python Backend Service

Entry point for the primary backend API and real-time chat server.
Replaces the Spring Boot Java backend with 100% Python + FastAPI.
Implements Polyglot Persistence:
  - PostgreSQL (Relational Core: Users, Channels, Audit Logs)
  - Redis (High-Speed Memory Cache: Sliding Window Rate Limiting & PubSub)
  - MongoDB (Document Core: Chat History, AI Traces, Continuous Learning Store)

Run with:
    uvicorn safety_platform.main:app --host 0.0.0.0 --port 8000 --reload
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from safety_platform.core.config import settings
from safety_platform.core.db import (
    init_postgres_tables,
    connect_redis,
    disconnect_redis,
    connect_mongo,
    disconnect_mongo,
    AsyncSessionLocal,
)
from safety_platform.services.channel_service import ChannelService
from safety_platform.api.router import api_router
from safety_platform.api.routes import websocket


# ── Lifespan Connection Management ─────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup:
      1. Initialize PostgreSQL tables and seed default # general channel
      2. Connect Redis connection pool for rate limiting
      3. Connect MongoDB Motor client for message history
    Shutdown:
      1. Close Redis and MongoDB connections
    """
    logger.info("Starting SafeChat Python API Gateway & Chat Server...")

    # 1. PostgreSQL setup
    await init_postgres_tables()
    try:
        async with AsyncSessionLocal() as db:
            await ChannelService.seed_default_channels(db)
    except Exception as e:
        logger.warning(f"Could not seed default channels: {e}")

    # 2. Redis setup
    await connect_redis()

    # 3. MongoDB setup
    await connect_mongo()

    logger.success(f"SafeChat API Gateway ready on {settings.HOST}:{settings.PORT}")
    yield

    logger.info("Shutting down SafeChat API Gateway...")
    await disconnect_redis()
    await disconnect_mongo()
    logger.info("Shutdown complete. Goodbye!")


# ── Create FastAPI Application ─────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Production-grade Python API Gateway and Real-Time Chat Server for SafeChat. "
        "Implements polyglot persistence across PostgreSQL, Redis, and MongoDB, "
        "with asynchronous proxying to the fine-tuned MuRIL & Gemini ML service."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ── CORS Middleware ────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Register Routes ───────────────────────────────────────────────────
app.include_router(api_router, prefix=settings.API_PREFIX)
app.include_router(websocket.router)  # /ws/chat real-time gateway


# ── Frontend SPA Mounting / Root Endpoint ─────────────────────────────
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_dist_dir = os.path.join(_project_root, "frontend", "dist")
_assets_dir = os.path.join(_dist_dir, "assets")

if os.path.exists(_assets_dir):
    app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")


@app.get("/", tags=["Root"])
async def root(request: Request):
    """
    Root endpoint:
    - Serves the compiled React SPA index.html for web browsers (Accept: text/html).
    - Returns JSON Service status and API link registry for API clients and automated tests.
    """
    accept = request.headers.get("accept", "")
    index_file = os.path.join(_dist_dir, "index.html")

    if "text/html" in accept and os.path.exists(index_file):
        return FileResponse(index_file)

    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": f"{settings.API_PREFIX}/health",
        "ready": f"{settings.API_PREFIX}/ready",
        "endpoints": {
            "auth_register": f"POST {settings.API_PREFIX}/auth/register",
            "auth_login": f"POST {settings.API_PREFIX}/auth/login",
            "channels": f"GET/POST {settings.API_PREFIX}/channels",
            "chat_history": f"GET {settings.API_PREFIX}/chat/messages/{{channel_id}}",
            "moderate_rest": f"POST {settings.API_PREFIX}/moderate",
            "feedback": f"POST {settings.API_PREFIX}/feedback",
            "websocket_chat": "WS /ws/chat",
        },
    }


@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(request: Request, full_path: str):
    """
    SPA catch-all fallback: serves existing static files or redirects routes back to index.html.
    """
    file_path = os.path.join(_dist_dir, full_path)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    index_file = os.path.join(_dist_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return JSONResponse(status_code=404, content={"detail": "Not Found"})
