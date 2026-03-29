# Veriti

> "We verify content, not identity."

**Author:** Darsh Tejusinghani  
**Event:** HackPSU Spring 2026

Veriti is a privacy-first, real-time crisis signal verification platform built for Dubai. It accepts anonymous public submissions and official alerts, cross-validates them with AI, and turns fragmented signals into confidence-scored incidents on a live map. The project is designed for the information gap that opens during emergencies: rumors move fast, recycled footage spreads faster, and official channels often lag behind the crowd. Veriti’s answer is simple: sanitize what people share, verify the content itself, and present a clearer picture of what is happening on the ground.

---

## Table of Contents

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

During a fast-moving crisis, residents are hit with a flood of conflicting information: shaky videos, screenshots without context, recycled footage from older events, speculation, and panic-driven reposts. Official channels matter, but they are often slower than the public stream and may not answer the immediate question people care about most: what is actually happening right now?

Dubai is a particularly compelling setting for this problem. It is a high-density, globally connected city with airports, ports, highways, towers, and large mixed-use districts packed tightly together. It also has a large expat population and a multilingual information environment, which means many residents may not be following the same official sources or may receive crisis information through fragmented social channels first. In that gap between public signals and formal confirmation, Veriti aims to provide a calmer, more trustworthy layer of situational awareness.

---

## The Solution

Veriti’s approach is:

1. Anonymous public submission from Android
2. Privacy pipeline runs before the upload is sent
3. Backend verifies, clusters, and scores the signal
4. Live dashboard presents active incidents on a map
5. Operators can ingest official alerts to upgrade nearby public signals

> Core principle: **We verify content, not identity.**

The trust engine is deliberately multi-signal. A report is not judged by who sent it. Instead, Veriti combines independent submissions, duplicate detection, device trust, media presence, official overlap, and Gemini-based image/video cross-validation to compute a confidence score and assign a tier. That lets weaker single-source claims stay visible but clearly labeled, while better-supported incidents rise in confidence as evidence accumulates.

---

## How It Works

### 1. Anonymous reporting on Android

The Android app is a single-screen Jetpack Compose client rooted at [`mobile/android/app/src/main/java/com/veriti/app/ui/ReportScreen.kt`](mobile/android/app/src/main/java/com/veriti/app/ui/ReportScreen.kt). There is no account system, no login screen, and no persistent user identity model in the mobile code or backend schema.

The user can:

- take a photo with the camera
- choose media from the gallery
- optionally add a text note
- pick an incident category from the UI chips

The Android chip labels are:

- `Drone-related`
- `Explosion`
- `Debris`
- `Siren/Warning`
- `Missile-related`
- `Structural Damage`
- `Other`

Those chips map to backend values through [`ReportScreen.kt`](mobile/android/app/src/main/java/com/veriti/app/ui/ReportScreen.kt), but the backend currently only recognizes the canonical incident types listed later in this README.

### 2. On-device privacy pipeline runs before upload

The app runs a local processing pipeline in [`LocalPipeline.kt`](mobile/android/app/src/main/java/com/veriti/app/pipeline/LocalPipeline.kt) before upload is prepared.

#### EXIF metadata stripping

Implemented in [`ExifStripper.kt`](mobile/android/app/src/main/java/com/veriti/app/pipeline/ExifStripper.kt).

For images, the app copies the selected media into app-private storage and removes these EXIF tags:

- `GPS_LATITUDE`
- `GPS_LONGITUDE`
- `GPS_ALTITUDE`
- `GPS_LATITUDE_REF`
- `GPS_LONGITUDE_REF`
- `MAKE`
- `MODEL`
- `DATETIME`
- `DATETIME_ORIGINAL`
- `DATETIME_DIGITIZED`
- `SOFTWARE`
- `IMAGE_UNIQUE_ID`

For videos, the mobile pipeline currently copies the file into app-private storage but does **not** scrub container metadata on-device. The code explicitly marks broader mobile video metadata scrubbing as a TODO in [`LocalPipeline.kt`](mobile/android/app/src/main/java/com/veriti/app/pipeline/LocalPipeline.kt).

#### Location coarsening

Implemented in [`LocationCoarsener.kt`](mobile/android/app/src/main/java/com/veriti/app/pipeline/LocationCoarsener.kt).

The app requests `ACCESS_COARSE_LOCATION`, fetches a balanced-accuracy location from Google Play Services, then rounds latitude and longitude to `0.0045` degree steps before upload. That is the mobile-side approximation layer.

The backend also coarsens coordinates again using [`backend/utils/location.py`](backend/utils/location.py), where the default grid is `500` meters (`GRID_SIZE_METERS`, configurable in `config.py`). The backend assigns a durable `grid_cell` in the form:

```text
grid_<lat_index>_<lng_index>
```

