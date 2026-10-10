"""Step 2: travel distance (km) and drive time (minutes) between every pair of locations.

Real road values come from the public OSRM server (OpenStreetMap data, no API key).
Without internet we estimate: straight-line (haversine) distance x 1.35 road factor,
driven at an average city speed of 20 km/h.
"""
from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt

import numpy as np
import requests

OSRM_URL = "https://router.project-osrm.org"
ROAD_FACTOR = 1.35
CITY_SPEED_KMPH = 20.0
EARTH_RADIUS_KM = 6371.0
TIMEOUT_S = 15
# OSRM's public server returns free-flow drive times; city traffic makes trips slower.
DEFAULT_TRAFFIC_FACTOR = 1.5


@dataclass
class DistanceMatrix:
    km: np.ndarray  # km[i][j] = road km from location i to j
    minutes: np.ndarray  # minutes[i][j] = drive time from i to j
    source: str  # "OSRM road network" or "Estimate (haversine x 1.35 @ 20 km/h)"


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1, lon1, lat2, lon2 = map(radians, (lat1, lon1, lat2, lon2))
    a = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(a))


def estimate_matrix(points: list[tuple[float, float]]) -> DistanceMatrix:
    n = len(points)
    km = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            d = haversine_km(*points[i], *points[j]) * ROAD_FACTOR
            km[i, j] = km[j, i] = d
    minutes = km / CITY_SPEED_KMPH * 60
    return DistanceMatrix(km, minutes, f"Estimate (haversine x {ROAD_FACTOR} @ {CITY_SPEED_KMPH:g} km/h)")


def _coord_string(points: list[tuple[float, float]]) -> str:
    # OSRM expects lon,lat pairs separated by ';'
    return ";".join(f"{lon:.6f},{lat:.6f}" for lat, lon in points)


def osrm_matrix(points: list[tuple[float, float]]) -> DistanceMatrix:
    url = f"{OSRM_URL}/table/v1/driving/{_coord_string(points)}"
    resp = requests.get(url, params={"annotations": "distance,duration"}, timeout=TIMEOUT_S)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != "Ok":
        raise RuntimeError(f"OSRM error: {data.get('code')} {data.get('message', '')}")
    km = np.array(data["distances"], dtype=float) / 1000
    minutes = np.array(data["durations"], dtype=float) / 60
    if np.isnan(km).any() or np.isnan(minutes).any():
        raise RuntimeError("OSRM could not route between some locations")
    return DistanceMatrix(km, minutes, "OSRM road network")


def build_matrix(
    points: list[tuple[float, float]], use_osrm: bool = True, traffic_factor: float = DEFAULT_TRAFFIC_FACTOR
) -> DistanceMatrix:
    """Road matrix from OSRM when possible, otherwise the offline estimate.

    traffic_factor scales OSRM's free-flow drive times; the estimate already assumes city speed.
    """
    if use_osrm:
        try:
            matrix = osrm_matrix(points)
            matrix.minutes = matrix.minutes * traffic_factor
            if traffic_factor != 1:
                matrix.source += f" (drive times x {traffic_factor:g} for traffic)"
            return matrix
        except (requests.RequestException, RuntimeError, KeyError, ValueError):
            pass
    return estimate_matrix(points)


def route_geometry(points: list[tuple[float, float]], use_osrm: bool = True) -> list[tuple[float, float]]:
    """Road-following polyline (lat, lon) through points in order; straight lines as fallback."""
    if use_osrm and len(points) >= 2:
        try:
            url = f"{OSRM_URL}/route/v1/driving/{_coord_string(points)}"
            resp = requests.get(url, params={"overview": "full", "geometries": "geojson"}, timeout=TIMEOUT_S)
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") == "Ok":
                return [(lat, lon) for lon, lat in data["routes"][0]["geometry"]["coordinates"]]
        except (requests.RequestException, KeyError, IndexError, ValueError):
            pass
    return list(points)
