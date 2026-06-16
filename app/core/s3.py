import logging
import hashlib
import asyncio
import boto3
from botocore.exceptions import ClientError
from typing import Tuple, Optional
from fastapi import HTTPException

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class S3StorageService:
    def __init__(self):
        if not all([settings.aws_region, settings.aws_access_key_id, settings.aws_secret_access_key, settings.aws_s3_bucket]):
            logger.warning("AWS S3 credentials are not fully configured in environment.")
            self.client = None
            return
            
        try:
            self.client = boto3.client(
                's3',
                region_name=settings.aws_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key
            )
            # Parse bucket name and default prefix if a slash is provided (e.g., gramosoft/grag)
            bucket_parts = settings.aws_s3_bucket.split('/', 1)
            self.bucket_name = bucket_parts[0]
            self.base_prefix = bucket_parts[1] + '/' if len(bucket_parts) > 1 else ''
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            self.client = None

    def _store_file_sync(self, tenant_id: str, filename: str, file_bytes: bytes) -> Tuple[bool, Optional[str]]:
        """
        Synchronous method to check for duplicates and upload to S3.
        Returns (is_duplicate: bool, error_message: str|None)
        """
        if not self.client:
            logger.error("S3 client not initialized. Cannot store file.")
            raise ValueError("S3 configuration is missing or invalid.")

        # Compute SHA-256 hash of the file
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        
        # Construct S3 key: base_prefix + uploads/tenant_id/hash
        s3_key = f"{self.base_prefix}uploads/{tenant_id}/{file_hash}"
        
        # Check if the file already exists (duplicate detection)
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=s3_key)
            # If we succeed, the object exists -> it's a duplicate
            logger.info(f"Duplicate file detected for tenant {tenant_id}: {filename} (Hash: {file_hash})")
            return True, None
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            if error_code == '404':
                # File doesn't exist, proceed to upload
                pass
            else:
                logger.error(f"Error checking S3 object existence: {e}")
                raise e

        # Upload the new file
        try:
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_bytes,
                Metadata={
                    'original-filename': filename.encode('utf-8', 'ignore').decode('utf-8')
                }
            )
            logger.info(f"Successfully uploaded {filename} to S3 bucket {self.bucket_name} at key {s3_key}")
            return False, None
        except Exception as e:
            logger.error(f"Failed to upload file to S3: {e}")
            return False, str(e)

    async def store_file_if_not_duplicate(self, tenant_id: str, filename: str, file_bytes: bytes) -> None:
        """
        Asynchronously checks for duplicates and stores the file in S3.
        Raises HTTPException if duplicate or error occurs.
        """
        if not self.client:
            # If S3 is not configured, we might want to skip or raise error. 
            # Given the requirement, S3 storage is mandatory for user uploads.
            raise HTTPException(status_code=500, detail="S3 storage is not configured properly on the server.")

        try:
            is_duplicate, error_msg = await asyncio.to_thread(
                self._store_file_sync, str(tenant_id), filename, file_bytes
            )
            
            if is_duplicate:
                raise HTTPException(
                    status_code=409, 
                    detail="Duplicate file detected. This exact file has already been uploaded to your Knowledge Base."
                )
            
            if error_msg:
                raise HTTPException(status_code=500, detail=f"Failed to store file in S3: {error_msg}")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in S3 storage service: {e}")
            raise HTTPException(status_code=500, detail="An error occurred while communicating with AWS S3.")