#### Media validation

Implemented in [`MediaValidator.kt`](mobile/android/app/src/main/java/com/veriti/app/pipeline/MediaValidator.kt).

Checks performed locally:

- file exists
- file size must be `<= 50MB`
- media header must match a supported image or video type
- SHA-256 hash is computed
- exact same media is flagged if already selected earlier in the same app session
- images must be at least `100x100`
- images must decode successfully
- images must have more than one sampled color to avoid blank/solid-color uploads
- videos must be at least `100x100`

Supported signatures include:

- images: JPEG, PNG, WEBP, BMP
- videos: MP4/MOV (`ftyp`), Matroska/WebM, AVI

#### Device integrity assessment

Implemented in [`IntegrityChecker.kt`](mobile/android/app/src/main/java/com/veriti/app/pipeline/IntegrityChecker.kt).

This no longer depends on Google Play Integrity. Instead, it computes a local heuristic `device_trust_score` from six signals:

- **Emulator detection** (`weight 0.25`)
  - checks `Build.FINGERPRINT` for `generic` or `unknown`
  - checks `Build.MODEL` for `google_sdk`, `Emulator`, or `Android SDK`
  - checks `Build.MANUFACTURER` for `Genymotion`
  - checks `Build.HARDWARE` for `goldfish` or `ranchu`
  - checks `Build.PRODUCT` for `sdk`, `google_sdk`, or `sdk_x86`
- **Root detection** (`weight 0.20`)
  - checks for:
    - `/system/app/Superuser.apk`
    - `/system/xbin/su`
    - `/sbin/su`
    - `/data/local/xbin/su`
    - `/data/local/bin/su`
  - also attempts `which su`
- **Debugger detection** (`weight 0.15`)
  - `Debug.isDebuggerConnected()`
  - `ApplicationInfo.FLAG_DEBUGGABLE`
- **Install source** (`weight 0.15`)
  - Play Store: `com.android.vending`
  - Amazon Appstore: `com.amazon.venezia`
  - sideload / shell / null installer lowers the score
- **Overlay risk** (`weight 0.10`)
  - `Settings.canDrawOverlays(context)`
  - scans installed packages for `SYSTEM_ALERT_WINDOW`
- **Mock location risk** (`weight 0.15`)
  - checks `Settings.Secure.ALLOW_MOCK_LOCATION`
  - scans installed packages for `ACCESS_MOCK_LOCATION`

The composite score is:

```text
(emulator * 0.25) +
(root * 0.20) +
(debugger * 0.15) +
(install * 0.15) +
(overlay * 0.10) +
(mock_location * 0.15)
```

It is rounded to two decimal places. The app also generates a transparent local integrity token such as:

```text
local-v1|em:0|rt:0|db:1|is:side|ol:0|ml:0|ts:0.72
```

The UI shows:

- `Device integrity: Strong`
- `Device integrity: Moderate`
- `Device integrity: Weak`

#### PII redaction in text notes

There are two sanitizers in the system.

On-device sanitization happens in [`TextSanitizer.kt`](mobile/android/app/src/main/java/com/veriti/app/pipeline/TextSanitizer.kt), which redacts:

- emails
- phone numbers
- phrases matching `my name is <name>`

It replaces with:

- `[redacted-email]`
- `[redacted-phone]`
- `my name is [redacted]`

and truncates text to `500` characters.

The backend sanitizes again in [`backend/utils/privacy.py`](backend/utils/privacy.py) using these regex classes:

- emails
- phone numbers
- social handles like `@username`
- self-identifying phrases such as:
  - `My name is ...`
  - `This is ...`
  - `I am ...`
  - `I'm ...`

Backend replacements use `[redacted]`.

#### Video metadata scrubbing

Actual metadata scrubbing for videos is implemented on the backend in [`backend/utils/media.py`](backend/utils/media.py), not on-device.

When a video upload reaches the backend, `scrub_video_metadata()` uses `ffmpeg` with:

```text
-map_metadata -1
-c copy
```

This removes container metadata without re-encoding the streams. If `ffmpeg` is missing, the backend logs a warning and continues.

### 3. Submission payload sent to the backend

The Android client constructs a multipart form in [`ApiClient.kt`](mobile/android/app/src/main/java/com/veriti/app/network/ApiClient.kt).

It currently sends these fields:

- `file`
- `text_note`
- `latitude`
- `longitude`
- `device_trust_score`
- `integrity_token`
- `incident_type`

The backend endpoint in [`backend/api/submissions.py`](backend/api/submissions.py) consumes:

- `file`
- `text_note`
- `latitude`
- `longitude`
- `device_trust_score`
- `integrity_token`

`incident_type` is sent by the Android app but is not part of the FastAPI form signature at the upload endpoint.

