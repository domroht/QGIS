import hashlib
from pathlib import Path

from processing.fit_parser import extract_gps_points
from database import save_route


BASE_DIR = Path(__file__).resolve().parent

# Ret denne sti, hvis din FIT-fil ligger et andet sted.
FIT_FILE = BASE_DIR / "data" / "uploads" / "activity.fit"


def calculate_file_hash(file_path):
    """Calculate a SHA-256 hash for the FIT file."""

    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(4096), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


def main():
    if not FIT_FILE.exists():
        print(f"FIT file not found: {FIT_FILE}")
        return

    print(f"Reading: {FIT_FILE.name}")

    gps_points = extract_gps_points(FIT_FILE)

    if len(gps_points) < 2:
        print("The FIT file does not contain enough GPS points.")
        return

    route_hash = calculate_file_hash(FIT_FILE)

    route_name = FIT_FILE.stem

    route_id, status = save_route(
        name=route_name,
        gps_points=gps_points,
        route_hash=route_hash,
    )

    print("\nRoute saved successfully!")
    print(f"Route ID: {route_id}")
    print(f"Name: {route_name}")
    print(f"GPS points: {len(gps_points)}")
    print(f"Status: {status}")


if __name__ == "__main__":
    main()