import json


def lambda_handler(event, context):
    http_method = event.get("httpMethod", "DIRECT")
    path = event.get("path", "/")
    name = (event.get("queryStringParameters") or {}).get("name", "World")

    body = {
        "message": f"Hello, {name}!",
        "method": http_method,
        "path": path,
    }

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
