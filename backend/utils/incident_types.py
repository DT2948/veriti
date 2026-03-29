INCIDENT_TYPES: dict[str, str] = {
    "drone": "💥",
    "explosion": "💥",
    "debris": "🧱",
    "missile": "🚀",
    "siren": "🚨",
    "warning": "⚠️",
    "unknown": "❓",
}

ALLOWED_TYPES: set[str] = set(INCIDENT_TYPES.keys())
DEFAULT_TYPE: str = "unknown"


def get_emoji(incident_type: str) -> str:
    return INCIDENT_TYPES.get(incident_type, INCIDENT_TYPES[DEFAULT_TYPE])
