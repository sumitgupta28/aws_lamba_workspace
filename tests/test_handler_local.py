"""
Local validation for lambda/handler.py.

Level 1 — Unit test  : moto fakes S3; psycopg2 is mocked (no Docker needed).
Level 2 — Integration: moto fakes S3; real Postgres via docker-compose.

Run unit tests only (fast, no Docker):
    pytest tests/test_handler_local.py -v -m unit

Run integration tests (needs `docker compose up -d` first):
    pytest tests/test_handler_local.py -v -m integration
"""

import csv
import io
import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_aws

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lambda"))

BUCKET = "test-users-bucket"
KEY = "users/users.csv"
SAMPLE_ROWS = [
    {
        "user_id": "aaaaaaaa-0000-0000-0000-000000000001",
        "first_name": "Alice", "last_name": "Smith",
        "email": "alice.smith@example.com", "phone": "+1-555-100-0001",
        "date_of_birth": "1990-06-15", "street_address": "1 Main St",
        "city": "Austin", "state": "TX", "zip_code": "73301",
        "country": "US", "department": "Engineering",
        "status": "active", "created_at": "2024-01-10",
    },
    {
        "user_id": "bbbbbbbb-0000-0000-0000-000000000002",
        "first_name": "Bob", "last_name": "Jones",
        "email": "bob.jones@example.com", "phone": "+1-555-200-0002",
        "date_of_birth": "1985-03-22", "street_address": "99 Oak Ave",
        "city": "Denver", "state": "CO", "zip_code": "80201",
        "country": "US", "department": "Finance",
        "status": "inactive", "created_at": "2024-05-20",
    },
]


def _make_csv(rows: list[dict]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def _s3_event(bucket: str, key: str) -> dict:
    return {"Records": [{"s3": {"bucket": {"name": bucket}, "object": {"key": key}}}]}


# ---------------------------------------------------------------------------
# Level 1 — Unit tests (moto S3 + mocked psycopg2)
# ---------------------------------------------------------------------------

@pytest.mark.unit
@mock_aws
def test_handler_parses_csv_and_calls_db():
    """Handler extracts rows from S3 and passes them to psycopg2 executemany."""
    os.environ.update({
        "DB_HOST": "localhost", "DB_PORT": "5432",
        "DB_NAME": "testdb", "DB_USER": "user", "DB_PASSWORD": "pass",
        "AWS_DEFAULT_REGION": "us-east-1",
        "AWS_ACCESS_KEY_ID": "test", "AWS_SECRET_ACCESS_KEY": "test",
    })

    # Put CSV in moto-faked S3
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=BUCKET)
    s3.put_object(Bucket=BUCKET, Key=KEY, Body=_make_csv(SAMPLE_ROWS))

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur

    with patch("psycopg2.connect", return_value=mock_conn):
        import handler
        response = handler.lambda_handler(_s3_event(BUCKET, KEY), None)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["inserted"] == 2
    assert body["file"] == KEY

    # executemany must have been called with 2 rows
    call_args = mock_cur.executemany.call_args
    assert len(call_args[0][1]) == 2
    mock_conn.commit.assert_called_once()


@pytest.mark.unit
@mock_aws
def test_handler_returns_correct_row_count_for_100_rows():
    """Smoke-test with the full generated CSV (100 rows)."""
    os.environ.update({
        "DB_HOST": "localhost", "DB_PORT": "5432",
        "DB_NAME": "testdb", "DB_USER": "user", "DB_PASSWORD": "pass",
        "AWS_DEFAULT_REGION": "us-east-1",
        "AWS_ACCESS_KEY_ID": "test", "AWS_SECRET_ACCESS_KEY": "test",
    })

    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "users.csv")
    with open(csv_path) as f:
        csv_content = f.read()

    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=BUCKET)
    s3.put_object(Bucket=BUCKET, Key=KEY, Body=csv_content)

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur

    with patch("psycopg2.connect", return_value=mock_conn):
        import importlib, handler
        importlib.reload(handler)
        response = handler.lambda_handler(_s3_event(BUCKET, KEY), None)

    assert response["statusCode"] == 200
    assert json.loads(response["body"])["inserted"] == 100


# ---------------------------------------------------------------------------
# Level 2 — Integration tests (moto S3 + real Postgres via docker-compose)
# ---------------------------------------------------------------------------

def _pg_available() -> bool:
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="localhost", port=5433, dbname="testdb",
            user="testuser", password="testpass", connect_timeout=2,
        )
        conn.close()
        return True
    except Exception:
        return False


@pytest.mark.integration
@pytest.mark.skipif(not _pg_available(), reason="Postgres not running on localhost:5433")
@mock_aws
def test_handler_inserts_into_real_postgres():
    """End-to-end: moto S3 + real Postgres — verifies actual rows in DB."""
    os.environ.update({
        "DB_HOST": "localhost", "DB_PORT": "5433",
        "DB_NAME": "testdb", "DB_USER": "testuser", "DB_PASSWORD": "testpass",
        "AWS_DEFAULT_REGION": "us-east-1",
        "AWS_ACCESS_KEY_ID": "test", "AWS_SECRET_ACCESS_KEY": "test",
    })

    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=BUCKET)
    s3.put_object(Bucket=BUCKET, Key=KEY, Body=_make_csv(SAMPLE_ROWS))

    import importlib, handler
    importlib.reload(handler)
    response = handler.lambda_handler(_s3_event(BUCKET, KEY), None)

    assert response["statusCode"] == 200

    import psycopg2
    conn = psycopg2.connect(
        host="localhost", port=5433, dbname="testdb",
        user="testuser", password="testpass",
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users WHERE email LIKE '%example.com'")
            count = cur.fetchone()[0]
        assert count == 2, f"Expected 2 rows, got {count}"
    finally:
        # clean up for test idempotency
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS users")
        conn.commit()
        conn.close()
