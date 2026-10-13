# Scriber Agent

Scriber Agent is an AI-powered clinical documentation application that captures doctor–patient conversations, transcribes them in real time, and generates structured clinical summaries after a session.

The system consists of three primary components:

* **Chrome Extension** — Captures microphone audio and supports real-time transcription.
* **Backend** — Handles authentication, real-time transcription, AI summary generation, background processing, and data management.
* **Frontend** — Provides the user interface for authentication, live transcription, summaries, and session history.

---

## Architecture Overview

```text
                    ┌─────────────────────┐
                    │     Chrome Browser  │
                    │                     │
                    │  Scriber Extension  │
                    │  Microphone Capture │
                    └──────────┬──────────┘
                               │
                               │ Audio / WebSocket
                               ▼
                    ┌─────────────────────┐
                    │       Backend       │
                    │      FastAPI        │
                    └──────────┬──────────┘
                               │
                 ┌─────────────┴─────────────┐
                 │                           │
                 ▼                           ▼
        ┌─────────────────┐        ┌─────────────────┐
        │    Deepgram     │        │ Redis / Celery  │
        │ Speech-to-Text  │        │ Background Jobs │
        └────────┬────────┘        └────────┬────────┘
                 │                          │
                 ▼                          ▼
        ┌─────────────────┐        ┌─────────────────┐
        │ Live Transcript │        │ LLM Generation  │
        └─────────────────┘        │ Gemini / Groq   │
                                   └────────┬────────┘
                                            │
                                            ▼
                                  ┌──────────────────┐
                                  │ Clinical Summary │
                                  └──────────────────┘

                 ┌─────────────────────────────┐
                 │         Frontend            │
                 │ Login / Transcription /     │
                 │ Summary / Dashboard        │
                 └─────────────────────────────┘
```

---

# Project Structure

```text
scriber-agent/
│
├── chrome-extension/
│   ├── manifest.json
│   ├── offscreen.html
│   ├── package.json
│   ├── package-lock.json
│   ├── popup.html
│   ├── vite.config.js
│   │
│   └── src/
│       ├── background.js
│       ├── constants.js
│       ├── content-bridge.js
│       ├── offscreen.js
│       └── popup/
│           ├── App.jsx
│           ├── index.css
│           └── main.jsx
│
├── backend/
│   ├── main.py
│   └── app/
│       ├── core/
│       ├── prompts/
│       ├── router/
│       │   ├── auth/
│       │   ├── admin/
│       │   ├── visits/
│       │   └── telemetry/
│       │
│       ├── schemas/
│       ├── services/
│       │   ├── auth/
│       │   ├── celery/
│       │   ├── redis/
│       │   ├── mongo/
│       │   ├── telemetry/
│       │   └── visits/
│       │       ├── transcription/
│       │       ├── generation/
│       │       └── status/
│       │
│       └── utils/
│
├── frontend/
│   ├── ai_transcribe/
│   │   └── js/
│   ├── assets/
│   ├── dashboard/
│   ├── js/
│   ├── login/
│   └── transcribe/
│
└── documents/
    └── README.md
```

---

# Application Flow

## 1. User Authentication

The provider logs in using:

```text
Email
  │
  ▼
OTP Verification
  │
  ▼
JWT Token
  │
  ├── Practice
  ├── Provider
  └── Specialty
```

The provider's specialty determines which system prompt is used during AI summary generation.

Specialty prompts are stored in PostgreSQL and served through a Redis cache.

---

## 2. Start Transcription

When the user clicks **Start**:

```text
Frontend
   │
   ▼
Chrome Extension
   │
   │ Microphone Audio
   ▼
Backend WebSocket
   │
   ▼
Deepgram
   │
   │ Real-time Transcript
   ▼
Backend
   │
   ▼
Frontend
```

The transcript is streamed back to the frontend while the session is active.

---

## 3. Stop Transcription

When the user clicks **Stop**:

