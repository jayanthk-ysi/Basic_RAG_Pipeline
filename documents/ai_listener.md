# Healthcare Conversational AI Demo

A minimal healthcare chat application built with a FastAPI backend and a static frontend. The app lets a user interact with an AI assistant and receive a structured clinical summary at the end of the conversation.

## Project Structure

```
AI_listener_poc/
├── README.md
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── router/
│   │   │   └── api.py
│   │   ├── schemas/
│   │   │   └── models.py
│   │   ├── services/
│   │   │   ├── conversation_chain.py
│   │   │   ├── llm.py
│   │   │   └── summary_chain.py
│   │   └── prompts/
│   │       └── prompts.py
│   └── requirements.txt
└── frontend/
    ├── index.html
    ├── style.css
    └── app.js
```

## Architecture Overview

The project has two main parts:

- `backend/`: FastAPI service that exposes two API endpoints and routes requests to the AI model.
- `frontend/`: Static HTML/CSS/JavaScript client that sends user messages and renders AI responses.

### Backend architecture

1. `backend/app/main.py`
   - Creates the FastAPI application.
   - Configures CORS to allow requests from the frontend.
   - Loads the Groq LLM via `app.services.llm.get_llm()`.
   - Builds two chains:
     - `conversation_chain` for interactive chat.
     - `summary_chain` for final structured summaries.
   - Injects these chain objects into `app.router.api` before including the router.

2. `backend/app/router/api.py`
   - Defines two POST endpoints:
     - `POST /chat` for conversational replies.
     - `POST /summary` for structured summary generation.
   - Uses shared chain objects to invoke the LLM.
   - Converts incoming conversation history into plain text for prompt formatting.

3. `backend/app/services/llm.py`
   - Creates a `ChatGroq` client for Groq model access.
   - Reads model configuration from environment variables when available.
   - Returns an LLM object used by both conversation and summary chains.

4. `backend/app/services/conversation_chain.py`
   - Builds the chat prompt using `app.prompts.prompts.build_chat_prompt()`.
   - Sends the formatted conversation history and latest patient message to the LLM.
   - Returns the assistant reply.

5. `backend/app/services/summary_chain.py`
   - Builds the summary prompt using `app.prompts.prompts.build_summary_prompt()`.
   - Sends the full conversation history to the LLM.
   - Expects JSON output that matches `SummaryResponse`.

6. `backend/app/schemas/models.py`
   - Defines request/response models with Pydantic.
   - `ChatRequest` requires `message` and `conversation_history`.
   - `SummaryRequest` requires only `conversation_history`.
   - `SummaryResponse` defines structured summary fields.

### Frontend architecture

- `frontend/index.html`
  - Contains the chat UI and summary panel.
- `frontend/style.css`
  - Styles the chat window, buttons, and summary display.
- `frontend/app.js`
  - Manages conversation state in `conversationHistory`.
  - Sends chat requests to `http://localhost:8004/chat`.
  - Sends summary requests to `http://localhost:8004/summary` when the user types a termination keyword.
  - Renders messages and the final summary in the browser.

## API Reference

### `POST /chat`

- Description: Sends the current message and conversation history to the AI assistant.
- Request body:
  - `message` (string): Latest user message.
  - `conversation_history` (array of messages): Chat history so far.
    - Each message includes `role` and `content`.
- Response body:
  - `reply` (string): Assistant response text.

Example request:

```json
{
  "message": "I have a headache today.",
  "conversation_history": [
    {"role": "assistant", "content": "Hello, how have you been feeling since your last check-in?"}
  ]
}
```

Example response:

```json
{
  "reply": "I am sorry to hear that. Can you describe the headache intensity and any other symptoms?"
}
```

### `POST /summary`

- Description: Sends the full conversation history to the summary model and returns a structured clinical summary.
- Request body:
  - `conversation_history` (array of messages): The complete chat history.
- Response body: Structured summary fields:
  - `patient_progress` (string)
  - `current_symptoms` (array of strings)
  - `pain_level` (string)
  - `functional_status` (string)
  - `exercise_adherence` (string)
  - `medication_concerns` (string)
  - `new_symptoms` (array of strings)
  - `patient_concerns` (array of strings)
  - `clinical_summary` (string)

Example request:

```json
{
  "conversation_history": [
    {"role": "assistant", "content": "Hello, how have you been feeling since your last check-in?"},
    {"role": "user", "content": "I have been sore and tired."}
  ]
}
```

Example response:

```json
{
  "patient_progress": "Patient reports slight improvement in symptoms.",
  "current_symptoms": ["soreness", "fatigue"],
  "pain_level": "Mild to moderate",
  "functional_status": "Able to perform daily activities with some discomfort.",
  "exercise_adherence": "Patient is maintaining exercise, but with reduced intensity.",
  "medication_concerns": "None reported.",
  "new_symptoms": ["none"],
  "patient_concerns": ["ongoing soreness"],
  "clinical_summary": "The patient reports persistent soreness and fatigue after their last visit. Continue monitoring and adjust therapy if symptoms worsen."
}
```

## Setup

1. Open a terminal in `backend/`.
2. Create and activate a Python virtual environment:

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
```

3. Install dependencies:

```powershell
pip install -r requirements.txt
```

4. Create a `.env` file in `backend/` with your Groq API configuration:

```text
GROQ_API_KEY=your_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

5. Start the backend service:

```powershell
uvicorn main:app --reload --host 0.0.0.0 --port 8004
```

6. In a second terminal, serve the frontend:

```powershell
cd frontend
python -m http.server 8080
```

7. Open the frontend in your browser:

```text
http://localhost:8080
```

## How it works

- The frontend sends the user text to `/chat`.
- The backend converts the full `conversation_history` into a text prompt.
- The AI assistant responds and the frontend displays that reply.
- When the user sends a termination keyword (`done`, `finish`, `end conversation`), the frontend calls `/summary`.
- The backend returns a JSON summary with clinical fields.

## Notes

- This app stores chat history only in the browser memory and does not persist data.
- The summary endpoint expects valid JSON from the model; if the model responds with invalid JSON, the backend returns a 500 error.
- `backend/app/services/llm.py` is responsible for creating the Groq client.
- `frontend/app.js` defines the API endpoints used by the UI.