### 4. Backend ingestion and verification pipeline

The upload endpoint:

- applies short-lived in-memory rate limiting
- stores the upload in `uploads/`
- strips image EXIF again or scrubs video metadata
- sanitizes text
- coarsens location to the backend grid
- creates a `Submission` row
- queues `run_verification_pipeline()` as a background task

The worker lives in [`backend/workers/pipeline.py`](backend/workers/pipeline.py).

#### Duplicate detection via perceptual hashing

Handled in [`backend/services/verification_service.py`](backend/services/verification_service.py).

For image submissions:

- `compute_phash()` from [`backend/utils/hashing.py`](backend/utils/hashing.py) generates a perceptual hash
- the hash is compared against prior image submissions
- duplicates are identified by Hamming distance using the configured threshold (`DUPLICATE_HASH_THRESHOLD`, default `5`)
- duplicate submissions inherit the original `duplicate_group_id`

Videos do not get perceptual hashing in the current backend pipeline.

#### Embeddings

Also in [`verification_service.py`](backend/services/verification_service.py).

The backend currently stores a synthetic `512`-dimension vector generated from file bytes as a placeholder. The code explicitly marks this as a TODO to replace with CLIP or multimodal embeddings in production.

#### Gemini Vision cross-validation

Implemented in [`backend/services/gemini_service.py`](backend/services/gemini_service.py).

For images:

- image is loaded and resized if needed
- Gemini extracts concrete visual evidence into structured JSON
- that evidence is synthesized with:
  - the caption
  - claimed coordinates
  - inferred neighborhood name

For videos:

- `ffmpeg` extracts up to `3` frames at `fps=1/2`
- those frames are fed through the same evidence and synthesis flow

The cross-validation output includes:

- `media_description`
- `detected_incident_type`
- `severity_estimate`
- `visible_landmarks`
- `inferred_location`
- `plausibility`
- `cross_validation`
  - `caption_media_match`
  - `location_media_match`
  - `caption_location_match`
  - `overall_consistency`
  - `explanation`
- `trust_modifier`
- `inferred_data`

The worker may override the report’s stored location if Gemini strongly points to a known Dubai place and the claimed location is implausible or inconsistent. That location override uses [`resolve_known_location()`](backend/utils/dubai_locations.py) plus the same backend coarsening grid.

#### Incident type classification

There are two classification paths:

- Gemini-based `extract_incident_type()` in [`gemini_service.py`](backend/services/gemini_service.py)
- fallback keyword matching if Gemini fails

Special handling prefers `drone` over `missile` for generic strike language unless explicit missile or rocket evidence exists.

#### Clustering engine

Implemented in [`backend/services/clustering_service.py`](backend/services/clustering_service.py).

Reports are grouped in this order:

1. if perceptual hash matches an existing submission already linked to an incident, join that incident
2. otherwise, look for nearby active incidents in the same `grid_cell` within the configured time window (`CLUSTERING_TIME_WINDOW_MINUTES`, default `30`)
3. if none match, create a new incident

Nearby incident search is based on:

- same backend `grid_cell`
- `timestamp_last_updated >= now - time_window`
- `is_active == True`

#### Confidence scoring

Implemented in [`backend/services/scoring_service.py`](backend/services/scoring_service.py).

Scoring combines:

- report count
- number of independent evidence groups
- average device trust score
- media presence
- detail level in notes
- duplicate penalty
- official overlap

Gemini’s media analysis can then apply a bounded `trust_modifier` in the worker:

- clamped to `[-0.3, 0.3]` in `gemini_service.py`
- added to the incident score in `workers/pipeline.py`

#### Summary generation

`generate_incident_summary()` in [`gemini_service.py`](backend/services/gemini_service.py) produces a factual `2-3` sentence incident summary using:

- incident type
- location
- report notes
- report count
- time range
- confidence tier
- media analysis context

If Gemini fails, the backend uses a fallback summary generator.

#### Confidence explanation generation

`generate_confidence_explanation()` asks Gemini to explain the tier in `1-2` plain-language sentences without exposing internal numeric mechanics. It also has a rule-based fallback.

#### Raw media deletion

After processing finishes, [`workers/pipeline.py`](backend/workers/pipeline.py) deletes the raw uploaded media file from `UPLOAD_DIR` in a `finally` block using [`delete_raw_media()`](backend/utils/media.py).

### 5. Live dashboard

The web dashboard is a Next.js app rooted at [`web/app/page.tsx`](web/app/page.tsx).

It:

- polls active incidents every `5` seconds in [`useIncidents.ts`](web/hooks/useIncidents.ts)
- renders a Leaflet map centered on Dubai (`25.2048, 55.2708`)
- colors markers by confidence tier
- shows an incident feed, popup details, verification notes, and confidence score
- supports operator-side official source ingestion
- supports browser-side audio playback for the generated briefing

