from pathlib import Path
import json

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import get_settings
from models.submission import Submission
from utils.hashing import compute_phash, hamming_distance


settings = get_settings()


def verify_submission(db: Session, submission: Submission) -> Submission:
    if submission.media_path and submission.media_type == "image":
        submission.perceptual_hash = generate_perceptual_hash(submission.media_path)
        duplicates = check_duplicate(
            db,
            submission.perceptual_hash,
            threshold=settings.duplicate_hash_threshold,
            exclude_submission_id=submission.id,
        )
        if duplicates:
            submission.duplicate_group_id = duplicates[0]
            submission.verification_status = "duplicate"
        else:
            submission.duplicate_group_id = submission.id

        submission.embedding_vector = json.dumps(generate_embedding(submission.media_path))

    raw_integrity_token = submission.integrity_token
    if raw_integrity_token and submission.device_trust_score is None:
        submission.device_trust_score = validate_integrity_token(raw_integrity_token)

    # We only retain whether a token was supplied in this MVP, not the
    # attestation payload itself, to avoid storing raw device-linked tokens.
    submission.integrity_token = _sanitize_integrity_token(raw_integrity_token)

    if submission.verification_status == "pending":
        submission.verification_status = "processing"

    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission


def generate_perceptual_hash(file_path: str) -> str:
    return compute_phash(file_path)


def check_duplicate(
    db: Session,
    perceptual_hash: str,
    threshold: int = 5,
    exclude_submission_id: str | None = None,
) -> list[str]:
    if not perceptual_hash:
        return []

    stmt = select(Submission).where(Submission.perceptual_hash.is_not(None))
    if exclude_submission_id:
        stmt = stmt.where(Submission.id != exclude_submission_id)

    matches: list[str] = []
    for existing in db.scalars(stmt).all():
        if existing.perceptual_hash and hamming_distance(perceptual_hash, existing.perceptual_hash) <= threshold:
            matches.append(existing.id)
    return matches


def generate_embedding(file_path: str) -> list[float]:
    raw = Path(file_path).read_bytes() if file_path else b""
    seed = int.from_bytes(raw[:8].ljust(8, b"\0"), "big", signed=False)
    rng = np.random.default_rng(seed)
    # TODO: Replace with CLIP or multimodal embedding generation for production similarity matching.
    return rng.random(512).astype(float).tolist()


def compute_embedding_similarity(vec1: list[float], vec2: list[float]) -> float:
    if not vec1 or not vec2:
        return 0.0

    array1 = np.array(vec1, dtype=float)
    array2 = np.array(vec2, dtype=float)
    denominator = np.linalg.norm(array1) * np.linalg.norm(array2)
    if denominator == 0:
        return 0.0
    return float(np.dot(array1, array2) / denominator)


def validate_integrity_token(token: str) -> float:
    # TODO: Verify against the Google Play Integrity API and return an attestation-backed trust score.
    if not token:
        return 0.4
    trimmed_length = len(token.strip())
    if trimmed_length > 64:
        return 0.85
    if trimmed_length > 24:
        return 0.7
    return 0.55


def _sanitize_integrity_token(token: str | None) -> str:
    if not token:
        return "missing"

    # Current MVP records that a token was provided, but does not retain the
    # raw attestation payload after evaluating device trust.
    return "provided"
