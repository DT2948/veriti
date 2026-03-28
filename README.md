# Veriti

Privacy-first real-time crisis signal verification for Dubai.

## Quick Start

1. `cd backend`
2. `python -m venv .venv`
3. Activate the virtual environment.
4. `pip install -r requirements.txt`
5. Set environment variables as needed:
   - `GEMINI_API_KEY` for Gemini-powered summaries and incident classification
   - `DATABASE_URL` defaults to `sqlite:///veriti.db`
   - `UPLOAD_DIR` defaults to `uploads`
6. `python main.py`

The API will start on `http://localhost:8000` with interactive docs at `http://localhost:8000/docs`.

## API Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/v1/health` | Service health check |
| GET | `/api/v1/incidents` | List active incidents with optional confidence filter |
| GET | `/api/v1/incidents/map` | Lightweight incident payload for map rendering |
| GET | `/api/v1/incidents/{incident_id}` | Fetch one incident in full detail |
| POST | `/api/v1/submissions/upload` | Submit anonymous public media/text for verification |
| GET | `/api/v1/submissions/{submission_id}/status` | Check processing status for a submission |

## Architecture Overview

Veriti ingests anonymous public submissions and official alerts, normalizes and privacy-sanitizes them, verifies likely duplicates using perceptual hashing and embeddings, clusters related reports into incidents, computes a confidence tier, and optionally asks Gemini for careful summaries that avoid overstating uncertainty. The backend in this repository is designed as a runnable MVP monorepo skeleton, with placeholders for the future web dashboard and Android client.

## Repo Layout

- `backend/`: FastAPI backend, SQLAlchemy models, services, pipeline worker, and seed script
- `web/`: placeholder for the future Next.js dashboard
- `mobile/`: placeholder for the future Android app
- `docs/`: architecture and setup guides
