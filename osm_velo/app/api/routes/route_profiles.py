
from pathlib import Path
from fastapi import APIRouter, HTTPException
from psycopg.rows import dict_row

from app.db.connection import get_connection
from app.services.elevation import analyse_elevation
from app.services.wind import analyse_wind
from app.schemas import WindAnalysisRequest

router = APIRouter(prefix="/api/route_profiles", tags=["route_profiles"])

@router.post("/{route_id}/elevation")
def run_elevation_analysis(route_id: int):
    try:
        return analyse_elevation(route_id)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{route_id}/wind")
def run_wind_analysis(route_id: int, request: WindAnalysisRequest):
    direction = 0.0 if request.wind_direction_deg == 360 else request.wind_direction_deg

    try:
        return analyse_wind(
            route_id,
            wind_speed_ms=request.wind_speed_ms,
            wind_direction_deg=direction,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{route_id}/analysis")
def get_analysis_results(route_id: int):
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT id, name, point_count, distance_m, created_at
                FROM public.routes
                WHERE id = %s
                """,
                (route_id,),
            )
            route = cursor.fetchone()

            if route is None:
                raise HTTPException(status_code=404, detail="Route not found.")

            cursor.execute(
                """
                SELECT
                    min_elevation_m,
                    max_elevation_m,
                    min_elevation_distance_m,
                    max_elevation_distance_m,
                    total_gain_m,
                    total_loss_m,
                    min_slope_percent,
                    max_slope_percent,
                    calculated_at
                FROM public.route_terrain_stats
                WHERE route_id = %s
                """,
                (route_id,),
            )

            elevation = cursor.fetchone()

            cursor.execute(
                """
                SELECT
                    COUNT(*) FILTER (
                        WHERE elevation_m IS NOT NULL
                    ) AS sampled_elevation_points,
                    COUNT(*) FILTER (
                        WHERE wind_effect_ms IS NOT NULL
                    ) AS points_with_wind_analysis
                FROM public.route_points
                WHERE route_id = %s
                """,
                (route_id,),
            )

            counts = cursor.fetchone()

    return {
        "route_id": route["id"],
        "name": route["name"],
        "point_count": route["point_count"],
        "distance_m": route["distance_m"],
        "created_at": route["created_at"],
        "elevation": elevation,
        "sampled_elevation_points": counts["sampled_elevation_points"],
        "points_with_wind_analysis": counts["points_with_wind_analysis"],
        "has_elevation_analysis": elevation is not None,
        "has_wind_analysis": counts["points_with_wind_analysis"] > 0,
    }
