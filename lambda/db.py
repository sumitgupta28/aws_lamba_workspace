import logging
import os

import psycopg2

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_DDL = """
    CREATE TABLE IF NOT EXISTS users (
        id             SERIAL PRIMARY KEY,
        user_id        UUID UNIQUE,
        first_name     VARCHAR(100),
        last_name      VARCHAR(100),
        email          VARCHAR(255) UNIQUE,
        phone          VARCHAR(30),
        date_of_birth  DATE,
        street_address TEXT,
        city           VARCHAR(100),
        state          VARCHAR(50),
        zip_code       VARCHAR(20),
        country        VARCHAR(10),
        department     VARCHAR(100),
        status         VARCHAR(20),
        created_at     DATE
    )
"""

_INSERT = """
    INSERT INTO users (
        user_id, first_name, last_name, email, phone,
        date_of_birth, street_address, city, state, zip_code,
        country, department, status, created_at
    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    ON CONFLICT (user_id) DO NOTHING
"""


def connect():
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", "5432")),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        connect_timeout=10,
    )


def bulk_insert(conn, rows: list[tuple]) -> None:
    with conn.cursor() as cur:
        cur.execute(_DDL)
        cur.executemany(_INSERT, rows)
        inserted = cur.rowcount
    conn.commit()
    logger.info("DB bulk_insert committed: %d rows affected (rowcount)", inserted)
