import json

import psycopg


DATABASE_URL = "postgresql://postgres@localhost:5432/geotrack"


def save_route(name, gps_points, route_hash):

    if not gps_points:
        raise ValueError("No GPS points found in route.")

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
                FROM routes
                WHERE route_hash = %s
                """,
                (route_hash,),
            )

            existing = cursor.fetchone()

            if existing:
                route_id = existing[0]

                cursor.execute(
                    """
                    UPDATE routes
                    SET name = %s,
                        route = ST_SetSRID(
                            ST_GeomFromGeoJSON(%s),
                            4326
                        )
                    WHERE id = %s
                    """,
                    (
                        name,
                        geometry_json,
                        route_id,
                    ),
                )

                return route_id, "updated"

            cursor.execute(
                """
                INSERT INTO routes (
                    name,
                    route_hash,
                    route
                )
                VALUES (
                    %s,
                    %s,
                    ST_SetSRID(
                        ST_GeomFromGeoJSON(%s),
                        4326
                    )
                )
                RETURNING id
                """,
                (
                    name,
                    route_hash,
                    geometry_json,
                ),
            )

            route_id = cursor.fetchone()[0]

            return route_id, "created"


def get_route(route_id):
    """
    Retrieve a saved route and its GeoJSON geometry from PostGIS.
    """

    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    name,
                    route_hash,
                    created_at,
                    ST_AsGeoJSON(route)
                FROM routes
                WHERE id = %s
                """,
                (route_id,),
            )

            row = cursor.fetchone()

            if row is None:
                return None

            return {
                "id": row[0],
                "name": row[1],
                "route_hash": row[2],
                "created_at": row[3].isoformat(),
                "geometry": json.loads(row[4]),
            }