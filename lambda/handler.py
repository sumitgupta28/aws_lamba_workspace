import json
import logging
import os

from service import process

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    record = event["Records"][0]["s3"]
    bucket = record["bucket"]["name"]
    key = record["object"]["key"]
    logger.info("Processing S3 event: bucket=%s key=%s", bucket, key)
    processed_bucket = os.environ["PROCESSED_BUCKET"]
    result = process(bucket, key, processed_bucket)
    logger.info("Lambda completed: inserted=%d file=%s", result["inserted"], result["file"])
    return {"statusCode": 200, "body": json.dumps(result)}
