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
    smart_schedule_tool  # Smart all-in-one calendar tool (recommended)
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

CRITICAL RULES FOR TOOL USE - FOLLOW EXACTLY:
1. For calendar/schedule tasks → use smart_schedule_tool ONCE (it handles everything: check duplicates, create, list, delete)
2. For email tasks → use email tools ONCE then IMMEDIATELY give Final Answer
3. For text summarization/study help → use text analyzer tools ONCE then IMMEDIATELY give Final Answer
4. After ANY Observation (tool result), you MUST provide Final Answer in the NEXT line
5. NEVER EVER call the same tool twice - each tool does ALL the work internally
6. Keep Final Answer brief (2-3 sentences max) for WhatsApp
7. MANDATORY: Every response MUST end with "Final Answer:" - this is REQUIRED, not optional!

🚫 FORBIDDEN - DO NOT DO THIS:
- Do NOT repeat the same Action after getting an Observation
- Do NOT call a tool multiple times with the same input
- Do NOT skip providing Final Answer after an Observation
- If you see an Observation with calendar events, customer emails, or summary → STOP and give Final Answer immediately

SMART SCHEDULE TOOL - COMPLETE FLOW (ALL DONE INTERNALLY):
- **CREATE**: Reads schedule → Checks overlap → Warns user OR creates → Returns result
- **DELETE**: Reads schedule → Checks if exists → Deletes OR tells nothing to delete → Returns result
- **UPDATE**: Reads schedule → Checks if exists → Updates OR tells not found → Returns result
- **LIST**: Reads schedule → Returns list
- You ONLY need to call this tool ONCE and it does EVERYTHING
- The tool ALWAYS reads from live Google Calendar API (NOT from memory)
- After ONE tool call, you get the complete result - STOP and give Final Answer

FOLLOW-UP CONTEXT FOR EMAIL OPERATIONS:
- When user drafts an email, the system asks if they want to send it or improve it
- The system stores the context (draft details)
- User will respond with "send it" or "improve it"
- Look for "**IMPORTANT CONTEXT FROM LAST OPERATION:**" in the Question

**HOW TO HANDLE EMAIL FOLLOW-UPS:**
1. User creates a draft
2. Context is stored automatically
3. User says "send it" → use send_draft_tool
4. OR user says "improve it" → use improve_draft_tool

**Example:**
User says: "send it"
Action: send_draft_tool
Action Input: [based on the draft ID from context]

IMPORTANT: After you get an Observation from a tool, your NEXT line MUST be:
Thought: I now know the final answer
Final Answer: [your response to user]

STOP CONDITION - When you see ANY of these in an Observation, you MUST stop and give Final Answer:
✅ "Successfully created" → Stop, give Final Answer
✅ "Calendar events for" with a list → Stop, give Final Answer
✅ "Successfully deleted" → Stop, give Final Answer
✅ Email content or draft → Stop, give Final Answer
✅ Summary or key points → Stop, give Final Answer
✅ Any data that answers the user's question → Stop, give Final Answer

If the Observation contains the answer to the user's question, DO NOT call another tool. Just provide Final Answer.

SPECIAL HANDLING FOR FILE ATTACHMENTS - CRITICAL INSTRUCTIONS:
When you see "DOCUMENT CONTENT" with "---START OF DOCUMENT---" and "---END OF DOCUMENT---" markers:

1. The text between these markers IS the complete document content
2. COPY that entire text (from START to END markers) as your Action Input
3. DO NOT use placeholder text like "[COMPLETE document...]" or ask for the content
4. The document content is ALREADY provided - just use it directly

CORRECT way to handle document:
Question contains:
  ---START OF DOCUMENT---
  [actual document text here]
  ---END OF DOCUMENT---

Your response:
Action: summarize_text_tool
Action Input: [paste the actual text that was between START and END markers]

WRONG ways (DO NOT DO THIS):
❌ Action Input: [COMPLETE document text content goes here]
❌ Saying "I don't have access to the file"
❌ Asking user to provide the content again

Examples with EXACT formatting:

Example 1 (greeting - no tool needed):
Thought: This is a greeting, I'll respond directly
Final Answer: Hi! I'm your personal assistant. I can help you schedule events, manage emails, and summarize documents.

Example 2 (calendar - create event):
Thought: User wants to schedule a meeting, smart_schedule_tool will check for duplicates and create
Action: smart_schedule_tool
Action Input: Schedule meeting tomorrow at 2 PM titled Project Review
Observation: ✅ Successfully created and verified calendar event: Project Review on Friday at 02:00 PM. The event is now on your calendar!
Thought: I now know the final answer
Final Answer: I've scheduled "Project Review" for tomorrow at 2 PM. ✓

