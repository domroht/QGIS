
from pathlib import Path

import geopandas as gpd
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from psycopg.rows import dict_row
from shapely import wkb

from app.db.connection import get_connection
from app.services.plot_service import RESULTS_DIR, generate_route_plots

PROJECT_DIR = Path(__file__).resolve().parents[2]
EXPORT_DIR = PROJECT_DIR / "data" / "results"

router = APIRouter(prefix="/api/route_visulization", tags=["route_visulization"])

@router.post("/{route_id}/plots")
def create_route_plots(route_id: int):
    try:
        return generate_route_plots(route_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not generate route plots: {exc}",
        ) from exc


@router.get("/{route_id}/plots/{plot_name}")
def get_route_plot(route_id: int, plot_name: str):

    if plot_name not in {"elevation", "slope", "wind"}:
        raise HTTPException(
            status_code=404,
            detail="Unknown plot. Choose elevation, slope, or wind.",
        )

    plot_path = RESULTS_DIR / f"route_{route_id}" / f"{plot_name}.png"

    if not plot_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Plot not found. Generate the route plots first.",
        )

    return FileResponse(
        path=plot_path,
        media_type="image/png",
        filename=plot_path.name,
    )


@router.get("/{route_id}/export.gpkg")
def export_route_geopackage(route_id: int):

    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    r.id,
                    r.name,
                    r.point_count,
                    r.distance_m,
                    ST_AsBinary(
                        COALESCE(
                            r.route,
                            (
                                SELECT ST_MakeLine(rp.geom ORDER BY rp.sequence)
                                FROM public.route_points AS rp
                                WHERE rp.route_id = r.id
                            )
                        )
                    ) AS geometry_wkb
                FROM public.routes AS r
                WHERE r.id = %s
                """,
                (route_id,),
            )
            route = cursor.fetchone()

            if route is None:
                raise HTTPException(status_code=404, detail="Route not found.")

            cursor.execute(
                """
                SELECT
                    sequence,
                    distance_from_start,
                    elevation_m,
                    slope_percent,
                    travel_direction_deg,
                    wind_effect_percent,
                    wind_effect_ms,
                    ST_AsBinary(geom) AS geometry_wkb
                FROM public.route_points
                WHERE route_id = %s
                ORDER BY sequence
                """,
                (route_id,),
            )
            point_rows = cursor.fetchall()

    if route["geometry_wkb"] is None:
        raise HTTPException(
            status_code=404,
            detail="This route has no usable geometry to export.",
        )

    if not point_rows:
        raise HTTPException(
            status_code=404,
            detail="This route has no route points to export.",
        )

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    export_path = EXPORT_DIR / f"route_{route_id}.gpkg"

    try:
        route_geometry = wkb.loads(bytes(route["geometry_wkb"]))

        route_gdf = gpd.GeoDataFrame(
            [
                {
                    "route_id": route["id"],
                    "name": route["name"],
                    "point_count": route["point_count"],
                    "distance_m": route["distance_m"],
                    "geometry": route_geometry,
                }
            ],
            geometry="geometry",
            crs="EPSG:4326",
        )

        point_records = []
        for row in point_rows:
            record = dict(row)
            geometry_wkb = record.pop("geometry_wkb")
            record["geometry"] = wkb.loads(bytes(geometry_wkb))
            point_records.append(record)

        points_gdf = gpd.GeoDataFrame(
            point_records,
            geometry="geometry",
            crs="EPSG:4326",
        )

        if export_path.exists():
            export_path.unlink()

        route_gdf.to_file(
            export_path,
            layer="routes",
            driver="GPKG",
            index=False,
        )
        points_gdf.to_file(
            export_path,
            layer="route_points",
            driver="GPKG",
            mode="a",
            index=False,
        )

    except Exception as exc:
        export_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail=f"Could not create GeoPackage: {exc}",
        ) from exc

    return FileResponse(
        path=export_path,
        media_type="application/geopackage+sqlite3",
        filename=export_path.name,
    )
