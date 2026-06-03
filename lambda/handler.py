import csv
import io
import json
import os

import boto3
import psycopg2


def lambda_handler(event, context):
    record = event["Records"][0]["s3"]
    bucket = record["bucket"]["name"]
    key = record["object"]["key"]

    s3 = boto3.client("s3")
    obj = s3.get_object(Bucket=bucket, Key=key)
    content = obj["Body"].read().decode("utf-8")

    conn = psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", "5432")),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        connect_timeout=10,
    )

    try:
        with conn.cursor() as cur:
            cur.execute("""
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
            """)

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

            cur.executemany(
                """INSERT INTO users (
                    user_id, first_name, last_name, email, phone,
                    date_of_birth, street_address, city, state, zip_code,
                    country, department, status, created_at
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (user_id) DO NOTHING""",
                rows,
            )

        conn.commit()
    finally:
        conn.close()

    return {
        "statusCode": 200,
        "body": json.dumps({"inserted": len(rows), "file": key}),
    }
