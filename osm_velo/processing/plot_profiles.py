import csv
import matplotlib.pyplot as plt
import warnings
import psycopg2

INPUT_FILE_ELEV = "data/output/elevation_profile.csv"
OUTPUT_FILE_ELEV = "data/output/elevation_profile.png"

DATABASE_URL = "postgresql://postgres@localhost:5432/osmvelo"
ROUTE_ID = 1
OUTPUT_FILE_WIND = "data/output/wind_profile.png"

def get_elevation_profile() -> tuple[list[float], list[float]]:
    dist: list[float] = []
    elev: list[float] = []
    skipped_rows = 0

    with open(INPUT_FILE_ELEV, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        if reader.fieldnames is None or not {"distance_m", "elevation_m"}.issubset(reader.fieldnames):
            raise KeyError("ERROR: Profile must contain 'distance_m' and 'elevation_m'")

        for row in reader:
            if not row["distance_m"] or not row["elevation_m"]:
                skipped_rows += 1
                continue
    
            dist.append(float(row["distance_m"]))
            elev.append(float(row["elevation_m"]))


        if skipped_rows > 0: 
            warnings.warn("WARNING: Rows where skipped due to missing data in profile")
    return dist, elev

def plot_elevation_profile(dist: list[float], elev: list[float]) -> None:

    if not dist or not elev: 
        raise ValueError("ERROR: 'dist' or 'elev' is empty")
    
    if len(dist) != len(elev):
        raise ValueError("ERROR: 'dist' and 'elev' does not have same lenght")
    

    plt.figure(figsize=(14, 6))

    plt.plot(dist,elev)

    plt.xlabel("Distance (m)")
    plt.ylabel("Elevation (m)")
    plt.title("Elavation profile")

    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUTPUT_FILE_ELEV, dpi=150)
    plt.close()

def get_wind_profile():
    conn = psycopg2.connect(DATABASE_URL)

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    distance_from_start,
                    wind_effect_percent
                FROM route_points
                WHERE route_id = %s
                  AND wind_effect_percent IS NOT NULL
                ORDER BY sequence;
            """, (ROUTE_ID,))

            return cursor.fetchall()

    finally:
        conn.close()

def plot_wind_profile(data):

    if not data:
        raise ValueError("ERROR: no wind data to plot")

    distances = [row[0] for row in data]
    wind_effect = [row[1] for row in data]

    plt.figure(figsize=(14, 6))

    plt.plot(distances,wind_effect)

    plt.xlabel("Distance (m)")
    plt.ylabel("Wind effect (%)")
    plt.title("Wind profile")

    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUTPUT_FILE_WIND, dpi=150)
    plt.close()

def main():

    try:
        dist, elev = get_elevation_profile()
        plot_elevation_profile(dist,elev)
        print("SUCCES: Elevation profile saved")
    
    except (FileNotFoundError, KeyError, ValueError) as e:
        print(e)

    try: 
        data = get_wind_profile()
        plot_wind_profile(data)
        print("SUCCESS: Wind profile saved")
    
    except (ValueError) as e:
        print(e)


if __name__ == "__main__":
    main()