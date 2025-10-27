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
from typing import Dict, List, Optional
from config.settings import get_settings
from sqlalchemy.orm import Session
import re
from datetime import datetime
import base64
import json
import os  # Always import os for path operations

# Gmail API imports
try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from google.auth.transport.requests import Request
    GMAIL_API_AVAILABLE = True
except ImportError:
    GMAIL_API_AVAILABLE = False
    logger.warning("Gmail API libraries not installed. Gmail draft sync will be disabled.")

settings = get_settings()

# Database session will be injected via factory function
# No more global in-memory storage


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
# DATABASE HELPERS FOR EMAIL DRAFTS
# ============================================

def _get_active_draft(db: Session, user_id: str) -> Optional[object]:
    """
    Get the active (non-expired) draft for a user

    Args:
        db: Database session
        user_id: WhatsApp user ID

    Returns:
        EmailDraft object or None
    """
    from models.email_draft import EmailDraft

    # Get the most recent active draft that hasn't expired
    draft = db.query(EmailDraft).filter(
        EmailDraft.user_id == user_id,
        EmailDraft.status == "draft",
        EmailDraft.expires_at > datetime.utcnow()
    ).order_by(EmailDraft.created_at.desc()).first()

    return draft


def _cleanup_expired_drafts(db: Session, user_id: str):
    """
    Clean up expired drafts for a user

    Args:
        db: Database session
        user_id: WhatsApp user ID
    """
    from models.email_draft import EmailDraft

    try:
        expired_count = db.query(EmailDraft).filter(
            EmailDraft.user_id == user_id,
            EmailDraft.expires_at <= datetime.utcnow()
        ).delete()

        if expired_count > 0:
            db.commit()
            logger.info(f"Cleaned up {expired_count} expired drafts for user {user_id}")
    except Exception as e:
        logger.error(f"Error cleaning up expired drafts: {e}")
        db.rollback()


# ============================================
# EMAIL DRAFTING (Stateful Workflow)
# ============================================

