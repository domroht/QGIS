import csv
import matplotlib.pyplot as plt
import warnings

INPUT_FILE = "data/output/elevation_profile.csv"
OUTPUT_FILE = "data/output/elevation_profile.png"

def read_profile() -> tuple[list[float], list[float]]:
    dist: list[float] = []
    elev:list[float] = []
    skipped_rows = 0

    with open(INPUT_FILE, "r", encoding="utf-8") as file:
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

def plot_elev_to_dist(dist: list[float], elev: list[float]) -> None:

    if dist is None or elev is None:
        raise ValueError("ERROR: 'dist' or 'elev' is None")

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
    plt.savefig(OUTPUT_FILE, dpi=150)
    plt.close()

def main():

    try:
        dist, elev = read_profile()
        plot_elev_to_dist(dist,elev)
        print("SUCCES: Elevation profile saved")
    
    except (FileNotFoundError, KeyError, ValueError) as e:
        print(e)


if __name__ == "__main__":
    main()