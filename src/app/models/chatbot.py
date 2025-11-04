"""AI chatbot system models for chat sessions and message history."""

from datetime import datetime
from typing import Optional
from uuid import uuid4
import uuid as uuid_pkg # Added to specify uuid.UUID type hint

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.app.core.db.database import Base


class ChatSession(Base):
    """Chat sessions for AI conversations."""
    
    __tablename__ = "chat_sessions"
    
    # Fields without defaults come first
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    
    # Fields with defaults come after
    id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    model_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("uploaded_models.id"), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="chat_sessions")
    model = relationship("UploadedModel", back_populates="chat_sessions")
    messages = relationship("ChatHistory", back_populates="session", cascade="all, delete-orphan")


class ChatHistory(Base):
    """Chat message history for AI conversations."""
    
    __tablename__ = "chat_history"
    
    # Fields without defaults come first
    session_id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"))
    
    message_type: Mapped[str] = mapped_column(String(50), nullable=False)  # user|ai
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Fields with defaults come after
    id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    file_name: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    file_data: Mapped[Optional[str]] = mapped_column(Text, default=None)  # Base64 encoded file data
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    session = relationship("ChatSession", back_populates="messages")