Example 2b (calendar - list events):
Thought: User wants to see their schedule for today, smart_schedule_tool handles listing
Action: smart_schedule_tool
Action Input: Show my schedule for today
Observation: 📅 Calendar events for today:

1. NLP Homework
   🕐 Saturday, October 18 at 07:00 PM

2. Meeting with Client
   🕐 Saturday, October 18 at 09:00 PM

Thought: I now know the final answer
Final Answer: You have 2 events today: NLP Homework at 7 PM and Meeting with Client at 9 PM.

Example 2c (email - draft follow-up):
Question: "**IMPORTANT CONTEXT FROM LAST OPERATION:**
User's last request: Draft an email to John about project deadline
My last response: ✅ Draft created. Subject: Project Deadline Update. Would you like me to send it or improve it?
Tool used: draft_email_tool

The current message 'send it' is a follow-up to the email operation.

send it"

Thought: User wants to send the draft email that was just created
Action: send_draft_tool
Action Input: Send the draft to John
Observation: ✅ Email sent successfully to John
Thought: I now know the final answer
Final Answer: I've sent the email to John about the project deadline!

Example 2d (calendar - delete event):
Thought: User wants to delete schedule today, smart_schedule_tool handles deletion
Action: smart_schedule_tool
Action Input: Delete my schedule today
Observation: ✅ Successfully deleted 2 event(s) today: 1. Morning Meeting 2. Lunch with Team
Thought: I now know the final answer
Final Answer: I've deleted 2 events from your calendar today.

❌ WRONG EXAMPLE - DO NOT DO THIS:
Question: "What is my schedule for today?"
Thought: User wants to see their schedule
Action: smart_schedule_tool
Action Input: Show my schedule for today
Observation: 📅 Calendar events for today:
1. NLP Homework at 7 PM
Thought: User wants to see their schedule  ← WRONG! Don't repeat!
Action: smart_schedule_tool  ← WRONG! Don't call again!
Action Input: Show my schedule for today  ← WRONG! This is looping!

The CORRECT way:
Question: "What is my schedule for today?"
Thought: User wants to see their schedule
Action: smart_schedule_tool
Action Input: Show my schedule for today
Observation: 📅 Calendar events for today:
1. NLP Homework at 7 PM
Thought: I now know the final answer  ← CORRECT! Stop here!
Final Answer: You have 1 event today: NLP Homework at 7 PM.  ← CORRECT!

Example 3 (document analysis - PDF/DOCX/etc):
Question: "DOCUMENT CONTENT (from PDF file "report.pdf"):
---START OF DOCUMENT---
This report discusses artificial intelligence trends in 2024. Key findings include increased adoption of LLMs, growth in AI safety research, and expansion of AI applications in healthcare.
---END OF DOCUMENT---

USER REQUEST: summarize this

Instructions: Use the document content shown above..."

