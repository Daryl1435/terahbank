"""
S3 helpers for KYC document storage.
All documents uploaded with AES256 server-side encryption.
Storage keys are stored in DB — never the presigned URLs.
Presigned URLs are generated on-demand and cached in Redis (5-min TTL).
"""

import asyncio
import logging
from functools import partial

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from .config import settings

logger = logging.getLogger("terahbank.s3")


def _build_client():
    """Build a boto3 S3 client. Credentials come from env / IAM role."""
    kwargs: dict = {"region_name": settings.AWS_REGION}
    if settings.AWS_ACCESS_KEY_ID:
        kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
    if settings.AWS_SECRET_ACCESS_KEY:
        kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
    return boto3.client("s3", **kwargs)


async def upload_kyc_document(key: str, data: bytes, content_type: str) -> None:
    """
    Upload a KYC document to S3 with AES256 server-side encryption.
    Runs the blocking boto3 call in a thread pool to avoid blocking the event loop.

    Args:
        key: S3 object key — e.g. kyc/{user_id}/{doc_type}/{uuid}.jpg
        data: raw file bytes
        content_type: MIME type (image/jpeg, image/png, application/pdf)
    Raises:
        RuntimeError on S3 upload failure.
    """
    client = _build_client()
    loop = asyncio.get_event_loop()
    put = partial(
        client.put_object,
        Bucket=settings.AWS_S3_KYC_BUCKET,
        Key=key,
        Body=data,
        ContentType=content_type,
        ServerSideEncryption="AES256",
    )
    try:
        await loop.run_in_executor(None, put)
    except (BotoCoreError, ClientError) as exc:
        logger.error("S3 upload failed for key=%s: %s", key, exc)
        raise RuntimeError(f"Document storage failed: {exc}") from exc


async def generate_presigned_url(key: str, expires_in: int = 300) -> str:
    """
    Generate a presigned GET URL for a KYC document.
    Valid for `expires_in` seconds (default 5 min).
    Cache the result in Redis with the same TTL — caller's responsibility.
    """
    client = _build_client()
    loop = asyncio.get_event_loop()
    generate = partial(
        client.generate_presigned_url,
        "get_object",
        Params={"Bucket": settings.AWS_S3_KYC_BUCKET, "Key": key},
        ExpiresIn=expires_in,
    )
    try:
        return await loop.run_in_executor(None, generate)
    except (BotoCoreError, ClientError) as exc:
        logger.error("Presigned URL generation failed for key=%s: %s", key, exc)
        raise RuntimeError(f"Could not generate document URL: {exc}") from exc
