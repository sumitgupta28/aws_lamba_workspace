# How to Run

## Prerequisites

Install Terraform and AWS CLI (one-time setup):

```bash
brew tap hashicorp/tap
brew install hashicorp/tap/terraform awscli
```

Configure AWS credentials:

```bash
aws configure
```

You will be prompted for:
- AWS Access Key ID
- AWS Secret Access Key
- Default region (e.g. `us-east-1`)
- Default output format (e.g. `json`)

---

## 1. Package the Lambda Code

Builds two artefacts in `terraform-lambda/`:

| Artefact | Contents |
|---|---|
| `layer.zip` | `psycopg2-binary` packaged as a Lambda Layer |
| `lambda.zip` | Function source: `handler.py`, `service.py`, `db.py`, `s3_reader.py` |

```bash
chmod +x scripts/package.sh
./scripts/package.sh
```

Run this again whenever you change any file under `lambda/` or `layer/`.

---

## 2. Initialize Terraform

Downloads the AWS provider plugin (one-time per checkout):

```bash
terraform -chdir=terraform-lambda init
```

---

## 3. Preview Changes

Dry-run to see what will be created without making any changes:

```bash
terraform -chdir=terraform-lambda plan
```

---

## 4. Deploy to AWS

```bash
terraform -chdir=terraform-lambda apply
```

Type `yes` when prompted. After apply completes, Terraform prints the Lambda function name, ARN, S3 bucket name, and RDS endpoint.

---

## 5. Test the Deployment

**Upload the CSV to trigger the Lambda:**

```bash
aws s3 cp data/users.csv s3://<bucket-name>/users/users.csv \
  --profile lambda_manager_profile
```

**Watch Lambda logs in real time:**

```bash
aws logs tail /aws/lambda/<function-name> --follow --profile lambda_manager_profile
```

Expected log line:

```json
{"inserted": 100, "file": "users/users.csv"}
```

**Query the database directly** (RDS is publicly accessible):

```bash
psql -h <rds-endpoint> -U dbadmin -d csvdb -c "SELECT COUNT(*) FROM users;"
```

**Direct Lambda invocation via AWS CLI:**

```bash
aws lambda invoke \
  --function-name csv-to-rds \
  --payload '{"Records":[{"s3":{"bucket":{"name":"<bucket>"},"object":{"key":"users/users.csv"}}}]}' \
  --cli-binary-format raw-in-base64-out \
  --profile lambda_manager_profile \
  /tmp/response.json && cat /tmp/response.json
```

---

## 6. Run Tests Locally (No AWS Required)

Install test dependencies:

```bash
pip install -r lambda/requirements-dev.txt
```

**Unit tests** (no Docker, ~3 sec):

```bash
pytest tests/ -v -m unit
```

**Integration tests** (requires Docker):

```bash
docker compose up -d
pytest tests/ -v -m integration
docker compose down
```

---

## 7. Redeploy After Code Changes

```bash
./scripts/package.sh && terraform -chdir=terraform-lambda apply -auto-approve
```

---

## 8. Tear Down

Destroys all AWS resources created by Terraform:

```bash
terraform -chdir=terraform-lambda destroy
```
