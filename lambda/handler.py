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
                    id         SERIAL PRIMARY KEY,
                    first_name VARCHAR(100),
                    last_name  VARCHAR(100),
                    age        INTEGER,
                    address    TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)

            reader = csv.DictReader(io.StringIO(content))
            rows = [
                (r["first_name"], r["last_name"], int(r["age"]), r["address"])
                for r in reader
            ]

            cur.executemany(
                "INSERT INTO users (first_name, last_name, age, address) VALUES (%s, %s, %s, %s)",
                rows,
            )

        conn.commit()
    finally:
        conn.close()

    return {
        "statusCode": 200,
        "body": json.dumps({"inserted": len(rows), "file": key}),
    }
