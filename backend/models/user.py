"""
User Model
Stores user profile information and preferences
"""

from sqlalchemy import Column, String, DateTime, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from database.connection import Base


class User(Base):
    """
    User model for storing WhatsApp user information
    """
    __tablename__ = "users"

    # Primary identifier (WhatsApp user ID: phone@c.us)
    user_id = Column(String, primary_key=True, index=True)

    # User profile
    name = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    timezone = Column(String, default="UTC")

    # User preferences (stored as JSON)
    preferences = Column(JSON, default={})

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_interaction = Column(DateTime, default=datetime.utcnow)

    # Status
    is_active = Column(Boolean, default=True)

    # Relationships
    conversations = relationship(
        "Conversation",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User(user_id='{self.user_id}', name='{self.name}')>"

    def to_dict(self):
        """Convert user to dictionary"""
        return {
            "user_id": self.user_id,
            "name": self.name,
            "phone_number": self.phone_number,
            "timezone": self.timezone,
            "preferences": self.preferences,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_interaction": self.last_interaction.isoformat() if self.last_interaction else None,
            "is_active": self.is_active,
        }