### 6. Official source ingestion

The operator workflow is:

1. paste a tweet or statement into the dashboard panel
2. frontend calls `POST /api/v1/official-alerts`
3. Gemini parses the text into structured incident data
4. backend either:
   - merges it into a nearby public incident, or
   - creates a new official incident
5. nearby public incidents in adjacent grid cells can be marked with `official_overlap`

Official ingestion is implemented across:

- [`web/components/OfficialSourcePanel.tsx`](web/components/OfficialSourcePanel.tsx)
- [`backend/api/official_alerts.py`](backend/api/official_alerts.py)
- [`backend/services/gemini_service.py`](backend/services/gemini_service.py)
- [`backend/services/ingestion_service.py`](backend/services/ingestion_service.py)

### 7. Audio briefing

The dashboard `Audio briefing` button in [`Header.tsx`](web/components/Header.tsx) fetches `GET /api/v1/audio-briefing`, receives an MP3 blob, and plays it with the browser `Audio` API.

The backend:

- queries active incidents
- asks Gemini to write a spoken script
- sends that script to ElevenLabs
- returns `audio/mpeg`

---

## Architecture

### Backend

Backend lives in `backend/` and uses:

- **FastAPI** for HTTP API
- **Uvicorn** for serving
- **SQLAlchemy** for ORM and SQLite access
- **Pydantic** for request/response models
- **python-multipart** for file uploads
- **Pillow** for image handling
- **imagehash** for perceptual hashing
- **numpy** for placeholder embeddings and similarity math
- **google-genai** for Gemini access
- **python-dotenv** for environment loading
- **aiofiles** for async upload writing
- **httpx** for ElevenLabs HTTP calls

Database defaults to SQLite via:

```text
sqlite:///veriti.db
```

### Frontend

Frontend lives in `web/` and uses:

- **Next.js 14**
- **React 18**
- **TypeScript**
- **Leaflet**
- **react-leaflet**
- **Tailwind CSS**

Map tiles currently come from the default OpenStreetMap tile server.

### Mobile

Mobile lives in `mobile/android/` and uses:

- **Jetpack Compose**
- **Material 3**
- **Kotlin coroutines**
- **OkHttp**
- **AndroidX ExifInterface**
- **Google Play Services Location**
- **Android FileProvider**

The Gradle config still includes the Play Integrity dependency:

- `com.google.android.play:integrity:1.4.0`

but the current device trust implementation no longer uses the Play Integrity API in the app code.\r\n\r\n### AI / ML services

Actual external AI services in use:

- **Google Gemini (`gemini-2.5-flash`)**
  - image/video evidence extraction
  - cross-validation synthesis
  - incident type classification
  - incident summary generation
  - confidence explanation generation
  - official source parsing
  - audio briefing script generation
- **ElevenLabs**
  - text-to-speech for dashboard audio briefings

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

Privacy is Veriti’s sharpest product decision. The system is built around minimizing identity exposure while still preserving enough structure to evaluate whether a report is useful.

### On-device protections

| Measure | What it does | Where |
| --- | --- | --- |
| EXIF stripping | Removes GPS, device make/model, timestamps, software, and image unique ID for images | [`ExifStripper.kt`](mobile/android/app/src/main/java/com/veriti/app/pipeline/ExifStripper.kt) |
| Location coarsening | Rounds location to `0.0045` degree steps before upload | [`LocationCoarsener.kt`](mobile/android/app/src/main/java/com/veriti/app/pipeline/LocationCoarsener.kt) |
| Media validation | Validates size, type, resolution, decodability, entropy, and exact-session duplicates | [`MediaValidator.kt`](mobile/android/app/src/main/java/com/veriti/app/pipeline/MediaValidator.kt) |
| PII redaction | Redacts emails, phone numbers, and `my name is ...` patterns, truncates to `500` chars | [`TextSanitizer.kt`](mobile/android/app/src/main/java/com/veriti/app/pipeline/TextSanitizer.kt) |
| Device integrity heuristics | Scores emulator, root, debugger, installer, overlay, and mock-location signals | [`IntegrityChecker.kt`](mobile/android/app/src/main/java/com/veriti/app/pipeline/IntegrityChecker.kt) |
| Private file copy | Selected media is copied into app-private storage before processing | [`ExifStripper.kt`](mobile/android/app/src/main/java/com/veriti/app/pipeline/ExifStripper.kt) |

### Backend protections

