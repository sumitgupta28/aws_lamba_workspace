#!/usr/bin/env bash
# Builds two artefacts in terraform-lambda/:
#   layer.zip   — psycopg2 Lambda Layer (python/lib/python3.12/site-packages/)
#   lambda.zip  — function source only (handler.py, service.py, db.py, s3_reader.py)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LAMBDA_SRC="$REPO_ROOT/lambda"
LAYER_SRC="$REPO_ROOT/layer"
TERRAFORM_DIR="$REPO_ROOT/terraform-lambda"
FUNCTION_ZIP="$TERRAFORM_DIR/lambda.zip"
LAYER_ZIP="$TERRAFORM_DIR/layer.zip"

LAYER_STAGING=$(mktemp -d)
FUNC_STAGING=$(mktemp -d)
trap "rm -rf '$LAYER_STAGING' '$FUNC_STAGING'" EXIT

echo "=== Building Lambda layer (psycopg2) ==="
pip3 install -r "$LAYER_SRC/requirements.txt" \
    --platform manylinux2014_x86_64 \
    --implementation cp \
    --python-version 3.12 \
    --only-binary=:all: \
    --trusted-host pypi.org \
    --trusted-host files.pythonhosted.org \
    --target "$LAYER_STAGING/python/lib/python3.12/site-packages" \
    --quiet
(cd "$LAYER_STAGING" && zip -r "$LAYER_ZIP" .)
echo "Layer:    $LAYER_ZIP"

echo "=== Building Lambda function (source only) ==="
cp "$LAMBDA_SRC"/*.py "$FUNC_STAGING/"
(cd "$FUNC_STAGING" && zip -r "$FUNCTION_ZIP" .)
echo "Function: $FUNCTION_ZIP"