def draft_email_tool(email_request: str, user_id: str, db: Session) -> str:
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
        user_id: User identifier for stateful tracking (REQUIRED)
        db: Database session (REQUIRED)

    Returns:
        str: Draft email for review
    """
    from models.email_draft import EmailDraft

    try:
        logger.info(f"Creating email draft for user {user_id}")

        # Clean up any expired drafts first
        _cleanup_expired_drafts(db, user_id)

        # Check if user already has an active draft
        existing_draft = _get_active_draft(db, user_id)
        if existing_draft:
            logger.info(f"User {user_id} already has an active draft, marking it as cancelled")
            existing_draft.status = "cancelled"
            db.commit()

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

        # Create Gmail draft first (real-time sync)
        gmail_draft_id = _create_gmail_draft(
            to_email=email_data["to"],
            subject=email_data.get("subject", "Message from Personal Assistant"),
            body=email_data["body"]
        )

        # Create draft in database (with Gmail draft ID if available)
        draft = EmailDraft(
            user_id=user_id,
            to_email=email_data["to"],
            subject=email_data.get("subject", "Message from Personal Assistant"),
            body=email_data["body"],
            gmail_draft_id=gmail_draft_id,  # Store Gmail draft ID
            status="draft"
        )

        db.add(draft)
        db.commit()
        db.refresh(draft)

        logger.info(f"Draft created with ID: {draft.id}" +
                   (f" | Gmail: {gmail_draft_id}" if gmail_draft_id else ""))

        # Format response
        response = f"📧 Email Draft Created:\n\n"
        response += f"To: {draft.to_email}\n"
        response += f"Subject: {draft.subject}\n\n"
        response += f"Body:\n{draft.body}\n\n"

        # Add Gmail sync status
        if gmail_draft_id:
            response += "✉️ Also saved to your Gmail Drafts folder!\n\n"

        response += "---\n"
        response += "What would you like to do?\n"
        response += "• Say 'send it' to send this email\n"
        response += "• Say 'improve it' to make changes\n"
        response += "• Say 'keep it' to save and move to other topics\n"
        response += "• Say 'cancel' to discard\n"

        return response

    except Exception as e:
        logger.error(f"Error creating draft: {e}")
        db.rollback()
        return "I encountered an error creating the email draft. Please try again."


def send_draft_tool(user_id: str, db: Session) -> str:
    """
    Send the current email draft.

    Usage:
    - "Send it"
    - "Send the email"
    - "Approve and send"

    Args:
        user_id: User identifier (REQUIRED)
        db: Database session (REQUIRED)

    Returns:
        str: Confirmation message
    """
    try:
        # Get active draft from database
        draft = _get_active_draft(db, user_id)

        if not draft:
            return "No draft email found. Please create a draft first."

        # Try to send from Gmail draft first (preferred method)
        result = False
        sent_via = "SMTP"

        if draft.gmail_draft_id:
            result = _send_gmail_draft(draft.gmail_draft_id)
            if result:
                sent_via = "Gmail"

        # Fallback to SMTP if Gmail sending failed or not available
        if not result:
            result = _send_email(
                to_email=draft.to_email,
                subject=draft.subject,
                body=draft.body
            )

        if result:
            # Mark draft as sent
            draft.status = "sent"
            db.commit()

            logger.info(f"Email sent successfully to {draft.to_email} via {sent_via}")
            return f"✓ Email sent successfully to {draft.to_email}!"
        else:
            return "I encountered an error sending the email. Please check your email configuration."

    except Exception as e:
        logger.error(f"Error sending draft: {e}")
        db.rollback()
        return "I couldn't send the email due to an error. Please try again."


def improve_draft_tool(improvement_request: str, user_id: str, db: Session) -> str:
    """
    Improve the current email draft based on user feedback.

    Usage examples:
    - "Make it more formal"
    - "Add a closing paragraph"
    - "Change the tone to friendly"
    - "Make it shorter"

    Args:
        improvement_request: What to improve
        user_id: User identifier (REQUIRED)
        db: Database session (REQUIRED)

    Returns:
        str: Updated draft
    """
    try:
        # Get active draft from database
        draft = _get_active_draft(db, user_id)

        if not draft:
            return "No draft email found. Please create a draft first."

        # Use LLM to improve draft (may include subject change)
        improved_body, new_subject = _improve_email_body(
            current_body=draft.body,
            improvement_request=improvement_request,
            subject=draft.subject
        )

        # Update draft in database
        draft.body = improved_body
        if new_subject:  # Update subject if it was changed
            draft.subject = new_subject
            logger.info(f"Subject changed to: {new_subject}")

        draft.updated_at = datetime.utcnow()
        draft.extend_expiry(hours=1)  # Extend expiry since user is still working on it

        # Sync updates to Gmail draft (real-time)
        if draft.gmail_draft_id:
            _update_gmail_draft(
                draft_id=draft.gmail_draft_id,
                to_email=draft.to_email,
                subject=draft.subject,
                body=draft.body
            )

        db.commit()
        db.refresh(draft)

        logger.info(f"Draft {draft.id} improved for user {user_id}")

        # Format response
        response = f"📧 Updated Email Draft:\n\n"
        response += f"To: {draft.to_email}\n"
        response += f"Subject: {draft.subject}\n\n"
        response += f"Body:\n{draft.body}\n\n"
        response += "---\n"
        response += "What would you like to do?\n"
        response += "• Say 'send it' to send this email\n"
        response += "• Say 'improve it again' for more changes\n"
        response += "• Say 'keep it' to save and move to other topics\n"
        response += "• Say 'cancel' to discard\n"

        return response

    except Exception as e:
        logger.error(f"Error improving draft: {e}")
        db.rollback()
        return "I encountered an error improving the draft. Please try again."


def cancel_draft_tool(user_id: str, db: Session) -> str:
    """
    Cancel and discard the current email draft.

    Usage:
    - "Cancel"
    - "Discard the draft"
    - "Never mind"

    Args:
        user_id: User identifier (REQUIRED)
        db: Database session (REQUIRED)

    Returns:
        str: Confirmation message
    """
    try:
        # Get active draft from database
        draft = _get_active_draft(db, user_id)

        if not draft:
            return "No draft to cancel."

        # Delete Gmail draft if exists
        if draft.gmail_draft_id:
            _delete_gmail_draft(draft.gmail_draft_id)

        # Mark as cancelled
        draft.status = "cancelled"
        db.commit()

        logger.info(f"Draft {draft.id} cancelled for user {user_id}")
        return "Email draft discarded."

    except Exception as e:
        logger.error(f"Error cancelling draft: {e}")
        db.rollback()
        return "Error cancelling draft."


def keep_draft_tool(user_id: str, db: Session) -> str:
    """
    Keep the current draft in Gmail and allow user to move to other topics.

    Usage:
    - "Keep it"
    - "Save the draft"
    - "Keep it for later"

    This marks the draft as "kept" so the user can continue using the chatbot
    for other topics. The draft remains in Gmail Drafts folder for later editing/sending.

    Args:
        user_id: User identifier (REQUIRED)
        db: Database session (REQUIRED)

    Returns:
        str: Confirmation message
    """
    try:
        # Get active draft from database
        draft = _get_active_draft(db, user_id)

        if not draft:
            return "No draft to keep."

        # Mark as "kept" (not cancelled, just saved for later)
        draft.status = "kept"
        # Extend expiry to 24 hours instead of 1 hour
        draft.extend_expiry(hours=24)
        db.commit()

        logger.info(f"Draft {draft.id} kept for user {user_id}")

        response = "✓ Draft saved in your Gmail Drafts folder!\n\n"
        response += "You can continue editing or send it later from Gmail.\n"
        response += "What else can I help you with?"

        return response

    except Exception as e:
        logger.error(f"Error keeping draft: {e}")
        db.rollback()
        return "Error saving draft."


def list_drafts_tool(user_id: str, db: Session) -> str:
    """
    List all active drafts (draft and kept status) for the user.

    Usage:
    - "Show my drafts"
    - "List all drafts"
    - "What drafts do I have?"

    Returns a numbered list of drafts with:
    - Draft number (for selection)
    - Recipient email
    - Subject
    - Status (draft/kept)
    - Created date

    Args:
        user_id: User identifier (REQUIRED)
        db: Database session (REQUIRED)

    Returns:
        str: Formatted list of drafts or message if none exist
    """
    try:
        from models.email_draft import EmailDraft

        # Get all active drafts (both "draft" and "kept" status)
        drafts = db.query(EmailDraft).filter(
            EmailDraft.user_id == user_id,
            EmailDraft.status.in_(["draft", "kept"]),
            EmailDraft.expires_at > datetime.utcnow()
        ).order_by(EmailDraft.created_at.desc()).all()

        if not drafts:
            return "You have no active drafts."

        # Sync from Gmail: Update each draft with latest content from Gmail
        synced_count = 0
        for draft in drafts:
            if draft.gmail_draft_id:
                gmail_content = _fetch_gmail_draft(draft.gmail_draft_id)
                if gmail_content:
                    # Update database with Gmail content
                    draft.to_email = gmail_content['to_email'] or draft.to_email
                    draft.subject = gmail_content['subject'] or draft.subject
                    draft.body = gmail_content['body'] or draft.body
                    synced_count += 1

        if synced_count > 0:
            db.commit()
            logger.info(f"📥 Synced {synced_count} drafts from Gmail for user {user_id}")

        # Format response with numbered list
        response = f"📧 You have {len(drafts)} active draft(s):\n\n"

        for idx, draft in enumerate(drafts, 1):
            # Format created date
            created_str = draft.created_at.strftime("%b %d, %I:%M %p")

            # Status emoji
            status_emoji = "📝" if draft.status == "draft" else "💾"

            response += f"{idx}. {status_emoji} To: {draft.to_email}\n"
            response += f"   Subject: {draft.subject}\n"
            response += f"   Created: {created_str}\n"
            response += f"   Status: {draft.status}\n\n"

        response += "---\n"
        response += "What would you like to do?\n"
        response += "• Say 'select draft 1' to work with a specific draft\n"

        logger.info(f"Listed {len(drafts)} drafts for user {user_id}")
        return response

    except Exception as e:
        logger.error(f"Error listing drafts: {e}")
        return "Error retrieving drafts."


def select_draft_tool(draft_number: str, user_id: str, db: Session) -> str:
    """
    Select a specific draft by number to view, edit, send, or manage.

    Usage:
    - "Select draft 1"
    - "Open draft 1"

    This makes the selected draft the "active" draft, allowing you to:
    - View full content
    - Send it
    - Improve it
    - Keep it
    - Cancel it

    Args:
        draft_number: Draft number from the list (e.g., "1", "2", "3")
        user_id: User identifier (REQUIRED)
        db: Database session (REQUIRED)

    Returns:
        str: Full draft content with action options
    """
    try:
        from models.email_draft import EmailDraft

        # Parse draft number
        try:
            # Extract number from input like "draft 1", "select 1", "1"
            import re
            numbers = re.findall(r'\d+', draft_number)
            if not numbers:
                return "Please specify a draft number (e.g., 'select draft 1')"
            idx = int(numbers[0])
        except (ValueError, IndexError):
            return "Invalid draft number. Please use a number (e.g., 'select draft 1')"

        # Get all active drafts
        drafts = db.query(EmailDraft).filter(
            EmailDraft.user_id == user_id,
            EmailDraft.status.in_(["draft", "kept"]),
            EmailDraft.expires_at > datetime.utcnow()
        ).order_by(EmailDraft.created_at.desc()).all()

        if not drafts:
            return "You have no active drafts."

        if idx < 1 or idx > len(drafts):
            return f"Invalid draft number. You have {len(drafts)} draft(s). Please select 1-{len(drafts)}."

        # Get selected draft (idx is 1-based, list is 0-based)
        selected_draft = drafts[idx - 1]

        # Sync from Gmail: Fetch latest content from Gmail before showing
        if selected_draft.gmail_draft_id:
            gmail_content = _fetch_gmail_draft(selected_draft.gmail_draft_id)
            if gmail_content:
                # Update database with latest Gmail content
                selected_draft.to_email = gmail_content['to_email'] or selected_draft.to_email
                selected_draft.subject = gmail_content['subject'] or selected_draft.subject
                selected_draft.body = gmail_content['body'] or selected_draft.body
                logger.info(f"📥 Synced draft {selected_draft.id} from Gmail")

        # First, cancel any other "draft" status drafts to make this one active
        # This prevents conflicts when user tries to send/improve
        db.query(EmailDraft).filter(
            EmailDraft.user_id == user_id,
            EmailDraft.status == "draft",
            EmailDraft.id != selected_draft.id
        ).update({"status": "cancelled"})

        # Set selected draft to "draft" status (make it active)
        selected_draft.status = "draft"
        selected_draft.extend_expiry(hours=1)  # Reset expiry to 1 hour
        db.commit()

        # Format response
        response = f"📧 Selected Draft #{idx}:\n\n"
        response += f"To: {selected_draft.to_email}\n"
        response += f"Subject: {selected_draft.subject}\n\n"
        response += f"Body:\n{selected_draft.body}\n\n"

        if selected_draft.gmail_draft_id:
            response += "✉️ Synced with Gmail Drafts folder\n\n"

        response += "---\n"
        response += "What would you like to do?\n"
        response += "• Say 'send it' to send this email\n"
        response += "• Say 'improve it' to make changes\n"
        response += "• Say 'keep it' to save and move to other topics\n"
        response += "• Say 'cancel' to discard\n"

        logger.info(f"Selected draft {selected_draft.id} (#{idx}) for user {user_id}")
        return response

    except Exception as e:
        logger.error(f"Error selecting draft: {e}")
        db.rollback()
        return "Error selecting draft."


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


def _improve_email_body(current_body: str, improvement_request: str, subject: str) -> tuple:
    """
    Improve email body and/or subject using LLM

    Returns:
        tuple: (improved_body, new_subject_or_None)
    """
    try:
        llm = ChatGroq(
            api_key=settings.groq_api_key,
            model_name=settings.groq_model,
            temperature=0.7
        )

        # Check if user wants to change subject
        request_lower = improvement_request.lower()
        wants_subject_change = any(keyword in request_lower for keyword in [
            'subject', 'title', 'heading', 'change the subject', 'update subject', 'rename'
        ])

        if wants_subject_change:
            prompt = f"""
            You are helping improve an email draft. The user wants to make changes to the email.

            Current email:
            Subject: {subject}
            Body:
            {current_body}

            User's requested changes: {improvement_request}

            IMPORTANT INSTRUCTIONS:
            1. Apply ALL requested changes to the email body (time, location, name, etc.)
            2. If the user specifies a new subject, extract it and use it EXACTLY
            3. Keep the full email body - don't shorten it
            4. Format your response EXACTLY as shown below

            Return your response in this EXACT format:
            SUBJECT: [new subject line here]
            BODY:
            [Complete improved email body with all requested changes]

            Now write the improved email:
            """
        else:
            prompt = f"""
            You are helping improve an email draft body.

            Current email body:
            {current_body}

            Subject: {subject}

            User's requested changes: {improvement_request}

            IMPORTANT INSTRUCTIONS:
            1. Apply ALL requested changes to the email body (time, location, name, details, etc.)
            2. Keep the email professional and complete
            3. Include proper greeting, body, and closing
            4. Write ONLY the improved email body (no To:/From:/Subject: lines)

            Now write the improved email body:
            """

        response = llm.invoke(prompt)
        improved = response.content if hasattr(response, 'content') else str(response)
        improved = improved.strip()

        # Parse response if subject change was requested
        if wants_subject_change and 'SUBJECT:' in improved:
            lines = improved.split('\n')
            new_subject = None
            body_lines = []
            found_body = False

            for line in lines:
                if line.startswith('SUBJECT:'):
                    new_subject = line.replace('SUBJECT:', '').strip()
                elif line.startswith('BODY:'):
                    found_body = True
                    # Check if body content is on the same line
                    body_on_same_line = line.replace('BODY:', '').strip()
                    if body_on_same_line:
                        body_lines.append(body_on_same_line)
                elif found_body:
                    body_lines.append(line)

            if new_subject and body_lines:
                improved_body = '\n'.join(body_lines).strip()
                logger.info(f"Parsed improved body: {improved_body[:100]}...")  # Log first 100 chars
                return (improved_body, new_subject)

        return (improved, None)

    except Exception as e:
        logger.error(f"Error improving email: {e}")
        return (current_body, None)  # Return unchanged if error


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


# ============================================
# GMAIL API HELPER FUNCTIONS
# ============================================

def _get_gmail_service():
    """
    Get Gmail API service

    Returns Gmail API service object or None if not available
    """
    if not GMAIL_API_AVAILABLE:
        return None

    try:
        creds = None
        # Token file stores user's access and refresh tokens
        token_path = settings.get_absolute_path("backend/config/gmail_token.json")
        credentials_path = settings.google_calendar_credentials_file

        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(str(token_path), [
                'https://www.googleapis.com/auth/gmail.compose',
                'https://www.googleapis.com/auth/gmail.modify'
            ])

        # If no valid credentials, return None (user needs to authorize)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                # Save refreshed credentials
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
            else:
                logger.warning("Gmail API credentials not found or invalid")
                return None

        return build('gmail', 'v1', credentials=creds)

    except Exception as e:
        logger.error(f"Error initializing Gmail API: {e}")
        return None


def _create_gmail_draft(to_email: str, subject: str, body: str) -> Optional[str]:
    """
    Create a draft in Gmail

    Args:
        to_email: Recipient email
        subject: Email subject
        body: Email body

    Returns:
        str: Gmail draft ID or None if failed
    """
    try:
        service = _get_gmail_service()
        if not service:
            logger.warning("⚠️ Gmail API not available - draft will NOT sync to Gmail")
            logger.info("To enable Gmail sync: 1) Install libraries 2) Configure OAuth 3) See GMAIL_DRAFT_INTEGRATION.md")
            return None

        # Create message
        message = MIMEText(body)
        message['to'] = to_email
        message['subject'] = subject
        message['from'] = settings.email_user

        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

        # Create draft
        draft = service.users().drafts().create(
            userId='me',
            body={'message': {'raw': raw_message}}
        ).execute()

        draft_id = draft['id']
        logger.info(f"✉️ Created Gmail draft: {draft_id}")

        return draft_id

    except Exception as e:
        logger.error(f"Error creating Gmail draft: {e}")
        return None


def _update_gmail_draft(draft_id: str, to_email: str, subject: str, body: str) -> bool:
    """
    Update an existing Gmail draft

    Args:
        draft_id: Gmail draft ID
        to_email: Recipient email
        subject: Email subject
        body: Email body

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        service = _get_gmail_service()
        if not service:
            return False

        # Create updated message
        message = MIMEText(body)
        message['to'] = to_email
        message['subject'] = subject
        message['from'] = settings.email_user

        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

        # Update draft
        service.users().drafts().update(
            userId='me',
            id=draft_id,
            body={'message': {'raw': raw_message}}
        ).execute()

        logger.info(f"✉️ Updated Gmail draft: {draft_id}")
        return True

    except Exception as e:
        logger.error(f"Error updating Gmail draft: {e}")
        return False


