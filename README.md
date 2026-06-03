# AWS Lambda — S3 CSV Ingestion to PostgreSQL

A Python Lambda function triggered by S3 uploads that parses a CSV of user records and inserts them into a PostgreSQL database. Infrastructure is managed with Terraform.

---

## Project Structure

```
.
├── data/
│   └── users.csv                        # Generated test CSV (100 user records)
├── lambda/
│   ├── handler.py                       # Lambda function source
│   ├── requirements.txt                 # Runtime dependencies (psycopg2)
│   └── requirements-dev.txt            # Test dependencies (moto, pytest)
├── scripts/
│   ├── package.sh                       # Builds terraform/lambda.zip
│   └── generate_users_csv.py           # Generates data/users.csv
├── terraform-lambda/                    # Terraform: Lambda + API Gateway + S3 trigger
├── terraform-lambda-user-creation/      # Terraform: one-time IAM bootstrap
├── tests/
│   └── test_handler_local.py           # Unit + integration tests
├── docker-compose.yml                   # Local Postgres (port 5433)
└── pytest.ini                           # Test mark definitions
```

---

## How the Lambda Works

```
S3 upload (users.csv)
       │
       ▼
lambda_handler(event, context)
       │
       ├── Reads CSV from S3 via boto3
       ├── Connects to PostgreSQL via psycopg2 (env vars for credentials)
       ├── CREATE TABLE IF NOT EXISTS users (...)
       └── INSERT rows with ON CONFLICT DO NOTHING
```

The S3 event payload provides the bucket name and object key. All DB connection details come from Lambda environment variables (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`).

---

## Test & Validation Strategy

Validation is split into two levels so you can catch issues fast locally before touching AWS.

```
Level 1 — Unit        : moto (fake S3) + mocked psycopg2   ~2 sec, no Docker
Level 2 — Integration : moto (fake S3) + real Postgres      ~5 sec, Docker required
Level 3 — AWS         : real S3 trigger + real RDS/Postgres  post-deploy smoke test
```

### Prerequisites

```bash
pip install -r lambda/requirements-dev.txt
```

---

### Level 1 — Unit Tests (no Docker required)

**What is tested:**
- S3 `get_object` is intercepted by `moto` — no AWS credentials needed
- `psycopg2.connect` is replaced with a `MagicMock` — no database needed
- Asserts the handler returns `statusCode: 200`
- Asserts `executemany` is called with the correct number of rows
- Asserts `commit` is called exactly once
- Smoke-tested against the full 100-row `data/users.csv`

**Run:**

```bash
pytest tests/test_handler_local.py -v -m unit
```

**Expected output:**

```
tests/test_handler_local.py::test_handler_parses_csv_and_calls_db          PASSED
tests/test_handler_local.py::test_handler_returns_correct_row_count_for_100_rows  PASSED
2 passed in 1.65s
```

---

### Level 2 — Integration Tests (Docker required)

**What is tested:**
- Everything in Level 1, plus:
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
pytest tests/test_handler_local.py -v -m integration
```

The integration test auto-skips if Postgres is not reachable on `localhost:5433`, so it is safe to run `pytest -v` (all marks) without Docker — Level 1 tests still run.

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

**3. Query the database directly** (if RDS is accessible):

```bash
psql -h <rds-endpoint> -U <user> -d <dbname> -c "SELECT COUNT(*) FROM users;"
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
# 1. Package Lambda
./scripts/package.sh

# 2. Deploy
terraform -chdir=terraform-lambda apply

# 3. Redeploy after handler changes
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
