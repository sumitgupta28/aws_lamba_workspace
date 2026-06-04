"""
Multi-layer Lambda test suite.

Layer coverage:
  s3_reader  — fetches CSV content from S3
  db         — DDL + bulk insert against Postgres
  service    — orchestrates s3_reader + db
  handler    — event parsing + response shaping

Run unit tests (no Docker):
    pytest tests/ -v -m unit

Run integration tests (needs docker compose up -d):
    pytest tests/ -v -m integration
"""

import csv
import io
import json
import os
import sys
from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_aws

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lambda"))

import db          # noqa: E402
import handler     # noqa: E402
import s3_reader   # noqa: E402
import service     # noqa: E402

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

_AWS_ENV = {
    "AWS_DEFAULT_REGION": "us-east-1",
    "AWS_ACCESS_KEY_ID": "test",
    "AWS_SECRET_ACCESS_KEY": "test",
}
_DB_ENV = {
    "DB_HOST": "localhost", "DB_PORT": "5432",
    "DB_NAME": "testdb", "DB_USER": "user", "DB_PASSWORD": "pass",
}


def _make_csv(rows: list[dict]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def _s3_event(bucket: str, key: str) -> dict:
    return {"Records": [{"s3": {"bucket": {"name": bucket}, "object": {"key": key}}}]}


def _mock_conn():
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    return conn, cur


# ---------------------------------------------------------------------------
# s3_reader layer
# ---------------------------------------------------------------------------

@pytest.mark.unit
@mock_aws
def test_s3_reader_fetches_and_decodes():
    os.environ.update(_AWS_ENV)
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=BUCKET)
    s3.put_object(Bucket=BUCKET, Key=KEY, Body=_make_csv(SAMPLE_ROWS).encode())

    result = s3_reader.fetch_csv(BUCKET, KEY)
    assert "Alice" in result
    assert "Bob" in result


# ---------------------------------------------------------------------------
# db layer
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_db_bulk_insert_executes_ddl_and_insert():
    conn, cur = _mock_conn()
    rows = [(
        "aaaaaaaa-0000-0000-0000-000000000001", "Alice", "Smith",
        "alice@example.com", "+1-555-100-0001", "1990-06-15", "1 Main St",
        "Austin", "TX", "73301", "US", "Engineering", "active", "2024-01-10",
    )]
    db.bulk_insert(conn, rows)

    cur.execute.assert_called_once()
    cur.executemany.assert_called_once()
    assert cur.executemany.call_args[0][1] == rows
    conn.commit.assert_called_once()


@pytest.mark.unit
def test_db_bulk_insert_empty_rows():
    conn, cur = _mock_conn()
    db.bulk_insert(conn, [])
    cur.executemany.assert_called_once_with(db._INSERT, [])
    conn.commit.assert_called_once()


@pytest.mark.unit
def test_db_connect_uses_env_vars():
    os.environ.update(_DB_ENV)
    with patch("db.psycopg2.connect", return_value=MagicMock()) as mock_pg:
        db.connect()
    mock_pg.assert_called_once_with(
        host="localhost", port=5432, dbname="testdb",
        user="user", password="pass", connect_timeout=10,
    )


# ---------------------------------------------------------------------------
# service layer
# ---------------------------------------------------------------------------

@pytest.mark.unit
@mock_aws
def test_service_process_returns_count_and_key():
    os.environ.update({**_AWS_ENV, **_DB_ENV})
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=BUCKET)
    s3.put_object(Bucket=BUCKET, Key=KEY, Body=_make_csv(SAMPLE_ROWS).encode())

    conn, _ = _mock_conn()
    with patch("service.connect", return_value=conn):
        result = service.process(BUCKET, KEY)

    assert result == {"inserted": 2, "file": KEY}
    conn.commit.assert_called_once()
    conn.close.assert_called_once()


@pytest.mark.unit
@mock_aws
def test_service_process_closes_conn_on_error():
    """conn.close() is called even when bulk_insert raises."""
    os.environ.update({**_AWS_ENV, **_DB_ENV})
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=BUCKET)
    s3.put_object(Bucket=BUCKET, Key=KEY, Body=_make_csv(SAMPLE_ROWS).encode())

    conn, _ = _mock_conn()
    with patch("service.connect", return_value=conn), \
         patch("service.bulk_insert", side_effect=RuntimeError("DB failure")):
        with pytest.raises(RuntimeError, match="DB failure"):
            service.process(BUCKET, KEY)
    conn.close.assert_called_once()


# ---------------------------------------------------------------------------
# handler layer (end-to-end unit)
# ---------------------------------------------------------------------------

@pytest.mark.unit
@mock_aws
def test_handler_parses_event_and_returns_200():
    os.environ.update({**_AWS_ENV, **_DB_ENV})
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=BUCKET)
    s3.put_object(Bucket=BUCKET, Key=KEY, Body=_make_csv(SAMPLE_ROWS).encode())

    conn, cur = _mock_conn()
    with patch("db.psycopg2.connect", return_value=conn):
        response = handler.lambda_handler(_s3_event(BUCKET, KEY), None)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["inserted"] == 2
    assert body["file"] == KEY
    assert cur.executemany.call_args[0][1].__len__() == 2
    conn.commit.assert_called_once()


@pytest.mark.unit
@mock_aws
def test_handler_returns_correct_row_count_for_100_rows():
    os.environ.update({**_AWS_ENV, **_DB_ENV})
    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "users.csv")
    with open(csv_path) as f:
        csv_content = f.read()

    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=BUCKET)
    s3.put_object(Bucket=BUCKET, Key=KEY, Body=csv_content.encode())

    conn, _ = _mock_conn()
    with patch("db.psycopg2.connect", return_value=conn):
        response = handler.lambda_handler(_s3_event(BUCKET, KEY), None)

    assert response["statusCode"] == 200
    assert json.loads(response["body"])["inserted"] == 100


# ---------------------------------------------------------------------------
# Integration tests (moto S3 + real Postgres via docker-compose)
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
        **_AWS_ENV,
        "DB_HOST": "localhost", "DB_PORT": "5433",
        "DB_NAME": "testdb", "DB_USER": "testuser", "DB_PASSWORD": "testpass",
    })

    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=BUCKET)
    s3.put_object(Bucket=BUCKET, Key=KEY, Body=_make_csv(SAMPLE_ROWS).encode())

    response = handler.lambda_handler(_s3_event(BUCKET, KEY), None)
    assert response["statusCode"] == 200

    import psycopg2 as pg
    conn = pg.connect(
        host="localhost", port=5433, dbname="testdb",
        user="testuser", password="testpass",
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users WHERE email LIKE '%example.com'")
            count = cur.fetchone()[0]
        assert count == 2, f"Expected 2 rows, got {count}"
    finally:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS users")
        conn.commit()
        conn.close()
