
from pathlib import Path

import numpy as np
import psycopg
import rasterio
from pyproj import Transformer
from rasterio.errors import RasterioError

from app.db.connection import get_connection


PROJECT_DIR = Path(__file__).resolve().parents[2]
TERRAIN_DIR = PROJECT_DIR / "data" / "terrain"

ELEVATION_NOISE_THRESHOLD_M = 0.5


def find_terrain_files() -> list[Path]:
    if not TERRAIN_DIR.exists():
        raise FileNotFoundError(f"Terrain directory does not exist: {TERRAIN_DIR}")

    files = sorted(
        path
        for path in TERRAIN_DIR.rglob("*")
        if path.is_file() and path.suffix.lower() in {".tif", ".tiff"}
    )

    if not files:
        raise FileNotFoundError(f"No .tif or .tiff terrain files found in {TERRAIN_DIR}")

    return files


def load_route_points(cursor: psycopg.Cursor, route_id: int) -> list[tuple[int, float, float, float]]:

    cursor.execute(
        """
        SELECT
            sequence,
            ST_X(geom) AS longitude,
            ST_Y(geom) AS latitude,
            distance_from_start
        FROM public.route_points
        WHERE route_id = %s
        ORDER BY sequence
        """,
        (route_id,),
    )

    rows = cursor.fetchall()

    if len(rows) < 2:
        raise ValueError(f"Route {route_id} does not have enough points for analysis.")

    return [
        (int(row[0]), float(row[1]), float(row[2]), float(row[3]))
        for row in rows
    ]


def sample_raster(raster_path: Path, route_points: list[tuple[int, float, float, float]]) -> dict[int, float]:

    elevations: dict[int, float] = {}

    try:
        with rasterio.open(raster_path) as dataset:
            if dataset.crs is None:
                print(f"Skipping raster without CRS: {raster_path}")
                return elevations

            transformer = Transformer.from_crs(
                "EPSG:4326",
                dataset.crs,
                always_xy=True,
            )

            coordinates = [
                transformer.transform(longitude, latitude)
                for _, longitude, latitude, _ in route_points
            ]

            samples = dataset.sample(coordinates, masked=True)
            nodata = dataset.nodata

            for route_point, sample in zip(route_points, samples):
                sequence = route_point[0]

                if sample is None or len(sample) == 0:
                    continue

                value = sample[0]

                if np.ma.is_masked(value):
                    continue

                elevation = float(value)

                if not np.isfinite(elevation):
                    continue

                if nodata is not None and np.isclose(elevation, nodata):
                    continue

                elevations[sequence] = elevation

    except (RasterioError, OSError) as exc:
        print(f"Could not read terrain raster {raster_path}: {exc}")

    return elevations


def calculate_slopes(route_points: list[tuple[int, float, float, float]], elevations: dict[int, float]) -> dict[int, float | None]:

    slopes: dict[int, float | None] = {}
    previous_valid: tuple[float, float] | None = None

    for sequence, _, _, distance_m in route_points:
        elevation = elevations.get(sequence)

        if elevation is None:
            slopes[sequence] = None
            continue

        if previous_valid is None:
            slopes[sequence] = 0.0
            previous_valid = (distance_m, elevation)
            continue

        previous_distance, previous_elevation = previous_valid
        horizontal_distance = distance_m - previous_distance

        if horizontal_distance <= 0:
            slopes[sequence] = 0.0
        else:
            slopes[sequence] = ((elevation - previous_elevation) / horizontal_distance * 100.0)

        previous_valid = (distance_m, elevation)

    return slopes


def calculate_elevation_stats(route_points: list[tuple[int, float, float, float]], levations: dict[int, float]) -> dict:

    valid_points = [
        point
        for point in route_points
        if point[0] in elevations
    ]

    if not valid_points:
        raise ValueError("No route points overlap valid terrain elevation data.")

    valid_elevations = [
        (point[0], point[3], elevations[point[0]])
        for point in valid_points
    ]

    values = [item[2] for item in valid_elevations]
    gain_m = 0.0
    loss_m = 0.0

    for previous, current in zip(values, values[1:]):
        difference = current - previous

        if difference > ELEVATION_NOISE_THRESHOLD_M:
            gain_m += difference
        elif difference < -ELEVATION_NOISE_THRESHOLD_M:
            loss_m += abs(difference)

    min_point = min(valid_elevations, key=lambda item: item[2])
    max_point = max(valid_elevations, key=lambda item: item[2])

    return {
        "min_elevation_m": min(values),
        "max_elevation_m": max(values),
        "min_elevation_distance_m": min_point[1],
        "max_elevation_distance_m": max_point[1],
        "total_gain_m": gain_m,
        "total_loss_m": loss_m,
    }


def analyse_elevation(route_id: int) -> dict:

    terrain_files = find_terrain_files()

    with get_connection() as connection:
        with connection.cursor() as cursor:
            route_points = load_route_points(cursor, route_id)

            elevations: dict[int, float] = {}

            for terrain_file in terrain_files:
                remaining_points = [
                    point
                    for point in route_points
                    if point[0] not in elevations
                ]

                if not remaining_points:
                    break

                elevations.update(
                    sample_raster(terrain_file, remaining_points)
                )

            if not elevations:
                raise ValueError("No route points could be sampled from the terrain files.")

            slopes = calculate_slopes(route_points, elevations)
            stats = calculate_elevation_stats(route_points, elevations)

            cursor.executemany(
                """
                UPDATE public.route_points
                SET elevation_m = %s,
                    slope_percent = %s
                WHERE route_id = %s
                  AND sequence = %s
                """,
                [
                    (
                        elevations.get(sequence),
                        slopes.get(sequence),
                        route_id,
                        sequence,
                    )
                    for sequence, _, _, _ in route_points
                ],
            )

            valid_slopes = [
                value
                for value in slopes.values()
                if value is not None
            ]

            min_slope = min(valid_slopes) if valid_slopes else None
            max_slope = max(valid_slopes) if valid_slopes else None

            cursor.execute(
                """
                INSERT INTO public.route_terrain_stats (
                    route_id,
                    min_elevation_m,
                    max_elevation_m,
                    min_elevation_distance_m,
                    max_elevation_distance_m,
                    total_gain_m,
                    total_loss_m,
                    min_slope_percent,
                    max_slope_percent,
                    calculated_at
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                )
                ON CONFLICT (route_id)
                DO UPDATE SET
                    min_elevation_m = EXCLUDED.min_elevation_m,
                    max_elevation_m = EXCLUDED.max_elevation_m,
                    min_elevation_distance_m =
                        EXCLUDED.min_elevation_distance_m,
                    max_elevation_distance_m =
                        EXCLUDED.max_elevation_distance_m,
                    total_gain_m = EXCLUDED.total_gain_m,
                    total_loss_m = EXCLUDED.total_loss_m,
                    min_slope_percent = EXCLUDED.min_slope_percent,
                    max_slope_percent = EXCLUDED.max_slope_percent,
                    calculated_at = NOW()
                """,
                (
                    route_id,
                    stats["min_elevation_m"],
                    stats["max_elevation_m"],
                    stats["min_elevation_distance_m"],
                    stats["max_elevation_distance_m"],
                    stats["total_gain_m"],
                    stats["total_loss_m"],
                    min_slope,
                    max_slope,
                ),
            )

    return {
        "route_id": route_id,
        "sampled_points": len(elevations),
        "total_points": len(route_points),
        **stats,
        "min_slope_percent": min_slope,
        "max_slope_percent": max_slope,
    }
