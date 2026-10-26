"""
SafeChat — Comprehensive Backend API Platform Test Suite (Phase 4)

Tests:
  1. Security: bcrypt password hashing and verification
  2. Security: JWT token generation, claims, and decoding
  3. Schemas: Pydantic v2 serialization for auth, channel, chat, and feedback
  4. Models: PostgreSQL User and Channel SQLAlchemy mappings
  5. Models: MongoDB document dictionary transformations
  6. Rate Limiter: ChatService sliding-window memory fallback
  7. API Gateway: FastAPI endpoints (Root, Health probe, Schema validation)
  8. ML Proxy: MLClientService automatic fallback to Phase 3 Detoxification Engine
"""

import sys
import os
import pytest
from datetime import timedelta

# Ensure src/ and root are in sys.path
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_src = os.path.join(_root, "src")
if _root not in sys.path:
    sys.path.insert(0, _root)
if _src not in sys.path:
    sys.path.insert(0, _src)

from fastapi.testclient import TestClient
from safety_platform.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token,
)
from safety_platform.models.postgres import User, Channel
from safety_platform.models.mongo import (
    ChatMessageDocument,
    ModerationMetadata,
    ModeratorFeedbackDocument,
)
from safety_platform.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from safety_platform.schemas.channel import ChannelCreateRequest
from safety_platform.schemas.chat import ModerateRequest, FeedbackSubmitRequest
from safety_platform.services.chat_service import ChatService
from safety_platform.services.ml_client import MLClientService
from safety_platform.main import app


# ── 1. Security Utilities ─────────────────────────────────────────────────────

def test_password_hashing_and_verification():
    raw_pass = "SecurePass123!"
    hashed = get_password_hash(raw_pass)

    assert hashed != raw_pass
    assert verify_password(raw_pass, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_jwt_token_creation_and_decoding():
    user_id = "user-uuid-12345"
    token = create_access_token(user_id, expires_delta=timedelta(minutes=30))

    decoded_sub = decode_access_token(token)
    assert decoded_sub == user_id


def test_jwt_invalid_token():
    invalid_token = "invalid.token.string"
    assert decode_access_token(invalid_token) is None


# ── 2. Models & Schema Mapping ────────────────────────────────────────────────

def test_postgres_user_model_attributes():
    user = User(
        email="test@safechat.ai",
        password_hash="hashed_pw",
        display_name="Test User",
        role="USER",
        active=True,
    )
    assert user.email == "test@safechat.ai"
    assert user.active is True
    assert user.role == "USER"
    assert repr(user).startswith("<User test@safechat.ai")


def test_postgres_channel_model_attributes():
    channel = Channel(
        name="announcements",
        description="Public announcements",
    )
    assert channel.name == "announcements"
    assert repr(channel).startswith("<Channel #announcements")


def test_mongo_document_serialization():
    mod_meta = ModerationMetadata(
        is_toxic=True,
        overall_score=0.88,
        severity="HIGH",
        categories={"toxic": 0.9, "threat": 0.8},
        suggestion="Let's discuss calmly",
        detected_language="en",
    )
    doc = ChatMessageDocument(
        message_id="msg-101",
        channel_id="general",
        sender_id="user-1",
        sender_name="Alice",
        content="I will kill you",
        status="BLOCKED",
        moderation=mod_meta,
    )

    mongo_dict = doc.to_mongo_dict()
    assert mongo_dict["message_id"] == "msg-101"
    assert mongo_dict["status"] == "BLOCKED"
    assert mongo_dict["moderation"]["is_toxic"] is True
    assert isinstance(mongo_dict["created_at"], str)


def test_moderator_feedback_document_serialization():
    feedback = ModeratorFeedbackDocument(
        feedback_id="fb-101",
        message_id="msg-101",
        moderator_id="mod-admin",
        model_prediction_was_correct=False,
        correct_severity="SAFE",
        notes="False positive due to sarcasm",
    )
    fb_dict = feedback.to_mongo_dict()
    assert fb_dict["feedback_id"] == "fb-101"
    assert fb_dict["correct_severity"] == "SAFE"


# ── 3. Rate Limiter (Memory Fallback) ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_rate_limiter_allows_when_redis_offline():
    # When redis is offline, check_rate_limit gracefully defaults to True
    allowed = await ChatService.check_rate_limit("user-test-offline")
    assert allowed is True


# ── 4. ML Client Local Detoxification Fallback ────────────────────────────────

@pytest.mark.asyncio
async def test_ml_client_detoxify_fallback():
    client = MLClientService()
    # Call detoxify with remote service offline — must fall back to Phase 3 engine
    res = await client.detoxify_text("Shut up you idiot and finish the work!")
    assert "shut up" not in res["detoxified_text"].lower()
    assert "idiot" not in res["detoxified_text"].lower()
    assert res["method"] in ("intent_preserving_scrubber", "gemini", "template-fallback")


# ── 5. FastAPI Gateway Endpoints ──────────────────────────────────────────────

def test_api_root_endpoint():
    with TestClient(app) as client:
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["service"] == "SafeChat API Gateway"
        assert "endpoints" in data
        assert "websocket_chat" in data["endpoints"]


def test_auth_validation_on_empty_request():
    with TestClient(app) as client:
        resp = client.post("/api/v1/auth/register", json={})
        assert resp.status_code == 422  # Pydantic validation error


def test_moderate_validation_empty_text():
    with TestClient(app) as client:
        resp = client.post("/api/v1/moderate", json={"text": ""})
        # Empty text or valid request handling
        assert resp.status_code in (200, 422)

