# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This workspace deploys a Python Lambda function to AWS via Terraform. The Lambda is triggered by S3 CSV uploads and ingests records into a PostgreSQL (RDS) database. The function is structured as four layers: `handler → service → db / s3_reader`. The `psycopg2` dependency is packaged as a separate Lambda Layer rather than bundled into the function zip.

## Workflow

The deploy flow has a strict ordering dependency:

```
lambda/*.py + layer/requirements.txt
        │
        ▼
scripts/package.sh   →   terraform-lambda/layer.zip
                     →   terraform-lambda/lambda.zip
        │
        ▼
terraform-lambda apply
```

### 1. Package Lambda

Run after any change to `lambda/*.py`, `layer/requirements.txt`, or `lambda/requirements.txt`:

```bash
chmod +x scripts/package.sh
./scripts/package.sh
```

`scripts/package.sh` builds **two** artefacts in `terraform-lambda/`:

| Artefact | Contents | Source |
|---|---|---|
| `layer.zip` | `psycopg2-binary` packaged under `python/lib/python3.12/site-packages/` | `layer/requirements.txt` |
| `lambda.zip` | `handler.py`, `service.py`, `db.py`, `s3_reader.py` | `lambda/*.py` |

The Lambda runtime is Python 3.12 and `boto3` is pre-installed — only add third-party packages to `layer/requirements.txt`.

### 2. Deploy

```bash
terraform -chdir=terraform-lambda init    # one-time per checkout
terraform -chdir=terraform-lambda plan
terraform -chdir=terraform-lambda apply
```

Redeploy shortcut after code changes:

```bash
./scripts/package.sh && terraform -chdir=terraform-lambda apply -auto-approve
```

### 3. Tear down

```bash
terraform -chdir=terraform-lambda destroy
```

## Module Structure

| Path | Purpose |
|---|---|
| `lambda/handler.py` | Entry point — parses S3 event, calls `service.process()`, returns HTTP response |
| `lambda/service.py` | Orchestration — reads S3, parses CSV, calls DB |
| `lambda/db.py` | Data-access layer — `connect()`, DDL, `bulk_insert()` |
| `lambda/s3_reader.py` | Infrastructure layer — fetches and decodes CSV from S3 |
| `lambda/requirements.txt` | Runtime deps for the function zip (empty; psycopg2 is in the layer) |
| `lambda/requirements-dev.txt` | Local test deps: moto, boto3, psycopg2-binary, pytest |
| `layer/requirements.txt` | Lambda Layer deps: psycopg2-binary |
| `scripts/package.sh` | Builds `layer.zip` and `lambda.zip` |
| `terraform-lambda/` | **Primary** Terraform root: Lambda + Layer + RDS + S3 trigger (uses `lambda_manager_profile` AWS CLI profile) |
| `terraform-lambda-user-creation/` | One-time setup: creates the `lambda-manager-user` IAM user + access keys and writes the `lambda_manager_profile` credentials block to `~/.aws/credentials` |

## AWS Credential Setup

Two AWS profiles are involved:

- `user-creation` — a pre-existing admin-level profile used to bootstrap the IAM user. Set via `export AWS_PROFILE=user-creation` before running `terraform-lambda-user-creation/`.
- `lambda_manager_profile` — written to `~/.aws/credentials` by `terraform-lambda-user-creation/outputs.tf` after apply. Used by `terraform-lambda/` for all subsequent operations.

Bootstrap sequence (first time only):

```bash
export AWS_PROFILE=user-creation
cd terraform-lambda-user-creation
terraform init && terraform apply -auto-approve
```

## Running Tests Locally

```bash
pip install -r lambda/requirements-dev.txt

# Unit tests only (no Docker, ~2 sec)
pytest tests/ -v -m unit

# Integration tests (requires docker compose up -d)
docker compose up -d
pytest tests/ -v -m integration
```

## Post-Deploy Testing

```bash
# Upload the generated CSV to trigger the Lambda
aws s3 cp data/users.csv s3://<bucket-name>/users/users.csv \
  --profile lambda_manager_profile

# Tail CloudWatch logs
aws logs tail /aws/lambda/<function-name> --follow --profile lambda_manager_profile

# Query RDS directly (now publicly accessible)
psql -h <rds-endpoint> -U dbadmin -d csvdb -c "SELECT COUNT(*) FROM users;"
```

## Key Terraform Variables

Configured in `terraform-lambda/terraform.tfvars` (gitignored):

```
aws_region    = "us-east-1"
function_name = "csv-to-rds"
environment   = "dev"
db_name       = "csvdb"
db_username   = "dbadmin"
```

Override on the command line: `terraform -chdir=terraform-lambda apply -var="function_name=my-fn"`.
