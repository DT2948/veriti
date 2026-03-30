# Veriti

> "We verify content, not identity."

**Author:** Darsh Tejusinghani  
**Event:** HackPSU Spring 2026

Veriti is a privacy-first, real-time crisis signal verification platform built for Dubai. It was designed for the information gap that opens during fast-moving emergencies, when official channels are slow, social feeds fill with recycled footage and rumor, and ordinary residents are left trying to decide what is real. Veriti accepts anonymous public submissions and official alerts, cross-validates them with AI, and turns fragmented signals into confidence-scored incidents on a live map. The goal is not just to collect reports, but to help people on the ground build a calmer, more trustworthy picture of what is actually happening around them.

**Devpost:** https://devpost.com/software/veriti

## Highlights

- Anonymous Android reporting flow with no account creation or login
- On-device privacy pipeline before upload
- AI-assisted media cross-validation and incident summarization
- Confidence-scored incident clustering across public and official signals
- Live web dashboard with map-based situational awareness
- Browser-played audio briefing generated from active incidents

## Tech Stack

- **Backend:** FastAPI, SQLAlchemy, SQLite, Gemini, ElevenLabs
- **Frontend:** Next.js, React, TypeScript, Tailwind CSS, Leaflet
- **Mobile:** Kotlin, Jetpack Compose, OkHttp, Android location/media APIs

---

## Table of Contents

