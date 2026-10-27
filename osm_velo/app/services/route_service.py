
import hashlib
import math
from pathlib import Path

import gpxpy
from pyproj import Geod
from shapely.geometry import LineString

from app.db.connection import get_connection


PROJECT_DIR = Path(__file__).resolve().parents[2]
UPLOAD_DIR = PROJECT_DIR / "data" / "uploads"

GEOD = Geod(ellps="WGS84")


def parse_gpx(file_path: Path) -> list[tuple[float, float]]:

    try:
        with file_path.open("r", encoding="utf-8-sig") as gpx_file:
            gpx = gpxpy.parse(gpx_file)
    except Exception as exc:
        raise ValueError(f"Could not parse GPX file: {exc}") from exc

    gps_points: list[tuple[float, float]] = []

    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                gps_points.append((point.longitude, point.latitude))

    if not gps_points:
        for route in gpx.routes:
            for point in route.points:
                gps_points.append((point.longitude, point.latitude))

    if len(gps_points) < 2:
        raise ValueError("The GPX file must contain at least two GPS points.")

    for longitude, latitude in gps_points:
        if not (
            math.isfinite(longitude)
            and math.isfinite(latitude)
            and -180 <= longitude <= 180
            and -90 <= latitude <= 90
        ):
            raise ValueError("The GPX file contains invalid GPS coordinates.")

    return gps_points


def calculate_route_hash(file_path: Path) -> str:

    sha256 = hashlib.sha256()

    with file_path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


def calculate_distances(gps_points: list[tuple[float, float]]) -> tuple[list[float], float]:

    cumulative_distances: list[float] = []
    total_distance = 0.0
    previous_point: tuple[float, float] | None = None

    for longitude, latitude in gps_points:
        if previous_point is not None:
            _, _, segment_distance = GEOD.inv(
                previous_point[0],
                previous_point[1],
                longitude,
                latitude,
            )
            total_distance += segment_distance

        cumulative_distances.append(total_distance)
        previous_point = (longitude, latitude)

    return cumulative_distances, total_distance


def save_route(name: str, gps_points: list[tuple[float, float]], route_hash: str) -> tuple[int, str, float]:

    if len(gps_points) < 2:
        raise ValueError("A route must contain at least two GPS points.")

    line = LineString(gps_points)
    cumulative_distances, total_distance = calculate_distances(gps_points)

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id
                FROM public.routes
                WHERE route_hash = %s
                """,
                (route_hash,),
            )
            existing_route = cursor.fetchone()

            if existing_route:
                route_id = existing_route[0]
                route_status = "updated"

                cursor.execute(
                    """
                    UPDATE public.routes
                    SET name = %s,
                        route = ST_GeomFromText(%s, 4326),
                        point_count = %s,
                        distance_m = %s
                    WHERE id = %s
                    """,
                    (
                        name,
                        line.wkt,
                        len(gps_points),
                        total_distance,
                        route_id,
                    ),
                )

                cursor.execute(
                    """
                    DELETE FROM public.route_points
                    WHERE route_id = %s
                    """,
                    (route_id,),
                )

            else:
                route_status = "created"

                cursor.execute(
                    """
                    INSERT INTO public.routes (
                        name,
                        route_hash,
                        route,
                        point_count,
                        distance_m
                    )
                    VALUES (
                        %s,
                        %s,
                        ST_GeomFromText(%s, 4326),
                        %s,
                        %s
                    )
                    RETURNING id
                    """,
                    (
                        name,
                        route_hash,
                        line.wkt,
                        len(gps_points),
                        total_distance,
                    ),
                )

                route_id = cursor.fetchone()[0]

            point_rows = [
                (
                    route_id,
                    sequence,
                    longitude,
                    latitude,
                    cumulative_distances[sequence - 1],
                )
                for sequence, (longitude, latitude) in enumerate(
                    gps_points, start=1
                )
            ]

            cursor.executemany(
                """
                INSERT INTO public.route_points (
                    route_id,
                    sequence,
                    geom,
                    distance_from_start
                )
                VALUES (
                    %s,
                    %s,
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                    %s
                )
                """,
                point_rows,
            )

    return route_id, route_status, total_distance


def import_gpx(file_path: Path, name: str | None = None) -> dict:

    file_path = Path(file_path)

    if file_path.suffix.lower() != ".gpx":
        raise ValueError("Only GPX files are supported.")

    if not file_path.is_file():
        raise ValueError("The uploaded GPX file could not be found.")

    gps_points = parse_gpx(file_path)
    route_hash = calculate_route_hash(file_path)
    route_name = name or file_path.stem

    route_id, route_status, distance_m = save_route(
        name=route_name,
        gps_points=gps_points,
        route_hash=route_hash,
    )

    return {
        "route_id": route_id,
        "name": route_name,
        "distance_km": round(distance_m / 1000, 3),
        "point_count": len(gps_points),
        "status": route_status,
    }
