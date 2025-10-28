"""
Unit Tests for General Conversation Tool - Happy Path Only
Tests basic successful conversational scenarios
"""

import pytest
from tools.general_conversation_tool import general_conversation_tool


class TestGeneralConversationTool:
    """Happy path tests for general conversation tool"""

    def test_technical_question(self, mock_groq_llm):
        """Test: Answer technical question successfully"""
        result = general_conversation_tool("How does machine learning work?")

        assert isinstance(result, str)
        assert len(result) > 0

    def test_explanation_request(self, mock_groq_llm):
        """Test: Provide explanation successfully"""
        result = general_conversation_tool("Explain artificial intelligence")

        assert isinstance(result, str)
        assert len(result) > 0

    def test_long_question(self, mock_groq_llm):
        """Test: Answer longer detailed question successfully"""
        result = general_conversation_tool(
            "Can you explain the difference between supervised and unsupervised learning?"
        )

        assert isinstance(result, str)
        assert len(result) > 0

    def test_casual_conversation(self, mock_groq_llm):
        """Test: Handle casual conversation successfully"""
        result = general_conversation_tool("Tell me something interesting")

        assert isinstance(result, str)
        assert len(result) > 0

    def test_programming_question(self, mock_groq_llm):
        """Test: Answer programming question successfully"""
        result = general_conversation_tool("What is a function in programming?")

        assert isinstance(result, str)
        assert len(result) > 0

    def test_general_knowledge_question(self, mock_groq_llm):
        """Test: Answer general knowledge question successfully"""
        result = general_conversation_tool("What is the weather like?")

        assert isinstance(result, str)
        assert len(result) > 0