- [Highlights](#highlights)
- [Tech Stack](#tech-stack)
- [The Problem](#the-problem)
- [The Solution](#the-solution)
- [How It Works](#how-it-works)
- [Architecture](#architecture)
- [Privacy Architecture](#privacy-architecture)
- [Confidence Scoring System](#confidence-scoring-system)
- [AI Pipeline](#ai-pipeline)
- [Incident Types](#incident-types)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)
- [Setup & Running](#setup--running)
- [Demo Script](#demo-script)
- [Acknowledgments](#acknowledgments)

---

## The Problem

During a fast-moving crisis, residents are hit with a flood of conflicting information: shaky videos, screenshots without context, recycled footage from older events, speculation, panic-driven reposts, and forwarded messages that are impossible to verify in the moment. Official channels matter, but they are often slower than the public stream and may not answer the immediate question people care about most: what is actually happening right now?

Dubai is a particularly compelling setting for this problem. It is a high-density, globally connected city with airports, ports, highways, towers, and large mixed-use districts packed tightly together. It also has a large expat population and a multilingual information environment, which means many residents may not be following the same official sources or may receive crisis information first through fragmented social channels, private group chats, or forwarded clips. In that gap between public signals and formal confirmation, Veriti is meant to provide a more trustworthy layer of situational awareness for ordinary residents trying to separate credible signals from noise.

---

## The Solution

Veriti’s approach is:

1. Anonymous public submission from Android
2. Privacy pipeline runs before the upload is sent
3. Backend verifies, clusters, and scores the signal
4. Live dashboard presents active incidents on a map
5. Operators can ingest official alerts to upgrade nearby public signals

> Core principle: **We verify content, not identity.**

The trust engine is deliberately multi-signal. A report is not judged by who sent it. Instead, Veriti combines independent submissions, duplicate detection, device trust, media presence, official overlap, and Gemini-based image/video cross-validation to compute a confidence score and assign a tier. The result is a system built for the messy middle of a crisis: not a replacement for emergency services, and not a rumor feed, but a way to turn scattered anonymous signals into a more usable, trust-scored view of reality.

---

## How It Works

### 1. Anonymous reporting on Android

The Android app is designed for speed under stress. A user can open the app, capture or choose media, optionally add a short note, select an incident type, and submit without creating an account or signing in.

### 2. On-device privacy pipeline runs before upload

Before anything leaves the phone, the app runs a local privacy pipeline. Images are stripped of identifying metadata, location is coarsened so exact coordinates are not uploaded, text notes are sanitized for obvious personal information, media is validated, and the app produces a local device trust score based on environmental heuristics rather than user identity. The goal is simple: reduce re-identification risk before the backend ever sees the report.

### 3. Submission payload sent to the backend

The app sends the sanitized report to the backend with media, coarse location, optional note text, and the local trust signals generated on-device.

### 4. Backend ingestion and verification pipeline

Once a submission reaches the backend, Veriti stores it, re-sanitizes it, and pushes it through a background verification pipeline. That pipeline handles duplicate detection, media analysis, incident-type inference, clustering into nearby ongoing incidents, confidence scoring, and summary generation. Raw uploaded media is removed after processing so the platform retains structured signal value without keeping unnecessary source files around.

### 5. Live dashboard

The web dashboard turns verified signals into a live operating picture. Active incidents are shown on a Dubai map, color-coded by confidence tier, with a feed of incident cards, summaries, confidence notes, and official-source context.

### 6. Official source ingestion

Operators can paste text from official statements into the dashboard. Veriti parses the alert, creates or merges the corresponding incident, and upgrades nearby public signals when they overlap with the official record.

### 7. Audio briefing

The dashboard can also generate an audio briefing. Active incidents are summarized into a spoken script, converted to speech, and played directly in the browser as a short situational update.

---

## Architecture

### Backend

Backend lives in `backend/` and uses:

- **FastAPI** for the API layer
- **Uvicorn** for serving
- **SQLAlchemy** with **SQLite** for persistence
- **Pydantic** for validation and schemas
- **google-genai** for Gemini integration
- **httpx** for ElevenLabs requests
- supporting libraries for uploads, hashing, image handling, and media processing

The backend is responsible for intake, privacy-aware preprocessing, AI verification, clustering, scoring, official alert ingestion, and audio briefing generation.

### Frontend

Frontend lives in `web/` and uses:

- **Next.js 14**
- **React 18**
- **TypeScript**
- **Leaflet** and **react-leaflet**
- **Tailwind CSS**

The web app is the live operations dashboard for viewing incidents, investigating their status, ingesting official alerts, and playing audio briefings.

### Mobile

Mobile lives in `mobile/android/` and uses:

- **Kotlin**
- **Jetpack Compose**
- **Material 3**
- **OkHttp**
- **AndroidX ExifInterface**
- **Google Play Services Location**

The Android app is the privacy-first reporting client. It handles anonymous capture, on-device sanitization, local trust scoring, and submission to the backend.

### AI / ML services

Veriti uses AI as a verification and interpretation layer rather than as a standalone source of truth:

- **Google Gemini** for media cross-validation, incident typing, summaries, confidence explanations, official-source parsing, and audio briefing script generation
- **ElevenLabs** for turning briefing scripts into spoken audio

### External APIs and services

- Gemini API
- ElevenLabs Text-to-Speech API
- OpenStreetMap tile server

### Architecture diagram

```text
Android App
  +-> FastAPI Backend
       +-> SQLite (incidents, submissions)
       +-> Gemini API
       +-> ElevenLabs API

Next.js Dashboard
  +-> FastAPI Backend
```

---

## Privacy Architecture

Privacy is Veriti's core design constraint. The platform is structured to verify what happened without asking who reported it.

### On-device protections

- image metadata is stripped before upload
- location is coarsened so the backend receives an area, not an exact personal coordinate
- text notes are sanitized for obvious personal identifiers
- media is validated before submission
- device integrity is scored using local heuristic checks rather than identity-based attestation
- selected files are copied into app-private storage before processing

### Backend protections

- uploaded images are scrubbed again and videos can have container metadata removed
- raw media is deleted after processing
- integrity tokens are reduced before long-term retention in the public submission flow
- rate limiting is in-memory and expires automatically
- there are no user accounts or persistent profile identifiers in the system design

### What is stored vs what is deleted

Veriti keeps the incident record, confidence data, sanitized note text, coarsened location, and lightweight verification signals needed to reason about whether a report is credible. It does not keep user accounts, profile identities, or long-term raw media after processing. That balance lets the system build situational awareness without turning submissions into a people-tracking dataset.

### Privacy audit summary

| Data point | Current handling | Privacy status |
| --- | --- | --- |
| User account | Not collected | Strong |
| Username / login | Not implemented | Strong |
| Exact GPS | Coarsened before storage | Protected |
| Image metadata | Removed before and during processing | Protected |
| Video metadata | Scrubbed during backend processing when available | Partial |
| Free-text self-identification | Best-effort redaction on device and backend | Partial |
| Device attestation payload | Reduced before long-term retention in public flows | Protected |
| Device trust signal | Stored only as a lightweight score | Low-risk |
| IP address | Used only for temporary in-memory rate limiting | Protected |
| Raw uploaded media | Deleted after processing | Protected |
| Duplicate matching signal | Reduced to similarity fingerprints | Low-risk |

---

## Confidence Scoring System

Veriti separates numeric confidence from tier labels so reports can improve over time as more signals arrive.

### Tiers

The backend emits these tiers:

- `unverified`
- `plausible`
- `corroborated`
- `official`

### How incidents move up

- a single report starts low
- multiple nearby reports raise confidence
- stronger supporting detail and media help
- duplicate or recycled content reduces confidence
- overlap with an official source upgrades the incident significantly
- Gemini media analysis can nudge the score up or down based on how well the evidence, caption, and location agree

This allows Veriti to keep a simple tier system for readability while still distinguishing stronger and weaker incidents within the same category.

---

## AI Pipeline

AI sits at the center of Veriti's verification layer.

- **Media cross-validation:** Gemini compares uploaded media, user caption, and claimed location to judge whether they align.
- **Incident typing:** Gemini helps classify reports into the platform's incident categories.
- **Summaries and explanations:** Incidents are described in plain language for the dashboard, along with readable confidence notes.
- **Official-source parsing:** Pasted official statements are converted into structured incident records.
- **Audio briefing generation:** Gemini writes a spoken briefing script, and ElevenLabs turns it into audio for the dashboard.

The goal is not to let AI replace human judgment. It is to help structure noisy signals into something readable, comparable, and easier to verify.

---

## Incident Types

Veriti groups reports into a small set of canonical incident types so public submissions, official alerts, and AI analysis can all resolve into the same incident model.

| Backend value | Meaning |
| --- | --- |
| `drone` | Drone-related activity or airborne threat language |
| `explosion` | Explosion or blast event |
| `debris` | Debris, rubble, or aftermath |
| `missile` | Explicit missile, rocket, or projectile language |
| `siren` | Siren or alarm event |
| `warning` | Warning, shelter, or alert language |
| `unknown` | Fallback when the signal is ambiguous |

---

## API Reference

All API routers are mounted under `/api/v1`.

### `GET /api/v1/health`

Simple health check for the backend service.

### `GET /api/v1/incidents`

Returns active incidents for the dashboard feed, including confidence, summaries, and map coordinates.

### `GET /api/v1/incidents/map`

Returns a lightweight incident payload for map rendering.

### `GET /api/v1/incidents/{incident_id}`

Returns a full incident record for detail views.

### `POST /api/v1/submissions/upload`

Accepts an anonymous public submission from the Android app. Reports are queued for background verification after upload.

### `GET /api/v1/submissions/{submission_id}/status`

Returns the current processing state of a previously uploaded submission.

### `POST /api/v1/official-alerts`

Parses pasted official-source text and creates or updates the corresponding official incident.

### `GET /api/v1/audio-briefing`

Generates and returns an MP3 audio briefing of active incidents for in-browser playback.

---

## Project Structure

```text
veriti/
+-- backend/        # FastAPI API, verification pipeline, AI services, persistence
+-- web/            # Next.js live dashboard
+-- mobile/android/ # Android reporting client
+-- docs/           # supplementary project notes
+-- README.md
```

---

## Setup & Running

### Prerequisites

- Python `3.11+`
- Node.js and npm for the dashboard
- Android Studio with an Android 8.0+ device or emulator
- `ffmpeg` if you want server-side video metadata scrubbing and video keyframe extraction

### Environment variables

Backend:

- `GEMINI_API_KEY`
- `ELEVENLABS_API_KEY`

Optional backend configuration such as database path, upload directory, grid size, and clustering thresholds can be adjusted in [`backend/config.py`](backend/config.py).

Frontend:

- `NEXT_PUBLIC_API_URL` optional, defaults to `http://localhost:8000`

Android:

- the app points to `http://localhost:8000` in the current development configuration

### Backend setup

```bash
cd backend
python -m venv .venv
```

Activate the environment, then:

```bash
pip install -r requirements.txt
python main.py
```

API will be available at:

```text
http://localhost:8000
```

Docs:

```text
http://localhost:8000/docs
```

Optional demo data:

```bash
python seed_data.py
```

### Frontend setup

```bash
cd web
npm install
npm run dev
```

Dashboard will run on the standard Next.js dev port unless overridden.

### Android setup

1. Open `mobile/android` in Android Studio
2. Sync Gradle
3. Connect a device or start an emulator
4. Run the `app` configuration

The app requires:

- camera permission for direct capture
- coarse location permission
- gallery read permission depending on Android version

### Connecting Android to a local backend

If the backend is running on your development machine and the phone is attached over ADB:

```bash
adb reverse tcp:8000 tcp:8000
```

That lets the phone resolve `http://localhost:8000` to your local FastAPI server.

---

## Acknowledgments

- HackPSU Spring 2026
- Google Gemini API
- ElevenLabs
- FastAPI
- SQLAlchemy
- Next.js
- React
- Leaflet / React Leaflet
- Jetpack Compose
- OkHttp
- Pillow
- imagehash
- NumPy
- OpenStreetMap contributors






