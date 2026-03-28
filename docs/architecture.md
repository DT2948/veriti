# Veriti Architecture

## Verification Pipeline

Veriti accepts anonymous public submissions and official alerts, coarsens their location to a privacy-preserving grid, strips sensitive metadata where possible, and stores them as submissions. The processing pipeline then verifies likely duplicates, clusters related submissions into incidents, computes a confidence score, and generates a concise factual incident summary for the live map.

## Pipeline Diagram

```text
Upload / Official Alert
         |
         v
      Verify
  (hash, trust, dupes)
         |
         v
      Cluster
 (grid + time + similarity)
         |
         v
       Score
 (confidence tier + notes)
         |
         v
     Summarize
   (Gemini or fallback)
         |
         v
      Display
   (API + live map)
```

## Privacy Principles

- No user accounts or persistent identity are required for submissions.
- Coordinates are coarsened to a 500m grid before long-term storage.
- Image EXIF metadata is stripped server-side for supported image formats.
- Text notes are sanitized to redact phone numbers and email addresses.
- Confidence explanations are designed to communicate uncertainty instead of overstating facts.

## Confidence Tiers

- `official`: confirmed by an official alert or strong overlap with an official source
- `corroborated`: supported by at least three independent reports or strong similarity evidence
- `plausible`: supported by two independent reports or moderate supporting signals
- `unverified`: only a single report or insufficient corroboration