def _send_gmail_draft(draft_id: str) -> bool:
    """
    Send a Gmail draft

    Args:
        draft_id: Gmail draft ID

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        service = _get_gmail_service()
        if not service:
            return False

        # Send the draft
        service.users().drafts().send(
            userId='me',
            body={'id': draft_id}
        ).execute()

        logger.info(f"✉️ Sent Gmail draft: {draft_id}")
        return True

    except Exception as e:
        logger.error(f"Error sending Gmail draft: {e}")
        return False


def _delete_gmail_draft(draft_id: str) -> bool:
    """
    Delete a Gmail draft

    Args:
        draft_id: Gmail draft ID

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        service = _get_gmail_service()
        if not service:
            return False

        service.users().drafts().delete(
            userId='me',
            id=draft_id
        ).execute()

        logger.info(f"✉️ Deleted Gmail draft: {draft_id}")
        return True

    except Exception as e:
        logger.error(f"Error deleting Gmail draft: {e}")
        return False


def _fetch_gmail_draft(draft_id: str) -> Optional[dict]:
    """
    Fetch a draft from Gmail to sync latest changes

    Args:
        draft_id: Gmail draft ID

    Returns:
        dict: {'to_email': str, 'subject': str, 'body': str} or None if failed
    """
    try:
        service = _get_gmail_service()
        if not service:
            return None

        # Get the draft
        draft = service.users().drafts().get(
            userId='me',
            id=draft_id,
            format='raw'
        ).execute()

        # Decode the message
        if 'message' not in draft:
            logger.warning(f"No message found in Gmail draft: {draft_id}")
            return None

        msg_str = base64.urlsafe_b64decode(
            draft['message']['raw'].encode('utf-8')
        ).decode('utf-8')

        # Parse the email
        import email
        msg = email.message_from_string(msg_str)

        # Extract fields
        to_email = msg.get('To', '')
        subject = msg.get('Subject', '')

        # Get body
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
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

        logger.info(f"📥 Fetched Gmail draft: {draft_id}")

        return {
            'to_email': to_email,
            'subject': subject,
            'body': body.strip()
        }

    except Exception as e:
        logger.error(f"Error fetching Gmail draft: {e}")
        return None