| Measure | What it does | Where |
| --- | --- | --- |
| Server-side image scrub | Rewrites image pixel data to remove metadata for supported formats | [`utils/privacy.py`](backend/utils/privacy.py) |
| Server-side video metadata scrub | Uses `ffmpeg -map_metadata -1 -c copy` | [`utils/media.py`](backend/utils/media.py) |
| Raw media deletion | Deletes uploaded raw media after verification attempt completes | [`workers/pipeline.py`](backend/workers/pipeline.py), [`utils/media.py`](backend/utils/media.py) |
| Integrity token sanitization | Stores `provided` or `missing` instead of raw attestation token for normal public submissions | [`services/verification_service.py`](backend/services/verification_service.py) |
| In-memory rate limiting | Uses IP address only in memory for temporary upload throttling | [`utils/rate_limiter.py`](backend/utils/rate_limiter.py) |
| No account model | No user table, auth flow, or persistent identity layer exists | backend schema |

### What is stored vs what is deleted

#### Stored in the database

`submissions` table stores:

- `id`
- `incident_id`
- `source_type`
- `media_type`
- `media_path`
- `text_note` (sanitized)
- `latitude` (coarsened)
- `longitude` (coarsened)
- `grid_cell`
- `submitted_at`
- `device_trust_score`
- `integrity_token` (sanitized for public verification flow)
- `duplicate_group_id`
- `perceptual_hash`
- `embedding_vector`
- `verification_status`
- `anonymous_token` (currently `None`)
- `processed_at`
- `created_at`

`incidents` table stores:

- `id`
- `type`
- `title`
- `summary`
- `source_type`
- `confidence_tier`
- `confidence_score`
- `latitude`
- `longitude`
- `grid_cell`
- `timestamp_first_seen`
- `timestamp_last_updated`
- `number_of_reports`
- `official_overlap`
- `media_count`
- `tags`
- `verification_notes`
- `is_active`
- `created_at`
- `updated_at`

#### Deleted or discarded

- raw uploaded media file after processing
- original image EXIF metadata
- original video container metadata when `ffmpeg` is available
- raw public integrity token payload after scoring
- transient IP rate-limit timestamps once the in-memory window expires

#### Why retained fields are lower-risk

- location is stored in coarsened form, not precise GPS
- text notes are sanitized before persistence
- no account, phone number, email, or username is part of the schema
- no IP address is written to the database
- device trust is stored as a float, not a device identifier
- integrity token is reduced to a status string for public submissions after verification

### Privacy audit summary

| Data point | Current handling | Privacy status |
| --- | --- | --- |
| User account | Not collected | Strong |
| Username / login | Not implemented | Strong |
| Exact GPS | Coarsened before storage | Protected |
| Image EXIF GPS/device metadata | Removed on device, and images are scrubbed again server-side | Protected |
| Video container metadata | Scrubbed server-side if `ffmpeg` is available | Partial |
| Free-text self-identification | Best-effort regex redaction on device and backend | Partial |
| Device attestation payload | Not retained raw for public submissions | Protected |
| Device trust signal | Stored as numeric trust score | Low-risk |
| IP address | Used only in temporary in-memory rate limiting | Protected |
| Raw uploaded media | Deleted after processing | Protected |
| Duplicate matching signal | Perceptual hash retained for images | Low-risk |
| Embedding vector | Placeholder 512-float vector retained | Low-risk but present |

---

## Confidence Scoring System

### Actual emitted tiers

The backend scoring code in [`backend/services/scoring_service.py`](backend/services/scoring_service.py) emits these tiers:

- `unverified`
- `plausible`
- `corroborated`
- `official`

`confirmed` is **not** assigned by the backend scoring engine. It only appears as an extra marker style key in [`web/components/MapMarker.tsx`](web/components/MapMarker.tsx).

### Tier escalation logic

Tier assignment is currently based on report structure, not directly on numeric score:

- `official` if `official_overlap` is true
- `corroborated` if `number_of_reports >= 3`
- `plausible` if `number_of_reports >= 2`
- `unverified` otherwise

### Score formula

The numeric score is computed as:

```text
score =
  base_score
  + trust_adjustment
  + media_bonus
  + detail_bonus
  - duplicate_penalty
```

Where:

- `base_score`
  - `0.9` if official overlap
  - `0.65` if report count >= 5
  - `0.5` if report count >= 3
  - `0.35` if report count == 2
  - `0.15` if only one report
- `trust_adjustment = (avg_device_score - 0.5) * 0.2`
- `media_bonus = 0.08` if any linked submission has media
- `detail_bonus = min(0.1, 0.03 per detailed note with at least 8 words)`
- `duplicate_penalty = min(0.08, (report_count - distinct_group_count) * 0.01)`

The score is clamped to `[0.1, 1.0]`, rounded to three decimals, and then the tier is assigned separately.

### Official overlap

If an incident overlaps with an official source:

- tier becomes `official`
- score floor becomes `0.9`
- verification notes reflect the official corroboration

### Gemini trust modifier

