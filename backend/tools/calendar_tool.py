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
import pytz

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

        # Convert to RFC3339 format WITH timezone offset (Google Calendar API requirement)
        # The datetime objects from _parse_time_query already have timezone info
        start_time = time_params['start'].isoformat()
        end_time = time_params['end'].isoformat()

        events_result = service.events().list(
            calendarId=settings.google_calendar_id,
            timeMin=start_time,
            timeMax=end_time,
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

            response += f"\n"

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

        # Get current time in user's timezone
        user_tz = pytz.timezone(settings.default_timezone)
        now_in_user_tz = datetime.now(user_tz)
        tomorrow_in_user_tz = now_in_user_tz + timedelta(days=1)

        prompt = f"""Extract calendar event information from this description: "{description}"

IMPORTANT TIMEZONE INFORMATION:
- User's timezone: {settings.default_timezone} (GMT+7 / WIB - Western Indonesian Time)
- Current date and time in user's timezone: {now_in_user_tz.strftime('%Y-%m-%d %H:%M %Z')}
- All times mentioned by user are in {settings.default_timezone} timezone
- When user says "23:59" they mean 23:59 in {settings.default_timezone}, NOT UTC

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
- Interpret ALL times as {settings.default_timezone} (GMT+7)
- If date is "tomorrow", use {tomorrow_in_user_tz.strftime('%Y-%m-%d')}
- If user says "19 october at 23:59", that means 2025-10-19T23:59:00 in their timezone
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
    # Get current time in user's timezone
    user_tz = pytz.timezone(settings.default_timezone)
    now = datetime.now(user_tz)

    # Default event (1 hour from now, in user's timezone)
    # Keep timezone info for consistency
    event = {
        'summary': description[:50],
        'start_time': (now + timedelta(hours=1)).isoformat(),
        'end_time': (now + timedelta(hours=2)).isoformat(),
        'description': description
    }

    return event


def _parse_time_query(query: str) -> Dict:
    """Parse time range from query"""
    # Get current time in user's timezone
    user_tz = pytz.timezone(settings.default_timezone)
    now = datetime.now(user_tz)
    query_lower = query.lower()

    if 'today' in query_lower:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(hour=23, minute=59, second=59, microsecond=0)
        description = "today"

    elif 'tomorrow' in query_lower:
        tomorrow = now + timedelta(days=1)
        start = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
        end = tomorrow.replace(hour=23, minute=59, second=59, microsecond=0)
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


# ============================================
# SMART SCHEDULE MANAGEMENT (ALL-IN-ONE)
# ============================================

@tool
def smart_schedule_tool(request: str) -> str:
    """
    COMPLETE calendar management tool - does EVERYTHING in ONE call using live Google Calendar API.

    This tool handles the ENTIRE flow internally:
    - CREATE: Reads calendar → Checks for overlaps → Creates OR warns about conflict → Returns result
    - READ/LIST: Reads calendar → Returns formatted list of events
    - DELETE: Reads calendar → Deletes OR says nothing to delete → Returns result
    - UPDATE: Reads calendar → Updates OR says event not found → Returns result

    IMPORTANT: This tool ALWAYS uses live Google Calendar API data (NOT memory).
    You only need to call this tool ONCE - it returns the complete result.

    Examples:
    - "Schedule NLP homework tonight 6-9 PM"
    - "Show my schedule for today"
    - "Delete all events today"
    - "Update my NLP homework to 8 PM"

    Args:
        request: User's natural language request about their schedule

    Returns:
        str: Complete result - ready to send to user (no further tool calls needed)
    """
    try:
        logger.info(f"Smart schedule request: {request}")
        request_lower = request.lower()

        # Detect intent
        if any(word in request_lower for word in ['delete', 'remove', 'cancel', 'apus', 'hapus']):
            return _smart_delete(request)
        elif any(word in request_lower for word in ['show', 'list', 'what', 'check', 'lihat', 'cek', 'tampil']):
            return _smart_list(request)
        elif any(word in request_lower for word in ['update', 'change', 'reschedule', 'ubah', 'ganti', 'rubah']):
            return _smart_update(request)
        else:
            # Default to smart create
            return _smart_create(request)

    except Exception as e:
        logger.error(f"Error in smart_schedule_tool: {e}")
        return f"I encountered an error processing your schedule request. Please try again."


def _smart_create(request: str) -> str:
    """
    Smart event creation following CoT:
    1. Parse the request
    2. Read all user's schedule in the target timeframe
    3. Check for overlap
    4. If overlap: Ask user to update conflicting event (don't create)
    5. If no overlap: Create event
    6. Give response (no duplicate calls)
    """
    try:
        # Step 1: Parse the event request
        event_data = _parse_event_with_llm(request)
        logger.info(f"Parsed event: {event_data['summary']} at {event_data['start_time']}")

        # Step 1.5: Check if the event is in the past (based on user's timezone)
        user_tz = pytz.timezone(settings.default_timezone)
        now = datetime.now(user_tz)

        start_dt = datetime.fromisoformat(event_data['start_time'])
        if start_dt.tzinfo is None:
            start_dt = user_tz.localize(start_dt)

        # Refuse to create events in the past
        if start_dt < now:
            response = f"❌ **Cannot Create Event in the Past**\n\n"
            response += f"You're trying to schedule:\n"
            response += f"📅 {event_data['summary']}\n"
            response += f"🕐 {start_dt.strftime('%A, %B %d at %I:%M %p')}\n\n"
            response += f"Current time: {now.strftime('%A, %B %d at %I:%M %p')} ({settings.default_timezone})\n\n"
            response += f"⏰ This time has already passed. Please specify a future time."
            logger.info(f"Refused to create event in the past: {start_dt} < {now}")
            return response

        # Step 2: Read all schedule in the target timeframe (entire day)
        service = _get_calendar_service()

        # Read the whole day to check for overlaps
        day_start = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = start_dt.replace(hour=23, minute=59, second=59, microsecond=0)

        existing_events = service.events().list(
            calendarId=settings.google_calendar_id,
            timeMin=day_start.isoformat(),
            timeMax=day_end.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute().get('items', [])

        logger.info(f"Found {len(existing_events)} existing events on {start_dt.strftime('%Y-%m-%d')}")

        # Step 3: Check for time overlap
        end_dt = datetime.fromisoformat(event_data['end_time'])
        if end_dt.tzinfo is None:
            end_dt = user_tz.localize(end_dt)

        overlap_found = False
        overlap_details = []

        for event in existing_events:
            existing_start = event['start'].get('dateTime', event['start'].get('date'))
            existing_end = event['end'].get('dateTime', event['end'].get('date'))

            existing_start_dt = datetime.fromisoformat(existing_start.replace('Z', '+00:00'))
            existing_end_dt = datetime.fromisoformat(existing_end.replace('Z', '+00:00'))

            # Check for time overlap
            if not (end_dt <= existing_start_dt or start_dt >= existing_end_dt):
                overlap_found = True
                overlap_details.append({
                    'title': event.get('summary', 'Untitled'),
                    'start': existing_start_dt,
                    'end': existing_end_dt
                })

        # Step 4: If overlap, ask user to update conflicting event
        if overlap_found:
            response = f"⚠️ **Schedule Conflict Detected**\n\n"
            response += f"You want to schedule:\n"
            response += f"📅 {event_data['summary']}\n"
            response += f"🕐 {start_dt.strftime('%I:%M %p')} - {end_dt.strftime('%I:%M %p')}\n\n"
            response += f"But you already have:\n"
            for i, overlap in enumerate(overlap_details, 1):
                response += f"{i}. {overlap['title']} ({overlap['start'].strftime('%I:%M %p')} - {overlap['end'].strftime('%I:%M %p')})\n"
            response += f"\n❌ Cannot create due to conflict.\n\n"
            response += f"**Please update one of the conflicting events to a different time:**\n"
            response += f"Example: 'Update {overlap_details[0]['title']} to 5 PM' or 'Change {overlap_details[0]['title']} to tomorrow at 3 PM'"

            logger.info("Overlap detected, asking user to update conflicting event")
            return response

        # Step 5: No overlap, create the event
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

        if event_data.get('location'):
            event['location'] = event_data['location']

        created_event = service.events().insert(
            calendarId=settings.google_calendar_id,
            body=event
        ).execute()

        # Step 6: Give response (no duplicate calls)
        response = f"✅ **Event Created Successfully**\n\n"
        response += f"📅 {event_data['summary']}\n"
        response += f"🕐 {start_dt.strftime('%A, %B %d at %I:%M %p')} - {end_dt.strftime('%I:%M %p')}"

        logger.info(f"Event created: {created_event['id']}")
        return response

    except Exception as e:
        logger.error(f"Error in _smart_create: {e}", exc_info=True)
        return f"❌ I couldn't create the event. Error: {str(e)}"


def _smart_delete(request: str) -> str:
    """
    Smart event deletion following CoT:
    1. Read all user's schedule based on user instruction
    2. If no schedule matches, reply there's nothing to delete
    3. If there is a match, do the deletion
    4. Directly give response (no duplicate calls)
    """
    try:
        service = _get_calendar_service()
        request_lower = request.lower()
        user_tz = pytz.timezone(settings.default_timezone)
        now = datetime.now(user_tz)

        # Step 1: Determine time range from user instruction
        if 'today' in request_lower or 'hari ini' in request_lower:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now.replace(hour=23, minute=59, second=59, microsecond=0)
            period = "today"
        elif 'tomorrow' in request_lower or 'besok' in request_lower:
            tomorrow = now + timedelta(days=1)
            start = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
            end = tomorrow.replace(hour=23, minute=59, second=59, microsecond=0)
            period = "tomorrow"
        elif 'tonight' in request_lower or 'malam ini' in request_lower:
            start = now.replace(hour=18, minute=0, second=0, microsecond=0)
            end = now.replace(hour=23, minute=59, second=59, microsecond=0)
            period = "tonight"
        else:
            # Default: next 7 days
            start = now
            end = now + timedelta(days=7)
            period = "in the next week"

        # Step 2: Read all schedule in the timeframe
        events = service.events().list(
            calendarId=settings.google_calendar_id,
            timeMin=start.isoformat(),
            timeMax=end.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute().get('items', [])

        logger.info(f"Found {len(events)} events {period} for deletion")

        # Step 3: If no schedule matches, reply there's nothing to delete
        if not events:
            return f"✅ You don't have any events {period} to delete. Your schedule is clear!"

        # Step 4: If there is a match, do the deletion
        deleted_count = 0
        deleted_titles = []

        for event in events:
            try:
                service.events().delete(
                    calendarId=settings.google_calendar_id,
                    eventId=event['id']
                ).execute()
                deleted_count += 1
                deleted_titles.append(event.get('summary', 'Untitled'))
                logger.info(f"Deleted event: {event['id']}")
            except Exception as e:
                logger.error(f"Error deleting event {event['id']}: {e}")

        # Step 5: Directly give response (no duplicate calls)
        if deleted_count > 0:
            response = f"✅ **Successfully Deleted {deleted_count} Event(s) {period.title()}**\n\n"
            for i, title in enumerate(deleted_titles, 1):
                response += f"{i}. {title}\n"
            logger.info(f"Deleted {deleted_count} events {period}")
            return response
        else:
            return f"❌ I found events {period} but couldn't delete them. Please try again."

    except Exception as e:
        logger.error(f"Error in _smart_delete: {e}", exc_info=True)
        return f"❌ Error deleting events: {str(e)}"


def _smart_list(request: str) -> str:
    """Smart event listing with natural language parsing"""
    try:
        # Reuse existing list_calendar_events_tool logic
        return list_calendar_events_tool(request)
    except Exception as e:
        logger.error(f"Error in _smart_list: {e}")
        return "I couldn't retrieve your calendar events. Please try again."


def _smart_update(request: str) -> str:
    """
    Smart event update following CoT:
    1. Read all user's schedule first based on user instruction
    2. If no schedule matches that user is asking for, respond that user doesn't have any schedule for that specific timeframe
    3. If there is a schedule match, do the update
    4. Directly give response after update (no duplicate calls)
    """
    try:
        service = _get_calendar_service()
        request_lower = request.lower()
        user_tz = pytz.timezone(settings.default_timezone)
        now = datetime.now(user_tz)

        # Step 1: Determine time range from user instruction
        if 'today' in request_lower or 'hari ini' in request_lower:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now.replace(hour=23, minute=59, second=59, microsecond=0)
            period = "today"
        elif 'tomorrow' in request_lower or 'besok' in request_lower:
            tomorrow = now + timedelta(days=1)
            start = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
            end = tomorrow.replace(hour=23, minute=59, second=59, microsecond=0)
            period = "tomorrow"
        elif 'tonight' in request_lower or 'malam ini' in request_lower:
            start = now.replace(hour=18, minute=0, second=0, microsecond=0)
            end = now.replace(hour=23, minute=59, second=59, microsecond=0)
            period = "tonight"
        else:
            # Default: next 7 days
            start = now
            end = now + timedelta(days=7)
            period = "in the next week"

        # Step 2: Read all schedule in the timeframe
        events = service.events().list(
            calendarId=settings.google_calendar_id,
            timeMin=start.isoformat(),
            timeMax=end.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute().get('items', [])

        logger.info(f"Found {len(events)} events {period} for update")

        # Step 3: If no schedule matches, respond accordingly
        if not events:
            return f"❌ You don't have any events {period} to update."

        # Try to find the event mentioned in the request
        # Look for keywords like event titles
        target_event = None
        for event in events:
            event_title = event.get('summary', '').lower()
            # Check if any significant word from the request matches the event title
            request_words = request_lower.replace('update', '').replace('change', '').replace('reschedule', '').replace('ubah', '').replace('ganti', '').replace('rubah', '').split()
            for word in request_words:
                if len(word) > 3 and word in event_title:  # Only match significant words
                    target_event = event
                    break
            if target_event:
                break

        # If we found a matching event, try to parse the new time
        if target_event:
            # Parse the new time from the request using LLM
            try:
                llm = ChatGroq(
                    api_key=settings.groq_api_key,
                    model_name=settings.groq_model,
                    temperature=0.1
                )

                prompt = f"""Extract the NEW time information from this update request: "{request}"

Current event:
- Title: {target_event.get('summary')}
- Current time: {target_event['start'].get('dateTime', target_event['start'].get('date'))}

User's timezone: {settings.default_timezone}
Today's date: {now.strftime('%Y-%m-%d')}

Return ONLY a valid JSON object with the new start and end times:
{{
  "start_time": "YYYY-MM-DDTHH:MM:SS",
  "end_time": "YYYY-MM-DDTHH:MM:SS"
}}

Return ONLY the JSON, nothing else."""

                response = llm.invoke(prompt)
                json_text = response.content if hasattr(response, 'content') else str(response)

                # Clean and extract JSON
                json_text = re.sub(r'```json\s*', '', json_text)
                json_text = re.sub(r'```\s*', '', json_text)
                json_text = json_text.strip()

                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', json_text)
                if json_match:
                    new_times = json.loads(json_match.group(0))

                    # Update the event
                    target_event['start'] = {
                        'dateTime': new_times['start_time'],
                        'timeZone': settings.default_timezone
                    }
                    target_event['end'] = {
                        'dateTime': new_times['end_time'],
                        'timeZone': settings.default_timezone
                    }

                    updated_event = service.events().update(
                        calendarId=settings.google_calendar_id,
                        eventId=target_event['id'],
                        body=target_event
                    ).execute()

                    # Step 4: Directly give response (no duplicate calls)
                    start_dt = datetime.fromisoformat(new_times['start_time'])
                    end_dt = datetime.fromisoformat(new_times['end_time'])
                    response = f"✅ **Event Updated Successfully**\n\n"
                    response += f"📅 {target_event.get('summary')}\n"
                    response += f"🕐 New time: {start_dt.strftime('%A, %B %d at %I:%M %p')} - {end_dt.strftime('%I:%M %p')}"

                    logger.info(f"Event updated: {updated_event['id']}")
                    return response
                else:
                    return f"❌ I couldn't understand the new time. Please specify clearly, e.g., 'Update my NLP homework to 8 PM tonight'"

            except Exception as e:
                logger.error(f"Error parsing update request: {e}")
                return f"❌ I couldn't parse the update request. Please be more specific about the new time."

        # If no matching event found
        return f"❌ I couldn't find the event you want to update {period}. Available events:\n" + "\n".join([f"- {e.get('summary', 'Untitled')}" for e in events])

    except Exception as e:
        logger.error(f"Error in _smart_update: {e}", exc_info=True)
        return f"❌ Error updating event: {str(e)}"