# ============================================
# USER-AWARE TOOL FACTORY FUNCTIONS
# ============================================

def create_user_email_tools(user_id: str, db: Session) -> tuple:
    """
    Create user-specific email tools with bound user_id and database session.

    This factory function solves the user isolation problem by creating
    tool instances that automatically inject the WhatsApp user_id and
    database session into all email operations, preventing cross-user
    draft conflicts and enabling persistent draft storage.

    Args:
        user_id: WhatsApp user identifier (e.g., "1234567890@c.us")
        db: Database session for persistent storage

    Returns:
        tuple: (draft_tool, send_tool, improve_tool, cancel_tool, keep_tool, list_tool, select_tool) all bound to user_id and db
    """

    # Create wrapper functions that bind user_id and db
    # We use wrapper functions instead of functools.partial because
    # LangChain's @tool decorator requires functions with __name__ attribute

    def user_draft_tool(email_request: str) -> str:
        """Create an email draft for user approval"""
        return draft_email_tool(email_request, user_id, db)

    def user_send_tool(input_text: str = "") -> str:
        """Send the current email draft"""
        # Agent may pass text like "Send the draft to X", but we ignore it
        # We get the draft from database instead
        return send_draft_tool(user_id, db)

    def user_improve_tool(improvement_request: str) -> str:
        """Improve the current email draft based on user feedback"""
        return improve_draft_tool(improvement_request, user_id, db)

    def user_cancel_tool(input_text: str = "") -> str:
        """Cancel and discard the current email draft"""
        # Agent may pass text, but we ignore it
        return cancel_draft_tool(user_id, db)

    def user_keep_tool(input_text: str = "") -> str:
        """Keep the draft in Gmail and move to other topics"""
        # Agent may pass text, but we ignore it
        return keep_draft_tool(user_id, db)

    def user_list_drafts_tool(input_text: str = "") -> str:
        """List all active drafts for the user"""
        # Agent may pass text, but we ignore it
        return list_drafts_tool(user_id, db)

    def user_select_draft_tool(draft_number: str) -> str:
        """Select a specific draft by number to work with"""
        return select_draft_tool(draft_number, user_id, db)

    # Wrap with @tool decorator
    draft_tool_instance = tool(user_draft_tool)
    send_tool_instance = tool(user_send_tool)
    improve_tool_instance = tool(user_improve_tool)
    cancel_tool_instance = tool(user_cancel_tool)
    keep_tool_instance = tool(user_keep_tool)
    list_drafts_instance = tool(user_list_drafts_tool)
    select_draft_instance = tool(user_select_draft_tool)

    # Set proper names and descriptions from original functions
    draft_tool_instance.name = "draft_email_tool"
    draft_tool_instance.description = draft_email_tool.__doc__

    send_tool_instance.name = "send_draft_tool"
    send_tool_instance.description = send_draft_tool.__doc__

    improve_tool_instance.name = "improve_draft_tool"
    improve_tool_instance.description = improve_draft_tool.__doc__

    cancel_tool_instance.name = "cancel_draft_tool"
    cancel_tool_instance.description = cancel_draft_tool.__doc__

    keep_tool_instance.name = "keep_draft_tool"
    keep_tool_instance.description = keep_draft_tool.__doc__

    list_drafts_instance.name = "list_drafts_tool"
    list_drafts_instance.description = list_drafts_tool.__doc__

    select_draft_instance.name = "select_draft_tool"
    select_draft_instance.description = select_draft_tool.__doc__

    logger.info(f"Created user-aware email tools with DB persistence for user: {user_id}")

    return (
        draft_tool_instance,
        send_tool_instance,
        improve_tool_instance,
        cancel_tool_instance,
        keep_tool_instance,
        list_drafts_instance,
        select_draft_instance
    )
