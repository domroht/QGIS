import rasterio
import psycopg2

from pathlib import Path
from rasterio.warp import transform_bounds
from psycopg2.extras import RealDictCursor

PROJECT_DIR = Path(__file__).resolve().parent.parent
TERRAIN_DIR = PROJECT_DIR / "data" / "terrain"

DATABASE_URL = "postgresql://postgres:your_password@localhost:5432/osmvelo"

def get_route_bounds(route_id):
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    ST_XMin(bounds) AS min_x,
                    ST_YMin(bounds) AS min_y,
                    ST_XMax(bounds) AS max_x,
                    ST_YMax(bounds) AS max_y
                FROM (
                    SELECT
                        ST_Envelope(
                            ST_Transform(route, 25832)
                        ) AS bounds
                    FROM routes
                    WHERE id = %s
                ) AS r;
                """,
                (route_id,),
            )
            result = cur.fetchone()

    if result is None or result["min_x"] is None:
        raise ValueError(f"Rute {route_id} blev ikke fundet.")

    return (
        result["min_x"],
        result["min_y"],
        result["max_x"],
        result["max_y"],
    )


def find_relevant_tiles(route_bounds):
    
    route_min_x, route_min_y, route_max_x, route_max_y = route_bounds
    relevant = []

    for tif_path in sorted(TERRAIN_DIR.glob("*.tif")):
        try:
            with rasterio.open(tif_path) as src:
                if src.crs is None:
                    print(f"spring over mangler CRS: {tif_path.name}")
                    continue

                # transformer rasterets bounds til EPSG:25832.
                tile_bounds = transform_bounds(
                    src.crs,
                    "EPSG:25832",
                    *src.bounds,
                    densify_pts=21,
                )

                tile_min_x, tile_min_y, tile_max_x, tile_max_y = tile_bounds

                overlaps = (
                    tile_min_x <= route_max_x
                    and tile_max_x >= route_min_x
                    and tile_min_y <= route_max_y
                    and tile_max_y >= route_min_y
                )

                if overlaps:
                    relevant.append(tif_path)

        except Exception as exc:
            print(f"fejl: {tif_path.name}: {exc}")

    return relevant


def main():
    if not TERRAIN_DIR.is_dir():
        raise FileNotFoundError(
            f"mappe med .tif filer ikke fundet: {TERRAIN_DIR}"
        )

    bounds = get_route_bounds(1)

    tiles = find_relevant_tiles(bounds)

    print(f"\nFandt {len(tiles)} relevante fliser:")
    for tile in tiles:
        print(f"  {tile.name}")

    if not tiles:
        print("fejl: ingen raster overlapper med ruten")


if __name__ == "__main__":
    main()
