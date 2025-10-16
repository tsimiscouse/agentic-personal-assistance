"""
Long-Term Memory Management
Integrates PostgreSQL and ChromaDB for persistent memory
"""

from sqlalchemy.orm import Session
from typing import List, Dict
from loguru import logger
from datetime import datetime

from models.user import User
from models.conversation import Conversation
from database.connection import get_chroma_manager
from config.settings import get_settings

settings = get_settings()


class LongTermMemory:
    """
    Manages long-term memory using PostgreSQL and ChromaDB
    """

    def __init__(self, db: Session, user_id: str):
        """
        Initialize long-term memory for a user

        Args:
            db: SQLAlchemy database session
            user_id: WhatsApp user ID
        """
        self.db = db
        self.user_id = user_id
        self.chroma = get_chroma_manager()
        self._ensure_user_exists()

    def _ensure_user_exists(self):
        """Ensure user exists in database, create if not"""
        user = self.db.query(User).filter(User.user_id == self.user_id).first()

        if not user:
            user = User(
                user_id=self.user_id,
                created_at=datetime.utcnow(),
                last_interaction=datetime.utcnow()
            )
            self.db.add(user)
            self.db.commit()
            logger.info(f"Created new user: {self.user_id}")
        else:
            # Update last interaction time
            user.last_interaction = datetime.utcnow()
            self.db.commit()

    def save_conversation(
        self,
        user_message: str,
        agent_response: str,
        tool_used: str = None,
        metadata: dict = None
    ) -> str:
        """
        Save conversation to both PostgreSQL and ChromaDB

        Args:
            user_message: User's message
            agent_response: Agent's response
            tool_used: Name of tool used (if any)
            metadata: Additional metadata

        Returns:
            str: Conversation ID
        """
        try:
            # Save to PostgreSQL
            conversation = Conversation(
                user_id=self.user_id,
                user_message=user_message,
                agent_response=agent_response,
                tool_used=tool_used,
                metadata=metadata or {}
            )

            self.db.add(conversation)
            self.db.commit()
            self.db.refresh(conversation)

            # Save to ChromaDB for semantic search
            # ChromaDB doesn't accept None values - filter them out
            chroma_metadata = {
                "timestamp": conversation.created_at.isoformat(),
                **(metadata or {})
            }

            # Only add tool_used if it's not None
            if tool_used is not None:
                chroma_metadata["tool_used"] = tool_used

            # Filter out any None values from metadata dict
            chroma_metadata = {k: v for k, v in chroma_metadata.items() if v is not None}

            self.chroma.add_conversation(
                user_id=self.user_id,
                message=user_message,
                response=agent_response,
                conversation_id=conversation.id,
                metadata=chroma_metadata
            )

            logger.info(f"Saved conversation {conversation.id} to long-term memory")
            return conversation.id

        except Exception as e:
            logger.error(f"Error saving conversation: {e}")
            self.db.rollback()
            raise

    def get_recent_conversations(self, limit: int = None) -> List[Dict]:
        """
        Retrieve recent conversations from PostgreSQL

        Args:
            limit: Maximum number of conversations to retrieve

        Returns:
            List[Dict]: Recent conversations
        """
        try:
            if limit is None:
                limit = settings.short_term_memory_size

            conversations = (
                self.db.query(Conversation)
                .filter(Conversation.user_id == self.user_id)
                .order_by(Conversation.created_at.desc())
                .limit(limit)
                .all()
            )

            return [conv.to_dict() for conv in reversed(conversations)]

        except Exception as e:
            logger.error(f"Error retrieving recent conversations: {e}")
            return []

    def search_similar_conversations(self, query: str, n_results: int = None) -> List[Dict]:
        """
        Search for semantically similar past conversations

        Args:
            query: Search query
            n_results: Number of results to return

        Returns:
            List[Dict]: Similar conversations with context
        """
        try:
            if n_results is None:
                n_results = settings.long_term_memory_retrieval_count

            # Search ChromaDB
            results = self.chroma.search_similar_conversations(
                user_id=self.user_id,
                query=query,
                n_results=n_results
            )

            # Format results
            similar_conversations = []
            if results and results.get("documents"):
                for i, doc in enumerate(results["documents"][0]):
                    similar_conversations.append({
                        "text": doc,
                        "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                        "distance": results["distances"][0][i] if results.get("distances") else 0
                    })

            logger.info(f"Found {len(similar_conversations)} similar conversations")
            return similar_conversations

        except Exception as e:
            logger.error(f"Error searching similar conversations: {e}")
            return []

    def get_user_profile(self) -> Dict:
        """
        Get user profile information

        Returns:
            Dict: User profile data
        """
        try:
            user = self.db.query(User).filter(User.user_id == self.user_id).first()
            return user.to_dict() if user else {}
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            return {}

    def update_user_profile(self, **kwargs):
        """
        Update user profile information

        Args:
            **kwargs: Fields to update (name, timezone, preferences, etc.)
        """
        try:
            user = self.db.query(User).filter(User.user_id == self.user_id).first()

            if user:
                for key, value in kwargs.items():
                    if hasattr(user, key):
                        setattr(user, key, value)

                user.updated_at = datetime.utcnow()
                self.db.commit()
                logger.info(f"Updated profile for user {self.user_id}")

        except Exception as e:
            logger.error(f"Error updating user profile: {e}")
            self.db.rollback()
            raise

    def get_conversation_count(self) -> int:
        """
        Get total number of conversations for user

        Returns:
            int: Conversation count
        """
        try:
            count = (
                self.db.query(Conversation)
                .filter(Conversation.user_id == self.user_id)
                .count()
            )
            return count
        except Exception as e:
            logger.error(f"Error getting conversation count: {e}")
            return 0

    def delete_all_conversations(self):
        """
        Delete all conversations for user (GDPR compliance)
        """
        try:
            # Delete from PostgreSQL
            self.db.query(Conversation).filter(
                Conversation.user_id == self.user_id
            ).delete()
            self.db.commit()

            # Delete from ChromaDB
            self.chroma.delete_user_data(self.user_id)

            logger.info(f"Deleted all conversations for user {self.user_id}")

        except Exception as e:
            logger.error(f"Error deleting conversations: {e}")
            self.db.rollback()
            raise


def get_long_term_memory(db: Session, user_id: str) -> LongTermMemory:
    """
    Factory function to create LongTermMemory instance

    Args:
        db: SQLAlchemy database session
        user_id: WhatsApp user ID

    Returns:
        LongTermMemory: Memory manager instance
    """
    return LongTermMemory(db, user_id)
