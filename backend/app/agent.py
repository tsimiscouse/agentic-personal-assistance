"""
LangChain Agent Implementation
Uses ReAct (Reasoning + Acting) framework with Groq LLM
"""

from langchain.agents import create_react_agent, AgentExecutor
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from langchain.tools import Tool
from sqlalchemy.orm import Session
from loguru import logger
from typing import Dict, List

from config.settings import get_settings
from memory.short_term import get_short_term_memory
from memory.long_term import get_long_term_memory
# Import all tools
from tools.calendar_tool import (
    create_calendar_event_tool,
    list_calendar_events_tool,
    delete_calendar_event_tool
)
from tools.email_tool import (
    read_emails_tool,
    draft_email_tool,
    send_draft_tool,
    improve_draft_tool
)
from tools.text_analyzer_tool import (
    summarize_text_tool,
    extract_key_points_tool,
    explain_concept_tool,
    compare_concepts_tool
)

settings = get_settings()


# ============================================
# Agent Prompt Template
# ============================================

AGENT_PROMPT_TEMPLATE = """You are a helpful personal assistant accessible via WhatsApp.

You have access to the following tools:

{tools}

Use this EXACT format (no commas, no extra punctuation):

Thought: Do I need to use a tool? What does the user want?
Action: tool_name_here
Action Input: input text here
Observation: the result of the action
... (repeat Thought/Action/Action Input/Observation ONLY if needed)
Thought: I now know the final answer
Final Answer: the final answer to send to the user

CRITICAL: Tool names must be written WITHOUT commas or any punctuation after them.
WRONG: "Action: summarize_text_tool,"
CORRECT: "Action: summarize_text_tool"

IMPORTANT: You can respond WITHOUT using any tool if:
- User is greeting you (Hello, Hi, Good morning, etc.)
- User asks who you are or what you can do
- User is saying thanks or goodbye
- User is having casual conversation

For these cases, skip Action/Observation and go directly to:
Thought: This is a greeting/casual question, I'll respond directly
Final Answer: [your friendly response]

CRITICAL RULES FOR TOOL USE:
1. For calendar events → use create_calendar_event_tool ONCE then give Final Answer
2. For email tasks → use email tools ONCE then give Final Answer
3. For text summarization/study help → use text analyzer tools ONCE then give Final Answer
4. After ANY tool succeeds (shows ✓ or returns content), IMMEDIATELY give Final Answer
5. Do NOT call the same tool multiple times
6. Keep Final Answer brief (2-3 sentences max) for WhatsApp
7. ALWAYS end with "Final Answer:" - never skip it!

SPECIAL HANDLING FOR FILE ATTACHMENTS:
When you see a message starting with "User uploaded a [FILE_TYPE] document":
- The message contains the COMPLETE TEXT CONTENT extracted from the document
- The text content appears after "Here is the complete text content from the document:"
- You MUST pass this full text content to the summarization/analysis tool
- Do NOT say you cannot access files - the content is already provided in the message
- Use the document text directly as input to summarize_text_tool or other text analysis tools
- The content is NOT external - it's right there in the message you received

Examples with EXACT formatting:

Example 1 (greeting - no tool needed):
Thought: This is a greeting, I'll respond directly
Final Answer: Hi! I'm your personal assistant. I can help you schedule events, manage emails, and summarize documents.

Example 2 (calendar event):
Thought: User wants to schedule a meeting
Action: create_calendar_event_tool
Action Input: Schedule meeting tomorrow at 2 PM titled Project Review
Observation: ✓ Calendar event created: Project Review on 2024-10-18 at 14:00
Thought: I now know the final answer
Final Answer: I've scheduled "Project Review" for tomorrow at 2 PM.

Example 3 (document summarization):
Thought: User wants a document summary
Action: summarize_text_tool
Action Input: [COMPLETE document text content goes here]
Observation: [summary result]
Thought: I now know the final answer
Final Answer: Here's the summary of your document: [brief summary]

Begin!

Previous conversation:
{chat_history}

Question: {input}
Thought:{agent_scratchpad}"""


def create_agent_prompt() -> PromptTemplate:
    """
    Create the agent prompt template

    Returns:
        PromptTemplate: Configured prompt template
    """
    return PromptTemplate(
        template=AGENT_PROMPT_TEMPLATE,
        input_variables=["input", "chat_history", "agent_scratchpad"],
        partial_variables={
            "tools": "\n".join([
                f"- {tool.name}: {tool.description}"
                for tool in get_agent_tools()
            ]),
            "tool_names": ", ".join([tool.name for tool in get_agent_tools()])
        }
    )


def get_agent_tools() -> List[Tool]:
    """
    Get list of tools available to the agent

    Returns:
        List[Tool]: Configured tools
    """
    return [
        # Calendar Tools
        create_calendar_event_tool,
        list_calendar_events_tool,
        delete_calendar_event_tool,

        # Email Tools
        read_emails_tool,
        draft_email_tool,
        send_draft_tool,
        improve_draft_tool,

        # Text Analysis & Study Tools
        summarize_text_tool,
        extract_key_points_tool,
        explain_concept_tool,
        compare_concepts_tool
    ]


