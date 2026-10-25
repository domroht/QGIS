import csv
import psycopg2


DATABASE_URL = "postgresql://postgres@localhost:5432/osmvelo"
ROUTE_ID = 1
OUTPUT_FILE = "data/output/elevation_profile.csv"

def get_profile_data() -> list[tuple[int, float, float, float, float, float]]:
    conn = psycopg2.connect(DATABASE_URL)

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    sequence,
                    distance_from_start,
                    ST_X(geom) AS longitude,
                    ST_Y(geom) AS latitude,
                    elevation_m,
                    slope_percent
                FROM route_points
                WHERE route_id = %s
                  AND elevation_m IS NOT NULL
                ORDER BY sequence;
            """, (ROUTE_ID,))

            return cursor.fetchall()

    finally:
        conn.close()


def write_csv(rows: list[tuple[int, float, float, float, float, float]]) -> None:
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as file:

        writer = csv.writer(file)

        writer.writerow([
            "sequence",
            "distance_m",
            "longitude",
            "latitude",
            "elevation_m",
            "slope_percent",
        ])

        for row in rows:
            writer.writerow([
                row[0],
                round(row[1], 3),
                row[2],
                row[3],
                round(row[4], 3),
                None if row[5] is None else round(row[5], 3),
            ])


def main():
    rows = get_profile_data()
    write_csv(rows)



if __name__ == "__main__":
    main()