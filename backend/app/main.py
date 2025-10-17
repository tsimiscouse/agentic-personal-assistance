"""
FastAPI Main Application
Entry point for the Personal Assistant WhatsApp Bot backend
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
from loguru import logger
import sys

from config.settings import get_settings
from database.connection import get_db, startup_db, shutdown_db
from app.agent import create_agent_for_user
from utils.file_extractor import extract_text_from_base64

settings = get_settings()


# ============================================
# Configure Logging
# ============================================

logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    level=settings.log_level,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
)

# File logging
log_path = settings.log_path
log_path.parent.mkdir(parents=True, exist_ok=True)
logger.add(
    str(log_path),
    rotation=settings.log_max_bytes,  # Pass integer directly (bytes)
    retention=settings.log_backup_count,
    level=settings.log_level,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}"
)


# ============================================
# Application Lifespan
# ============================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handle application startup and shutdown
    """
    # Startup
    logger.info("Starting Personal Assistant WhatsApp Bot backend...")
    try:
        startup_db()
        logger.info("Application started successfully")
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down application...")
    shutdown_db()
    logger.info("Application shutdown complete")


# ============================================
# FastAPI Application
# ============================================

app = FastAPI(
    title="Personal Assistant WhatsApp Bot",
    description="AI-powered personal assistant with calendar, email, and resume tools",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# Request/Response Models
# ============================================

class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    user_id: str = Field(..., description="WhatsApp user ID (phone@c.us)")
    message: str = Field(..., min_length=1, description="User's message")
    file_data: str | None = Field(None, description="Base64 encoded file content (optional)")
    file_name: str | None = Field(None, description="Original filename (optional)")
    file_mime: str | None = Field(None, description="File MIME type (optional)")

    class Config:
        schema_extra = {
            "example": {
                "user_id": "1234567890@c.us",
                "message": "Schedule a meeting tomorrow at 2 PM with John"
            }
        }


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    response: str = Field(..., description="Agent's response")
    status: str = Field(..., description="Status: success or error")
    tool_used: str | None = Field(None, description="Tool used (if any)")
    conversation_id: str | None = Field(None, description="Conversation ID")


class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str
    version: str
    environment: str


# ============================================
# API Endpoints
# ============================================

@app.get("/", response_model=dict)
async def root():
    """
    Root endpoint
    """
    return {
        "message": "Personal Assistant WhatsApp Bot API",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint

    Returns application status and version information
    """
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        environment=settings.environment
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Main chat endpoint

    Processes user messages through the LangChain agent

    Args:
        request: Chat request with user_id and message
        db: Database session (injected)

    Returns:
        ChatResponse: Agent's response with metadata

    Raises:
        HTTPException: If processing fails
    """
    try:
        logger.info(f"Received message from user {request.user_id}")

        # Prepare message
        message = request.message

        # If file attached, extract text and prepend to message
        if request.file_data and request.file_name:
            logger.info(f"Processing file attachment: {request.file_name}")

            # Extract text from file
            extraction_result = extract_text_from_base64(
                base64_data=request.file_data,
                filename=request.file_name,
                max_chars=15000
            )

            if extraction_result['success']:
                # Prepend extracted text to message
                file_content = extraction_result['text']
                file_type = extraction_result['file_type'].upper()

                # Format message to make it clear for the agent
                message = f"""User uploaded a {file_type} document ({request.file_name}) and asked: "{request.message}"

Here is the complete text content from the document:

{file_content}

Please process the document content above according to the user's request."""

                logger.info(f"Successfully extracted {len(file_content)} characters from {file_type}")
            else:
                # If extraction fails, inform the user
                error_msg = extraction_result.get('error', 'Unknown error')
                message = f"{request.message}\n\n[Note: I tried to read the file '{request.file_name}' but encountered an error: {error_msg}]"
                logger.warning(f"File extraction failed: {error_msg}")

        # Create agent for user
        agent = create_agent_for_user(db, request.user_id)

        # Process message
        result = agent.process_message(message)

        # Return response
        return ChatResponse(
            response=result["response"],
            status=result["status"],
            tool_used=result.get("tool_used"),
            conversation_id=result.get("conversation_id")
        )

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred processing your message"
        )


@app.get("/history/{user_id}")
async def get_history(
    user_id: str,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Get conversation history for a user

    Args:
        user_id: WhatsApp user ID
        limit: Number of conversations to retrieve
        db: Database session (injected)

    Returns:
        dict: Conversation history
    """
    try:
        agent = create_agent_for_user(db, user_id)
        history = agent.get_conversation_history(limit=limit)

        return {
            "user_id": user_id,
            "count": len(history),
            "conversations": history
        }

    except Exception as e:
        logger.error(f"Error getting history: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve conversation history"
        )


@app.delete("/session/{user_id}")
async def clear_session(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Clear short-term memory (current session) for a user

    Args:
        user_id: WhatsApp user ID
        db: Database session (injected)

    Returns:
        dict: Confirmation message
    """
    try:
        agent = create_agent_for_user(db, user_id)
        agent.clear_session()

        return {
            "message": f"Session cleared for user {user_id}",
            "status": "success"
        }

    except Exception as e:
        logger.error(f"Error clearing session: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to clear session"
        )


# ============================================
# Error Handlers
# ============================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler

    Catches unhandled exceptions and returns a proper error response
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal error occurred",
            "status": "error"
        }
    )


# ============================================
# Run Application
# ============================================

if __name__ == "__main__":
    import uvicorn

    logger.info("Starting FastAPI server directly...")

    uvicorn.run(
        "main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