```text
Active Session
      │
      ▼
Session Ends
      │
      ▼
Full Transcript
      │
      ▼
Background Processing
      │
      ▼
AI Generation Pipeline
      │
      ▼
Six Clinical Summaries
```

The heavy AI processing runs through Celery so that the API remains responsive.

---

# AI-Generated Summaries

After a session ends, the complete transcript is processed by the AI generation pipeline.

The system generates six summary formats:

| Summary Type           | Description                                |
| ---------------------- | ------------------------------------------ |
| Quick Reference        | Key points at a glance                     |
| Brief Summary          | Short narrative overview                   |
| Goldilocks Summary     | Balanced level of detail                   |
| Detailed Summary       | Comprehensive clinical narrative           |
| Super Detailed Summary | Exhaustive documentation                   |
| SOAP Notes             | Subjective / Objective / Assessment / Plan |

The summaries are exposed to the frontend through separate API endpoints.

---

# Frontend

The frontend provides the user-facing application.

## Pages

| Page          | Description                                      |
| ------------- | ------------------------------------------------ |
| Login         | Authentication entry point                       |
| Transcription | Real-time transcription during an active session |
| Summary       | AI-generated clinical summaries                  |
| Dashboard     | History of previous sessions and summaries       |

## Transcription Page

The transcription page becomes active when the user clicks **Start**.

It displays the live transcript of the doctor–patient conversation as the backend receives and processes the audio stream.

## Summary Page

The summary page is displayed after the user clicks **Stop**.

It provides access to all six generated summary formats:

* Quick Reference
* Brief Summary
* Goldilocks Summary
* Detailed Summary
* Super Detailed Summary
* SOAP Notes

## Dashboard

The dashboard provides an overview of previous sessions.

Users can open an individual session and review its generated summaries.

---

# Chrome Extension

The Scriber Agent Chrome Extension captures microphone audio and supports the real-time transcription workflow.

## Installation

### 1. Generate the Extension Build

Run the appropriate build script:

```text
.ps1
.sh
.cat
```

This generates the `dist` folder.

### 2. Open Chrome Extensions

Open Google Chrome and navigate to:

```text
chrome://extensions/
```

### 3. Enable Developer Mode

Enable **Developer Mode** using the toggle in the top-right corner.

### 4. Load the Extension

Click:

```text
Load Unpacked
```

Then select:

```text
pronex_demo/chrome-extension/dist
```

The **ScriberAgent** extension should now appear in the installed extensions list.

---

## Grant Microphone Permission

Open the ScriberAgent extension's details page.

Navigate to:

```text
Site Settings → Microphone
```

Set the microphone permission to:

```text
Allow
```

The extension can now access the microphone for audio capture.

---

# Backend

The backend provides the APIs and services responsible for:

* Authentication
* Real-time transcription
* WebSocket communication
* AI summary generation
* Background processing
* Session management
* Specialty-specific prompts
* Usage and cost telemetry
* Data storage and archival

## Backend Technology Stack

| Layer                      | Technology            |
| -------------------------- | --------------------- |
| Language                   | Python                |
| API Framework              | FastAPI               |
| Server                     | Uvicorn               |
| Background Jobs            | Celery                |
| Task Scheduler             | Celery Beat           |
| Message Broker             | Redis                 |
| AI Orchestration           | LangChain, LangGraph  |
| Speech-to-Text             | Deepgram              |
| LLM                        | Google Gemini or Groq |
| Hot Data Store             | Redis                 |
| Archive Store              | MongoDB               |
| Authentication / Telemetry | PostgreSQL            |

---

# Backend Services

## Authentication

Providers authenticate using email and OTP.

After successful authentication, the backend issues a JWT containing information such as:

* Practice
* Provider
* Specialty

Admin and back-office endpoints are protected using an admin key.

---

## Transcription

The transcription service:

1. Receives audio through a WebSocket.
2. Streams audio to Deepgram.
3. Receives speech-to-text results.
4. Streams the transcript back to the frontend.

---

## Generation

