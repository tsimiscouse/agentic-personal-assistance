"""
Database Connection Management
Handles PostgreSQL and ChromaDB connections
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import chromadb
from chromadb.config import Settings as ChromaSettings
from loguru import logger

from config.settings import get_settings

settings = get_settings()

# ============================================
# PostgreSQL Connection
# ============================================

# Create SQLAlchemy engine
engine = create_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=True,  # Verify connections before using
    echo=settings.debug,  # Log SQL queries in debug mode
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for SQLAlchemy models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function for FastAPI to get database session

    Yields:
        Session: SQLAlchemy database session

    Example:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """
    Initialize database tables

    Creates all tables defined in SQLAlchemy models
    Call this on application startup
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


# ============================================
# ChromaDB (Vector Database) Connection
# ============================================

class ChromaDBManager:
    """
    Manager for ChromaDB vector database operations
    Handles persistence, collection management, and queries
    """

    def __init__(self):
        """Initialize ChromaDB client with persistent storage"""
        self.client = None
        self.collection = None
        self._initialize_client()

    def _initialize_client(self):
        """Create and configure ChromaDB client"""
        try:
            # Ensure persist directory exists
            chroma_path = settings.chroma_path
            chroma_path.mkdir(parents=True, exist_ok=True)

            # Create ChromaDB client with persistent storage
            self.client = chromadb.PersistentClient(
                path=str(chroma_path),
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )

            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=settings.chroma_collection_name,
                metadata={"description": "WhatsApp conversation embeddings"}
            )

            logger.info(
                f"ChromaDB initialized successfully at {chroma_path}"
            )
            logger.info(
                f"Collection '{settings.chroma_collection_name}' ready"
            )

        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise

    def add_conversation(
        self,
        user_id: str,
        message: str,
        response: str,
        conversation_id: str,
        metadata: dict = None
    ):
        """
        Add a conversation to the vector store

        Args:
            user_id: WhatsApp user ID
            message: User's message
            response: Agent's response
            conversation_id: Unique conversation identifier
            metadata: Additional metadata to store
        """
        try:
            # Combine message and response for embedding
            text = f"User: {message}\nAssistant: {response}"

            # Prepare metadata
            meta = {
                "user_id": user_id,
                "conversation_id": conversation_id,
                **(metadata or {})
            }

            # Add to collection
            self.collection.add(
                documents=[text],
                metadatas=[meta],
                ids=[conversation_id]
            )

            logger.debug(
                f"Added conversation {conversation_id} to vector store"
            )

        except Exception as e:
            logger.error(f"Failed to add conversation to vector store: {e}")
            raise

    def search_similar_conversations(
        self,
        user_id: str,
        query: str,
        n_results: int = None
    ) -> list:
        """
        Search for similar past conversations

        Args:
            user_id: WhatsApp user ID to filter by
            query: Search query text
            n_results: Number of results to return

        Returns:
            list: Similar conversations with metadata
        """
        try:
            if n_results is None:
                n_results = settings.long_term_memory_retrieval_count

            # Query collection
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where={"user_id": user_id}  # Filter by user
            )

            logger.debug(
                f"Found {len(results['documents'][0])} similar conversations"
            )

            return results

        except Exception as e:
            logger.error(f"Failed to search vector store: {e}")
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

    def delete_user_data(self, user_id: str):
        """
        Delete all conversations for a specific user

        Args:
            user_id: WhatsApp user ID
        """
        try:
            # Get all documents for user
            results = self.collection.get(
                where={"user_id": user_id}
            )

            if results["ids"]:
                # Delete by IDs
                self.collection.delete(ids=results["ids"])
                logger.info(
                    f"Deleted {len(results['ids'])} conversations for user {user_id}"
                )

        except Exception as e:
            logger.error(f"Failed to delete user data from vector store: {e}")
            raise

    def reset_collection(self):
        """
        Reset the entire collection (use with caution!)
        For development/testing purposes only
        """
        try:
            self.client.delete_collection(settings.chroma_collection_name)
            self._initialize_client()
            logger.warning("ChromaDB collection has been reset!")

        except Exception as e:
            logger.error(f"Failed to reset ChromaDB collection: {e}")
            raise


# Singleton instance
_chroma_manager: ChromaDBManager = None


def get_chroma_manager() -> ChromaDBManager:
    """
    Get or create ChromaDB manager singleton

    Returns:
        ChromaDBManager: Vector database manager instance
    """
    global _chroma_manager
    if _chroma_manager is None:
        _chroma_manager = ChromaDBManager()
    return _chroma_manager


# ============================================
# Startup/Shutdown Handlers
# ============================================

def startup_db():
    """
    Initialize all database connections on application startup
    Call this in FastAPI lifespan or startup event
    """
    logger.info("Initializing database connections...")
    init_db()
    get_chroma_manager()
    logger.info("All database connections initialized successfully")


def shutdown_db():
    """
    Cleanup database connections on application shutdown
    Call this in FastAPI lifespan or shutdown event
    """
    logger.info("Closing database connections...")
    engine.dispose()
    logger.info("Database connections closed")
