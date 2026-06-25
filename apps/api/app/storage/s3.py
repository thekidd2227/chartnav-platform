"""Amazon S3 object-storage adapter (staging / production).

Server-side encryption with a customer-managed KMS key, presigned upload /
download URLs with short expiry, organization-scoped keys, public access
blocked at the bucket (enforced in infra/terraform/aws/s3.tf). boto3 is
imported lazily so dev/test environments without it can still import the
package.
"""
from __future__ import annotations

from .base import (
    ObjectStorage,
    StoredObject,
    StorageError,
    derive_key,
    key_belongs_to_org,
)


class S3ObjectStorage(ObjectStorage):
    def __init__(self, *, bucket: str, kms_key_id: str, region: str | None = None):
        if not bucket:
            raise StorageError("S3ObjectStorage requires a bucket")
        if not kms_key_id:
            raise StorageError(
                "S3ObjectStorage requires a KMS key id — unencrypted object "
                "storage is not permitted."
            )
        try:
            import boto3  # type: ignore
        except ImportError as e:  # pragma: no cover - depends on deploy image
            raise StorageError("boto3 is required for S3 storage") from e
        self.bucket = bucket
        self.kms_key_id = kms_key_id
        self._client = boto3.client("s3", region_name=region)

    def put(self, *, organization_id, kind, name, data, content_type,
            expected_sha256=None, metadata=None) -> StoredObject:
        digest = self._validate(data, content_type, expected_sha256)
        key = derive_key(organization_id, kind, name)
        self._client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            ServerSideEncryption="aws:kms",
            SSEKMSKeyId=self.kms_key_id,
            Metadata={
                "organization_id": str(organization_id),
                "sha256": digest,
                **{k: str(v) for k, v in (metadata or {}).items()},
            },
        )
        return StoredObject(key=key, organization_id=organization_id,
                            size=len(data), content_type=content_type,
                            sha256=digest, metadata=metadata or {})

    def presigned_get_url(self, *, key, organization_id, expires_seconds=300) -> str:
        if not key_belongs_to_org(key, organization_id):
            raise StorageError("key does not belong to organization")
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=min(expires_seconds, 3600),
        )

    def presigned_put_url(self, *, organization_id, kind, name, content_type,
                          expires_seconds=300) -> dict:
        key = derive_key(organization_id, kind, name)
        url = self._client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self.bucket,
                "Key": key,
                "ContentType": content_type,
                "ServerSideEncryption": "aws:kms",
                "SSEKMSKeyId": self.kms_key_id,
            },
            ExpiresIn=min(expires_seconds, 3600),
        )
        return {"url": url, "key": key, "method": "PUT",
                "headers": {"Content-Type": content_type,
                            "x-amz-server-side-encryption": "aws:kms"}}

    def delete(self, *, key, organization_id) -> None:
        if not key_belongs_to_org(key, organization_id):
            raise StorageError("key does not belong to organization")
        self._client.delete_object(Bucket=self.bucket, Key=key)
