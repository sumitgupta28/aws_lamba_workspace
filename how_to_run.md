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

This creates `terraform/lambda.zip` from `lambda/handler.py`:

```bash
chmod +x scripts/package.sh
./scripts/package.sh
```

Run this again whenever you change `lambda/handler.py`.

---

## 2. Initialize Terraform

Downloads the AWS provider plugin (one-time per checkout):

```bash
terraform -chdir=terraform init
```

---

## 3. Preview Changes

Dry-run to see what will be created without making any changes:

```bash
terraform -chdir=terraform plan
```

---

## 4. Deploy to AWS

```bash
terraform -chdir=terraform apply
```

Type `yes` when prompted. After apply completes, Terraform prints:

```
Outputs:
  lambda_function_name = "hello-world"
  lambda_function_arn  = "arn:aws:lambda:us-east-1:123456789:function:hello-world"
  api_gateway_url      = "https://<id>.execute-api.us-east-1.amazonaws.com"
  invoke_url           = "https://<id>.execute-api.us-east-1.amazonaws.com/hello"
```

---

## 5. Test the Deployment

**Via HTTP (API Gateway):**

```bash
INVOKE_URL=$(terraform -chdir=terraform output -raw invoke_url)
curl "$INVOKE_URL"
curl "$INVOKE_URL?name=Sumit"
```

Expected response:

```json
{"message": "Hello, Sumit!", "method": "GET", "path": "/hello"}
```

**Via AWS CLI (direct Lambda invocation):**

```bash
aws lambda invoke \
  --function-name hello-world \
  --payload '{"httpMethod":"GET","path":"/hello","queryStringParameters":{"name":"Sumit"}}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/response.json && cat /tmp/response.json
```

**View logs in CloudWatch:**

```bash
aws logs tail /aws/lambda/hello-world --follow
```

---

## 6. Local Test (No AWS Required)

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

---

## 7. Redeploy After Code Changes

```bash
./scripts/package.sh && terraform -chdir=terraform apply -auto-approve
```

---

## 8. Tear Down

Destroys all AWS resources created by Terraform:

```bash
terraform -chdir=terraform destroy
```
