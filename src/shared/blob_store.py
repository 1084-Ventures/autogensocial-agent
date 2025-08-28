import os
from typing import Optional

try:
    from azure.storage.blob import BlobServiceClient, ContentSettings  # type: ignore
except Exception:  # pragma: no cover
    BlobServiceClient = None  # type: ignore
    ContentSettings = None  # type: ignore


def _get_service_client() -> "BlobServiceClient":
    conn = os.getenv("PUBLIC_BLOB_CONNECTION_STRING")
    if not conn:
        raise RuntimeError("PUBLIC_BLOB_CONNECTION_STRING is required for blob uploads")
    if BlobServiceClient is None:
        raise RuntimeError("azure-storage-blob package not available")
    return BlobServiceClient.from_connection_string(conn)


def upload_bytes(
    *,
    container: str,
    blob_name: str,
    data: bytes,
    content_type: Optional[str] = None,
) -> str:
    """Upload bytes to blob storage, return the blob URL.

    Uses PUBLIC_BLOB_CONNECTION_STRING. Creates container if missing.
    """
    service = _get_service_client()
    container_client = service.get_container_client(container)
    try:
        container_client.create_container(public_access="blob")
    except Exception:
        pass
    blob = container_client.get_blob_client(blob_name)
    kwargs = {}
    if content_type and ContentSettings is not None:
        kwargs["content_settings"] = ContentSettings(content_type=content_type)
    blob.upload_blob(data, overwrite=True, **kwargs)
    return blob.url

