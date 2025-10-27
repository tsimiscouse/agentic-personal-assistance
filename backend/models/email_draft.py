"""
Email Draft Model
Stores email drafts with automatic expiry
"""

from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from database.connection import Base
import uuid


class EmailDraft(Base):
    """
    Email Draft model for storing temporary email drafts

    Drafts automatically expire after 1 hour to prevent database bloat
    """
    __tablename__ = "email_drafts"

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

    # Email content
    to_email = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)

    # Gmail integration
    gmail_draft_id = Column(
        String,
        nullable=True
    )  # Gmail draft ID for real-time sync

    # Status tracking
    status = Column(
        String,
        default="draft",
        nullable=False
    )  # draft, sent, cancelled

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(
        DateTime,
        default=lambda: datetime.utcnow() + timedelta(hours=1),
        index=True
    )  # Drafts expire after 1 hour

    # Relationship
    user = relationship("User", back_populates="email_drafts")

    def __repr__(self):
        return f"<EmailDraft(id='{self.id}', user_id='{self.user_id}', to='{self.to_email}', status='{self.status}')>"

    def to_dict(self):
        """Convert email draft to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "to_email": self.to_email,
            "subject": self.subject,
            "body": self.body,
            "gmail_draft_id": self.gmail_draft_id,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    def is_expired(self) -> bool:
        """Check if draft has expired"""
        return datetime.utcnow() > self.expires_at

    def extend_expiry(self, hours: int = 1):
        """Extend draft expiry time"""
        self.expires_at = datetime.utcnow() + timedelta(hours=hours)
