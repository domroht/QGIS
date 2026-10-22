import json
import psycopg

DATABASE_URL = "postgresql://postgres@localhost:5432/osmvelo"

def save_route(name, gps_points, route_hash):

    if len(gps_points) < 2:
        raise ValueError("rute skal indeholde mindst to GPS-punkter")

    coordinates = []

    for point in gps_points:
        if len(point) < 2:
            raise ValueError("GPS-punkt skal indeholde longitude og latitude")

        longitude = float(point[0])
        latitude = float(point[1])

        if not (-180 <= longitude <= 180):
            raise ValueError(f"Ugyldig longitude: {longitude}")

        if not (-90 <= latitude <= 90):
            raise ValueError(f"Ugyldig latitude: {latitude}")

        coordinates.append([longitude, latitude])

    geometry = {
        "type": "LineString",
        "coordinates": coordinates,
    }

    geometry_json = json.dumps(geometry)

    longitudes = [point[0] for point in coordinates]
    latitudes = [point[1] for point in coordinates]

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

            existing_route = cursor.fetchone()

            if existing_route:
                route_id = existing_route[0]

                cursor.execute(
                    """
                    UPDATE routes
                    SET
                        name = %s,
                        route = ST_SetSRID(
                            ST_GeomFromGeoJSON(%s),
                            4326
                        )
                    WHERE id = %s
                    """,
                    (name, geometry_json, route_id),
                )

                status = "updated"

            else:
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
                    (name, route_hash, geometry_json),
                )

                route_id = cursor.fetchone()[0]
                status = "created"

            cursor.execute(
                """
                DELETE FROM route_points
                WHERE route_id = %s
                """,
                (route_id,),
            )

            cursor.execute(
                """
                WITH points AS (
                    SELECT
                        point_sequence,
                        ST_SetSRID(
                            ST_MakePoint(longitude, latitude),
                            4326
                        ) AS geom
                    FROM unnest(
                        %s::double precision[],
                        %s::double precision[]
                    ) WITH ORDINALITY
                    AS p(
                        longitude,
                        latitude,
                        point_sequence
                    )
                ),
                previous_points AS (
                    SELECT
                        point_sequence,
                        geom,
                        LAG(geom) OVER (
                            ORDER BY point_sequence
                        ) AS previous_geom
                    FROM points
                ),
                segments AS (
                    SELECT
                        point_sequence,
                        geom,
                        CASE
                            WHEN previous_geom IS NULL THEN
                                0::double precision
                            ELSE ST_Distance(
                                geom::geography,
                                previous_geom::geography
                            )
                        END AS segment_distance
                    FROM previous_points
                ),
                measured AS (
                    SELECT
                        point_sequence,
                        geom,
                        SUM(segment_distance) OVER (
                            ORDER BY point_sequence
                            ROWS BETWEEN UNBOUNDED PRECEDING
                            AND CURRENT ROW
                        ) AS distance_from_start
                    FROM segments
                )
                INSERT INTO route_points (
                    route_id,
                    sequence,
                    geom,
                    distance_from_start
                )
                SELECT
                    %s,
                    point_sequence::integer,
                    geom,
                    distance_from_start
                FROM measured
                ORDER BY point_sequence
                """,
                (
                    longitudes,
                    latitudes,
                    route_id,
                ),
            )

    return route_id, status


def get_route_points(route_id):

    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    sequence,
                    ST_X(geom) AS longitude,
                    ST_Y(geom) AS latitude,
                    distance_from_start
                FROM route_points
                WHERE route_id = %s
                ORDER BY sequence
                """,
                (route_id,),
            )

            rows = cursor.fetchall()

    return [
        {
            "sequence": row[0],
            "longitude": row[1],
            "latitude": row[2],
            "distance_from_start": row[3],
        }
        for row in rows
    ]
