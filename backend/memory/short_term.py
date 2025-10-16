"""
Short-Term Memory Management
Handles conversation buffer memory for current session context
"""

from langchain.memory import ConversationBufferMemory
from langchain.memory.chat_memory import BaseChatMemory
from typing import Dict
from loguru import logger
from config.settings import get_settings

settings = get_settings()

# Dictionary to store memory instances per user
_memory_store: Dict[str, ConversationBufferMemory] = {}


def get_short_term_memory(user_id: str) -> ConversationBufferMemory:
    """
    Get or create short-term memory for a specific user

    Args:
        user_id: WhatsApp user ID

    Returns:
        ConversationBufferMemory: Memory instance for the user
    """
    global _memory_store

    if user_id not in _memory_store:
        logger.info(f"Creating new short-term memory for user {user_id}")

        _memory_store[user_id] = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="output",
            input_key="input"
        )

    return _memory_store[user_id]


def clear_short_term_memory(user_id: str):
    """
    Clear short-term memory for a user

    Args:
        user_id: WhatsApp user ID
    """
    if user_id in _memory_store:
        _memory_store[user_id].clear()
        logger.info(f"Cleared short-term memory for user {user_id}")


def remove_user_memory(user_id: str):
    """
    Remove user's memory instance completely

    Args:
        user_id: WhatsApp user ID
    """
    if user_id in _memory_store:
        del _memory_store[user_id]
        logger.info(f"Removed memory instance for user {user_id}")


def get_memory_summary(user_id: str) -> dict:
    """
    Get summary of user's short-term memory

    Args:
        user_id: WhatsApp user ID

    Returns:
        dict: Memory statistics and recent messages
    """
    if user_id not in _memory_store:
        return {"message_count": 0, "messages": []}

    memory = _memory_store[user_id]

    try:
        # Get buffer contents
        buffer = memory.load_memory_variables({})

        return {
            "message_count": len(buffer.get("chat_history", [])),
            "messages": buffer.get("chat_history", [])
        }
    except Exception as e:
        logger.error(f"Error getting memory summary: {e}")
        return {"message_count": 0, "messages": []}
