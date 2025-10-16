"""
Resume Tool
Summarizes professional experience with PDF support
"""

from langchain.tools import tool
from langchain_groq import ChatGroq
from loguru import logger
from config.settings import get_settings
import PyPDF2
import io
from typing import Optional

settings = get_settings()


@tool
def resume_tool(experience_input: str, is_pdf_path: bool = False) -> str:
    """
    Summarizes professional experience into concise resume format.

    Supports both plain text and PDF files.

    Input can be:
    - Plain text: "I worked as a software engineer at XYZ Corp for 3 years..."
    - PDF file path: "/path/to/resume.pdf" (set is_pdf_path=True)

    Args:
        experience_input: Raw text or PDF file path
        is_pdf_path: Set to True if input is a PDF file path

    Returns:
        str: Formatted resume summary with bullet points
    """
    try:
        # Extract text from PDF if needed
        if is_pdf_path:
            logger.info(f"Extracting text from PDF: {experience_input}")
            experience_text = _extract_text_from_pdf(experience_input)

            if not experience_text:
                return "I couldn't extract text from the PDF file. Please ensure it's a valid text-based PDF."
        else:
            experience_text = experience_input

        logger.info("Summarizing experience into resume format")

        # Initialize LLM for summarization
        llm = ChatGroq(
            api_key=settings.groq_api_key,
            model_name=settings.groq_model,
            temperature=0.3  # Low temperature for consistent formatting
        )

        # Create summarization prompt
        prompt = f"""
        You are a professional resume writer. Convert the following experience into concise,
        impactful resume bullet points.

        Guidelines:
        - Start each bullet with a strong action verb (Led, Developed, Managed, Architected, etc.)
        - Quantify achievements where possible (numbers, percentages, scale)
        - Keep bullets concise (1-2 lines each)
        - Focus on accomplishments and impact, not just responsibilities
        - Use professional language
        - Format as bullet points using "•"
        - Provide 3-7 bullet points depending on content

        Experience to summarize:
        {experience_text}

        Provide ONLY the formatted bullet points, no additional commentary:
        """

        # Get summarization from LLM
        response = llm.invoke(prompt)

        # Extract content
        if hasattr(response, 'content'):
            summary = response.content
        else:
            summary = str(response)

        logger.info("Resume summary generated successfully")

        return summary.strip()

    except Exception as e:
        logger.error(f"Error in resume tool: {e}")
        return "I encountered an error while processing the resume. Please ensure the file is valid or try with plain text."


@tool
def resume_tool_advanced(experience_input: str, job_title: Optional[str] = None,
                        is_pdf_path: bool = False) -> str:
    """
    Advanced resume tool with job title targeting.

    Optimizes bullet points for specific target roles.

    Args:
        experience_input: Raw text or PDF file path
        job_title: Target job title for tailored resume (optional)
        is_pdf_path: Set to True if input is a PDF file path

    Returns:
        str: Formatted resume summary optimized for target role
    """
    try:
        # Extract text from PDF if needed
        if is_pdf_path:
            logger.info(f"Extracting text from PDF: {experience_input}")
            experience_text = _extract_text_from_pdf(experience_input)

            if not experience_text:
                return "I couldn't extract text from the PDF file. Please ensure it's a valid text-based PDF."
        else:
            experience_text = experience_input

        llm = ChatGroq(
            api_key=settings.groq_api_key,
            model_name=settings.groq_model,
            temperature=0.3
        )

        job_context = f" for a {job_title} position" if job_title else ""

        prompt = f"""
        You are an expert resume writer. Create impactful resume bullet points{job_context}.

        Guidelines:
        - Use strong action verbs (Led, Architected, Delivered, Optimized, Spearheaded, etc.)
        - Quantify results with specific metrics (percentages, numbers, scale, ROI)
        - Highlight relevant technical skills, tools, and technologies
        - Show business impact and value delivered
        - Use STAR method when applicable (Situation, Task, Action, Result)
        - Keep each bullet point to 1-2 lines
        - Format with "•" bullets
        - Provide 4-8 bullet points

        {f"Target Role: {job_title}" if job_title else ""}

        Experience:
        {experience_text}

        Return ONLY the formatted bullet points:
        """

        response = llm.invoke(prompt)

        if hasattr(response, 'content'):
            summary = response.content
        else:
            summary = str(response)

        return summary.strip()

    except Exception as e:
        logger.error(f"Error in advanced resume tool: {e}")
        # Fallback to basic version
        return resume_tool(experience_input, is_pdf_path)


@tool
def extract_skills_tool(experience_input: str, is_pdf_path: bool = False) -> str:
    """
    Extract technical skills and competencies from resume/experience.

    Args:
        experience_input: Raw text or PDF file path
        is_pdf_path: Set to True if input is a PDF file path

    Returns:
        str: Categorized list of skills
    """
    try:
        # Extract text from PDF if needed
        if is_pdf_path:
            experience_text = _extract_text_from_pdf(experience_input)
            if not experience_text:
                return "Couldn't extract text from PDF."
        else:
            experience_text = experience_input

        llm = ChatGroq(
            api_key=settings.groq_api_key,
            model_name=settings.groq_model,
            temperature=0.2
        )

        prompt = f"""
        Extract and categorize all technical skills, tools, and competencies from this text.

        Text:
        {experience_text}

        Format the output as:
        **Technical Skills:**
        - Programming Languages: [list]
        - Frameworks & Libraries: [list]
        - Tools & Platforms: [list]
        - Databases: [list]

        **Soft Skills:**
        - [list]

        Only include skills that are explicitly mentioned or clearly implied. Be comprehensive.
        """

        response = llm.invoke(prompt)
        skills = response.content if hasattr(response, 'content') else str(response)

        return skills.strip()

    except Exception as e:
        logger.error(f"Error extracting skills: {e}")
        return "Error extracting skills from the provided text."


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

            # Extract text from each page
            for page_num in range(num_pages):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()

                if text:
                    extracted_text.append(text)

        # Combine all text
        full_text = '\n'.join(extracted_text)

        logger.info(f"Extracted {len(full_text)} characters from PDF")

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

        for page_num in range(num_pages):
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


# ============================================
# ADDITIONAL HELPER FUNCTIONS
# ============================================

def _extract_key_achievements(text: str) -> list:
    """
    Helper function to extract key achievements from text

    Args:
        text: Experience text

    Returns:
        list: Extracted achievements
    """
    achievements = []

    # Achievement indicators
    indicators = [
        "achieved", "improved", "increased", "reduced", "led",
        "managed", "delivered", "developed", "created", "implemented",
        "designed", "built", "launched", "optimized", "scaled"
    ]

    sentences = text.split(".")
    for sentence in sentences:
        sentence_lower = sentence.lower()
        for indicator in indicators:
            if indicator in sentence_lower:
                achievements.append(sentence.strip())
                break

    return achievements[:7]  # Top 7 achievements


def _calculate_experience_years(text: str) -> Optional[int]:
    """
    Try to extract years of experience from text

    Args:
        text: Experience text

    Returns:
        Optional[int]: Years of experience if found
    """
    import re

    # Patterns like "5 years", "3+ years", "2-4 years"
    year_patterns = [
        r'(\d+)\+?\s+years?',
        r'(\d+)-\d+\s+years?'
    ]

    for pattern in year_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))

    return None
