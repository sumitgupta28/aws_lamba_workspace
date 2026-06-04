# AWS Lambda — S3 CSV Ingestion to PostgreSQL

A Python Lambda function triggered by S3 uploads that parses a CSV of user records and inserts them into a PostgreSQL database. Infrastructure is managed with Terraform. The function is structured as a four-layer architecture with `psycopg2` packaged as a separate Lambda Layer.

---

## Project Structure

```
.
├── data/
│   └── users.csv                        # Generated test CSV (100 user records)
├── lambda/
│   ├── handler.py                       # Entry point — event parsing + response
│   ├── service.py                       # Orchestration layer
│   ├── db.py                            # Data-access layer (DDL + bulk insert)
│   ├── s3_reader.py                     # S3 fetch layer
│   ├── requirements.txt                 # Runtime deps for function zip (empty; psycopg2 is in layer)
│   └── requirements-dev.txt            # Test deps: moto, boto3, psycopg2-binary, pytest
├── layer/
│   └── requirements.txt                 # Lambda Layer deps: psycopg2-binary
├── scripts/
│   ├── package.sh                       # Builds terraform-lambda/layer.zip + lambda.zip
│   └── generate_users_csv.py           # Generates data/users.csv
├── terraform-lambda/                    # Terraform: Lambda + Layer + RDS + S3 trigger
├── terraform-lambda-user-creation/      # Terraform: one-time IAM bootstrap
├── tests/
│   └── test_handler_local.py           # Per-layer unit + integration tests
├── docker-compose.yml                   # Local Postgres (port 5433)
└── pytest.ini                           # Test mark definitions
```

---

## Architecture

### Lambda Layer Structure

```
terraform-lambda/
├── layer.zip          ← psycopg2-binary (python/lib/python3.12/site-packages/)
└── lambda.zip         ← function source (handler.py, service.py, db.py, s3_reader.py)
```

### Code Layers

```
S3 upload (users.csv)
       │
       ▼
handler.lambda_handler(event, context)   ← parse S3 event record
       │
       ▼
service.process(bucket, key)             ← orchestrate: S3 read + CSV parse + DB write
       │
       ├── s3_reader.fetch_csv()         ← boto3: get_object → decode UTF-8
       │
       └── db.bulk_insert(conn, rows)    ← psycopg2: CREATE TABLE IF NOT EXISTS + executemany
              └── db.connect()           ← psycopg2: connect via env vars
```

