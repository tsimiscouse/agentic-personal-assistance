"""
Text Analyzer Tool
General-purpose text summarization and analysis with PDF support
Designed for study materials, reports, articles, and any text content
"""

from langchain.tools import tool
from langchain_groq import ChatGroq
from loguru import logger
from config.settings import get_settings
import PyPDF2
import io
from typing import Optional

settings = get_settings()

# Token usage optimization
MAX_TEXT_LENGTH = 8000  # Limit input to ~2000 tokens (4 chars ≈ 1 token)
SUMMARY_TEMPERATURE = 0.2  # Low temperature for consistency
STUDY_TEMPERATURE = 0.4  # Slightly higher for creative explanations


# ============================================
# MAIN SUMMARIZATION TOOL
# ============================================

@tool
def summarize_text_tool(text_input: str, is_pdf_path: bool = False) -> str:
    """
    Summarize any text content into clear, structured bullet points.

    IMPORTANT: Pass the FULL TEXT CONTENT directly to this tool, not just filenames or references.
    When document content is provided in the message, use that complete text as input.

    Perfect for:
    - Study materials (textbooks, lecture notes, research papers)
    - Reports (business, technical, academic)
    - Articles and blog posts
    - Documentation and guides
    - Meeting notes and transcripts
    - Documents uploaded by users (PDF, DOCX, PPTX, etc.)

    Input examples:
    - Plain text: "Quantum computing is a revolutionary approach... [full content]"
    - Document content: "[Complete extracted text from user's uploaded document]"
    - Long articles: "[Full article text here]"

    Args:
        text_input: The FULL TEXT CONTENT to summarize (not a file path or reference)
        is_pdf_path: Set to True ONLY if input is an actual file path (rarely used)

    Returns:
        str: Structured summary with main topics and key points
    """
    try:
        # Extract text from PDF if needed
        if is_pdf_path:
            logger.info(f"Extracting text from PDF: {text_input}")
            text_content = _extract_text_from_pdf(text_input)

            if not text_content:
                return "I couldn't extract text from the PDF file. Please ensure it's a valid text-based PDF."
        else:
            text_content = text_input

        # Truncate if too long for token efficiency
        if len(text_content) > MAX_TEXT_LENGTH:
            logger.info(f"Truncating text from {len(text_content)} to {MAX_TEXT_LENGTH} chars")
            text_content = text_content[:MAX_TEXT_LENGTH] + "\n\n[Note: Text was truncated for processing]"

        logger.info(f"Summarizing text ({len(text_content)} characters)")

        # Initialize LLM with token-efficient settings
        llm = ChatGroq(
            api_key=settings.groq_api_key,
            model_name=settings.groq_model,  # llama-3.1-8b-instant for speed
            temperature=SUMMARY_TEMPERATURE,
            max_tokens=500  # Limit output for efficiency
        )

        # Create efficient summarization prompt
        prompt = f"""Analyze and summarize the following text in a clear, structured format.

Text to summarize:
{text_content}

Provide a summary with this structure:

📋 **Main Topic:**
[One sentence describing the overall subject]

🎯 **Key Points:**
• [Main point 1]
• [Main point 2]
• [Main point 3]
• [Continue with important points - max 6 points]

💡 **Key Takeaways:**
• [Important insight 1]
• [Important insight 2]

Keep it concise and focused on the most important information. Use bullet points for clarity."""

        # Get summary from LLM
        response = llm.invoke(prompt)

        # Extract content
        if hasattr(response, 'content'):
            summary = response.content
        else:
            summary = str(response)

        logger.info("Summary generated successfully")

        return summary.strip()

    except Exception as e:
        logger.error(f"Error in summarize_text_tool: {e}")
        return "I encountered an error while summarizing the text. Please ensure the content is valid or try with shorter text."


# ============================================
# KEY POINTS EXTRACTION TOOL
# ============================================

@tool
def extract_key_points_tool(text_input: str, is_pdf_path: bool = False) -> str:
    """
    Extract main topics and key points from any text content.

    Great for:
    - Quick overview of study materials
    - Identifying important concepts
    - Creating study guides
    - Reviewing long documents

    Args:
        text_input: Text content or PDF file path
        is_pdf_path: Set to True if input is a PDF file path

    Returns:
        str: Organized list of main topics and key points
    """
    try:
        # Extract text from PDF if needed
        if is_pdf_path:
            text_content = _extract_text_from_pdf(text_input)
            if not text_content:
                return "Couldn't extract text from PDF."
        else:
            text_content = text_input

        # Truncate for efficiency
        if len(text_content) > MAX_TEXT_LENGTH:
            text_content = text_content[:MAX_TEXT_LENGTH]

        logger.info("Extracting key points")

        llm = ChatGroq(
            api_key=settings.groq_api_key,
            model_name=settings.groq_model,
            temperature=SUMMARY_TEMPERATURE,
            max_tokens=400
        )

        prompt = f"""Extract and organize the main topics and key points from this text.

Text:
{text_content}

Format your response as:

**Main Topics:**
1. [Topic 1]
2. [Topic 2]
3. [Topic 3]
[Continue if needed, max 5 topics]

**Key Points:**
• [Important point 1]
• [Important point 2]
• [Important point 3]
• [Important point 4]
• [Important point 5]
[Continue if needed, max 8 points]

Focus on the most important and actionable information."""

        response = llm.invoke(prompt)
        key_points = response.content if hasattr(response, 'content') else str(response)

        logger.info("Key points extracted successfully")

        return key_points.strip()

    except Exception as e:
        logger.error(f"Error extracting key points: {e}")
        return "Error extracting key points from the text."


