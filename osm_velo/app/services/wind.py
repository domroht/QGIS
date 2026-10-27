
import math

from app.db.connection import get_connection


def calculate_bearing(lon1: float, lat1: float, lon2: float, lat2: float) -> float:

    lon1_rad = math.radians(lon1)
    lat1_rad = math.radians(lat1)
    lon2_rad = math.radians(lon2)
    lat2_rad = math.radians(lat2)

    delta_lon = lon2_rad - lon1_rad

    x = math.sin(delta_lon) * math.cos(lat2_rad)
    y = (
        math.cos(lat1_rad) * math.sin(lat2_rad)
        - math.sin(lat1_rad)
        * math.cos(lat2_rad)
        * math.cos(delta_lon)
    )

    return (math.degrees(math.atan2(x, y)) + 360) % 360


def calculate_wind_effect(travel_direction_deg: float, wind_speed_ms: float, wind_direction_deg: float) -> tuple[float, float]:

    if wind_speed_ms < 0:
        raise ValueError("Wind speed cannot be negative.")

    if not math.isfinite(wind_speed_ms):
        raise ValueError("Wind speed must be finite.")

    if not math.isfinite(travel_direction_deg):
        raise ValueError("Travel direction must be finite.")

    if not math.isfinite(wind_direction_deg):
        raise ValueError("Wind direction must be finite.")

    wind_to_deg = (wind_direction_deg + 180) % 360

    angle_rad = math.radians((wind_to_deg - travel_direction_deg + 180) % 360 - 180)

    wind_effect_ms = -wind_speed_ms * math.cos(angle_rad)

    wind_effect_percent = (
        0.0
        if wind_speed_ms == 0
        else wind_effect_ms / wind_speed_ms * 100
    )

    return wind_effect_ms, max(-100.0, min(100.0, wind_effect_percent))


def load_route_points(route_id: int) -> list[tuple[int, float, float]]:

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT sequence, ST_X(geom), ST_Y(geom)
                FROM public.route_points
                WHERE route_id = %s
                ORDER BY sequence
                """,
                (route_id,),
            )
            rows = cursor.fetchall()

    if len(rows) < 2:
        raise ValueError(f"Route {route_id} does not have enough GPS points.")

    return [
        (int(sequence), float(longitude), float(latitude))
        for sequence, longitude, latitude in rows
    ]


def analyse_wind(route_id: int, wind_speed_ms: float, wind_direction_deg: float) -> dict:

    if not math.isfinite(wind_speed_ms) or wind_speed_ms < 0:
        raise ValueError("Wind speed must be a finite non-negative number.")

    if not math.isfinite(wind_direction_deg):
        raise ValueError("Wind direction must be finite.")

    wind_direction_deg = wind_direction_deg % 360

    route_points = load_route_points(route_id)

    results: list[tuple[int, float, float, float]] = []

    for index, (sequence, longitude, latitude) in enumerate(route_points):
        if index < len(route_points) - 1:
            _, next_lon, next_lat = route_points[index + 1]
            bearing = calculate_bearing(
                longitude, latitude, next_lon, next_lat
            )
        else:
            _, previous_lon, previous_lat = route_points[index - 1]
            bearing = calculate_bearing(
                previous_lon, previous_lat, longitude, latitude
            )

        effect_ms, effect_percent = calculate_wind_effect(
            bearing,
            wind_speed_ms,
            wind_direction_deg,
        )

        results.append(
            (sequence, bearing, effect_percent, effect_ms)
        )

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.executemany(
                """
                UPDATE public.route_points
                SET travel_direction_deg = %s,
                    wind_effect_percent = %s,
                    wind_effect_ms = %s
                WHERE route_id = %s
                  AND sequence = %s
                """,
                [
                    (bearing, percent, effect_ms, route_id, sequence)
                    for sequence, bearing, percent, effect_ms in results
                ],
            )

    headwind_points = sum(
        1 for _, _, _, effect_ms in results if effect_ms > 0.05
    )
    tailwind_points = sum(
        1 for _, _, _, effect_ms in results if effect_ms < -0.05
    )
    crosswind_points = len(results) - headwind_points - tailwind_points

    return {
        "route_id": route_id,
        "point_count": len(results),
        "wind_speed_ms": wind_speed_ms,
        "wind_direction_deg": wind_direction_deg,
        "headwind_points": headwind_points,
        "tailwind_points": tailwind_points,
        "crosswind_points": crosswind_points,
    }
