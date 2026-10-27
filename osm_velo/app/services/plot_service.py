
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from app.db.connection import get_connection


PROJECT_DIR = Path(__file__).resolve().parents[2]
RESULTS_DIR = PROJECT_DIR / "data" / "results"


def load_plot_data(route_id: int) -> dict:

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT name
                FROM public.routes
                WHERE id = %s
                """,
                (route_id,),
            )
            route = cursor.fetchone()

            if route is None:
                raise ValueError(f"Route {route_id} does not exist.")

            cursor.execute(
                """
                SELECT
                    sequence,
                    distance_from_start,
                    elevation_m,
                    slope_percent,
                    travel_direction_deg,
                    wind_effect_ms,
                    wind_effect_percent
                FROM public.route_points
                WHERE route_id = %s
                ORDER BY sequence
                """,
                (route_id,),
            )
            rows = cursor.fetchall()

    if len(rows) < 2:
        raise ValueError(f"Route {route_id} does not have enough GPS points to plot.")

    return {
        "name": route[0],
        "sequence": [row[0] for row in rows],
        "distance_m": np.array(
            [row[1] for row in rows], dtype=float
        ),
        "elevation_m": np.array(
            [np.nan if row[2] is None else row[2] for row in rows],
            dtype=float,
        ),
        "slope_percent": np.array(
            [np.nan if row[3] is None else row[3] for row in rows],
            dtype=float,
        ),
        "travel_direction_deg": np.array(
            [np.nan if row[4] is None else row[4] for row in rows],
            dtype=float,
        ),
        "wind_effect_ms": np.array(
            [np.nan if row[5] is None else row[5] for row in rows],
            dtype=float,
        ),
        "wind_effect_percent": np.array(
            [np.nan if row[6] is None else row[6] for row in rows],
            dtype=float,
        ),
    }


def plot_elevation(data: dict, output_path: Path) -> None:

    distance_km = data["distance_m"] / 1000
    elevation = data["elevation_m"]
    valid = np.isfinite(elevation)

    if not np.any(valid):
        raise ValueError("No elevation data is available for this route.")

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(distance_km, elevation, linewidth=1.5)
    ax.set_title(f"Elevation profile — {data['name']}")
    ax.set_xlabel("Distance (km)")
    ax.set_ylabel("Elevation (m)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_slope(data: dict, output_path: Path) -> None:

    distance_km = data["distance_m"] / 1000
    slope = data["slope_percent"]
    valid = np.isfinite(slope)

    if not np.any(valid):
        raise ValueError("No slope data is available. Run elevation analysis first.")

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(distance_km, slope, linewidth=1.0)
    ax.axhline(0, linewidth=0.8)
    ax.set_title(f"Slope profile — {data['name']}")
    ax.set_xlabel("Distance (km)")
    ax.set_ylabel("Slope (%)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_wind(data: dict, output_path: Path) -> None:

    distance_km = data["distance_m"] / 1000
    wind = data["wind_effect_ms"]
    valid = np.isfinite(wind)

    if not np.any(valid):
        raise ValueError("No wind data is available. Run wind analysis first.")

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(distance_km, wind, linewidth=1.2)
    ax.axhline(0, linewidth=0.8)
    ax.set_title(f"Wind effect — {data['name']}")
    ax.set_xlabel("Distance (km)")
    ax.set_ylabel("Wind component (m/s)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def generate_route_plots(route_id: int) -> dict:

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    data = load_plot_data(route_id)
    route_dir = RESULTS_DIR / f"route_{route_id}"
    route_dir.mkdir(parents=True, exist_ok=True)

    outputs = {
        "elevation": route_dir / "elevation.png",
        "slope": route_dir / "slope.png",
        "wind": route_dir / "wind.png",
    }

    plot_elevation(data, outputs["elevation"])
    plot_slope(data, outputs["slope"])
    plot_wind(data, outputs["wind"])

    return {
        "route_id": route_id,
        "route_name": data["name"],
        "plots": {
            name: {
                "filename": path.name,
                "path": str(path.relative_to(PROJECT_DIR)),
            }
            for name, path in outputs.items()
        },
    }