Gemini media analysis returns a `trust_modifier`, normalized and clamped to `[-0.3, 0.3]`. In the worker, that modifier is added to the incident score after clustering/scoring, then the tier is recomputed with the existing tier rules.

This is how a report with stronger media evidence can end up with a better confidence score than another report in the same tier.

---

## AI Pipeline

### Gemini Vision cross-validation

The media analysis flow in [`backend/services/gemini_service.py`](backend/services/gemini_service.py) is two-stage:

1. **Visual evidence extraction**
   - Gemini is asked to describe only what is concretely visible
   - output is strict JSON with observations, environment, hazards, visual cues, smoke/fire/damage flags, airport-interior cues, and uncertainties
2. **Cross-validation synthesis**
   - Gemini receives:
     - structured visual evidence
     - user caption
     - claimed coordinates
     - neighborhood name
   - it must produce:
     - incident type
     - media description
     - location inference
     - plausibility
     - pairwise consistency judgments between caption/media/location
     - a trust modifier
The prompt explicitly asks for:

- specific recognizable Dubai places when possible
- `drone` instead of `missile` for generic strike language
- airport inference when terminal cues are visible
- `Palm Jumeirah` when media or caption mention Fairmont The Palm or a hotel on the Palm

### Incident type classification

`extract_incident_type()` asks Gemini to return exactly one label from the allowed backend types. If Gemini fails, `_fallback_incident_type()` uses keyword rules.

### Summary generation

`generate_incident_summary()` gives Gemini:

- incident type
- title
- neighborhood
- number of independent reports
- time range
- confidence tier
- reporter notes
- optional media analysis context

If uploaded media show smoke, fire, damage, debris, or airport interiors, the prompt tells Gemini to mention that directly instead of writing a generic sighting summary.

### Confidence explanation generation

`generate_confidence_explanation()` asks Gemini to explain the current tier in plain language without numeric scores or internal scoring mechanics.

### Official source parsing

`parse_official_source()` asks Gemini to convert pasted official text into JSON with:

- `incident_type`
- `title`
- `summary`
- `latitude`
- `longitude`
- `location_name`
- `severity`

The prompt includes a location-resolution table for many known Dubai landmarks and falls back to Dubai center if necessary.

### Audio briefing script generation

`generate_audio_briefing_script()` asks Gemini to produce a calm `30-60` second spoken summary of active incidents, starting with the current UTC time and ending with:

```text
This concludes the current briefing. Stay safe.
```

### ElevenLabs TTS

Implemented in [`backend/services/elevenlabs_service.py`](backend/services/elevenlabs_service.py).

- voice ID: `w9xM4Spfmuw28ZXAirWK`
- model: `eleven_flash_v2_5`
- endpoint: `https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/stream`
- settings:
  - `stability: 0.7`
  - `similarity_boost: 0.8`
  - `style: 0.15`

---

## Incident Types

Canonical backend values come from [`backend/utils/incident_types.py`](backend/utils/incident_types.py).

| Backend value | Human-facing meaning in the project | Emoji mapping |
| --- | --- | --- |
| `drone` | Drone-related / generic airborne strike language | ?? |
| `explosion` | Explosion / blast | ?? |
| `debris` | Debris / aftermath / rubble | ?? |
| `missile` | Explicit missile / rocket / projectile | ?? |
| `siren` | Siren / alarm | ?? |
| `warning` | Warning / shelter / alert language | ?? |
| `unknown` | Fallback when classification is ambiguous | ? |

Notes:

- The Android UI chip list is broader than the backend canonical list.
- `Structural Damage` and `Other` both map to `unknown` in the current Android app.
- `Siren/Warning` maps to `warning` in the current Android app.

---

## API Reference

All API routers are mounted under `/api/v1`.

### `GET /api/v1/health`

Health check.

**Response**

```json
{
  "status": "ok",
  "service": "veriti",
  "version": "0.1.0"
}
```

### `GET /api/v1/incidents`

List active incidents.

**Query params**

- `confidence_tier` optional
- `limit` default `50`, max `200`
- `offset` default `0`

**Response**

```json
{
  "total": 4,
  "items": [
    {
      "id": "uuid",
      "type": "warning",
      "emoji": "??",
      "title": "Official warning near Dubai Marina",
      "summary": "...",
      "source_type": "official",
      "confidence_tier": "official",
      "confidence_score": 0.97,
      "latitude": 25.0832,
      "longitude": 55.1403,
      "grid_cell": "grid_...",
      "timestamp_first_seen": "2026-03-29T12:00:00Z",
      "timestamp_last_updated": "2026-03-29T12:10:00Z",
      "number_of_reports": 2,
      "official_overlap": true,
      "media_count": 0,
      "tags": ["warning", "official"],
      "verification_notes": "...",
      "is_active": true,
      "created_at": "2026-03-29T12:00:00Z",
      "updated_at": "2026-03-29T12:10:00Z"
    }
  ]
}
```

