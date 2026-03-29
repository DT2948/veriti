from __future__ import annotations

from math import sqrt


GRID_STEP = 0.0045

_KNOWN_NEIGHBORHOODS = {
    "Dubai Marina": (25.0805, 55.1403),
    "Downtown Dubai / Burj Khalifa": (25.1972, 55.2744),
    "Jumeirah Beach (JBR)": (25.0780, 55.1330),
    "Palm Jumeirah": (25.1124, 55.1390),
    "Dubai International Airport (DXB)": (25.2532, 55.3657),
    "Deira": (25.2697, 55.3095),
    "Bur Dubai": (25.2560, 55.2920),
    "Business Bay": (25.1860, 55.2720),
    "Jumeirah Lake Towers (JLT)": (25.0750, 55.1500),
    "Al Barsha": (25.1000, 55.2000),
    "Dubai Creek": (25.2400, 55.3200),
    "Al Quoz": (25.1500, 55.2300),
    "Dubai Internet City": (25.0950, 55.1600),
    "Dubai Media City": (25.0900, 55.1550),
    "Al Karama": (25.2400, 55.3000),
    "Jumeirah": (25.2100, 55.2500),
    "Sheikh Zayed Road": (25.2000, 55.2700),
    "Dubai Hills": (25.1400, 55.2400),
    "Mirdif": (25.2300, 55.4200),
    "Silicon Oasis": (25.1200, 55.3800),
}

_LOCATION_ALIASES = {
    "Dubai Marina": ["dubai marina", "marina"],
    "Downtown Dubai / Burj Khalifa": ["downtown dubai", "burj khalifa", "downtown"],
    "Jumeirah Beach (JBR)": ["jbr", "jumeirah beach", "the beach"],
    "Palm Jumeirah": [
        "palm jumeirah",
        "the palm",
    ],
    "Dubai International Airport (DXB)": [
        "dubai international airport",
        "dxb",
        "dubai airport",
        "airport terminal",
        "terminal 1",
        "terminal 2",
        "terminal 3",
    ],
    "Deira": ["deira"],
    "Bur Dubai": ["bur dubai"],
    "Business Bay": ["business bay"],
    "Jumeirah Lake Towers (JLT)": ["jlt", "jumeirah lake towers"],
    "Al Barsha": ["al barsha", "barsha"],
    "Dubai Creek": ["dubai creek", "the creek"],
    "Al Quoz": ["al quoz"],
    "Dubai Internet City": ["dubai internet city", "internet city"],
    "Dubai Media City": ["dubai media city", "media city"],
    "Al Karama": ["al karama", "karama"],
    "Jumeirah": ["jumeirah"],
    "Sheikh Zayed Road": ["sheikh zayed road", "szr"],
    "Dubai Hills": ["dubai hills"],
    "Mirdif": ["mirdif"],
    "Silicon Oasis": ["silicon oasis", "dubai silicon oasis"],
}


def _grid_cell_for_coordinates(lat: float, lng: float) -> str:
    lat_index = round(lat / GRID_STEP)
    lng_index = round(lng / GRID_STEP)
    return f"grid_{lat_index}_{lng_index}"


GRID_TO_NEIGHBORHOOD = {
    _grid_cell_for_coordinates(lat, lng): name
    for name, (lat, lng) in _KNOWN_NEIGHBORHOODS.items()
}


def _nearest_neighborhood(lat: float, lng: float) -> tuple[str, float]:
    closest_name = "central Dubai"
    closest_distance = float("inf")
    for name, (candidate_lat, candidate_lng) in _KNOWN_NEIGHBORHOODS.items():
        distance = sqrt((lat - candidate_lat) ** 2 + (lng - candidate_lng) ** 2)
        if distance < closest_distance:
            closest_name = name
            closest_distance = distance
    return closest_name, closest_distance


def _general_area_description(lat: float | None, lng: float | None) -> str:
    if lat is None or lng is None:
        return "central Dubai"

    if lng >= 55.36:
        return "eastern Dubai"
    if lat >= 25.24 and lng >= 55.28:
        return "northern Dubai"
    if lat <= 25.12:
        return "southern Dubai"
    if lng <= 55.17:
        return "western Dubai"
    return "central Dubai"


def get_neighborhood_name(grid_cell: str, lat: float = None, lng: float = None) -> str:
    """
    Returns the nearest Dubai neighborhood name for a grid cell.
    Falls back to a general area description if no exact match.
    """
    exact_match = GRID_TO_NEIGHBORHOOD.get(grid_cell)
    if exact_match:
        return exact_match

    if lat is not None and lng is not None:
        nearest_name, distance = _nearest_neighborhood(lat, lng)
        if distance <= 0.08:
            return nearest_name

    return _general_area_description(lat, lng)


def resolve_known_location(text: str | None) -> tuple[str, float, float] | None:
    if not text:
        return None

    lowered = text.lower()
    best_match: tuple[str, str] | None = None
    for canonical_name, aliases in _LOCATION_ALIASES.items():
        for alias in aliases:
            if alias in lowered:
                if best_match is None or len(alias) > len(best_match[1]):
                    best_match = (canonical_name, alias)

    if best_match is not None:
        canonical_name, _ = best_match
        lat, lng = _KNOWN_NEIGHBORHOODS[canonical_name]
        return canonical_name, lat, lng
    return None


def is_implausible_report_location(lat: float | None, lng: float | None) -> bool:
    if lat is None or lng is None:
        return False

    # Conservative "in the sea" heuristic for the Gulf-facing west edge of Dubai.
    # We only use this to permit a landmark-based correction when Gemini also
    # identifies a recognizable Dubai location.
    return lng <= 55.08 and lat >= 24.95