All DB connection details come from Lambda environment variables (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`).

---

## Test & Validation Strategy

```
Level 1 — Unit        : moto (fake S3) + mocked psycopg2    ~3 sec, no Docker
Level 2 — Integration : moto (fake S3) + real Postgres       ~5 sec, Docker required
Level 3 — AWS         : real S3 trigger + real RDS/Postgres  post-deploy smoke test
```

### Prerequisites

```bash
pip install -r lambda/requirements-dev.txt
```

---

### Level 1 — Unit Tests (no Docker required)

Each layer is tested in isolation:

| Test | Layer | What is asserted |
|---|---|---|
| `test_s3_reader_fetches_and_decodes` | s3_reader | moto S3 object is fetched and decoded correctly |
| `test_db_bulk_insert_executes_ddl_and_insert` | db | DDL `execute` and `executemany` called with correct rows |
| `test_db_bulk_insert_empty_rows` | db | empty row list still calls executemany; commit called |
| `test_db_connect_uses_env_vars` | db | psycopg2.connect called with correct kwargs from env |
| `test_service_process_returns_count_and_key` | service | returns `{inserted, file}`; commit and close called |
| `test_service_process_closes_conn_on_error` | service | conn.close() called even when bulk_insert raises |
| `test_handler_parses_event_and_returns_200` | handler | statusCode 200, correct body, executemany called with 2 rows |
| `test_handler_returns_correct_row_count_for_100_rows` | handler | smoke test with full 100-row CSV |

**Run:**

```bash
pytest tests/ -v -m unit
```

**Expected output:**

```
tests/test_handler_local.py::test_s3_reader_fetches_and_decodes                    PASSED
tests/test_handler_local.py::test_db_bulk_insert_executes_ddl_and_insert           PASSED
tests/test_handler_local.py::test_db_bulk_insert_empty_rows                        PASSED
tests/test_handler_local.py::test_db_connect_uses_env_vars                         PASSED
tests/test_handler_local.py::test_service_process_returns_count_and_key            PASSED
tests/test_handler_local.py::test_service_process_closes_conn_on_error             PASSED
tests/test_handler_local.py::test_handler_parses_event_and_returns_200             PASSED
tests/test_handler_local.py::test_handler_returns_correct_row_count_for_100_rows   PASSED
8 passed in ~3s
```

---

### Level 2 — Integration Tests (Docker required)

**What is tested:**
- The `CREATE TABLE` DDL is valid Postgres syntax
- Column types accept the real CSV values (UUID, DATE, VARCHAR lengths)
- `ON CONFLICT DO NOTHING` constraint works on re-upload
- A live `SELECT COUNT(*)` confirms rows actually landed in the database

**Start Postgres:**

```bash
docker compose up -d
```

Wait for the health check to pass (~5 seconds), then:

```bash
pytest tests/ -v -m integration
```

The integration test auto-skips if Postgres is not reachable on `localhost:5433`, so it is safe to run `pytest -v` (all marks) without Docker.

**Tear down Postgres when done:**

```bash
docker compose down
```

---

### Level 3 — AWS Smoke Test (post-deploy)

After deploying with Terraform, validate end-to-end:

**1. Upload the CSV to the trigger bucket:**

```bash
aws s3 cp data/users.csv s3://<your-bucket-name>/users/users.csv \
  --profile lambda_manager_profile
```

**2. Watch Lambda logs in real time:**

```bash
aws logs tail /aws/lambda/<function-name> --follow --profile lambda_manager_profile
```

Expected log line:

```json
{"inserted": 100, "file": "users/users.csv"}
```

**3. Query the database directly** (RDS is publicly accessible):

```bash
psql -h <rds-endpoint> -U dbadmin -d csvdb -c "SELECT COUNT(*) FROM users;"
```

Expected: `100`

---

## Generating the Test CSV

Re-generate `data/users.csv` (100 rows, deterministic via `random.seed(42)`):

```bash
python3 scripts/generate_users_csv.py
```

CSV schema:

| Column | Type | Notes |
|---|---|---|
| `user_id` | UUID | Unique per row |
| `first_name` | string | |
| `last_name` | string | |
| `email` | string | Unique per row |
| `phone` | string | US format |
| `date_of_birth` | ISO date | 1960–2000 range |
| `street_address` | string | |
| `city` | string | |
| `state` | string | US state code |
| `zip_code` | string | |
| `country` | string | Always `US` |
| `department` | string | Engineering / Sales / etc. |
| `status` | string | `active` / `inactive` / `suspended` |
| `created_at` | ISO date | 2024 range |

---

## Deploy Flow

See [`how_to_run.md`](how_to_run.md) for the full Terraform deploy and teardown steps. The short version:

```bash
# 1. Build layer.zip (psycopg2) and lambda.zip (source)
./scripts/package.sh

# 2. Deploy
terraform -chdir=terraform-lambda apply

# 3. Redeploy after any code change
./scripts/package.sh && terraform -chdir=terraform-lambda apply -auto-approve
```

---

## Environment Variables (Lambda)

| Variable | Description |
|---|---|
| `DB_HOST` | PostgreSQL hostname or RDS endpoint |
| `DB_PORT` | PostgreSQL port (default `5432`) |
| `DB_NAME` | Database name |
| `DB_USER` | Database user |
| `DB_PASSWORD` | Database password |
| `ENVIRONMENT` | Deployment environment tag (e.g. `dev`) |
