"""
Calendar Tool
Full Google Calendar integration with CRUD operations
"""

from langchain.tools import tool
from langchain_groq import ChatGroq
from loguru import logger
from config.settings import get_settings
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import re
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os.path
import pickle
import json

settings = get_settings()

# Google Calendar API scopes
SCOPES = ['https://www.googleapis.com/auth/calendar']


# ============================================
# GOOGLE CALENDAR AUTHENTICATION
# ============================================

def _get_calendar_service():
    """Get authenticated Google Calendar service"""
    creds = None

    # Token file stores the user's access and refresh tokens
    token_path = settings.get_absolute_path('backend/config/token.pickle')
    credentials_path = settings.get_absolute_path(settings.google_calendar_credentials_file)

    # Load existing credentials
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    # If no valid credentials, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.error(f"Error refreshing token: {e}")
                creds = None

        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save credentials for next run
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)
    return service


# ============================================
# CREATE EVENTS
# ============================================

@tool
def create_calendar_event_tool(event_description: str) -> str:
    """
    Create a calendar event in Google Calendar.

    Supports natural language input:
    - "Meeting with John tomorrow at 2 PM about project review"
    - "Dentist appointment on Friday at 9 AM"
    - "Team standup every Monday at 10 AM for 30 minutes"
    - "Lunch with Sarah on December 25 at 1 PM"

    Args:
        event_description: Natural language event description

    Returns:
        str: Confirmation with event details
    """
    try:
        logger.info(f"Creating calendar event: {event_description}")

        # Use LLM to parse event details
        event_data = _parse_event_with_llm(event_description)

        # Create event in Google Calendar
        service = _get_calendar_service()

        event = {
            'summary': event_data['summary'],
            'description': event_data.get('description', ''),
            'start': {
                'dateTime': event_data['start_time'],
                'timeZone': settings.default_timezone,
            },
            'end': {
                'dateTime': event_data['end_time'],
                'timeZone': settings.default_timezone,
            },
        }

        # Add location if provided
        if event_data.get('location'):
            event['location'] = event_data['location']

        # Create event
        created_event = service.events().insert(
            calendarId=settings.google_calendar_id,
            body=event
        ).execute()

        logger.info(f"Event created: {created_event.get('id')}")

        # Format response
        start = datetime.fromisoformat(event_data['start_time'].replace('Z', '+00:00'))
        response = f"✓ Calendar event created:\n"
        response += f"📅 {event_data['summary']}\n"
        response += f"🕐 {start.strftime('%A, %B %d at %I:%M %p')}\n"
        response += f"🔗 Event ID: {created_event.get('id')}"

        return response

    except HttpError as e:
        logger.error(f"Google Calendar API error: {e}")
        return "I encountered an error creating the calendar event. Please check your Google Calendar API configuration."
    except Exception as e:
        logger.error(f"Error in calendar tool: {e}")
        return "I couldn't create the calendar event. Please try again with a clearer description."


# ============================================
# LIST EVENTS
# ============================================

@tool
def list_calendar_events_tool(query: str = "upcoming events") -> str:
    """
    List calendar events.

    Usage examples:
    - "Show my upcoming events"
    - "What's on my calendar today?"
    - "List events for next week"
    - "Show me meetings tomorrow"

    Args:
        query: Natural language query

    Returns:
        str: Formatted list of events
    """
    try:
        logger.info(f"Listing calendar events: {query}")

        # Parse query to get time range
        time_params = _parse_time_query(query)

        # Get events from Google Calendar
        service = _get_calendar_service()

        events_result = service.events().list(
            calendarId=settings.google_calendar_id,
            timeMin=time_params['start'].isoformat() + 'Z',
            timeMax=time_params['end'].isoformat() + 'Z',
            maxResults=10,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])

        if not events:
            return f"No events found for {time_params['description']}."

        # Format response
        response = f"📅 Calendar events for {time_params['description']}:\n\n"

        for i, event in enumerate(events, 1):
            start = event['start'].get('dateTime', event['start'].get('date'))
            start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))

            response += f"{i}. {event.get('summary', 'No title')}\n"
            response += f"   🕐 {start_dt.strftime('%A, %B %d at %I:%M %p')}\n"

            if event.get('location'):
                response += f"   📍 {event['location']}\n"

            response += f"   🔗 ID: {event['id']}\n\n"

        return response

    except HttpError as e:
        logger.error(f"Google Calendar API error: {e}")
        return "I encountered an error retrieving calendar events."
    except Exception as e:
        logger.error(f"Error listing events: {e}")
        return "I couldn't retrieve your calendar events. Please try again."


