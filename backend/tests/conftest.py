import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
import uuid

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.connection import Base
from models.user import User
from models.email_draft import EmailDraft

@pytest.fixture(scope="function")
def test_engine():
    """Create in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="function")
def test_db(test_engine):
    """Create a new database session for each test"""
    SessionLocal = sessionmaker(bind=test_engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="function")
def test_user(test_db):
    """Create a test user"""
    user = User(
        user_id="test_user_123",
        name="Test User",
        phone_number="1234567890",
        timezone="Asia/Jakarta",
        preferences={}
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user

@pytest.fixture
def mock_groq_llm():
    """Mock Groq LLM for testing"""
    with patch('langchain_groq.ChatGroq') as mock_groq_class:
        from langchain_core.messages import AIMessage

        mock_llm = MagicMock()

        def mock_invoke(prompt):
            # Return simple response based on input
            input_text = str(prompt)
            if 'summarize' in input_text.lower():
                content = "Summary: This is a test summary of the content."
            elif 'key points' in input_text.lower():
                content = "Key Points:\n- Point 1\n- Point 2\n- Point 3"
            elif 'explain' in input_text.lower():
                content = "Explanation: This is a clear explanation of the concept."
            elif 'compare' in input_text.lower():
                content = "Comparison:\nSimilarities:\n- Both are related\nDifferences:\n- One is different from the other"
            elif 'email' in input_text.lower() or 'draft' in input_text.lower():
                content = '{"to_email": "test@example.com", "subject": "Test Subject", "body": "Test email body"}'
            elif 'calendar' in input_text.lower() or 'event' in input_text.lower():
                content = '{"summary": "Test Meeting", "start_time": "2025-10-29T14:00:00", "end_time": "2025-10-29T15:00:00", "description": "Test description"}'
            else:
                content = "This is a test response from the LLM."

            return AIMessage(content=content)

        mock_llm.invoke = mock_invoke
        mock_groq_class.return_value = mock_llm

        yield mock_llm


@pytest.fixture
def mock_gmail_api():
    """Mock Gmail API for testing"""
    with patch('tools.email_tool._get_gmail_service') as mock_service, \
         patch('tools.email_tool._create_gmail_draft') as mock_create, \
         patch('tools.email_tool._update_gmail_draft') as mock_update, \
         patch('tools.email_tool._send_gmail_draft') as mock_send, \
         patch('tools.email_tool._delete_gmail_draft') as mock_delete, \
         patch('tools.email_tool._fetch_gmail_draft') as mock_fetch:

        # Mock service
        service = MagicMock()
        mock_service.return_value = service

        # Mock create draft
        mock_create.return_value = "gmail_draft_123"

        # Mock update draft
        mock_update.return_value = True

        # Mock send draft
        mock_send.return_value = True

        # Mock delete draft
        mock_delete.return_value = True

        # Mock fetch draft
        mock_fetch.return_value = {
            'to_email': 'test@example.com',
            'subject': 'Test Subject',
            'body': 'Test Body'
        }

        yield {
            'service': mock_service,
            'create': mock_create,
            'update': mock_update,
            'send': mock_send,
            'delete': mock_delete,
            'fetch': mock_fetch
        }


@pytest.fixture
def mock_smtp():
    """Mock SMTP for email sending"""
    with patch('smtplib.SMTP') as mock_smtp_class:
        smtp_server = MagicMock()
        smtp_server.starttls.return_value = None
        smtp_server.login.return_value = None
        smtp_server.sendmail.return_value = {}
        smtp_server.quit.return_value = None

        mock_smtp_class.return_value = smtp_server
        yield smtp_server


@pytest.fixture
def mock_imap():
    """Mock IMAP for reading emails"""
    with patch('imaplib.IMAP4_SSL') as mock_imap_class:
        imap_server = MagicMock()

        # Mock successful login
        imap_server.login.return_value = ('OK', [b'Logged in'])
        imap_server.select.return_value = ('OK', [b'5'])
        imap_server.search.return_value = ('OK', [b'1 2 3'])

        # Mock email fetch
        email_msg = b'From: john@example.com\r\nSubject: Project Meeting\r\nDate: Mon, 27 Oct 2025 10:30:00\r\n\r\nHi, lets discuss the project timeline.'
        imap_server.fetch.return_value = ('OK', [(b'1', email_msg)])

        imap_server.close.return_value = ('OK', [])
        imap_server.logout.return_value = ('BYE', [])

        mock_imap_class.return_value = imap_server
        yield imap_server


@pytest.fixture
def mock_calendar_api():
    """Mock Google Calendar API"""
    with patch('tools.calendar_tool._get_calendar_service') as mock_get_service:
        # Mock the calendar service
        mock_service = MagicMock()
        mock_events = MagicMock()

        # Mock events().insert() for create operations
        mock_insert = MagicMock()
        mock_insert_response = MagicMock()
        mock_insert_response.execute.return_value = {
            'id': 'event_123',
            'summary': 'Test Meeting',
            'start': {'dateTime': '2025-10-28T14:00:00+07:00'},
            'end': {'dateTime': '2025-10-28T15:00:00+07:00'},
            'htmlLink': 'https://calendar.google.com/event?eid=event_123'
        }
        mock_insert.return_value = mock_insert_response
        mock_events.insert = mock_insert

        # Mock events().list() for read/list operations
        mock_list = MagicMock()
        mock_list_response = MagicMock()
        mock_list_response.execute.return_value = {
            'items': []
        }
        mock_list.return_value = mock_list_response
        mock_events.list = mock_list

        # Mock events().delete() for delete operations
        mock_delete = MagicMock()
        mock_delete_response = MagicMock()
        mock_delete_response.execute.return_value = {}
        mock_delete.return_value = mock_delete_response
        mock_events.delete = mock_delete

        # Wire up the mocks
        mock_service.events.return_value = mock_events
        mock_get_service.return_value = mock_service

        yield {
            'service': mock_service,
            'events': mock_events,
            'insert': mock_insert,
            'list': mock_list,
            'delete': mock_delete
        }

@pytest.fixture
def sample_text():
    """Sample text for text analysis tools"""
    return """
    Artificial intelligence has revolutionized the way we interact with technology.
    Machine learning algorithms can now process vast amounts of data and make
    predictions with remarkable accuracy. Natural language processing enables
    computers to understand and generate human language.
    """


@pytest.fixture
def sample_email_draft(test_db, test_user):
    """Create a sample email draft"""
    draft = EmailDraft(
        id=str(uuid.uuid4()),
        user_id=test_user.user_id,
        to_email="test@example.com",
        subject="Test Subject",
        body="Test email body",
        status="draft",
        gmail_draft_id="gmail_draft_123",
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(hours=24)
    )
    test_db.add(draft)
    test_db.commit()
    test_db.refresh(draft)
    return draft


@pytest.fixture(autouse=True)
def mock_settings(monkeypatch):
    """Mock settings for all tests"""
    import os
    from dotenv import load_dotenv

    # Load environment variables from .env file
    load_dotenv()

    # Create a mock settings object
    class MockSettings:
        # Groq/LLM settings
        groq_api_key = os.getenv("GROQ_API_KEY", "test_groq_key")
        groq_model = "llama-3.1-8b-instant"
        llm_temperature = 0.7
        llm_max_tokens = 1024
        max_response_tokens = 1024

        # Email settings
        email_user = "test@example.com"
        email_password = "test_password"
        smtp_host = "smtp.gmail.com"
        smtp_port = 587
        smtp_tls = True
        imap_host = "imap.gmail.com"
        imap_port = 993

        # Calendar settings
        pipedream_calendar_endpoint = "https://mock.pipedream.net"
        default_timezone = "Asia/Jakarta"
        google_calendar_credentials_file = "config/google_credentials.json"
        google_calendar_id = "primary"

        # Database settings
        database_url = "sqlite:///:memory:"
        chroma_persist_directory = "./test_vector_store"

        # Other settings
        debug = False
        max_agent_iterations = 10
        log_level = "INFO"
        environment = "test"

        @staticmethod
        def get_absolute_path(x):
            return f"/mock/path/{x}"

    mock = MockSettings()

    # Monkey patch get_settings to return our mock
    import config.settings
    monkeypatch.setattr(config.settings, 'get_settings', lambda: mock)

    yield mock

@pytest.fixture(autouse=True)
def cleanup_after_test(test_db):
    """Clean up database after each test"""
    yield
    # Rollback any uncommitted changes
    test_db.rollback()
