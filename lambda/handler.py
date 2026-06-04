import json

from service import process


def lambda_handler(event, context):
    record = event["Records"][0]["s3"]
    return {
        "statusCode": 200,
        "body": json.dumps(process(record["bucket"]["name"], record["object"]["key"])),
    }
