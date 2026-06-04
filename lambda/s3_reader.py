import logging

import boto3

logger = logging.getLogger(__name__)


def fetch_csv(bucket: str, key: str) -> str:
    s3 = boto3.client("s3")
    obj = s3.get_object(Bucket=bucket, Key=key)
    return obj["Body"].read().decode("utf-8")


def move_to_processed(source_bucket: str, key: str, dest_bucket: str) -> None:
    s3 = boto3.client("s3")
    s3.copy_object(
        CopySource={"Bucket": source_bucket, "Key": key},
        Bucket=dest_bucket,
        Key=key,
    )
    s3.delete_object(Bucket=source_bucket, Key=key)
    logger.info("Moved s3://%s/%s -> s3://%s/%s", source_bucket, key, dest_bucket, key)