# ============================================
# STUDY PARTNER - CONCEPT EXPLANATION TOOL
# ============================================

@tool
def explain_concept_tool(concept_query: str, context_text: Optional[str] = None) -> str:
    """
    Explain concepts in simple terms - your AI study partner.

    Use for:
    - Understanding difficult concepts
    - Breaking down complex topics
    - Getting examples and analogies
    - Study session Q&A

    Args:
        concept_query: The concept or question to explain (e.g., "What is photosynthesis?")
        context_text: Optional context from study materials

    Returns:
        str: Clear, friendly explanation with examples
    """
    try:
        logger.info(f"Explaining concept: {concept_query[:100]}")

        llm = ChatGroq(
            api_key=settings.groq_api_key,
            model_name=settings.groq_model,
            temperature=STUDY_TEMPERATURE,  # Slightly higher for better explanations
            max_tokens=600
        )

        # Build context-aware prompt
        context_section = ""
        if context_text:
            # Truncate context if too long
            if len(context_text) > 3000:
                context_text = context_text[:3000]
            context_section = f"\n\nContext from study materials:\n{context_text}\n"

        prompt = f"""You are a friendly and knowledgeable study partner. Explain the following concept in a clear, easy-to-understand way.
{context_section}
Concept to explain: {concept_query}

Provide your explanation in this format:

🎓 **Simple Explanation:**
[Explain in simple terms, like explaining to a friend]

📝 **Key Points to Remember:**
• [Important point 1]
• [Important point 2]
• [Important point 3]

💡 **Example:**
[Provide a practical example or analogy if helpful]

Keep it conversational, clear, and helpful for studying."""

        response = llm.invoke(prompt)
        explanation = response.content if hasattr(response, 'content') else str(response)

        logger.info("Concept explained successfully")

        return explanation.strip()

    except Exception as e:
        logger.error(f"Error explaining concept: {e}")
        return "I had trouble explaining that concept. Could you rephrase your question?"


# ============================================
# COMPARISON TOOL (for study materials)
# ============================================

@tool
def compare_concepts_tool(concept1: str, concept2: str, context_text: Optional[str] = None) -> str:
    """
    Compare two concepts or topics - great for understanding differences.

    Use for:
    - Understanding differences between similar concepts
    - Comparing theories or approaches
    - Distinguishing between related terms
    - Study review and exam prep

    Args:
        concept1: First concept to compare
        concept2: Second concept to compare
        context_text: Optional context from study materials

    Returns:
        str: Clear comparison showing similarities and differences
    """
    try:
        logger.info(f"Comparing: {concept1} vs {concept2}")

        llm = ChatGroq(
            api_key=settings.groq_api_key,
            model_name=settings.groq_model,
            temperature=SUMMARY_TEMPERATURE,
            max_tokens=500
        )

        context_section = ""
        if context_text:
            if len(context_text) > 2000:
                context_text = context_text[:2000]
            context_section = f"\n\nContext:\n{context_text}\n"

        prompt = f"""Compare and contrast these two concepts:{context_section}

Concept A: {concept1}
Concept B: {concept2}

Format:

🔹 **{concept1}:**
[Brief description]

🔹 **{concept2}:**
[Brief description]

**Key Differences:**
• [Difference 1]
• [Difference 2]
• [Difference 3]

**Similarities:**
• [Similarity 1]
• [Similarity 2]

**When to use each:**
• Use {concept1} when: [scenario]
• Use {concept2} when: [scenario]

Keep it clear and focused on helping understand the differences."""

        response = llm.invoke(prompt)
        comparison = response.content if hasattr(response, 'content') else str(response)

        logger.info("Comparison completed successfully")

        return comparison.strip()

    except Exception as e:
        logger.error(f"Error comparing concepts: {e}")
        return "I had trouble comparing those concepts. Please try again."


# ============================================
# PDF PROCESSING FUNCTIONS
# ============================================

def _extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text from PDF file.

    Args:
        pdf_path: Path to PDF file

    Returns:
        str: Extracted text
    """
    try:
        extracted_text = []

        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)

            # Get number of pages
            num_pages = len(pdf_reader.pages)
            logger.info(f"PDF has {num_pages} pages")

            # Extract text from each page (limit to first 20 pages for efficiency)
            max_pages = min(num_pages, 20)
            for page_num in range(max_pages):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()

                if text:
                    extracted_text.append(text)

        # Combine all text
        full_text = '\n'.join(extracted_text)

        logger.info(f"Extracted {len(full_text)} characters from {max_pages} pages")

        return full_text

    except FileNotFoundError:
        logger.error(f"PDF file not found: {pdf_path}")
        return ""
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        return ""


def _extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """
    Extract text from PDF bytes (for file uploads).

    Args:
        pdf_bytes: PDF file as bytes

    Returns:
        str: Extracted text
    """
    try:
        extracted_text = []

        pdf_file = io.BytesIO(pdf_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file)

        num_pages = len(pdf_reader.pages)
        max_pages = min(num_pages, 20)  # Limit for efficiency

        for page_num in range(max_pages):
            page = pdf_reader.pages[page_num]
            text = page.extract_text()

            if text:
                extracted_text.append(text)

        full_text = '\n'.join(extracted_text)

        logger.info(f"Extracted {len(full_text)} characters from PDF bytes")

        return full_text

    except Exception as e:
        logger.error(f"Error extracting text from PDF bytes: {e}")
        return ""