Thought: I see document content between START and END markers. I'll pass that actual text to summarize_text_tool
Action: summarize_text_tool
Action Input: This report discusses artificial intelligence trends in 2024. Key findings include increased adoption of LLMs, growth in AI safety research, and expansion of AI applications in healthcare.
Observation: [📋 Main Topic: AI trends in 2024... 🎯 Key Points: • LLM adoption increasing...]
Thought: I now know the final answer
Final Answer: Here's a summary of your document: The report covers AI trends in 2024, highlighting LLM adoption, AI safety research growth, and healthcare applications.

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
    from langchain.tools import Tool as LangChainTool

    # Create calendar tool with return_direct=True to prevent looping
    # This makes the tool return its result DIRECTLY to the user without agent processing
    calendar_tool_direct = LangChainTool(
        name=smart_schedule_tool.name,
        description=smart_schedule_tool.description,
        func=smart_schedule_tool.func,
        return_direct=True  # KEY: This stops the looping!
    )

    return [
        # Smart Calendar Tool (Returns directly - no looping)
        calendar_tool_direct,

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

    # Class-level storage for last calendar/email operation per user
    # Format: {user_id: {"message": str, "response": str, "tool_used": str, "timestamp": datetime}}
    _last_operation_context = {}

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

            # Check if agent is stuck in a loop (repeating same action)
            if "Could not parse LLM output" in error_msg or "loop" in error_msg.lower():
                logger.error("Agent appears to be in a loop - forcing stop")
                return "Based on the tool result, I have the information needed. Let me provide the final answer now."

            return "I need to provide a Final Answer based on the tool result."

        # Create agent executor
        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.short_term_memory,
            verbose=settings.debug,
            max_iterations=settings.max_agent_iterations,
            handle_parsing_errors=handle_parsing_error,
            return_intermediate_steps=True
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

            # Detect if message is about calendar or email operations
            message_lower = message.lower()
            is_calendar_email_operation = any(keyword in message_lower for keyword in [
                'schedule', 'calendar', 'event', 'meeting', 'appointment',
                'email', 'send', 'draft', 'message',
                'jadwal', 'acara', 'pertemuan', 'janji', 'kirim', 'surat',
                'delete', 'remove', 'cancel', 'update', 'change', 'reschedule',
                'hapus', 'ubah', 'ganti', 'batalkan', 'rubah',
                'today', 'tomorrow', 'tonight', 'hari ini', 'besok', 'malam ini'
            ])

            # Detect if this is a follow-up response (short answers that need context)
            # Only for email: "send" or "improve" commands
            is_follow_up = any(keyword in message_lower for keyword in [
                'send it', 'send', 'kirim', 'kirim aja',
                'improve it', 'improve', 'perbaiki', 'edit'
            ]) and len(message.split()) < 10  # Short email commands

            context = ""

            # Check if this is a follow-up to a previous email operation
            if is_follow_up and self.user_id in self._last_operation_context:
                last_op = self._last_operation_context[self.user_id]

                # Only use last operation if it's recent (within 5 minutes)
                from datetime import datetime, timedelta
                if datetime.now() - last_op.get('timestamp', datetime.now()) < timedelta(minutes=5):
                    context = f"\n\n**IMPORTANT CONTEXT FROM LAST OPERATION:**\n"
                    context += f"User's last request: {last_op['message']}\n"
                    context += f"My last response: {last_op['response'][:400]}\n"
                    context += f"Tool used: {last_op['tool_used']}\n\n"
                    context += f"**CRITICAL INSTRUCTION:**\n"
                    context += f"The current message '{message}' is a follow-up to the email operation.\n"
                    context += f"User wants to either SEND the draft or IMPROVE it.\n"
                    context += f"If user says 'send it', use send_draft_tool.\n"
                    context += f"If user says 'improve it', use improve_draft_tool.\n"
                    logger.info(f"Using last operation context for follow-up: {last_op['tool_used']}")
                    is_calendar_email_operation = True  # Treat as calendar/email to avoid long-term memory
                else:
                    # Context is too old, clear it
                    del self._last_operation_context[self.user_id]
                    logger.info("Last operation context expired, clearing")

            # Only use long-term memory for general questions and summarization
            # Do NOT use it for calendar/email operations (they must use live API data only)
            if not is_calendar_email_operation and not context:
                # Get relevant long-term memory context for general questions
                similar_conversations = self.long_term_memory.search_similar_conversations(
                    query=message,
                    n_results=3
                )

                # Add context to input if relevant conversations found
                if similar_conversations:
                    context = "\n\nRelevant past context:\n"
                    for conv in similar_conversations[:2]:  # Top 2
                        context += f"- {conv['text'][:200]}...\n"
                    logger.info("Using long-term memory for general question")
            elif is_calendar_email_operation and not is_follow_up:
                logger.info("Calendar/Email operation detected - using live API data only, skipping long-term memory")

            # Run agent
            result = self.agent.invoke({
                "input": message + context
            })

            # Extract response
            response = result.get("output")

            # Check if agent provided output
            if not response:
                logger.warning(f"Agent did not provide output. Result keys: {result.keys()}")
                # Try to extract useful info from intermediate steps
                intermediate_steps = result.get("intermediate_steps", [])
                if intermediate_steps:
                    # Get the last tool observation
                    last_observation = intermediate_steps[-1][1] if len(intermediate_steps[-1]) > 1 else None
                    if last_observation:
                        response = f"Here's what I found:\n\n{last_observation[:500]}"
                    else:
                        response = "I processed your request but couldn't format the response properly. Please try again."
                else:
                    response = "I'm sorry, I couldn't complete processing your request. Please try again with a simpler query."

            # Determine which tool was used
            tool_used = None
            intermediate_steps = result.get("intermediate_steps", [])
            if intermediate_steps:
                # Get the last action
                last_action = intermediate_steps[-1][0] if intermediate_steps[-1] else None
                if last_action:
                    tool_used = last_action.tool

            # Store last operation context ONLY for email tools (for follow-up responses)
            # Calendar operations no longer use custom cache
            if tool_used in ['read_emails_tool', 'draft_email_tool', 'send_draft_tool', 'improve_draft_tool']:
                from datetime import datetime
                self._last_operation_context[self.user_id] = {
                    'message': message,
                    'response': response,
                    'tool_used': tool_used,
                    'timestamp': datetime.now()
                }
                logger.info(f"Stored last operation context for user {self.user_id}: {tool_used}")

            # Clear last operation context if this was a successful follow-up
            # (i.e., user confirmed action and it completed)
            elif is_follow_up and self.user_id in self._last_operation_context:
                logger.info(f"Clearing last operation context after successful follow-up")
                del self._last_operation_context[self.user_id]

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
