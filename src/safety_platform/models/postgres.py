"""
SafeChat Safety Platform — PostgreSQL Relational Models

Defines:
  - User: user identity, password hash, role, activation status
  - Channel: discussion rooms, ownership, description
"""

import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from safety_platform.core.db import Base


class User(Base):
    """User account model stored in PostgreSQL."""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(100), nullable=False)
    role = Column(String(20), default="USER", nullable=False)  # USER | ADMIN | MODERATOR
    active = Column(Boolean, default=True, nullable=False)
    is_muted = Column(Boolean, default=False, nullable=False)
    violation_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    channels = relationship("Channel", back_populates="creator", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email} ({self.id})>"


class Channel(Base):
    """Chat channel/room model stored in PostgreSQL."""
    __tablename__ = "channels"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    created_by_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    creator = relationship("User", back_populates="channels")

    def __repr__(self):
        return f"<Channel #{self.name} ({self.id})>"
