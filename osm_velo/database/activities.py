import json
import psycopg


DATABASE_URL = "postgresql://postgres@localhost:5432/geotrack"


def save_activity(name, activity_data, gps_points, file_hash):

    if not gps_points:
        raise ValueError("No GPS points found in FIT file.")

    geometry = {
        "type": "LineString",
        "coordinates": gps_points,
    }

    geometry_json = json.dumps(geometry)

    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT id
                FROM activities
                WHERE file_hash = %s
                """,
                (file_hash,),
            )

            existing = cursor.fetchone()

            if existing:
                activity_id = existing[0]

                cursor.execute(
                    """
                    UPDATE activities
                    SET name = %s,
                        start_time = %s,
                        route = ST_SetSRID(
                            ST_GeomFromGeoJSON(%s),
                            4326
                        ),
                        total_distance = %s,
                        total_timer_time = %s,
                        total_elapsed_time = %s,
                        total_ascent = %s,
                        avg_speed = %s
                    WHERE id = %s
                    """,
                    (
                        name,
                        activity_data["start_time"],
                        geometry_json,
                        activity_data["total_distance"],
                        activity_data["total_timer_time"],
                        activity_data["total_elapsed_time"],
                        activity_data["total_ascent"],
                        activity_data["avg_speed"],
                        activity_id,
                    ),
                )

                return activity_id, "updated"

            cursor.execute(
                """
                INSERT INTO activities (
                    name,
                    start_time,
                    route,
                    file_hash,
                    total_distance,
                    total_timer_time,
                    total_elapsed_time,
                    total_ascent,
                    avg_speed
                )
                VALUES (
                    %s,
                    %s,
                    ST_SetSRID(
                        ST_GeomFromGeoJSON(%s),
                        4326
                    ),
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                RETURNING id
                """,
                (
                    name,
                    activity_data["start_time"],
                    geometry_json,
                    file_hash,
                    activity_data["total_distance"],
                    activity_data["total_timer_time"],
                    activity_data["total_elapsed_time"],
                    activity_data["total_ascent"],
                    activity_data["avg_speed"],
                ),
            )

            activity_id = cursor.fetchone()[0]

            return activity_id, "created"

def get_activity(activity_id):

    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    id,
                    name,
                    start_time,
                    total_distance,
                    total_timer_time,
                    total_elapsed_time,
                    total_ascent,
                    avg_speed,
                    ST_AsGeoJSON(route)
                FROM activities
                WHERE id = %s
                """,
                (activity_id,),
            )

            row = cursor.fetchone()

            if row is None:
                return None

            return {
                "id": row[0],
                "name": row[1],
                "start_time": row[2],
                "total_distance": row[3],
                "total_timer_time": row[4],
                "total_elapsed_time": row[5],
                "total_ascent": row[6],
                "avg_speed": row[7],
                "route": json.loads(row[8]),
            }