def create_llm() -> ChatGroq:
    """
    Initialize Groq LLM

    Returns:
        ChatGroq: Configured Groq LLM instance
    """
    return ChatGroq(
        api_key=settings.groq_api_key,
        model_name=settings.groq_model,
        temperature=settings.llm_temperature,
        max_tokens=settings.max_response_tokens,
    )


class PersonalAssistantAgent:
    """
    Personal Assistant Agent using LangChain ReAct framework
    """

    def __init__(self, db: Session, user_id: str):
        """
        Initialize agent for a specific user

        Args:
            db: Database session
            user_id: WhatsApp user ID
        """
        self.user_id = user_id
        self.db = db

        # Initialize memory systems
        self.short_term_memory = get_short_term_memory(user_id)
        self.long_term_memory = get_long_term_memory(db, user_id)

        # Initialize LLM and tools
        self.llm = create_llm()
        self.tools = get_agent_tools()

        # Create agent
        self.agent = self._create_agent()

        logger.info(f"Initialized agent for user {user_id}")

    def _create_agent(self) -> AgentExecutor:
        """
        Create the ReAct agent with tools and memory

        Returns:
            AgentExecutor: Configured agent executor
        """
        # Create prompt
        prompt = create_agent_prompt()

        # Create ReAct agent
        agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )

        # Custom parsing error handler
        def handle_parsing_error(error):
            """Handle parsing errors gracefully"""
            error_msg = str(error)
            logger.warning(f"Agent parsing error: {error_msg}")
            return "I need to correct my response format and try again."

        # Create agent executor
        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.short_term_memory,
            verbose=settings.debug,
            max_iterations=settings.max_agent_iterations,
            handle_parsing_errors=handle_parsing_error,
            return_intermediate_steps=True,
            early_stopping_method="generate"  # Stop early if Final Answer is found
        )

        return agent_executor

    def process_message(self, message: str) -> Dict:
        """
        Process user message through the agent

        Args:
            message: User's WhatsApp message

        Returns:
            Dict: Agent response with metadata
        """
        try:
            logger.info(f"Processing message from {self.user_id}: {message[:50]}...")

            # Get relevant long-term memory context
            similar_conversations = self.long_term_memory.search_similar_conversations(
                query=message,
                n_results=3
            )

            # Add context to input if relevant conversations found
            context = ""
            if similar_conversations:
                context = "\n\nRelevant past context:\n"
                for conv in similar_conversations[:2]:  # Top 2
                    context += f"- {conv['text'][:200]}...\n"

            # Run agent
            result = self.agent.invoke({
                "input": message + context
            })

            # Extract response
            response = result.get("output", "I'm sorry, I couldn't process that.")

            # Determine which tool was used
            tool_used = None
            intermediate_steps = result.get("intermediate_steps", [])
            if intermediate_steps:
                # Get the last action
                last_action = intermediate_steps[-1][0] if intermediate_steps[-1] else None
                if last_action:
                    tool_used = last_action.tool

            # Save to long-term memory
            conversation_id = self.long_term_memory.save_conversation(
                user_message=message,
                agent_response=response,
                tool_used=tool_used,
                metadata={
                    "intermediate_steps_count": len(intermediate_steps)
                }
            )

            logger.info(f"Successfully processed message, conversation_id: {conversation_id}")

            return {
                "response": response,
                "tool_used": tool_used,
                "conversation_id": conversation_id,
                "status": "success"
            }

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)

            # Return user-friendly error message
            error_response = "I apologize, but I encountered an error processing your request. Please try again."

            # Still save to memory for debugging
            try:
                self.long_term_memory.save_conversation(
                    user_message=message,
                    agent_response=error_response,
                    metadata={"error": str(e)}
                )
            except:
                pass  # Don't fail if memory save fails

            return {
                "response": error_response,
                "tool_used": None,
                "conversation_id": None,
                "status": "error",
                "error": str(e)
            }

    def get_conversation_history(self, limit: int = 10) -> List[Dict]:
        """
        Get recent conversation history

        Args:
            limit: Number of conversations to retrieve

        Returns:
            List[Dict]: Recent conversations
        """
        return self.long_term_memory.get_recent_conversations(limit=limit)

    def clear_session(self):
        """Clear short-term memory (current session)"""
        self.short_term_memory.clear()
        logger.info(f"Cleared session for user {self.user_id}")


def create_agent_for_user(db: Session, user_id: str) -> PersonalAssistantAgent:
    """
    Factory function to create agent for a user

    Args:
        db: Database session
        user_id: WhatsApp user ID

    Returns:
        PersonalAssistantAgent: Configured agent instance
    """
    return PersonalAssistantAgent(db, user_id)