The generation service processes the completed transcript through a LangGraph-based AI pipeline.

The selected specialty determines the system prompt used for generation.

Prompts are stored in PostgreSQL and cached in Redis.

---

## Background Processing

Celery handles the heavier asynchronous operations.

Examples include:

* Clinical summary generation
* Session processing
* Archiving session data
* Prompt cache maintenance

Celery Beat periodically keeps the specialty prompt cache fresh.

---

# Backend Folder Structure

```text
backend/
└── app/
    ├── core/
    │   └── # Environment-backed configuration
    │
    ├── prompts/
    │
    ├── router/
    │   ├── auth/
    │   │   └── # OTP and service login
    │   │
    │   ├── admin/
    │   │   └── # Practices, providers, specialties
    │   │
    │   ├── visits/
    │   │   └── # WebSocket, transcription, processing, status
    │   │
    │   └── telemetry/
    │       └── # Usage and cost dashboards
    │
    ├── schemas/
    │   └── # API, Graph, MongoDB and PostgreSQL schemas
    │
    ├── services/
    │   ├── auth/
    │   │   └── # JWT, OTP and authentication database access
    │   │
    │   ├── celery/
    │   │   └── # Visit processing, MongoDB archival and Beat tasks
    │   │
    │   ├── redis/
    │   │   └── # Transcript, session, summary, OTP and cache stores
    │   │
    │   ├── mongo/
    │   │   └── # Archived session documents
    │   │
    │   ├── telemetry/
    │   │   └── # Usage and cost recording/querying
    │   │
    │   └── visits/
    │       ├── transcription/
    │       │   └── # WebSocket and Deepgram integration
    │       │
    │       ├── generation/
    │       │   └── # LangGraph pipeline and LLM calls
    │       │
    │       └── status/
    │           └── # Transcript and summary reads
    │
    └── utils/

main.py
```

---

# Running the Application

## Backend API

From the backend environment:

```bash
python -m backend.app.main
```

---

## Celery Worker

Start the Celery worker responsible for background generation:

```bash
celery -A backend.app.services.celery:celery_app worker --loglevel=info
```

---

## Celery Beat

Start Celery Beat for scheduled tasks such as specialty prompt cache maintenance:

```bash
celery -A backend.app.services.celery:celery_app beat --loglevel=info
```

---

## Frontend

From the frontend directory:

```bash
cd frontend
python -m main
```

---

# Data Storage

Scriber Agent uses multiple data stores, with each serving a different purpose.

```text
                    ┌──────────────┐
                    │   PostgreSQL  │
                    │              │
                    │ Auth         │
                    │ Providers    │
                    │ Practices    │
                    │ Specialties  │
                    │ Prompts      │
                    │ Telemetry    │
                    └──────────────┘

                    ┌──────────────┐
                    │    Redis     │
                    │              │
                    │ Sessions     │
                    │ Transcripts  │
                    │ Summaries    │
                    │ OTP          │
                    │ Prompt Cache │
                    └──────────────┘

                    ┌──────────────┐
                    │   MongoDB    │
                    │              │
                    │ Archived     │
                    │ Sessions     │
                    └──────────────┘
```

### PostgreSQL

Used for persistent application data such as:

* Authentication data
* Practices
* Providers
* Specialties
* System prompts
* Telemetry

### Redis

Used for fast-access and temporary data such as:

* Active sessions
* Transcripts
* Summaries
* OTP data
* Cached specialty prompts

Redis also acts as the Celery message broker.

### MongoDB

Used for archived session documents.

---

# Environment Configuration

The application requires environment-specific configuration for services such as:

* PostgreSQL
* Redis
* MongoDB
* Deepgram
* LLM provider
* Authentication
* Admin access
* Application configuration

The LLM provider can be selected using:

```text
USE_PROVIDER
```

Supported providers include:

```text
Google Gemini
Groq
```

Keep credentials and secrets outside the source code and provide them through the application's environment configuration.

---

