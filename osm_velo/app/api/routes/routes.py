
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile
from psycopg.rows import dict_row

from app.db.connection import get_connection
from app.schemas import RouteUploadResponse
from app.services.route_service import import_gpx

PROJECT_DIR = Path(__file__).resolve().parents[2]
UPLOAD_DIR = PROJECT_DIR / "data" / "uploads"

MAX_UPLOAD_SIZE = 50 * 1024 * 1024

router = APIRouter(prefix="/api/routes", tags=["routes"])

@router.post("", response_model=RouteUploadResponse, status_code=201)
async def upload_route(file: Annotated[UploadFile, File(...)]):
    if not file.filename or Path(file.filename).suffix.lower() != ".gpx":
        raise HTTPException(
            status_code=400,
            detail="Please upload a GPX file.",
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    temp_path = None
    size = 0

    try:
        with NamedTemporaryFile(
            mode="wb",
            suffix=".gpx",
            prefix="upload_",
            dir=UPLOAD_DIR,
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)

            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break

                size += len(chunk)
                if size > MAX_UPLOAD_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="The uploaded GPX file exceeds 50 MB.",
                    )

                temp_file.write(chunk)

        return import_gpx(temp_path, name=Path(file.filename).stem)

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not import the GPX file: {exc}",
        ) from exc
    finally:
        await file.close()
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


@router.get("")
def list_routes():
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    name,
                    point_count,
                    distance_m,
                    created_at
                FROM public.routes
                ORDER BY created_at DESC, id DESC
                """
            )
            rows = cursor.fetchall()

    return [
        {
            "route_id": row["id"],
            "name": row["name"],
            "point_count": row["point_count"],
            "distance_km": round((row["distance_m"] or 0) / 1000, 3),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


@router.get("/{route_id}")
def get_route(route_id: int):
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT id, name, point_count, distance_m, created_at
                FROM public.routes
                WHERE id = %s
                """,
                (route_id,),
            )
            row = cursor.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Route not found.")

    return {
        "route_id": row["id"],
        "name": row["name"],
        "point_count": row["point_count"],
        "distance_km": round((row["distance_m"] or 0) / 1000, 3),
        "created_at": row["created_at"],
    }


@router.get("/{route_id}/geometry")
def get_route_geometry(route_id: int):
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    r.id,
                    r.name,
                    ST_AsGeoJSON(
                        COALESCE(
                            r.route,
                            (
                                SELECT ST_MakeLine(rp.geom ORDER BY rp.sequence)
                                FROM public.route_points AS rp
                                WHERE rp.route_id = r.id
                            )
                        )
                    ) AS geometry
                FROM public.routes AS r
                WHERE r.id = %s
                """,
                (route_id,),
            )
            row = cursor.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Route not found.")

    if row["geometry"] is None:
        raise HTTPException(
            status_code=404,
            detail="This route has no usable geometry.",
        )

    import json

    return {
        "type": "Feature",
        "geometry": json.loads(row["geometry"]),
        "properties": {
            "route_id": row["id"],
            "name": row["name"],
        },
    }