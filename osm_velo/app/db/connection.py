import psycopg
from collections.abc import Generator

from app.core.config import settings

DATABASE_URL = settings.DATABASE_URL


def get_connection() -> psycopg.Connection:
    return psycopg.connect(DATABASE_URL)


def get_db() -> Generator[psycopg.Connection, None, None]:
    connection = get_connection()

    try:
        yield connection
    finally:
        connection.close()