"""
SafeChat API Gateway — ML Service Client

Asynchronous HTTP client for communicating with the Python ML inference service
(fine-tuned toxicity classifier and Gemini LLM detoxifier).
Includes automatic local fallback to the Phase 3 Detoxification Engine when the ML service is offline.
"""

import os
import sys
import httpx
from typing import Dict, Any, Optional, List
from loguru import logger
from safety_platform.core.config import settings

# Ensure project root is in sys.path for local detoxification engine fallback
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


class MLClientService:
    """Async client communicating with SafeChat ML Service (Port 8001 / 8000)."""

    def __init__(self):
        self.base_url = settings.ML_SERVICE_URL.rstrip("/")
        self.timeout = settings.ML_SERVICE_TIMEOUT_SECONDS

    async def moderate_text(self, text: str, context: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Send text to ML service for toxicity classification with context snapshot.
        Returns classification dictionary or safe fallback if ML service is unreachable.
        """
        url = f"{self.base_url}/api/v1/moderate"
        payload = {"text": text, "context": context or []}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    return res.json()
                logger.warning(f"ML Service returned HTTP {res.status_code}: {res.text}")
        except httpx.RequestError as e:
            logger.error(f"ML Service connection failed at {url}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error calling ML Service: {e}")

        # Fallback response so chat remains functional
        return {
            "is_toxic": False,
            "overall_score": 0.0,
            "severity": "SAFE",
            "categories": {},
            "suggestion": None,
            "detected_language": "en",
            "inference_time_ms": 0,
            "model_version": "fallback-offline",
        }

    async def detoxify_text(self, text: str, target_language: Optional[str] = "en", context: Optional[List[str]] = None) -> Dict[str, Any]:
        """Request intent-preserving LLM style transfer from ML Service with local fallback."""
        url = f"{self.base_url}/api/v1/detoxify"
        payload = {"text": text, "target_language": target_language, "context": context or []}

        try:
            async with httpx.AsyncClient(timeout=self.timeout * 2) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    return res.json()
        except Exception as e:
            logger.warning(f"Detoxification call to remote ML service failed: {e}. Using local engine.")

        # Local fallback using Phase 3 Detoxification Engine
        try:
            from detoxification.detoxifier import Detoxifier
            local_detox = Detoxifier()
            result = await local_detox.detoxify(text, target_language=target_language, context=context)
            return {
                "original_text": text,
                "detoxified_text": result["detoxified"],
                "language": result["language"],
                "method": result["method"],
            }
        except Exception as detox_err:
            logger.warning(f"Local fallback detoxifier failed: {detox_err}")

        return {
            "original_text": text,
            "detoxified_text": "Let's keep the conversation respectful.",
            "language": target_language or "en",
            "method": "template-fallback",
        }

    async def arbitrate_and_detoxify(
        self,
        text: str,
        roberta_labels: Optional[List[str]] = None,
        target_language: Optional[str] = "en",
        context: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Request Gemini to arbitrate classification (safe vs toxic in context) and detoxify.
        Returns accepted classification verdict and clean suggestion.
        """
        try:
            from detoxification.detoxifier import Detoxifier
            local_detox = Detoxifier()
            result = await local_detox.arbitrate_and_detoxify(
                text=text,
                roberta_labels=roberta_labels,
                target_language=target_language,
                context=context
            )
            return {
                "original_text": text,
                "is_toxic": result.get("is_toxic", True),
                "severity": result.get("severity", "MEDIUM"),
                "detoxified_text": result.get("detoxified", text),
                "categories": result.get("categories", roberta_labels or []),
                "reason": result.get("reason", ""),
                "method": result.get("method", "gemini_arbitration"),
                "language": result.get("language", target_language or "en"),
            }
        except Exception as e:
            logger.warning(f"Arbitration fallback failed: {e}")
            detox_res = await self.detoxify_text(text, target_language=target_language, context=context)
            return {
                "original_text": text,
                "is_toxic": True,
                "severity": "MEDIUM",
                "detoxified_text": detox_res.get("detoxified_text", text),
                "categories": roberta_labels or [],
                "reason": "Fallback",
                "method": "fallback",
                "language": target_language or "en",
            }

    async def check_ml_health(self) -> Dict[str, Any]:
        """Check health of remote ML service."""
        url = f"{self.base_url}/api/v1/health"
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    return {"status": "ok", **res.json()}
        except Exception as e:
            return {"status": "offline", "error": str(e)}
        return {"status": "unreachable"}


ml_client = MLClientService()