**Errors**

- `500` if incident fetch fails

### `GET /api/v1/incidents/map`

Lightweight payload for map rendering.

**Response**

```json
[
  {
    "id": "uuid",
    "type": "warning",
    "emoji": "??",
    "title": "Official warning near Dubai Marina",
    "confidence_tier": "official",
    "confidence_score": 0.97,
    "latitude": 25.0832,
    "longitude": 55.1403,
    "number_of_reports": 2,
    "is_active": true
  }
]
```

### `GET /api/v1/incidents/{incident_id}`

Fetch one full incident record.

**Errors**

- `404` if incident not found

### `POST /api/v1/submissions/upload`

Accept anonymous public submission.

**Multipart form fields consumed by backend**

- `file` optional
- `text_note` optional
- `latitude`
- `longitude`
- `device_trust_score` optional
- `integrity_token` optional

**Response**

```json
{
  "id": "uuid",
  "verification_status": "pending",
  "submitted_at": "2026-03-29T12:00:00Z",
  "message": "Submission received and queued for verification."
}
```

**Errors**

- `400` unsupported media type
- `429` rate limit exceeded
- `500` upload or processing enqueue failure

### `GET /api/v1/submissions/{submission_id}/status`

Check the current backend status of a submission.

**Response**

```json
{
  "id": "uuid",
  "verification_status": "verified",
  "incident_id": "uuid-or-null"
}
```

**Errors**

- `404` submission not found
### `POST /api/v1/official-alerts`

Parse an official statement and publish an official incident.

**Request**

```json
{
  "text": "Official statement text",
  "source_url": "https://example.com/post"
}
```

**Response**

- full `IncidentResponse`

**Errors**

- `422` Gemini failed to parse official text
- `500` official incident creation failed

### `GET /api/v1/audio-briefing`

Generate and return an MP3 audio briefing of active incidents.

**Response**

- `audio/mpeg`

**Headers**

- `Content-Disposition: inline; filename=briefing.mp3`
- `Cache-Control: no-cache`

**Errors**

- `503` audio briefing not configured
- `503` audio briefing temporarily unavailable

---

## Project Structure

