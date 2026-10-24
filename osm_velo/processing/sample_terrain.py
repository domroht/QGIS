import os
from collections import defaultdict

import psycopg2
import rasterio
from pyproj import Transformer


DATABASE_URL = "postgresql://postgres@localhost:5432/osmvelo"
ROUTE_ID = 1

TERRAIN_DIR = "data/terrain"

SOURCE_CRS = "EPSG:4326"
TERRAIN_CRS = "EPSG:25832"

# gøre opfor at DHM har en usikkerhed i data
SLOPE_WINDOW_M = 100.0


def get_connection():
    return psycopg2.connect(DATABASE_URL)


def ensure_database():
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                ALTER TABLE route_points
                ADD COLUMN IF NOT EXISTS elevation_m DOUBLE PRECISION;
            """)

            cur.execute("""
                ALTER TABLE route_points
                ADD COLUMN IF NOT EXISTS slope_percent DOUBLE PRECISION;
            """)

        conn.commit()

    finally:
        conn.close()


def get_route_points():
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    id,
                    sequence,
                    ST_X(geom) AS longitude,
                    ST_Y(geom) AS latitude,
                    distance_from_start
                FROM route_points
                WHERE route_id = %s
                ORDER BY sequence;
            """, (ROUTE_ID,))

            return cur.fetchall()

    finally:
        conn.close()


def build_tile_index():

    tiles = []

    for filename in os.listdir(TERRAIN_DIR):
        if not filename.lower().endswith(".tif"):
            continue

        path = os.path.join(TERRAIN_DIR, filename)

        with rasterio.open(path) as src:
            if src.crs is None:
                continue

            if src.crs.to_string() != TERRAIN_CRS:
                continue

            bounds = src.bounds

        tiles.append({
            "path": path,
            "min_x": bounds.left,
            "max_x": bounds.right,
            "min_y": bounds.bottom,
            "max_y": bounds.top,
        })

    return tiles


def find_tile_for_point(x, y, tiles):
    for tile in tiles:
        if (
            tile["min_x"] <= x <= tile["max_x"]
            and tile["min_y"] <= y <= tile["max_y"]
        ):
            return tile

    return None


def group_points_by_tile(points, tiles):
    transformer = Transformer.from_crs(
        SOURCE_CRS,
        TERRAIN_CRS,
        always_xy=True
    )

    grouped = defaultdict(list)

    for point in points:
        point_id, sequence, longitude, latitude, distance = point

        x, y = transformer.transform(longitude, latitude)

        tile = find_tile_for_point(x, y, tiles)

        if tile is None:
            grouped[None].append({
                "id": point_id,
                "sequence": sequence,
                "distance": distance,
                "x": x,
                "y": y,
            })
            continue

        grouped[tile["path"]].append({
            "id": point_id,
            "sequence": sequence,
            "distance": distance,
            "x": x,
            "y": y,
        })

    return grouped


def sample_tiles(grouped):
    elevations = {}

    missing_tile = 0
    nodata = 0

    for tile_path, points in grouped.items():

        if tile_path is None:
            missing_tile += len(points)
            continue

        with rasterio.open(tile_path) as src:

            for point in points:
                value = next(
                    src.sample([(point["x"], point["y"])])
                )[0]

                if src.nodata is not None and value == src.nodata:
                    elevations[point["id"]] = None
                    nodata += 1
                else:
                    elevations[point["id"]] = float(value)

    return elevations, nodata, missing_tile


def update_elevations(elevations):
    conn = get_connection()

    try:
        with conn.cursor() as cur:

            for point_id, elevation in elevations.items():
                cur.execute("""
                    UPDATE route_points
                    SET elevation_m = %s
                    WHERE id = %s;
                """, (elevation, point_id))

        conn.commit()

    finally:
        conn.close()


def calculate_slopes():

    conn = get_connection()

    try:
        with conn.cursor() as cur:

            cur.execute("""
                SELECT
                    id,
                    sequence,
                    distance_from_start,
                    elevation_m
                FROM route_points
                WHERE route_id = %s
                  AND elevation_m IS NOT NULL
                ORDER BY sequence;
            """, (ROUTE_ID,))

            points = cur.fetchall()

            updates = []

            for i, current in enumerate(points):

                current_id = current[0]
                current_distance = current[2]
                current_elevation = current[3]

                previous = None

                for j in range(i - 1, -1, -1):
                    candidate = points[j]

                    distance_difference = (
                        current_distance - candidate[2]
                    )

                    if distance_difference >= SLOPE_WINDOW_M:
                        previous = candidate
                        break

                if previous is None:
                    updates.append((None, current_id))
                    continue

                previous_distance = previous[2]
                previous_elevation = previous[3]

                distance_difference = (
                    current_distance - previous_distance
                )

                if distance_difference <= 0:
                    slope = None
                else:
                    slope = (
                        (current_elevation - previous_elevation)
                        / distance_difference
                        * 100.0
                    )

                updates.append((slope, current_id))

            for slope, point_id in updates:
                cur.execute("""
                    UPDATE route_points
                    SET slope_percent = %s
                    WHERE id = %s;
                """, (slope, point_id))

        conn.commit()

    finally:
        conn.close()


def main():

    ensure_database()

    points = get_route_points()

    tiles = build_tile_index()

    grouped = group_points_by_tile(points, tiles)

    elevations, nodata, missing_tile = sample_tiles(grouped)

    update_elevations(elevations)

    calculate_slopes()


if __name__ == "__main__":
    main()