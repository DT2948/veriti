# Veriti Setup

## Prerequisites

- Python 3.11+
- `pip`

## Step-by-Step Setup

1. Move into the backend directory:
   - `cd backend`
2. Create and activate a virtual environment:
   - Windows PowerShell: `python -m venv .venv`
   - Windows PowerShell activate: `.\.venv\Scripts\Activate.ps1`
3. Install dependencies:
   - `pip install -r requirements.txt`
4. Configure environment variables as needed:
   - `GEMINI_API_KEY` for Gemini features
   - `DATABASE_URL=sqlite:///veriti.db`
   - `UPLOAD_DIR=uploads`
   - `MAX_UPLOAD_SIZE_MB=50`
   - `GRID_SIZE_METERS=500`
   - `CLUSTERING_TIME_WINDOW_MINUTES=30`
   - `EMBEDDING_SIMILARITY_THRESHOLD=0.7`
   - `DUPLICATE_HASH_THRESHOLD=5`
5. Start the API:
   - `python main.py`
6. Optional demo data:
   - `python seed_data.py`

## How to Run

The API starts on `http://localhost:8000`, Swagger UI is at `http://localhost:8000/docs`, and the OpenAPI JSON is at `http://localhost:8000/openapi.json`.

## Curl Examples

Health check:

```bash
curl http://localhost:8000/api/v1/health
```

List incidents:

```bash
curl "http://localhost:8000/api/v1/incidents?limit=20&offset=0"
```

Map incidents:

```bash
curl http://localhost:8000/api/v1/incidents/map
```

Get one incident:

```bash
curl http://localhost:8000/api/v1/incidents/<incident_id>
```

Upload a text-only submission:

```bash
curl -X POST "http://localhost:8000/api/v1/submissions/upload" \
  -F "text_note=Heard repeated sirens near Dubai Marina" \
  -F "latitude=25.0832" \
  -F "longitude=55.1403"
```

Upload a media submission:

```bash
curl -X POST "http://localhost:8000/api/v1/submissions/upload" \
  -F "file=@sample.jpg" \
  -F "text_note=Smoke visible from Sheikh Zayed Road" \
  -F "latitude=25.2048" \
  -F "longitude=55.2708" \
  -F "device_trust_score=0.81"
```

Check submission status:

```bash
curl http://localhost:8000/api/v1/submissions/<submission_id>/status
```