```text
veriti/
+-- backend/
¦   +-- api/
¦   ¦   +-- audio_briefing.py      # ElevenLabs-backed MP3 endpoint
¦   ¦   +-- health.py              # health check
¦   ¦   +-- incidents.py           # incident list/detail/map endpoints
¦   ¦   +-- official_alerts.py     # official source ingestion endpoint
¦   ¦   +-- router.py              # API router aggregation
¦   ¦   +-- submissions.py         # anonymous upload + status endpoints
¦   +-- models/
¦   ¦   +-- incident.py            # Incident SQLAlchemy model
¦   ¦   +-- submission.py          # Submission SQLAlchemy model
¦   +-- schemas/
¦   ¦   +-- incident.py            # incident response models
¦   ¦   +-- submission.py          # submission response/status models
¦   +-- services/
¦   ¦   +-- clustering_service.py  # clustering and incident title building
¦   ¦   +-- elevenlabs_service.py  # TTS integration
¦   ¦   +-- gemini_service.py      # AI parsing, verification, summaries
¦   ¦   +-- ingestion_service.py   # submission processing + official merges
¦   ¦   +-- scoring_service.py     # confidence score and tier logic
¦   ¦   +-- verification_service.py# duplicate detection + trust handling
¦   +-- utils/
¦   ¦   +-- dubai_locations.py     # known locations and area inference
¦   ¦   +-- hashing.py             # perceptual hash helpers
¦   ¦   +-- incident_types.py      # canonical types and emoji mapping
¦   ¦   +-- location.py            # backend grid coarsening
¦   ¦   +-- media.py               # file save, video scrub, deletion
¦   ¦   +-- privacy.py             # text sanitization + image metadata scrub
¦   ¦   +-- rate_limiter.py        # in-memory upload throttle
¦   +-- workers/
¦   ¦   +-- pipeline.py            # background verification worker
¦   +-- config.py                  # environment-backed settings
¦   +-- database.py                # engine/session/Base init
¦   +-- main.py                    # FastAPI entry point
¦   +-- requirements.txt           # backend dependencies
¦   +-- seed_data.py               # demo incidents for hackathon demos
+-- web/
¦   +-- app/
¦   ¦   +-- globals.css            # global styles + Leaflet overrides
¦   ¦   +-- layout.tsx             # root layout and metadata
¦   ¦   +-- page.tsx               # dashboard shell
¦   +-- components/
¦   ¦   +-- ConfidenceBadge.tsx    # confidence tier badge
¦   ¦   +-- Header.tsx             # top bar + audio briefing control
¦   ¦   +-- IncidentCard.tsx       # feed row + expandable summary
¦   ¦   +-- IncidentDetail.tsx     # expanded detail body
¦   ¦   +-- IncidentFeed.tsx       # sidebar feed
¦   ¦   +-- Map.tsx                # Leaflet map container
¦   ¦   +-- MapMarker.tsx          # marker + popup rendering
¦   ¦   +-- OfficialSourcePanel.tsx# operator official ingestion modal
¦   ¦   +-- PulsingDot.tsx         # live indicator
¦   ¦   +-- StatusBar.tsx          # last-updated footer
¦   +-- hooks/
¦   ¦   +-- useIncidents.ts        # polling and highlight logic
¦   +-- lib/
¦   ¦   +-- api.ts                 # frontend API client
¦   +-- types/
¦   ¦   +-- incident.ts            # frontend incident types
¦   +-- package.json               # Next.js app dependencies
¦   +-- tailwind.config.ts         # shared dashboard tokens
+-- mobile/
¦   +-- android/
¦       +-- app/
¦       ¦   +-- build.gradle.kts   # Android app module config
¦       ¦   +-- src/main/
¦       ¦       +-- AndroidManifest.xml
¦       ¦       +-- java/com/veriti/app/
¦       ¦       ¦   +-- MainActivity.kt
¦       ¦       ¦   +-- model/
¦       ¦       ¦   ¦   +-- PipelineState.kt
¦       ¦       ¦   ¦   +-- SubmissionData.kt
¦       ¦       ¦   +-- network/
¦       ¦       ¦   ¦   +-- ApiClient.kt
¦       ¦       ¦   +-- pipeline/
¦       ¦       ¦   ¦   +-- ExifStripper.kt
¦       ¦       ¦   ¦   +-- IntegrityChecker.kt
¦       ¦       ¦   ¦   +-- LocalPipeline.kt
¦       ¦       ¦   ¦   +-- LocationCoarsener.kt
¦       ¦       ¦   ¦   +-- MediaValidator.kt
¦       ¦       ¦   ¦   +-- TextSanitizer.kt
¦       ¦       ¦   +-- ui/
¦       ¦       ¦       +-- PrivacyDialog.kt
¦       ¦       ¦       +-- PrivacyStatusCard.kt
¦       ¦       ¦       +-- ReportScreen.kt
¦       ¦       ¦       +-- theme/
¦       ¦       ¦           +-- Color.kt
¦       ¦       ¦           +-- Theme.kt
¦       ¦       +-- res/
¦       ¦           +-- values/strings.xml
¦       ¦           +-- xml/file_paths.xml
¦       +-- build.gradle.kts       # top-level Android build config
¦       +-- settings.gradle.kts    # Android project settings
+-- docs/
¦   +-- architecture.md
¦   +-- setup.md
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

Backend settings are defined in [`backend/config.py`](backend/config.py):

- `GEMINI_API_KEY`
- `ELEVENLABS_API_KEY`
- `DATABASE_URL` default: `sqlite:///veriti.db`
- `UPLOAD_DIR` default: `uploads`
- `MAX_UPLOAD_SIZE_MB` default: `50`
- `GRID_SIZE_METERS` default: `500`
- `CLUSTERING_TIME_WINDOW_MINUTES` default: `30`
- `EMBEDDING_SIMILARITY_THRESHOLD` default: `0.7`
- `DUPLICATE_HASH_THRESHOLD` default: `5`

Frontend runtime:

- `NEXT_PUBLIC_API_URL` optional, defaults to `http://localhost:8000`

Android build config:

- `API_BASE_URL` is currently hardcoded in [`mobile/android/app/build.gradle.kts`](mobile/android/app/build.gradle.kts) as `http://localhost:8000`
- `INTEGRITY_CLOUD_PROJECT_NUMBER` exists in build config but is currently set to `0L` and not used by the local heuristic integrity flow

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

## Demo Script

Suggested hackathon demo flow based on the shipped features:

1. Open the web dashboard and show the live Dubai map.
2. Open the Android app and point out the privacy-first flow: no account, no login, no identity field.
3. Capture or choose media and show the local checks:
   - metadata stripped
   - location coarsened
   - media validated
   - device integrity scored
4. Submit the first report and show it appear on the dashboard as low-confidence.
5. Submit a second report for the same area to demonstrate clustering and tier escalation.
6. Open the incident detail to show confidence notes and AI-generated summary text.
7. Paste an official statement into `Official Source Intake` and show official overlap changing the incident state.
8. Click `Audio briefing` and let the dashboard read the active situation aloud.
9. Close by explaining the privacy architecture: content is verified, not the sender.

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


