"""
Email Tool
Complete email management: read, draft, send, and approve workflow
"""

from langchain.tools import tool
from langchain_groq import ChatGroq
from loguru import logger
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr, parseaddr
from email.header import decode_header
from typing import Dict, List
from config.settings import get_settings
import re
from datetime import datetime

settings = get_settings()

# Global draft storage (user_id -> draft)
_email_drafts: Dict[str, Dict] = {}


# ============================================
# EMAIL READING (IMAP)
# ============================================

@tool
def read_emails_tool(request: str) -> str:
    """
    Read and retrieve emails from inbox.

    Usage examples:
    - "Show me my latest 5 emails"
    - "Check my unread emails"
    - "Get emails from john@example.com"
    - "Show emails with subject meeting"

    Args:
        request: Natural language request for email retrieval

    Returns:
        str: Formatted list of emails
    """
    try:
        logger.info(f"Reading emails: {request}")

        # Parse request
        params = _parse_read_request(request)

        # Connect to IMAP server
        emails = _fetch_emails(
            limit=params.get("limit", 5),
            unread_only=params.get("unread_only", False),
            sender_filter=params.get("sender"),
            subject_filter=params.get("subject")
        )

        if not emails:
            return "No emails found matching your criteria."

        # Format response
        response = f"Found {len(emails)} email(s):\n\n"
        for i, email_data in enumerate(emails, 1):
            response += f"{i}. From: {email_data['from']}\n"
            response += f"   Subject: {email_data['subject']}\n"
            response += f"   Date: {email_data['date']}\n"
            if email_data.get('unread'):
                response += "   Status: UNREAD\n"
            response += f"   Preview: {email_data['preview']}\n\n"

        return response

    except Exception as e:
        logger.error(f"Error reading emails: {e}")
        return "I encountered an error reading your emails. Please check your email configuration."


def _parse_read_request(request: str) -> dict:
    """Parse email read request"""
    params = {
        "limit": 5,
        "unread_only": False,
        "sender": None,
        "subject": None
    }

    request_lower = request.lower()

    # Extract number of emails
    num_match = re.search(r'(\d+)\s+(?:emails?|messages?)', request_lower)
    if num_match:
        params["limit"] = int(num_match.group(1))

    # Check for unread filter
    if any(word in request_lower for word in ['unread', 'new']):
        params["unread_only"] = True

    # Extract sender filter
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    sender_match = re.search(r'from\s+(' + email_pattern + ')', request, re.IGNORECASE)
    if sender_match:
        params["sender"] = sender_match.group(1)

    # Extract subject filter
    subject_match = re.search(r'(?:subject|about)\s+[\'"]?([^\'"]+)[\'"]?', request, re.IGNORECASE)
    if subject_match:
        params["subject"] = subject_match.group(1).strip()

    return params


def _fetch_emails(limit: int = 5, unread_only: bool = False,
                  sender_filter: str = None, subject_filter: str = None) -> List[Dict]:
    """Fetch emails from IMAP server"""
    try:
        # Connect to IMAP server
        mail = imaplib.IMAP4_SSL(settings.imap_host, settings.imap_port)
        mail.login(settings.email_user, settings.email_password)
        mail.select('inbox')

        # Build search criteria
        search_criteria = []
        if unread_only:
            search_criteria.append('UNSEEN')
        if sender_filter:
            search_criteria.append(f'FROM "{sender_filter}"')
        if subject_filter:
            search_criteria.append(f'SUBJECT "{subject_filter}"')

        # Search emails
        if search_criteria:
            search_str = ' '.join(search_criteria)
            status, messages = mail.search(None, search_str)
        else:
            status, messages = mail.search(None, 'ALL')

        email_ids = messages[0].split()
        email_ids = email_ids[-limit:]  # Get latest N emails
        email_ids.reverse()  # Newest first

        emails = []
        for email_id in email_ids:
            status, msg_data = mail.fetch(email_id, '(RFC822)')
            msg = email.message_from_bytes(msg_data[0][1])

            # Extract email data
            from_header = msg.get('From', '')
            from_name, from_email = parseaddr(from_header)

            subject = _decode_header(msg.get('Subject', 'No Subject'))
            date = msg.get('Date', '')

            # Get email body
            body = _get_email_body(msg)
            preview = body[:200] + '...' if len(body) > 200 else body

            emails.append({
                'from': f"{from_name} <{from_email}>" if from_name else from_email,
                'subject': subject,
                'date': date,
                'preview': preview,
                'body': body,
                'unread': unread_only
            })

        mail.close()
        mail.logout()

        return emails

    except Exception as e:
        logger.error(f"Error fetching emails: {e}")
        return []


