"""
General Conversation Tool
Handles general questions, greetings, and casual conversation
"""

from langchain.tools import tool
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from config.settings import get_settings
from loguru import logger

settings = get_settings()


def _get_llm():
    """Get Groq LLM instance"""
    return ChatGroq(
        api_key=settings.groq_api_key,
        model_name=settings.groq_model,
        temperature=0.7,  # More creative for conversation
        max_tokens=200,  # Keep responses concise
    )


CONVERSATION_PROMPT = PromptTemplate(
    input_variables=["question"],
    template="""You are a friendly and helpful personal assistant accessible via WhatsApp.

The user asked: {question}

Respond naturally and conversationally. Keep your response brief professional like an Assistance.

You can help users with:
- Creating and managing calendar events
- Reading and sending emails
- Summarizing any document content they provide

If the user is just greeting you or asking general questions, respond warmly and let them know you're here to help.

Your response:"""
)


@tool
def general_conversation_tool(question: str) -> str:
    """
    Use this tool for general questions, greetings, casual conversation, or when the user
    doesn't need calendar/email/resume functionality. Examples: "Hello", "Who are you?",
    "What can you do?", "How are you?", "Thank you", etc.

    Args:
        question: The user's message or question

    Returns:
        A natural, conversational response
    """
    try:
        logger.info(f"Handling general conversation: {question[:50]}...")

        llm = _get_llm()
        prompt = CONVERSATION_PROMPT.format(question=question)

        response = llm.invoke(prompt)

        # Extract text from response
        if hasattr(response, 'content'):
            answer = response.content.strip()
        else:
            answer = str(response).strip()

        logger.info(f"Generated conversation response: {answer[:100]}...")
        return answer

    except Exception as e:
        logger.error(f"Error in general conversation tool: {e}")
        return (
            "Hello! I'm your personal WhatsApp assistant. "
            "I can help you schedule events, manage emails, and work with your resume. "
            "How can I assist you today?"
        )


# Export the tool
__all__ = ["general_conversation_tool"]
