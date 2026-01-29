"""Google Cloud Storage adapter for document storage."""

from pathlib import Path
from typing import Optional
import io

try:
    from google.cloud import storage
    HAS_GCS = True
except ImportError:
    HAS_GCS = False


class GCSStore:
    """Google Cloud Storage adapter for documents."""

    def __init__(self, bucket_name: str, project_id: Optional[str] = None):
        """
        Initialize GCS store.
        
        Args:
            bucket_name: Name of the GCS bucket
            project_id: GCP project ID (optional, uses default if not provided)
        """
        if not HAS_GCS:
            raise ImportError(
                "google-cloud-storage is required for GCS support. "
                "Install with: pip install analyzer[gcp]"
            )

        self.bucket_name = bucket_name
        self.client = storage.Client(project=project_id)
        self.bucket = self.client.bucket(bucket_name)

    def upload_file(self, local_path: Path, remote_path: str) -> str:
        """
        Upload a file to GCS.
        
        Args:
            local_path: Local file path
            remote_path: Remote path in GCS bucket (e.g., "company_id/doc_id/file.pdf")
            
        Returns:
            GCS URI (gs://bucket/path)
        """
        blob = self.bucket.blob(remote_path)
        blob.upload_from_filename(str(local_path))
        return f"gs://{self.bucket_name}/{remote_path}"

    def download_file(self, remote_path: str, local_path: Path) -> None:
        """
        Download a file from GCS.
        
        Args:
            remote_path: Remote path in GCS bucket
            local_path: Local file path to save to
        """
        blob = self.bucket.blob(remote_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(str(local_path))

    def file_exists(self, remote_path: str) -> bool:
        """
        Check if a file exists in GCS.
        
        Args:
            remote_path: Remote path in GCS bucket
            
        Returns:
            True if file exists, False otherwise
        """
        blob = self.bucket.blob(remote_path)
        return blob.exists()

    def delete_file(self, remote_path: str) -> None:
        """
        Delete a file from GCS.
        
        Args:
            remote_path: Remote path in GCS bucket
        """
        blob = self.bucket.blob(remote_path)
        blob.delete()

    def list_files(self, prefix: str = "") -> list[str]:
        """
        List files in GCS bucket with optional prefix.
        
        Args:
            prefix: Prefix to filter files (e.g., "company_id/")
            
        Returns:
            List of file paths
        """
        blobs = self.client.list_blobs(self.bucket_name, prefix=prefix)
        return [blob.name for blob in blobs]

    def get_file_content(self, remote_path: str) -> bytes:
        """
        Get file content from GCS.
        
        Args:
            remote_path: Remote path in GCS bucket
            
        Returns:
            File content as bytes
        """
        blob = self.bucket.blob(remote_path)
        return blob.download_as_bytes()

    def put_file_content(self, remote_path: str, content: bytes) -> str:
        """
        Put file content to GCS.
        
        Args:
            remote_path: Remote path in GCS bucket
            content: File content as bytes
            
        Returns:
            GCS URI (gs://bucket/path)
        """
        blob = self.bucket.blob(remote_path)
        blob.upload_from_string(content)
        return f"gs://{self.bucket_name}/{remote_path}"


def get_gcs_store(config) -> Optional[GCSStore]:
    """
    Get GCS store instance from config.
    
    Args:
        config: Application config
        
    Returns:
        GCSStore instance or None if GCS is not configured
    """
    if config.use_gcs and config.gcs_bucket:
        return GCSStore(
            bucket_name=config.gcs_bucket,
            project_id=config.gcp_project_id,
        )
    return None