def _decode_header(header: str) -> str:
    """Decode email header"""
    if not header:
        return ""

    decoded_parts = []
    for part, encoding in decode_header(header):
        if isinstance(part, bytes):
            decoded_parts.append(part.decode(encoding or 'utf-8', errors='ignore'))
        else:
            decoded_parts.append(part)

    return ''.join(decoded_parts)


def _get_email_body(msg) -> str:
    """Extract email body"""
    body = ""

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                try:
                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    break
                except:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        except:
            body = str(msg.get_payload())

    return body.strip()


# ============================================
# EMAIL DRAFTING (Stateful Workflow)
# ============================================

@tool
def draft_email_tool(email_request: str, user_id: str = "default") -> str:
    """
    Create an email draft for user approval.

    Usage examples:
    - "Draft an email to john@example.com about the meeting"
    - "Create email draft to jane@company.com with subject Project Update"

    After drafting, user can:
    - Approve and send with send_draft_tool
    - Request improvements with improve_draft_tool
    - Cancel with cancel_draft_tool

    Args:
        email_request: Natural language email request
        user_id: User identifier for stateful tracking

    Returns:
        str: Draft email for review
    """
    try:
        logger.info(f"Creating email draft for user {user_id}")

        # Parse email components
        email_data = _parse_email_request(email_request)

        if not email_data.get("to"):
            return "I need a recipient email address. Please provide an email address."

        # Use LLM to generate professional email body if needed
        if not email_data.get("body") or len(email_data["body"]) < 20:
            email_data["body"] = _generate_email_body(
                email_request,
                email_data.get("subject", "")
            )

        # Store draft
        draft_id = f"draft_{user_id}_{datetime.now().timestamp()}"
        _email_drafts[user_id] = {
            "id": draft_id,
            "to": email_data["to"],
            "subject": email_data.get("subject", "Message from Personal Assistant"),
            "body": email_data["body"],
            "created_at": datetime.now().isoformat()
        }

        # Format response
        draft = _email_drafts[user_id]
        response = f"📧 Email Draft Created:\n\n"
        response += f"To: {draft['to']}\n"
        response += f"Subject: {draft['subject']}\n\n"
        response += f"Body:\n{draft['body']}\n\n"
        response += "---\n"
        response += "What would you like to do?\n"
        response += "• Say 'send it' to send this email\n"
        response += "• Say 'improve it' to make changes\n"
        response += "• Say 'cancel' to discard\n"

        return response

    except Exception as e:
        logger.error(f"Error creating draft: {e}")
        return "I encountered an error creating the email draft. Please try again."


@tool
def send_draft_tool(user_id: str = "default") -> str:
    """
    Send the current email draft.

    Usage:
    - "Send it"
    - "Send the email"
    - "Approve and send"

    Args:
        user_id: User identifier

    Returns:
        str: Confirmation message
    """
    try:
        if user_id not in _email_drafts:
            return "No draft email found. Please create a draft first."

        draft = _email_drafts[user_id]

        # Send email
        result = _send_email(
            to_email=draft["to"],
            subject=draft["subject"],
            body=draft["body"]
        )

        if result:
            # Clear draft
            del _email_drafts[user_id]
            logger.info(f"Email sent successfully to {draft['to']}")
            return f"✓ Email sent successfully to {draft['to']}!"
        else:
            return "I encountered an error sending the email. Please check your email configuration."

    except Exception as e:
        logger.error(f"Error sending draft: {e}")
        return "I couldn't send the email due to an error. Please try again."


@tool
def improve_draft_tool(improvement_request: str, user_id: str = "default") -> str:
    """
    Improve the current email draft based on user feedback.

    Usage examples:
    - "Make it more formal"
    - "Add a closing paragraph"
    - "Change the tone to friendly"
    - "Make it shorter"

    Args:
        improvement_request: What to improve
        user_id: User identifier

    Returns:
        str: Updated draft
    """
    try:
        if user_id not in _email_drafts:
            return "No draft email found. Please create a draft first."

        draft = _email_drafts[user_id]

        # Use LLM to improve draft
        improved_body = _improve_email_body(
            current_body=draft["body"],
            improvement_request=improvement_request,
            subject=draft["subject"]
        )

        # Update draft
        draft["body"] = improved_body
        draft["updated_at"] = datetime.now().isoformat()

        # Format response
        response = f"📧 Updated Email Draft:\n\n"
        response += f"To: {draft['to']}\n"
        response += f"Subject: {draft['subject']}\n\n"
        response += f"Body:\n{draft['body']}\n\n"
        response += "---\n"
        response += "What would you like to do?\n"
        response += "• Say 'send it' to send this email\n"
        response += "• Say 'improve it again' for more changes\n"
        response += "• Say 'cancel' to discard\n"

        return response

    except Exception as e:
        logger.error(f"Error improving draft: {e}")
        return "I encountered an error improving the draft. Please try again."


