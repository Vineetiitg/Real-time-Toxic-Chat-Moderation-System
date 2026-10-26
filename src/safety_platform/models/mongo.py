"""
SafeChat Safety Platform — MongoDB Document Models

Defines document schemas for:
  - ChatMessageDocument: full message history + moderation audit trace
  - ModerationMetadata: granular 6-category scores, severity, and AI rewrite
  - ModeratorFeedbackDocument: continuous learning review corrections
"""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ModerationMetadata(BaseModel):
    """Granular ML safety evaluation attached to each chat message."""
    is_toxic: bool = False
    overall_score: float = 0.0
    severity: str = "SAFE"  # SAFE | LOW | MEDIUM | HIGH
    categories: Dict[str, float] = Field(default_factory=dict)
    suggestion: Optional[str] = None
    detected_language: str = "en"
    inference_time_ms: int = 0
    model_version: str = "v3-deberta"


class ChatMessageDocument(BaseModel):
    """Complete chat message document stored in MongoDB."""
    message_id: str
    channel_id: str
    sender_id: str
    sender_name: str
    content: str
    status: str = "DELIVERED"  # DELIVERED | FLAGGED | BLOCKED
    moderation: Optional[ModerationMetadata] = None
    context_snapshot: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def to_mongo_dict(self) -> Dict:
        """Convert to MongoDB-compatible dictionary with ISO string datetimes."""
        data = self.model_dump()
        if isinstance(data.get("created_at"), datetime):
            data["created_at"] = data["created_at"].isoformat()
        return data


class ModeratorFeedbackDocument(BaseModel):
    """Human review correction stored in MongoDB for continuous learning."""
    feedback_id: str
    message_id: str
    moderator_id: str
    model_prediction_was_correct: bool
    correct_severity: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def to_mongo_dict(self) -> Dict:
        """Convert to MongoDB dictionary."""
        data = self.model_dump()
        if isinstance(data.get("created_at"), datetime):
            data["created_at"] = data["created_at"].isoformat()
        return data