# ============================================
# UPDATE EVENTS
# ============================================

@tool
def update_calendar_event_tool(update_request: str) -> str:
    """
    Update an existing calendar event.

    Usage examples:
    - "Reschedule my meeting with John to 3 PM"
    - "Change tomorrow's dentist appointment to 10 AM"
    - "Update the team meeting location to Conference Room B"

    Note: You'll need to identify the event first (by listing events)

    Args:
        update_request: Natural language update request

    Returns:
        str: Confirmation message
    """
    try:
        logger.info(f"Updating calendar event: {update_request}")

        # This is a simplified version - in production, you'd need to:
        # 1. Parse the request to identify which event
        # 2. Get the event ID
        # 3. Apply the updates

        return "Event update feature requires event ID. Please use list_calendar_events_tool first to get the event ID, then I can help you update it."

    except Exception as e:
        logger.error(f"Error updating event: {e}")
        return "I couldn't update the event. Please try again."


@tool
def update_event_by_id_tool(event_id: str, updates: str) -> str:
    """
    Update a specific calendar event by ID.

    Args:
        event_id: Google Calendar event ID
        updates: What to update (e.g., "change time to 3 PM", "add location: Office")

    Returns:
        str: Confirmation message
    """
    try:
        service = _get_calendar_service()

        # Get existing event
        event = service.events().get(
            calendarId=settings.google_calendar_id,
            eventId=event_id
        ).execute()

        # Parse updates
        update_data = _parse_updates_with_llm(updates, event)

        # Apply updates
        for key, value in update_data.items():
            if key in ['start', 'end']:
                event[key] = value
            else:
                event[key] = value

        # Update event
        updated_event = service.events().update(
            calendarId=settings.google_calendar_id,
            eventId=event_id,
            body=event
        ).execute()

        return f"✓ Event updated successfully: {updated_event.get('summary')}"

    except HttpError as e:
        logger.error(f"Error updating event: {e}")
        return f"Error updating event. Event ID might be invalid."
    except Exception as e:
        logger.error(f"Error: {e}")
        return "Couldn't update the event."


# ============================================
# DELETE EVENTS
# ============================================

@tool
def delete_calendar_event_tool(event_identifier: str) -> str:
    """
    Delete a calendar event.

    Args:
        event_identifier: Event ID or description to search for

    Returns:
        str: Confirmation message
    """
    try:
        service = _get_calendar_service()

        # If it looks like an event ID, delete directly
        if len(event_identifier) > 20 and '_' not in event_identifier:
            service.events().delete(
                calendarId=settings.google_calendar_id,
                eventId=event_identifier
            ).execute()

            return f"✓ Event deleted successfully."

        else:
            return "To delete an event, please provide the event ID. Use list_calendar_events_tool to find the event ID first."

    except HttpError as e:
        logger.error(f"Error deleting event: {e}")
        return "Error deleting event. The event might not exist or the ID is invalid."
    except Exception as e:
        logger.error(f"Error: {e}")
        return "Couldn't delete the event."


# ============================================
# HELPER FUNCTIONS
# ============================================

