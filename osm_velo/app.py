import hashlib
from pathlib import Path

from flask import Flask, render_template, request

from processing.fit_parser import extract_gps_points
from database import save_route


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "data" / "uploads"

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def calculate_file_hash(file_path):

    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(4096), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    uploaded_file = request.files.get("fit_file")

    if uploaded_file is None or uploaded_file.filename == "":
        return "No file selected", 400

    if not uploaded_file.filename.lower().endswith(".fit"):
        return "Only FIT files are allowed", 400

    temporary_name = hashlib.sha256(
        uploaded_file.filename.encode("utf-8")
    ).hexdigest()[:16] + ".fit"

    file_path = UPLOAD_FOLDER / temporary_name
    uploaded_file.save(file_path)

    try:
        route_hash = calculate_file_hash(file_path)
        gps_points = extract_gps_points(file_path)

        if len(gps_points) < 2:
            return "The file must contain at least two GPS points.", 400

        route_id, status = save_route(
            name=Path(uploaded_file.filename).stem,
            gps_points=gps_points,
            route_hash=route_hash,
        )

        return {
            "message": "Route saved successfully",
            "route_id": route_id,
            "name": Path(uploaded_file.filename).stem,
            "status": status,
            "point_count": len(gps_points),
        }

    except Exception:
        app.logger.exception("Failed to process uploaded route")
        return "Could not process or save the route.", 500


if __name__ == "__main__":
    app.run(debug=True)