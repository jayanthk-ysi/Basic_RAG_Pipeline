# AI Physiotherapy Call Agent

A demo-ready AI voice calling system for physiotherapy clinics that calls patients, uses structured dummy data, and persists appointments to JSON.

## Project structure

```
project/
├── connect_call.py              # Standalone Retell outbound call (run from project root)
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── backend/
│   ├── main.py                  # FastAPI app
│   ├── config.py                # Paths & settings (override via env)
│   ├── retell_service.py      # Retell AI SDK wrapper
│   ├── patient_details.json    # Patients (phone, DOB, provider, missed days)
│   ├── provider_details.json   # Per-weekday hourly grid 09:00–18:00 (0=free, 1=booked)
│   ├── appointments.json       # Saved appointments (append-only)
│   ├── call_logs.json          # Call / webhook logs
│   └── requirements.txt
└── README.md
```

## Tech stack

- **Backend**: Python, FastAPI
- **Frontend**: static HTML/CSS/JS in `frontend/` (served by FastAPI from project root)
- **Voice**: [Retell AI Python SDK](https://github.com/RetellAI/retell-python-sdk) (`retell-sdk` on PyPI)
- **Telephony**: Telnyx number configured in the **Retell** dashboard (no Telnyx code in this repo)

## Configuration (environment variables)

| Variable | Purpose |
|----------|---------|
| `RETELL_API_KEY` | Retell API key (required for real calls) |
| `RETELL_AGENT_ID` | Agent to use (`override_agent_id`); optional if default is set in Retell |
| `PATIENT_DETAILS_PATH` | Override path to patient JSON (default: `backend/patient_details.json`) |
| `PROVIDER_DETAILS_PATH` | Override path to provider availability JSON |
| `APPOINTMENTS_PATH` | Override path to appointments output JSON |
| `CALL_LOGS_PATH` | Override path to call logs JSON |
| `FRONTEND_DIR` | Override path to static frontend (default: `frontend/` next to `backend/`) |

## Setup

```bash
cd backend
pip install -r requirements.txt
```

Set environment variables (PowerShell example):

```powershell
$env:RETELL_API_KEY = "your_key"
$env:RETELL_AGENT_ID = "your_agent_id"
```

## Run the API + UI

From `backend/`:

```bash
python main.py
```

or:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` — the UI is served from `frontend/`.

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/patients` | List `patient_details.json` |
| POST | `/make-call` | Body: `{"phone": "+91..."}`. Looks up patient, starts Retell call. Response includes `status: "call generated"`. |
| GET | `/providers/availability` | Full provider records + weekly slot grids |
| POST | `/appointments` | Saves one appointment to `appointments.json` |
| GET | `/appointments` | Lists saved appointments |
| POST | `/retell-webhook` | Retell webhook receiver |
| GET | `/call-status?phone=...` | In-memory status for last active call per phone |
| GET | `/transcripts` | Reads `call_logs.json` |

## Standalone call script

From the **project root** (same folder as `connect_call.py`):

```bash
python connect_call.py +919876543210
```

Optional metadata flags: `--patient-name`, `--provider-name`, `--missed-days`.

Requires `RETELL_API_KEY` (and usually `RETELL_AGENT_ID`).

## Retell + Telnyx

1. Create an agent in Retell and assign your **Telnyx** number in the Retell dashboard (see Retell/Telnyx docs or your setup video).
2. Put the API key (and agent id if needed) in the environment as above.
3. Patient numbers in `patient_details.json` must be callable from your Telnyx/Retell configuration (E.164 recommended).

## Notes

- Demo UI includes a **simulated transcript** for local testing; production transcripts depend on webhooks and a public URL.
- This project is for demonstration only: add auth, a real database, and stricter validation before production use.

## License

Demonstration use only.