"""
Unit Tests for Text Analyzer Tool - Happy Path Only
Tests basic successful scenarios for text analysis tools
"""

import pytest
from tools.text_analyzer_tool import (
    summarize_text_tool,
    extract_key_points_tool,
    explain_concept_tool,
    answer_document_question_tool,
    compare_concepts_tool
)


class TestTextAnalyzerTool:
    """Happy path tests for text analyzer tools"""

    def test_summarize_medium_text(self, mock_groq_llm, sample_text):
        """Test: Summarize medium-length text successfully"""
        result = summarize_text_tool(sample_text)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_extract_key_points_from_text(self, mock_groq_llm, sample_text):
        """Test: Extract key points from text successfully"""
        result = extract_key_points_tool(sample_text)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_explain_technical_concept(self, mock_groq_llm):
        """Test: Explain a technical concept successfully"""
        result = explain_concept_tool("Explain machine learning")

        assert isinstance(result, str)
        assert len(result) > 0

    def test_answer_document_question_detailed(self, mock_groq_llm):
        """Test: Answer detailed question about document successfully"""
        document = """
        ---START OF DOCUMENT---
        Machine learning is a subset of AI.
        It enables computers to learn from data.
        Common algorithms include regression and classification.
        ---END OF DOCUMENT---

        Question: What is machine learning?
        """

        result = answer_document_question_tool(document)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_compare_two_concepts_technical(self, mock_groq_llm):
        """Test: Compare technical concepts successfully"""
        result = compare_concepts_tool.invoke({"concept1": "Machine Learning", "concept2": "Deep Learning"})

        assert isinstance(result, str)
        assert len(result) > 0

    def test_summarize_with_long_text(self, mock_groq_llm):
        """Test: Summarize longer paragraph successfully"""
        text = """
        Artificial intelligence has revolutionized technology in recent years.
        Machine learning algorithms can process vast amounts of data.
        Natural language processing enables computers to understand human language.
        Computer vision allows machines to interpret images and videos.
        These technologies are transforming industries worldwide.
        """

        result = summarize_text_tool(text)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_extract_key_points_educational_content(self, mock_groq_llm):
        """Test: Extract key points from educational content successfully"""
        text = """
        Learning programming requires practice and patience.
        Start with basic concepts before moving to advanced topics.
        Build projects to apply your knowledge.
        Read documentation and learn from examples.
        """

        result = extract_key_points_tool(text)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_summarize_technical_document(self, mock_groq_llm):
        """Test: Summarize technical documentation successfully"""
        text = """
        REST API is an architectural style for web services.
        It uses HTTP methods like GET, POST, PUT, and DELETE.
        RESTful APIs are stateless and scalable.
        They return data in JSON or XML format.
        """

        result = summarize_text_tool(text)

        assert isinstance(result, str)
        assert len(result) > 0
