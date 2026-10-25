import math
import psycopg2

DATABASE_URL = "postgresql://postgres@localhost:5432/osmvelo"
ROUTE_ID = 1

WIND_SPEED = 5.0
WIND_DIRECTION = 240.0

def alter_database():
    conn = psycopg2.connect(DATABASE_URL)

    try:
        with conn.cursor() as cursor:

            cursor.execute("""
                ALTER TABLE route_points
                ADD COLUMN IF NOT EXISTS
                travel_direction_deg DOUBLE PRECISION;
            """)

            cursor.execute("""
                ALTER TABLE route_points
                ADD COLUMN IF NOT EXISTS
                wind_effect_percent DOUBLE PRECISION;
            """)

            cursor.execute("""
                ALTER TABLE route_points
                ADD COLUMN IF NOT EXISTS
                wind_effect_ms DOUBLE PRECISION;
            """)

        conn.commit()

    finally:
        conn.close()

def get_route_points():

    conn = psycopg2.connect(DATABASE_URL)

    try:
        with conn.cursor() as cursor:

            cursor.execute("""
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

            return cursor.fetchall()

    finally:
        conn.close()

def calculate_point_direction(current_lon, current_lat, next_lon, next_lan):

    lon_1 = math.radians(current_lon)
    lat_1 = math.radians(current_lat)

    lon_2 = math.radians(next_lon)
    lat_2 = math.radians(next_lan)

    delta_lon = lon_2 - lon_1

    x =  math.sin(delta_lon) * math.cos(lat_2)

    y = math.cos(lat_1) * math.sin(lat_2) - math.sin(lat_1) * math.cos(lat_2) * math.cos(delta_lon)


    direction = math.degrees(math.atan2(x, y))

    return (direction + 360.0) % 360.0

# målt i et spektrum: medvind (100%) til modvind (-100%) 
def calculate_wind_effect(travel_direction):

    wind_movement_direction = WIND_DIRECTION + 180.0 % 360.0

    angle = wind_movement_direction - travel_direction

    normalized_angle = angle + 180.0 % 360.0 - 180.0

    effect = math.cos(math.radians(normalized_angle))

    return effect * 100.0

def calculate_wind(points):

    results = []

    for index, point in enumerate(points):

        point_id = point[0]

        longitude = point[2]
        latitude = point[3]

        if index == 0:

            next_point = points[index + 1]

            next_longitude = next_point[2]
            next_latitude = next_point[3]

            travel_direction = calculate_point_direction(
                longitude,
                latitude,
                next_longitude,
                next_latitude,
            )

        elif index == len(points) - 1:

            previous_point = points[index - 1]

            previous_longitude = previous_point[2]
            previous_latitude = previous_point[3]

            travel_direction = calculate_point_direction(
                previous_longitude,
                previous_latitude,
                longitude,
                latitude,
            )

        else:

            previous_point = points[index - 1]
            next_point = points[index + 1]

            previous_longitude = previous_point[2]
            previous_latitude = previous_point[3]

            next_longitude = next_point[2]
            next_latitude = next_point[3]

            travel_direction = calculate_point_direction(
                previous_longitude,
                previous_latitude,
                next_longitude,
                next_latitude,
            )

        wind_effect_percent = calculate_wind_effect(travel_direction)


        wind_effect_ms = WIND_SPEED * wind_effect_percent / 100.0

        results.append(
            (
                point_id,
                travel_direction,
                wind_effect_percent,
                wind_effect_ms,
            )
        )

    return results

def save_wind_data(results):

    conn = psycopg2.connect(DATABASE_URL)

    try:
        with conn.cursor() as cursor:

            for (
                point_id,
                travel_direction,
                wind_effect_percent,
                wind_effect_ms,
            ) in results:

                cursor.execute("""
                    UPDATE route_points
                    SET
                        travel_direction_deg = %s,
                        wind_effect_percent = %s,
                        wind_effect_ms = %s
                    WHERE id = %s;
                """, (
                    travel_direction,
                    wind_effect_percent,
                    wind_effect_ms,
                    point_id,
                ))

        conn.commit()

    finally:
        conn.close()


def main():

    alter_database()

    points = get_route_points()

    if len(points) < 2:
        print("mindre en to rute points")
        return

    results = calculate_wind(points)

    save_wind_data(results)



if __name__ == "__main__":
    main()