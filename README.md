# Personal Assistant WhatsApp Bot

A powerful AI-powered personal assistant accessible via WhatsApp, featuring calendar management, email composition, and resume summarization capabilities. Built with a two-part architecture: Node.js frontend for WhatsApp interface and Python LangChain backend for intelligent agent processing.

## Table of Contents
- [Architecture Overview](#architecture-overview)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Development](#development)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)

## Architecture Overview

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│   WhatsApp      │  HTTP   │   Node.js       │  HTTP   │   Python        │
│   Client        ├────────>│   Frontend      ├────────>│   Backend       │
│   (User)        │<────────┤   (whatsapp-    │<────────┤   (LangChain    │
│                 │         │   web.js)       │         │   + FastAPI)    │
└─────────────────┘         └─────────────────┘         └─────────────────┘
                                                                  │
                                                                  ├──> Groq LLM
                                                                  │    (Mixtral 8x7b)
                                                                  │
                                                                  ├──> PostgreSQL
                                                                  │    (Structured Data)
                                                                  │
                                                                  ├──> ChromaDB
                                                                  │    (Vector Store)
                                                                  │
                                                                  └──> External APIs
                                                                       ├─ Google Calendar
                                                                       ├─ Gmail/SMTP
                                                                       └─ Pipedream
```

### Two-Part Architecture

1. **Frontend (Node.js)**: Handles WhatsApp authentication and message routing
2. **Backend (Python)**: Processes messages using LangChain agent with ReAct framework

## Features

### Core Capabilities
- **Conversational AI**: Natural language understanding powered by Groq's Mixtral 8x7b
- **Calendar Management**: Create, update, and query Google Calendar events
- **Email Management**:
  - Draft, improve, send, and manage emails
  - Multi-draft support with numbered selection
  - Real-time Gmail sync (bidirectional)
  - Keep drafts for later editing
- **Resume Summarization**: Process and summarize professional information

### Memory System
- **Short-Term Memory**: Maintains context within current conversation using ConversationBufferMemory
- **Long-Term Memory**:
  - PostgreSQL for structured data (user profiles, email history)
  - ChromaDB for semantic search across past conversations
- **User-Specific Context**: Isolated memory per WhatsApp user ID

## Technology Stack

### Frontend
- **Runtime**: Node.js 18+
- **WhatsApp Client**: whatsapp-web.js
- **HTTP Client**: Axios
- **QR Code**: qrcode-terminal

### Backend
- **Framework**: FastAPI
- **AI Framework**: LangChain
- **LLM**: Groq API (Mixtral 8x7b)
- **Databases**:
  - PostgreSQL (structured data)
  - ChromaDB (vector embeddings)
- **ORM**: SQLAlchemy
- **Environment**: Python 3.10+

## Project Structure

```
agentic-personal-assistance/
├── backend/                    # Python LangChain Agent Backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI application entry point
│   │   └── agent.py           # LangChain agent initialization
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── calendar_tool.py   # Google Calendar integration
│   │   ├── email_tool.py      # Email management with Gmail sync
│   │   └── resume_tool.py     # Resume summarization
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py            # User data models
│   │   ├── email_draft.py     # Email draft models
│   │   └── conversation.py    # Conversation models
│   ├── scripts/
│   │   ├── authorize_gmail.py # Gmail OAuth authorization
│   │   └── migrate_gmail_draft_simple.py # Database migrations
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py        # Configuration management
│   ├── database/
│   │   ├── __init__.py
│   │   └── connection.py      # Database connections
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── short_term.py      # Conversation buffer memory
│   │   └── long_term.py       # Database & vector store integration
│   └── requirements.txt       # Python dependencies
│
├── frontend/                   # Node.js WhatsApp Interface
│   ├── src/
│   │   ├── index.js           # Main application entry
│   │   ├── whatsapp.js        # WhatsApp client logic
│   │   └── api.js             # Backend API client
│   ├── config/
│   │   └── config.js          # Configuration
│   └── package.json           # Node.js dependencies
│
├── database/                   # Database files
│   └── .gitkeep
│
├── vector_store/               # ChromaDB persistence
│   └── .gitkeep
│
├── data/                       # Data storage
│   └── .gitkeep
│
├── logs/                       # Application logs
│   └── .gitkeep
│
├── docs/                       # Documentation
│   ├── ARCHITECTURE.md        # Detailed architecture
│   └── API.md                 # API documentation
│
├── GMAIL_DRAFT_INTEGRATION.md # Gmail API setup guide
├── KEEP_DRAFT_FEATURE.md      # Draft keep functionality
├── DRAFT_MANAGEMENT_FEATURE.md # Draft listing & selection
├── BIDIRECTIONAL_GMAIL_SYNC.md # Gmail sync implementation
│
├── .env.example               # Environment variables template
├── .gitignore
├── README.md                  # This file
└── CLAUDE.md                  # Context for Claude Code sessions

```

## Prerequisites

- **Node.js**: v18.0.0 or higher
- **Python**: 3.10 or higher
- **PostgreSQL**: 14 or higher
- **Git**: For version control

### API Keys Required
- Groq API Key (from https://console.groq.com)
- Google Calendar API credentials (optional)
- Gmail API OAuth credentials (for draft sync)
- Gmail/SMTP credentials (for email sending)
- Pipedream endpoint URL (for calendar integration)

## Installation

### 1. Clone the Repository

```bash
cd C:\Users\ASUS\Projects\NLP\agentic-personal-assistance\agentic-personal-assistance
```

### 2. Backend Setup (Python)

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Frontend Setup (Node.js)

```bash
# Navigate to frontend
cd ../frontend

# Install dependencies
npm install
```

### 4. Database Setup

```bash
# Install PostgreSQL if not already installed
# Create database
psql -U postgres
CREATE DATABASE whatsapp_assistant;
\q

# Run migrations (after backend setup)
cd ../backend
alembic upgrade head
```

## Configuration

### 1. Environment Variables

Copy the example environment file and configure:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Backend API
BACKEND_API_URL=http://localhost:8000
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000

# Groq API
GROQ_API_KEY=your_groq_api_key_here

# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/whatsapp_assistant

# Vector Database
CHROMA_PERSIST_DIRECTORY=../vector_store

# Email Configuration
EMAIL_SERVICE=gmail
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-app-specific-password

# Calendar Integration
PIPEDREAM_CALENDAR_ENDPOINT=https://your-pipedream-endpoint.m.pipedream.net

# Logging
LOG_LEVEL=INFO
LOG_FILE=../logs/app.log

# Security
SECRET_KEY=your-secret-key-for-jwt
```

### 2. Google Calendar Setup (Optional)

If using Google Calendar directly instead of Pipedream:

1. Go to Google Cloud Console
2. Create a new project
3. Enable Google Calendar API
4. Create OAuth 2.0 credentials
5. Download credentials JSON
6. Place in `backend/config/google_credentials.json`

### 3. Gmail Setup

#### For Email Sending (SMTP):
1. Enable 2-Factor Authentication on your Google account
2. Go to App Passwords section
3. Generate new app password for "Mail"
4. Use this password in `.env` file as `EMAIL_PASSWORD`

#### For Gmail Draft Sync (Optional but Recommended):
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select a project
3. Enable Gmail API
4. Create OAuth 2.0 credentials (Desktop app type)
5. Download credentials JSON
6. Save as `backend/config/google_credentials.json`
7. Run authorization script:
   ```bash
   cd backend
   python scripts/authorize_gmail.py
   ```
8. Follow browser prompts to authorize
9. Token will be saved to `backend/config/gmail_token.json`

See `GMAIL_DRAFT_INTEGRATION.md` for detailed setup instructions.

## Usage

### Starting the Application

#### 1. Start Backend (Terminal 1)

```bash
cd backend
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend will be available at `http://localhost:8000`

#### 2. Start Frontend (Terminal 2)

```bash
cd frontend
node src/index.js
```

#### 3. WhatsApp Authentication

On first run, a QR code will appear in the terminal:
1. Open WhatsApp on your phone
2. Go to Settings > Linked Devices
3. Tap "Link a Device"
4. Scan the QR code displayed in terminal

### Interacting with the Bot

Send messages to your WhatsApp number:

**Calendar Management:**
```
"Schedule a meeting tomorrow at 2 PM with John about project review"
"Create a reminder for Friday at 9 AM to submit report"
```

**Email Management:**
```
# Create draft
"Draft an email to john@example.com about the meeting"

# Improve draft
"Improve it, add meeting time 3 PM tomorrow"
"Change subject to Project Meeting"

# Manage multiple drafts
"Show my drafts"
"Select draft 2"
"Send it"

# Keep for later
"Keep it"  # Saves draft to Gmail, extends expiry to 24 hours
```

**Resume Summarization:**
```
"Summarize this experience: I worked as a software engineer at XYZ Corp
for 3 years where I led the development of..."
```

## Development

### Backend Development

The LangChain agent uses the ReAct (Reasoning + Acting) framework:

```python
# agent.py structure
1. Tool Definition (using @tool decorator)
2. LLM Initialization (Groq)
3. Memory Setup (Short-term + Long-term)
4. Agent Creation (create_react_agent)
5. Agent Execution Loop
```

### Adding New Tools

Create a new tool in `backend/tools/`:

```python
from langchain.tools import tool

@tool
def my_custom_tool(input_text: str) -> str:
    """Description of what this tool does."""
    # Tool implementation
    return result
```

Register in `backend/app/agent.py`:

```python
from tools.my_custom_tool import my_custom_tool

tools = [calendar_tool, email_tool, resume_tool, my_custom_tool]
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## Deployment

### Docker Deployment (Recommended)

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Manual Deployment

#### Backend (Ubuntu/Linux Server)

```bash
# Install dependencies
sudo apt update
sudo apt install python3.10 python3.10-venv postgresql

# Setup application
cd backend
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run with gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

#### Frontend (Process Manager)

```bash
# Install PM2
npm install -g pm2

# Start application
cd frontend
pm2 start src/index.js --name whatsapp-bot

# Save configuration
pm2 save
pm2 startup
```

## Troubleshooting

### Common Issues

#### QR Code Not Appearing
- Ensure terminal supports UTF-8
- Try `npm install qrcode-terminal@latest`
- Check firewall settings

#### Backend Connection Failed
- Verify `BACKEND_API_URL` in frontend `.env`
- Check if backend is running on correct port
- Test endpoint: `curl http://localhost:8000/health`

#### Database Connection Error
- Verify PostgreSQL is running: `pg_isready`
- Check credentials in `.env`
- Ensure database exists: `psql -l`

#### Groq API Errors
- Verify API key is valid
- Check rate limits
- Monitor usage at console.groq.com

#### WhatsApp Disconnection
- Re-scan QR code
- Check WhatsApp app is updated
- Clear `frontend/.wwebjs_auth` folder and restart

### Logs

Check application logs:

```bash
# Backend logs
tail -f logs/app.log

# Frontend logs (if using PM2)
pm2 logs whatsapp-bot
```

## API Documentation

When backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -am 'Add feature'`
4. Push to branch: `git push origin feature-name`
5. Submit pull request

## License

This project is licensed under the MIT License.

## Support

For issues and questions:
- GitHub Issues: [Create an issue]
- Documentation: See `docs/` folder
- Email: your-email@example.com

## Acknowledgments

- LangChain for the agent framework
- Groq for lightning-fast LLM inference
- whatsapp-web.js for WhatsApp integration
- FastAPI for the excellent Python web framework

---

**Note**: This is a personal assistant bot. Never share your API keys or credentials. Keep your `.env` file secure and never commit it to version control.
