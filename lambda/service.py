import csv
import io
import logging

from db import bulk_insert, connect
from s3_reader import fetch_csv, move_to_processed

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def process(bucket: str, key: str, processed_bucket: str) -> dict:
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
    logger.info("Parsed %d rows from s3://%s/%s", len(rows), bucket, key)
    conn = connect()
    try:
        bulk_insert(conn, rows)
        logger.info("Successfully inserted %d records into the database", len(rows))
    finally:
        conn.close()
    move_to_processed(bucket, key, processed_bucket)
    return {"inserted": len(rows), "file": key}
