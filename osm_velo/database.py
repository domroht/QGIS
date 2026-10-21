import psycopg
import json

from pathlib import Path
from psycopg.types.json import Json

DATABASE_URL = "postgresql://postgres@localhost:5432/geotrack"

def test_cennection():
    with psycopg.connect(DATABASE_URL) as connection:
        print("connection works")

def setup_database():
    sql_path = Path(__file__).parent / "sql" / "setup.sql"

    with open(sql_path, encoding="utf-8") as file:
        sql = file.read()

    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql)

    print("setup complete")


def save_route(geojson_path, name):
    with open(geojson_path, encoding="utf-8") as file:
        geojson = json.load(file)

    geometry = geojson["geometry"]

    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO activities (name, route)
                VALUES (
                    %s,
                    ST_SetSRID(
                        ST_GeomFromGeoJSON(%s),
                        4326
                    )
                )
                """,
                (name, Json(geometry)),
            )

        connection.commit()

if __name__ == "__main__": 
    test_cennection()
    setup_database()
    save_route("data/route.geojson", "test_activity")