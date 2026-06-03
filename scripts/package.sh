#!/usr/bin/env bash
# Builds a deployable Lambda zip at terraform-lambda/lambda.zip
set -euo pipefail

LAMBDA_SRC="$(cd "$(dirname "$0")/../lambda" && pwd)"
OUTPUT="$(cd "$(dirname "$0")/../terraform-lambda" && pwd)/lambda.zip"

echo "Packaging Lambda from: $LAMBDA_SRC"
echo "Output:               $OUTPUT"

STAGING=$(mktemp -d)
trap "rm -rf $STAGING" EXIT

if [ -s "$LAMBDA_SRC/requirements.txt" ]; then
    pip3 install -r "$LAMBDA_SRC/requirements.txt" --target "$STAGING" --quiet
fi

cp "$LAMBDA_SRC/handler.py" "$STAGING/"

(cd "$STAGING" && zip -r "$OUTPUT" .)

echo "Done: $OUTPUT"
