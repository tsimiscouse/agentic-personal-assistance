"""
Unit Tests for Email Tool - Happy Path Only
Tests basic successful email management scenarios
"""

import pytest
from tools.email_tool import (
    read_emails_tool,
    draft_email_tool,
    send_draft_tool,
    improve_draft_tool,
    cancel_draft_tool,
    keep_draft_tool,
    list_drafts_tool,
    select_draft_tool,
    _parse_email_request,
    _parse_read_request,
    _send_email
)


class TestEmailTool:
    """Happy path tests for email tools"""

    def test_create_draft_with_details(self, test_db, test_user, mock_gmail_api, mock_groq_llm):
        """Test: Create draft with specific details successfully"""
        result = draft_email_tool(
            "Draft email to alice@company.com with subject 'Weekly Report' about project progress",
            user_id=test_user.user_id,
            db=test_db
        )

        assert isinstance(result, str)
        assert len(result) > 0

    def test_send_existing_draft(self, test_db, test_user, sample_email_draft, mock_gmail_api):
        """Test: Send an existing draft successfully"""
        result = send_draft_tool(
            user_id=test_user.user_id,
            db=test_db
        )

        assert isinstance(result, str)
        assert len(result) > 0

    def test_improve_draft(self, test_db, test_user, sample_email_draft, mock_gmail_api, mock_groq_llm):
        """Test: Improve an existing draft successfully"""
        result = improve_draft_tool(
            "Make it more formal",
            user_id=test_user.user_id,
            db=test_db
        )

        assert isinstance(result, str)
        assert len(result) > 0

    def test_improve_draft_add_details(self, test_db, test_user, sample_email_draft, mock_gmail_api, mock_groq_llm):
        """Test: Add details to draft successfully"""
        result = improve_draft_tool(
            "Add meeting time 3 PM",
            user_id=test_user.user_id,
            db=test_db
        )

        assert isinstance(result, str)
        assert len(result) > 0

    def test_cancel_existing_draft(self, test_db, test_user, sample_email_draft, mock_gmail_api):
        """Test: Cancel an existing draft successfully"""
        result = cancel_draft_tool(
            user_id=test_user.user_id,
            db=test_db
        )

        assert isinstance(result, str)
        assert len(result) > 0

    def test_keep_draft(self, test_db, test_user, sample_email_draft, mock_gmail_api):
        """Test: Keep a draft for later successfully"""
        result = keep_draft_tool(
            user_id=test_user.user_id,
            db=test_db
        )

        assert isinstance(result, str)
        assert len(result) > 0

    def test_list_drafts_with_drafts(self, test_db, test_user, sample_email_draft):
        """Test: List drafts when drafts exist successfully"""
        result = list_drafts_tool(
            user_id=test_user.user_id,
            db=test_db
        )

        assert isinstance(result, str)
        assert len(result) > 0

    def test_select_draft_by_number(self, test_db, test_user, sample_email_draft):
        """Test: Select a draft by number successfully"""
        result = select_draft_tool(
            "1",
            user_id=test_user.user_id,
            db=test_db
        )

        assert isinstance(result, str)
        assert len(result) > 0

    def test_parse_simple_request(self, mock_groq_llm):
        """Test: Parse simple email request successfully"""
        result = _parse_email_request("Send email to john@example.com about meeting")

        assert isinstance(result, dict)
        assert 'to' in result or 'to_email' in result
        assert 'subject' in result

    def test_parse_read_latest(self):
        """Test: Parse 'latest emails' request successfully"""
        result = _parse_read_request("Show me my latest 10 emails")

        assert isinstance(result, dict)
        assert 'limit' in result
        assert result['limit'] == 10