def _parse_event_with_llm(description: str) -> Dict:
    """Use LLM to parse event details from natural language"""
    try:
        llm = ChatGroq(
            api_key=settings.groq_api_key,
            model_name=settings.groq_model,
            temperature=0.1
        )

        prompt = f"""Extract calendar event information from this description: "{description}"

Today's date and time: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Current timezone: {settings.default_timezone}

Return ONLY a valid JSON object with these exact fields (no markdown, no explanations):
{{
  "summary": "event title",
  "start_time": "YYYY-MM-DDTHH:MM:SS",
  "end_time": "YYYY-MM-DDTHH:MM:SS",
  "description": "optional description",
  "location": "optional location"
}}

Rules:
- Use 24-hour time format
- Default duration: 1 hour
- If date is "tomorrow", use {(datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')}
- Return ONLY the JSON, nothing else

JSON:"""

        response = llm.invoke(prompt)
        json_text = response.content if hasattr(response, 'content') else str(response)

        # Clean the response - remove markdown code blocks if present
        json_text = re.sub(r'```json\s*', '', json_text)
        json_text = re.sub(r'```\s*', '', json_text)
        json_text = json_text.strip()

        # Extract JSON - use non-greedy match and ensure we get the first complete object
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', json_text)
        if json_match:
            json_str = json_match.group(0)
            event_data = json.loads(json_str)
            logger.info(f"Successfully parsed event: {event_data.get('summary')}")
            return event_data
        else:
            logger.warning(f"No JSON found in response: {json_text[:200]}")
            raise ValueError("Couldn't parse event data")

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        logger.error(f"Response was: {json_text[:300]}")
        # Fallback to basic parsing
        return _parse_event_basic(description)
    except Exception as e:
        logger.error(f"Error parsing event with LLM: {e}")
        # Fallback to basic parsing
        return _parse_event_basic(description)


def _parse_event_basic(description: str) -> Dict:
    """Basic event parsing without LLM"""
    now = datetime.now()

    # Default event
    event = {
        'summary': description[:50],
        'start_time': (now + timedelta(hours=1)).isoformat(),
        'end_time': (now + timedelta(hours=2)).isoformat(),
        'description': description
    }

    return event


def _parse_time_query(query: str) -> Dict:
    """Parse time range from query"""
    now = datetime.now()
    query_lower = query.lower()

    if 'today' in query_lower:
        start = now.replace(hour=0, minute=0, second=0)
        end = now.replace(hour=23, minute=59, second=59)
        description = "today"

    elif 'tomorrow' in query_lower:
        tomorrow = now + timedelta(days=1)
        start = tomorrow.replace(hour=0, minute=0, second=0)
        end = tomorrow.replace(hour=23, minute=59, second=59)
        description = "tomorrow"

    elif 'week' in query_lower:
        start = now
        end = now + timedelta(days=7)
        description = "the next week"

    elif 'month' in query_lower:
        start = now
        end = now + timedelta(days=30)
        description = "the next month"

    else:
        # Default: next 7 days
        start = now
        end = now + timedelta(days=7)
        description = "the next 7 days"

    return {
        'start': start,
        'end': end,
        'description': description
    }


def _parse_updates_with_llm(updates: str, current_event: Dict) -> Dict:
    """Parse update request using LLM"""
    try:
        llm = ChatGroq(
            api_key=settings.groq_api_key,
            model_name=settings.groq_model,
            temperature=0.1
        )

        prompt = f"""
        Parse this update request for a calendar event: "{updates}"

        Current event:
        {json.dumps(current_event, indent=2)}

        Return a JSON object with ONLY the fields that need to be updated:
        - summary: new title (if changed)
        - start: new start time in ISO format (if changed)
        - end: new end time in ISO format (if changed)
        - location: new location (if changed)
        - description: new description (if changed)

        Return ONLY valid JSON:
        """

        response = llm.invoke(prompt)
        json_text = response.content if hasattr(response, 'content') else str(response)

        json_match = re.search(r'\{.*\}', json_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))

        return {}

    except Exception as e:
        logger.error(f"Error parsing updates: {e}")
        return {}
