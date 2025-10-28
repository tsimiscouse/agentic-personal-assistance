"""
Unit Tests for Calendar Tool - Happy Path Only
Tests basic successful calendar management scenarios
"""

import pytest
from tools.calendar_tool import (
    create_calendar_event_tool,
    list_calendar_events_tool,
    delete_calendar_event_tool,
    smart_schedule_tool,
    _parse_event_with_llm,
    _parse_time_query
)


class TestCalendarTool:
    """Happy path tests for calendar tools"""

    def test_create_event_with_location(self, mock_calendar_api, mock_groq_llm):
        """Test: Create event with location successfully"""
        result = create_calendar_event_tool("Team meeting at Office Room 301 at 3 PM")

        assert isinstance(result, str)
        assert len(result) > 0

    def test_create_recurring_event(self, mock_calendar_api, mock_groq_llm):
        """Test: Create recurring event successfully"""
        result = create_calendar_event_tool("Weekly team standup every Monday at 9 AM")

        assert isinstance(result, str)
        assert len(result) > 0

    def test_create_event_with_description(self, mock_calendar_api, mock_groq_llm):
        """Test: Create event with description successfully"""
        result = create_calendar_event_tool("Project review tomorrow 2 PM to discuss Q4 goals")

        assert isinstance(result, str)
        assert len(result) > 0

    def test_list_events_this_week(self, mock_calendar_api):
        """Test: List this week's events successfully"""
        result = list_calendar_events_tool("Show me events for this week")

        assert isinstance(result, str)
        assert len(result) > 0

    def test_delete_event_by_id(self, mock_calendar_api):
        """Test: Delete event by ID successfully"""
        result = delete_calendar_event_tool("event_123")

        assert isinstance(result, str)
        assert len(result) > 0

    def test_smart_schedule_create(self, mock_calendar_api, mock_groq_llm):
        """Test: Create event via smart schedule successfully"""
        result = smart_schedule_tool("Schedule a meeting tomorrow at 2 PM")

        assert isinstance(result, str)
        assert len(result) > 0

    def test_smart_schedule_list(self, mock_calendar_api):
        """Test: List events via smart schedule successfully"""
        result = smart_schedule_tool("Show my schedule for today")

        assert isinstance(result, str)
        assert len(result) > 0

    def test_parse_event_with_llm(self, mock_groq_llm):
        """Test: Parse event description with LLM successfully"""
        result = _parse_event_with_llm("Meeting tomorrow at 2 PM")

        assert isinstance(result, dict)
        assert 'summary' in result
        assert 'start_time' in result
        assert 'end_time' in result

    def test_parse_time_query_this_week(self):
        """Test: Parse 'this week' time query successfully"""
        result = _parse_time_query("this week")

        assert isinstance(result, dict)
        assert 'start' in result
        assert 'end' in result
        assert 'description' in result