@tool
def cancel_draft_tool(user_id: str = "default") -> str:
    """
    Cancel and discard the current email draft.

    Usage:
    - "Cancel"
    - "Discard the draft"
    - "Never mind"

    Args:
        user_id: User identifier

    Returns:
        str: Confirmation message
    """
    if user_id in _email_drafts:
        del _email_drafts[user_id]
        return "Email draft discarded."
    return "No draft to cancel."


# ============================================
# HELPER FUNCTIONS
# ============================================

def _parse_email_request(request: str) -> dict:
    """Parse email request into components"""
    email_data = {
        "to": None,
        "subject": None,
        "body": None
    }

    # Extract recipient
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    to_match = re.search(r'to:\s*(' + email_pattern + ')', request, re.IGNORECASE)
    if not to_match:
        emails = re.findall(email_pattern, request)
        if emails:
            email_data["to"] = emails[0]
    else:
        email_data["to"] = to_match.group(1)

    # Extract subject
    subject_match = re.search(r'subject:\s*([^,\n]+)', request, re.IGNORECASE)
    if subject_match:
        email_data["subject"] = subject_match.group(1).strip()
    else:
        about_match = re.search(r'(?:about|regarding)\s+[\'"]?([^\'"]+)[\'"]?', request, re.IGNORECASE)
        if about_match:
            email_data["subject"] = about_match.group(1).strip()

    # Extract body
    body_match = re.search(r'body:\s*(.+)', request, re.IGNORECASE | re.DOTALL)
    if body_match:
        email_data["body"] = body_match.group(1).strip()

    return email_data


def _generate_email_body(request: str, subject: str) -> str:
    """Generate professional email body using LLM"""
    try:
        llm = ChatGroq(
            api_key=settings.groq_api_key,
            model_name=settings.groq_model,
            temperature=0.7
        )

        prompt = f"""
        Write a professional email body based on this request: "{request}"

        Subject: {subject if subject else "General inquiry"}

        Guidelines:
        - Professional and polite tone
        - Clear and concise
        - Proper greeting and closing
        - 3-5 sentences
        - Do NOT include To:, From:, or Subject: lines

        Write only the email body:
        """

        response = llm.invoke(prompt)
        body = response.content if hasattr(response, 'content') else str(response)

        return body.strip()

    except Exception as e:
        logger.error(f"Error generating email body: {e}")
        return f"Regarding: {subject}\n\n{request}"


def _improve_email_body(current_body: str, improvement_request: str, subject: str) -> str:
    """Improve email body using LLM"""
    try:
        llm = ChatGroq(
            api_key=settings.groq_api_key,
            model_name=settings.groq_model,
            temperature=0.7
        )

        prompt = f"""
        Improve this email based on the feedback.

        Current email body:
        {current_body}

        Subject: {subject}

        User feedback: {improvement_request}

        Write the improved email body (only the body, no To:/From:/Subject: lines):
        """

        response = llm.invoke(prompt)
        improved = response.content if hasattr(response, 'content') else str(response)

        return improved.strip()

    except Exception as e:
        logger.error(f"Error improving email: {e}")
        return current_body  # Return unchanged if error


def _send_email(to_email: str, subject: str, body: str) -> bool:
    """Send email using SMTP"""
    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = formataddr(("Personal Assistant", settings.email_user))
        message["To"] = to_email

        # Plain text
        text_part = MIMEText(body, "plain")
        message.attach(text_part)

        # HTML version
        html_body = f"""
        <html>
            <body>
                <p>{body.replace(chr(10), '<br>')}</p>
                <br><hr>
                <p style="color: #666; font-size: 12px;">
                    Sent by Personal Assistant Bot
                </p>
            </body>
        </html>
        """
        html_part = MIMEText(html_body, "html")
        message.attach(html_part)

        # Connect and send
        server = smtplib.SMTP(settings.smtp_host, settings.smtp_port)
        if settings.smtp_tls:
            server.starttls()

        server.login(settings.email_user, settings.email_password)
        server.sendmail(settings.email_user, to_email, message.as_string())
        server.quit()

        return True

    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return False
