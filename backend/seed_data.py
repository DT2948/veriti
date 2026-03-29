import json
from datetime import datetime, timedelta, timezone

from database import SessionLocal, init_db
from models.incident import Incident
from models.submission import Submission
from utils.incident_types import INCIDENT_TYPES
from utils.location import coarsen_location


def seed() -> None:
    init_db()
    db = SessionLocal()
    try:
        if db.query(Incident).count() > 0:
            print("Seed data already exists.")
            return

        now = datetime.now(timezone.utc)
        demos = [
            {
                "type": "warning",
                "title": "Official warning near Dubai Marina",
                "summary": "Authorities issued a warning for a localized airspace disruption near Dubai Marina.",
                "source_type": "official",
                "confidence_tier": "official",
                "confidence_score": 0.97,
                "lat": 25.0832,
                "lng": 55.1403,
                "reports": 2,
                "official_overlap": True,
                "media_count": 0,
            },
            {
                "type": "siren",
                "title": "Multiple siren reports in Jumeirah",
                "summary": "Several public submissions reported hearing repeated sirens in Jumeirah within a short time window.",
                "source_type": "public",
                "confidence_tier": "corroborated",
                "confidence_score": 0.74,
                "lat": 25.2048,
                "lng": 55.2708,
                "reports": 3,
                "official_overlap": False,
                "media_count": 1,
            },
            {
                "type": "debris",
                "title": "Single debris photo near Al Quoz",
                "summary": "One anonymous report included an image of suspected debris near Al Quoz, but corroboration is limited.",
                "source_type": "public",
                "confidence_tier": "unverified",
                "confidence_score": 0.19,
                "lat": 25.1365,
                "lng": 55.2350,
                "reports": 1,
                "official_overlap": False,
                "media_count": 1,
            },
            {
                "type": "missile",
                "title": "Plausible aerial flash near Deira",
                "summary": "Two independent reports mention a bright aerial flash over Deira without official confirmation yet.",
                "source_type": "mixed",
                "confidence_tier": "plausible",
                "confidence_score": 0.46,
                "lat": 25.2760,
                "lng": 55.3300,
                "reports": 2,
                "official_overlap": False,
                "media_count": 1,
            },
        ]

        for index, item in enumerate(demos, start=1):
            if item["type"] not in INCIDENT_TYPES:
                raise ValueError(f"Unsupported seed incident type: {item['type']}")
            lat, lng, grid_cell = coarsen_location(item["lat"], item["lng"])
            first_seen = now - timedelta(minutes=index * 18)
            incident = Incident(
                type=item["type"],
                title=item["title"],
                summary=item["summary"],
                source_type=item["source_type"],
                confidence_tier=item["confidence_tier"],
                confidence_score=item["confidence_score"],
                latitude=lat,
                longitude=lng,
                grid_cell=grid_cell,
                timestamp_first_seen=first_seen,
                timestamp_last_updated=first_seen + timedelta(minutes=10),
                number_of_reports=item["reports"],
                official_overlap=item["official_overlap"],
                media_count=item["media_count"],
                tags=json.dumps([item["type"], item["confidence_tier"]]),
                verification_notes=f"Demo incident seeded for hackathon scenario #{index}.",
                is_active=True,
            )
            db.add(incident)
            db.flush()

            for report_index in range(item["reports"]):
                submission = Submission(
                    incident_id=incident.id,
                    source_type="official" if item["official_overlap"] and report_index == 0 else "public",
                    media_type="image" if report_index < item["media_count"] else None,
                    media_path=None,
                    text_note=f"Demo report {report_index + 1} for {item['title']}.",
                    latitude=lat,
                    longitude=lng,
                    grid_cell=grid_cell,
                    submitted_at=first_seen + timedelta(minutes=report_index * 3),
                    device_trust_score=0.9 if report_index == 0 else 0.68,
                    integrity_token=None,
                    duplicate_group_id=f"{incident.id}-{report_index + 1}",
                    perceptual_hash=None,
                    embedding_vector=None,
                    verification_status="verified",
                    anonymous_token=None,
                    processed_at=first_seen + timedelta(minutes=report_index * 3 + 1),
                )
                db.add(submission)

        db.commit()
        print("Seeded 4 demo incidents.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
