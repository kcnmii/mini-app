from __future__ import annotations

import io
from typing import Optional

from aiobotocore.session import get_session
import botocore.exceptions

import boto3
from app.core.config import settings

def get_boto_config():
    # Only supply endpoint_url if host is not AWS (e.g., local MinIO)
    is_aws = "amazonaws.com" in settings.s3_endpoint
    config = {
        "aws_access_key_id": settings.s3_access_key,
        "aws_secret_access_key": settings.s3_secret_key,
    }
    if not is_aws and settings.s3_endpoint:
        config["endpoint_url"] = settings.s3_endpoint
    return config

def download_file_sync(key: str) -> Optional[bytes]:
    """Download a file from S3 synchronously using boto3."""
    config = get_boto_config()
    endpoint_url = config.pop("endpoint_url", None)
    s3_client = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        **config
    )
    try:
        response = s3_client.get_object(Bucket=settings.s3_bucket, Key=key)
        return response["Body"].read()
    except Exception:
        return None

async def upload_file(key: str, content: bytes, content_type: str = "application/octet-stream") -> str:
    """Upload a file to S3 and return its key."""
    session = get_session()
    async with session.create_client("s3", **get_boto_config()) as client:
        await client.put_object(
            Bucket=settings.s3_bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
        )
    return key

async def download_file(key: str) -> Optional[bytes]:
    """Download a file from S3."""
    session = get_session()
    async with session.create_client("s3", **get_boto_config()) as client:
        try:
            response = await client.get_object(Bucket=settings.s3_bucket, Key=key)
            async with response["Body"] as stream:
                return await stream.read()
        except client.exceptions.NoSuchKey:
            return None

async def delete_file(key: str) -> None:
    """Delete a file from S3."""
    session = get_session()
    async with session.create_client("s3", **get_boto_config()) as client:
        await client.delete_object(Bucket=settings.s3_bucket, Key=key)

async def check_file_exists(key: str) -> bool:
    """Check if a file exists in S3."""
    session = get_session()
    async with session.create_client("s3", **get_boto_config()) as client:
        try:
            await client.head_object(Bucket=settings.s3_bucket, Key=key)
            return True
        except botocore.exceptions.ClientError as e:
            if int(e.response["Error"]["Code"]) == 404:
                return False
            raise
