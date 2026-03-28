import math


DUBAI_MIN_LAT = 24.7
DUBAI_MAX_LAT = 25.4
DUBAI_MIN_LNG = 54.9
DUBAI_MAX_LNG = 55.6


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def coarsen_location(lat: float, lng: float, grid_size_meters: int = 500) -> tuple[float, float, str]:
    lat = _clamp(lat, DUBAI_MIN_LAT, DUBAI_MAX_LAT)
    lng = _clamp(lng, DUBAI_MIN_LNG, DUBAI_MAX_LNG)

    meters_per_degree_lat = 111_320
    meters_per_degree_lng = 111_320 * math.cos(math.radians(lat))

    lat_step = grid_size_meters / meters_per_degree_lat
    lng_step = grid_size_meters / meters_per_degree_lng if meters_per_degree_lng else 0.005

    lat_index = round((lat - DUBAI_MIN_LAT) / lat_step)
    lng_index = round((lng - DUBAI_MIN_LNG) / lng_step)

    coarsened_lat = DUBAI_MIN_LAT + (lat_index * lat_step)
    coarsened_lng = DUBAI_MIN_LNG + (lng_index * lng_step)
    grid_cell = f"grid_{lat_index}_{lng_index}"

    return round(coarsened_lat, 6), round(coarsened_lng, 6), grid_cell
