# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This workspace demonstrates deploying a Python Lambda function to AWS via Terraform, exposed through API Gateway v2 (HTTP API). It also includes a separate Terraform module for provisioning the IAM user needed to run deployments.

## Workflow

The deploy flow has a strict ordering dependency: `lambda/handler.py` → `scripts/package.sh` → `terraform/lambda.zip` → Terraform apply.

### 1. Package Lambda

Run after any change to `lambda/handler.py` or `lambda/requirements.txt`:

```bash
chmod +x scripts/package.sh
./scripts/package.sh
```

`scripts/package.sh` installs pip dependencies (if any) into a temp staging dir, copies `handler.py` alongside them, and zips everything into `terraform/lambda.zip`. The Lambda runtime is Python 3.12 and `boto3` is pre-installed — only add third-party packages to `requirements.txt`.

### 2. Deploy

```bash
terraform -chdir=terraform init    # one-time per checkout
terraform -chdir=terraform plan
terraform -chdir=terraform apply
```

Redeploy shortcut after code changes:

```bash
./scripts/package.sh && terraform -chdir=terraform apply -auto-approve
```

### 3. Tear down

```bash
terraform -chdir=terraform destroy
```

## Local Test (no AWS required)

```bash
python3 -c "
import json, importlib.util
spec = importlib.util.spec_from_file_location('handler', 'lambda/handler.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
result = mod.lambda_handler({'httpMethod':'GET','path':'/hello','queryStringParameters':{'name':'Sumit'}}, None)
print(json.dumps(result, indent=2))
"
```

## Module Structure

| Directory | Purpose |
|---|---|
| `lambda/` | Lambda source (`handler.py`) and `requirements.txt` |
| `scripts/` | `package.sh` — builds `terraform/lambda.zip` |
| `terraform-lambda/` | **Primary** Terraform root: Lambda + API Gateway deploymentt (uses `lambda_manager_profile` AWS CLI profile) |
| `terraform-lambda-user-creation/` | One-time setup: creates the `lambda-manager-user` IAM user + access keys and writes the `lambda_manager_profile` credentials block to `~/.aws/credentials` |

## AWS Credential Setup

Two AWS profiles are involved:

- `user-creation` — a pre-existing admin-level profile used to bootstrap the IAM user. Set via `export AWS_PROFILE=user-creation` before running `terraform-lambda-user-creation/`.
- `lambda_manager_profile` — written to `~/.aws/credentials` by `terraform-lambda-user-creation/outputs.tf` after apply. Used by `terraform-lambda/` for all subsequent Lambda/API Gateway operations.

Bootstrap sequence (first time only):

```bash
export AWS_PROFILE=user-creation
cd terraform-lambda-user-creation
terraform init && terraform apply -auto-approve
```

## Post-Deploy Testing

```bash
INVOKE_URL=$(terraform -chdir=terraform output -raw invoke_url)
curl "$INVOKE_URL?name=Sumit"

# Direct Lambda invocation via CLI
aws lambda invoke \
  --function-name hello-world \
  --payload '{"httpMethod":"GET","path":"/hello","queryStringParameters":{"name":"Sumit"}}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/response.json && cat /tmp/response.json

# Tail CloudWatch logs
aws logs tail /aws/lambda/hello-world --follow
```

## Key Terraform Variables

Configured in `terraform/terraform.tfvars` (gitignored):

```
aws_region    = "us-east-1"
function_name = "hello-world"
environment   = "dev"
```

Override on the command line: `terraform -chdir=terraform apply -var="function_name=my-fn"`.