# Full Backend Documentation

For a detailed, plain-language walkthrough of the backend architecture, transcription flow, AI generation pipeline, authentication, and data lifecycle, see:

```text
documents/README.md
```

---

# End-to-End Workflow

The complete application flow can be summarized as:

```text
┌──────────────────────┐
│       Provider       │
│       Login          │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│    Email + OTP       │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│        JWT           │
│ Practice / Provider  │
│      Specialty       │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│   Start Session      │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│   Chrome Extension   │
│  Microphone Capture  │
└──────────┬───────────┘
           │
           │ Audio
           ▼
┌──────────────────────┐
│   FastAPI WebSocket  │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│       Deepgram       │
│   Speech-to-Text     │
└──────────┬───────────┘
           │
           │ Live Transcript
           ▼
┌──────────────────────┐
│       Frontend       │
│ Live Transcription   │
└──────────┬───────────┘
           │
           │ Stop
           ▼
┌──────────────────────┐
│    Full Transcript   │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Celery Background   │
│      Processing      │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│   LangChain /        │
│   LangGraph Pipeline │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│   Gemini / Groq LLM  │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│   Six Summaries      │
│                      │
│ Quick Reference      │
│ Brief Summary        │
│ Goldilocks Summary   │
│ Detailed Summary     │
│ Super Detailed       │
│ SOAP Notes           │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│       Dashboard      │
│   Review Sessions    │
└──────────────────────┘
```

---

# Quick Start

### 1. Build the Chrome Extension

Generate the extension `dist` directory using the appropriate build script.

### 2. Load the Extension

Open:

```text
chrome://extensions/
```

Enable **Developer Mode**, select **Load Unpacked**, and choose:

```text
pronex_demo/chrome-extension/dist
```

### 3. Allow Microphone Access

Allow microphone access for the ScriberAgent extension.

### 4. Start Backend Services

Run:

```bash
python -m backend.app.main
```

Then start:

```bash
celery -A backend.app.services.celery:celery_app worker --loglevel=info
```

and:

```bash
celery -A backend.app.services.celery:celery_app beat --loglevel=info
```

### 5. Start Frontend

```bash
cd frontend
python -m main
```

### 6. Use Scriber Agent

```text
Login
  ↓
Start
  ↓
Speak with patient
  ↓
Live transcription
  ↓
Stop
  ↓
AI processing
  ↓
Review clinical summaries
  ↓
Access previous sessions from Dashboard
```

---

# Technology Summary

| Component                        | Technologies                       |
| -------------------------------- | ---------------------------------- |
| Browser Extension                | React, Vite, Chrome Extension APIs |
| Frontend                         | HTML, JavaScript                   |
| Backend                          | Python, FastAPI, Uvicorn           |
| Real-time Communication          | WebSocket                          |
| Speech-to-Text                   | Deepgram                           |
| AI Orchestration                 | LangChain, LangGraph               |
| LLM                              | Google Gemini / Groq               |
| Background Processing            | Celery, Celery Beat                |
| Cache / Broker                   | Redis                              |
| Authentication & Persistent Data | PostgreSQL                         |
| Session Archive                  | MongoDB                            |
| Browser                          | Google Chrome                      |

---

# Key Components

### Chrome Extension

Responsible for microphone access and audio capture required for real-time transcription.

### Frontend

Provides the application interface for authentication, live transcription, generated summaries, and historical sessions.

### Backend

Acts as the central service connecting the frontend, Chrome extension, Deepgram, AI models, databases, Redis, and background workers.

### Celery

Handles resource-intensive asynchronous processing, particularly the AI generation pipeline and archival operations.

### Deepgram

Converts the captured audio stream into real-time text.

### Gemini / Groq

Generates structured clinical summaries from completed transcripts.

### Redis

Provides fast-access session/cache storage and acts as the Celery broker.

### PostgreSQL

Stores authentication, provider, practice, specialty, prompt, and telemetry data.

### MongoDB

Stores archived session documents.
