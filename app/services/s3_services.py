import boto3
import os

BUCKET = os.environ["S3_BUCKET"]
s3 = boto3.client("s3")


def upload_document(key: str, content: bytes) -> None:
    s3.put_object(Bucket=BUCKET, Key=key, Body=content)


def list_documents() -> list[str]:
    response = s3.list_objects_v2(Bucket=BUCKET)
    return [obj["Key"] for obj in response.get("Contents", [])]


def read_document(key: str) -> str:
    obj = s3.get_object(Bucket=BUCKET, Key=key)
    return obj["Body"].read().decode("utf-8")


def delete_document(key: str) -> None:
    s3.delete_object(Bucket=BUCKET, Key=key)


def document_exists(key: str) -> bool:
    try:
        s3.head_object(Bucket=BUCKET, Key=key)
        return True
    except s3.exceptions.ClientError:
        return False