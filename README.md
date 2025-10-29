# Personal Assistant WhatsApp Bot

A powerful AI-powered personal assistant accessible via WhatsApp, featuring calendar management, email composition, and resume summarization capabilities. Built with a two-part architecture: Node.js frontend for WhatsApp interface and Python LangChain backend for intelligent agent processing.

## Developer Team
| Nama | NIM |
|------|------|
| **Muhammad Luthfi Attaqi** | 22/496427/TK/54387 |
| **Varick Zahir Sarjiman** | 22/496418/TK/54384 |

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
                                                                  │    (llama-3.1-8b-instant)
                                                                  │
                                                                  ├──> PostgreSQL
                                                                  │    (Structured Data)
                                                                  │
                                                                  ├──> ChromaDB
                                                                  │    (Vector Store)
                                                                  │
                                                                  └──> External APIs
                                                                       ├─ Google Calendar
                                                                       └─ Gmail/SMTP
```

### Two-Part Architecture

1. **Frontend (Node.js)**: Handles WhatsApp authentication and message routing
2. **Backend (Python)**: Processes messages using LangChain agent with ReAct framework

## Features

### Core Capabilities
- **Conversational AI**: Natural language understanding powered by Groq's llama-3.1-8b-instant
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
- **LLM**: Groq API (llama-3.1-8b-instant)
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
│   │   └── authorize_gmail.py # Gmail OAuth authorization
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
├── .env.example               # Environment variables template
├── .gitignore
└── README.md                  # This file

```

## Prerequisites

- **Node.js**: v18.0.0 or higher
- **Python**: 3.10 or higher
- **PostgreSQL**: 14 or higher
- **Git**: For version control

### API Keys Required
- Groq API Key (from https://console.groq.com)
- Google Calendar API credentials (for scheduling)
- Gmail API OAuth credentials (for draft sync)
- Gmail/SMTP credentials (for email sending)

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
# Backend API Configuration
BACKEND_API_URL=http://localhost:8000
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000

# Groq API Configuration
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant

# Database Configuration (PostgreSQL)
DATABASE_URL=postgresql://username:password@host:port/database_name

# Database Pool Settings
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# Vector Database Configuration (ChromaDB)
CHROMA_PERSIST_DIRECTORY=../vector_store
CHROMA_COLLECTION_NAME=whatsapp_conversations

# Embedding Model for ChromaDB
EMBEDDING_MODEL=sentence-transformers
EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2

# Email Configuration
EMAIL_SERVICE=gmail
EMAIL_USER=your_email@gmail.com
EMAIL_PASSWORD=your_app_specific_password_here

# SMTP Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_TLS=true

# IMAP Configuration
IMAP_HOST=imap.gmail.com
IMAP_PORT=993

# Calendar Integration (Google Calendar API)
GOOGLE_CALENDAR_CREDENTIALS_FILE=backend/config/google_credentials.json
GOOGLE_CALENDAR_ID=primary

# Timezone Configuration
# Examples: Asia/Jakarta (GMT+7/WIB), America/New_York (EST), Europe/London (GMT)
DEFAULT_TIMEZONE=Asia/Jakarta

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=../logs/app.log
LOG_MAX_BYTES=10485760
LOG_BACKUP_COUNT=5

# Security Configuration
# Generate: python -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=generate_your_own_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# Rate Limiting
RATE_LIMIT_PER_USER=30
RATE_LIMIT_WINDOW_SECONDS=60

# LangChain Agent Configuration
MAX_AGENT_ITERATIONS=5
MAX_RESPONSE_TOKENS=1000
LLM_TEMPERATURE=0.1

# Memory Configuration
SHORT_TERM_MEMORY_SIZE=10
LONG_TERM_MEMORY_RETRIEVAL_COUNT=5

# Development/Production Mode
ENVIRONMENT=development
DEBUG=true

# WhatsApp Frontend Configuration
WHATSAPP_SESSION_NAME=whatsapp-assistant-session
WHATSAPP_TIMEOUT=180000
ALLOWED_WHATSAPP_NUMBERS=621234567890,6289876543210
```

### 2. Google Calendar Setup 

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

#### For Gmail Draft Sync:
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
![QR Code for Authentication](demo/qr_code_setup.mp4)
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

## Demo & Example Usage

This section provides visual demonstrations of the Personal Assistant WhatsApp Bot in action, showing real-world usage of each feature.

---

### 1. Calendar Management Tool

The calendar tool integrates with Google Calendar to help you manage schedules, create events, and set reminders through natural conversation.

## 1.1 WhatsApp Chat - Creating Calendar Events

![Calendar Tool - Chat Interface](demo/calendar-chat-demo.mp4)

## 1.2 Google Calendar - Event Verification

![Calendar Tool - Event Verification](demo/calendar-event-verification.mp4)

---

### 2. Email Management Tool

The email tool provides comprehensive email management including drafting, improving, sending, and syncing with Gmail drafts.

## 2.1 WhatsApp Chat - Email Workflow

![Email Tool - Chat Interface](demo/email-chat-demo.mp4)

## 2.2 Gmail - Draft Synchronization

![Email Tool - Draft Synchronization](demo/email-draft-sync.mp4)

---

### 3. Text Analyzer Tool

The analyzer tool helps summarize or giving bullet points from a Documents (PPT/PDF/DOCX) or Text.

![Analyzer Tool - Chat Interface](demo/analyzer-chat-demo.mp4)


---


## Acknowledgments

- LangChain for the agent framework
- Groq for lightning-fast LLM inference
- whatsapp-web.js for WhatsApp integration
- FastAPI for the excellent Python web framework

---
