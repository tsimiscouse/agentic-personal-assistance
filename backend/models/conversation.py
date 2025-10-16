"""
Conversation Model
Stores conversation history and metadata
"""

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from database.connection import Base
import uuid


class Conversation(Base):
    """
    Conversation model for storing message exchanges
    """
    __tablename__ = "conversations"

    # Primary key
    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # Foreign key to user
    user_id = Column(
        String,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Conversation content
    user_message = Column(Text, nullable=False)
    agent_response = Column(Text, nullable=False)

    # Metadata
    tool_used = Column(String, nullable=True)  # Which tool was invoked
    conversation_metadata = Column(JSON, default={})  # Additional metadata (renamed from 'metadata')

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationship
    user = relationship("User", back_populates="conversations")

    def __repr__(self):
        return f"<Conversation(id='{self.id}', user_id='{self.user_id}')>"

    def to_dict(self):
        """Convert conversation to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_message": self.user_message,
            "agent_response": self.agent_response,
            "tool_used": self.tool_used,
            "conversation_metadata": self.conversation_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
