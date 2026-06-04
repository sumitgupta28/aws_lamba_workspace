import csv
import io

from db import bulk_insert, connect
from s3_reader import fetch_csv


def process(bucket: str, key: str) -> dict:
    content = fetch_csv(bucket, key)
    reader = csv.DictReader(io.StringIO(content))
    rows = [
        (
            r["user_id"], r["first_name"], r["last_name"], r["email"],
            r["phone"], r["date_of_birth"], r["street_address"],
            r["city"], r["state"], r["zip_code"], r["country"],
            r["department"], r["status"], r["created_at"],
        )
        for r in reader
    ]
    conn = connect()
    try:
        bulk_insert(conn, rows)
    finally:
        conn.close()
    return {"inserted": len(rows), "file": key}
