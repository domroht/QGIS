import psycopg2


DATABASE_URL = "postgresql://postgres@localhost:5432/osmvelo"
ROUTE_ID = 1

SLOPE_THRESHOLD = 0.3
MIN_HILL_LENGTH_M = 50.0

ELEVATION_NOISE_THRESHOLD_M = 0.5


def get_connection():
    return psycopg2.connect(DATABASE_URL)


def ensure_route_stats_table():
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS route_terrain_stats (
                    route_id BIGINT PRIMARY KEY
                        REFERENCES routes(id)
                        ON DELETE CASCADE,

                    min_elevation_m DOUBLE PRECISION,
                    max_elevation_m DOUBLE PRECISION,

                    min_elevation_distance_m DOUBLE PRECISION,
                    max_elevation_distance_m DOUBLE PRECISION,

                    total_gain_m DOUBLE PRECISION,
                    total_loss_m DOUBLE PRECISION,

                    max_slope_percent DOUBLE PRECISION,
                    min_slope_percent DOUBLE PRECISION,

                    calculated_at TIMESTAMPTZ DEFAULT NOW()
                );
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
                    sequence,
                    distance_from_start,
                    elevation_m,
                    slope_percent
                FROM route_points
                WHERE route_id = %s
                  AND elevation_m IS NOT NULL
                ORDER BY sequence;
            """, (ROUTE_ID,))

            return cur.fetchall()

    finally:
        conn.close()


def calculate_elevation_gain_loss(points):
    total_gain = 0.0
    total_loss = 0.0

    for i in range(1, len(points)):
        previous_elevation = points[i - 1][2]
        current_elevation = points[i][2]

        difference = current_elevation - previous_elevation

        if abs(difference) < ELEVATION_NOISE_THRESHOLD_M:
            continue

        if difference > 0:
            total_gain += difference
        else:
            total_loss += abs(difference)

    return total_gain, total_loss


def calculate_basic_stats(points):
    elevations = [p[2] for p in points]

    total_gain, total_loss = calculate_elevation_gain_loss(points)

    min_point = min(points, key=lambda p: p[2])
    max_point = max(points, key=lambda p: p[2])

    valid_slopes = [
        p[3]
        for p in points
        if p[3] is not None
    ]

    return {
        "total_gain": total_gain,
        "total_loss": total_loss,
        "min_elevation": min(elevations),
        "max_elevation": max(elevations),
        "min_point": min_point,
        "max_point": max_point,
        "min_slope": min(valid_slopes),
        "max_slope": max(valid_slopes),
    }


def find_hills(points):
    hills = []

    current_type = None
    start_point = None
    end_point = None

    for point in points:
        sequence, distance, elevation, slope = point

        if slope is None:
            direction = None
        elif slope >= SLOPE_THRESHOLD:
            direction = "up"
        elif slope <= -SLOPE_THRESHOLD:
            direction = "down"
        else:
            direction = None

        if direction != current_type:

            if current_type is not None and start_point is not None:
                length = (
                    end_point[1] - start_point[1]
                )

                elevation_change = (
                    end_point[2] - start_point[2]
                )

                if length >= MIN_HILL_LENGTH_M:
                    hills.append({
                        "type": current_type,
                        "start_distance": start_point[1],
                        "end_distance": end_point[1],
                        "length": length,
                        "elevation_change": elevation_change,
                    })

            if direction is None:
                current_type = None
                start_point = None
                end_point = None
            else:
                current_type = direction
                start_point = point
                end_point = point

        elif current_type is not None:
            end_point = point

    if current_type is not None and start_point is not None:
        length = end_point[1] - start_point[1]
        elevation_change = end_point[2] - start_point[2]

        if length >= MIN_HILL_LENGTH_M:
            hills.append({
                "type": current_type,
                "start_distance": start_point[1],
                "end_distance": end_point[1],
                "length": length,
                "elevation_change": elevation_change,
            })

    return hills


def save_stats(stats):
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO route_terrain_stats (
                    route_id,
                    min_elevation_m,
                    max_elevation_m,
                    min_elevation_distance_m,
                    max_elevation_distance_m,
                    total_gain_m,
                    total_loss_m,
                    max_slope_percent,
                    min_slope_percent,
                    calculated_at
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    NOW()
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
                    max_slope_percent =
                        EXCLUDED.max_slope_percent,
                    min_slope_percent =
                        EXCLUDED.min_slope_percent,
                    calculated_at = NOW();
            """, (
                ROUTE_ID,
                stats["min_elevation"],
                stats["max_elevation"],
                stats["min_point"][1],
                stats["max_point"][1],
                stats["total_gain"],
                stats["total_loss"],
                stats["max_slope"],
                stats["min_slope"],
            ))

        conn.commit()

    finally:
        conn.close()


def main():

    ensure_route_stats_table()

    points = get_route_points()

    if not points:
        return

    stats = calculate_basic_stats(points)

    hills = find_hills(points)

    save_stats(stats)

    print_stats(stats)
    print_hills(hills)


if __name__ == "__main__":
    main()