"""
SafeChat — Health Check API Route

GET /api/v1/health — Service health with model status and GPU info
GET /api/v1/ready — Readiness probe for load balancers and container orchestrators
"""

import time
from fastapi import APIRouter, HTTPException

from app.config import settings
from app.models.model_manager import model_manager

router = APIRouter(prefix="/api/v1", tags=["Health"])

_start_time = time.time()


@router.get("/health")
async def health_check():
    """
    Comprehensive health check including model status and GPU metrics.

    Used by:
      - Spring Boot backend to verify ML service availability
      - Docker health checks
      - Monitoring dashboards
    """
    import torch

    health = model_manager.get_health()

    # Add GPU memory info if available
    gpu_info = None
    if torch.cuda.is_available():
        gpu_info = {
            "name": torch.cuda.get_device_name(0),
            "memory_allocated_mb": round(torch.cuda.memory_allocated(0) / (1024 ** 2), 1),
            "memory_reserved_mb": round(torch.cuda.memory_reserved(0) / (1024 ** 2), 1),
        }

    return {
        **health,
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "uptime_seconds": int(time.time() - _start_time),
        "gpu": gpu_info,
    }


@router.get("/ready")
async def readiness_check():
    """
    Readiness probe — returns 200 only when models are loaded and ready.

    Returns HTTP 503 when not ready so that load balancers, Docker, and
    Kubernetes correctly stop routing traffic to this instance.
    """
    if model_manager.is_ready:
        return {"ready": True}

    raise HTTPException(
        status_code=503,
        detail="Models still loading. Service is not ready to accept requests.",
    )



@router.get("/health/gemini")
async def check_gemini_api():
    """Diagnostic endpoint to inspect Gemini API connectivity directly."""
    import httpx
    detox = model_manager.detoxifier
    if not detox:
        return {"error": "Detoxifier not initialized"}
    client = getattr(detox._core, "client", None)
    if not client or not client.is_configured:
        return {"error": "GeminiClient not configured with an API key"}

    try:
        res = await client.generate("Reply with OK")
        return {
            "status": "success" if res else "failed",
            "result": res,
            "model": client.cfg.model,
            "key_prefix": client.cfg.api_key[:8] + "..." if client.cfg.api_key else "none",
        }
    except Exception as e:
        return {"error": str(e), "model": client.cfg.model}
