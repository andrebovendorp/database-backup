"""
S3 service for uploading backup files to S3-compatible storage.
Supports AWS S3, MinIO, DigitalOcean Spaces, and other S3-compatible services.
"""
import logging
import os
from typing import List, Optional
from pathlib import Path
from datetime import datetime, timedelta

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

from models.database_config import S3Config


class S3Service:
    """Service for S3 operations."""
    
    def __init__(self, s3_config: S3Config):
        """Initialize S3 service."""
        if not BOTO3_AVAILABLE:
            raise ImportError("boto3 is required for S3 support. Install with: pip install boto3")
        
        self.s3_config = s3_config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize S3 client
        self._client = None
        self._setup_client()
    
    def _setup_client(self):
        """Setup boto3 S3 client."""
        try:
            session_kwargs = {}
            if self.s3_config.access_key and self.s3_config.secret_key:
                session_kwargs['aws_access_key_id'] = self.s3_config.access_key
                session_kwargs['aws_secret_access_key'] = self.s3_config.secret_key
            
            client_kwargs = {
                'region_name': self.s3_config.region
            }
            
            # Support for S3-compatible services (MinIO, DigitalOcean Spaces, etc.)
            if self.s3_config.endpoint_url:
                client_kwargs['endpoint_url'] = self.s3_config.endpoint_url
            
            session = boto3.Session(**session_kwargs)
            self._client = session.client('s3', **client_kwargs)
            
            self.logger.info(f"S3 client initialized for bucket: {self.s3_config.bucket}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize S3 client: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test connection to S3 bucket."""
        try:
            # Try to head the bucket to verify access
            self._client.head_bucket(Bucket=self.s3_config.bucket)
            self.logger.info(f"Successfully connected to S3 bucket: {self.s3_config.bucket}")
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                self.logger.error(f"S3 bucket does not exist: {self.s3_config.bucket}")
            elif error_code == '403':
                self.logger.error(f"Access denied to S3 bucket: {self.s3_config.bucket}")
            else:
                self.logger.error(f"S3 connection test failed: {e}")
            return False
        except NoCredentialsError:
            self.logger.error("No AWS credentials found")
            return False
        except Exception as e:
            self.logger.error(f"S3 connection test failed: {e}")
            return False
    
    def _get_s3_key(self, filename: str) -> str:
        """Get full S3 key with path prefix."""
        if self.s3_config.path_prefix:
            # Ensure path_prefix doesn't start with / and ends with /
            prefix = self.s3_config.path_prefix.strip('/')
            return f"{prefix}/{filename}"
        return filename
    
    def upload_file(self, local_file_path: str, remote_filename: Optional[str] = None) -> bool:
        """Upload a file to S3."""
        try:
            if not os.path.exists(local_file_path):
                self.logger.error(f"Local file does not exist: {local_file_path}")
                return False
            
            if remote_filename is None:
                remote_filename = Path(local_file_path).name
            
            s3_key = self._get_s3_key(remote_filename)
            
            # Upload file with progress tracking
            file_size = os.path.getsize(local_file_path)
            self.logger.info(f"Uploading {remote_filename} ({file_size} bytes) to S3...")
            
            self._client.upload_file(
                local_file_path,
                self.s3_config.bucket,
                s3_key,
                ExtraArgs={'StorageClass': 'STANDARD'}
            )
            
            self.logger.info(f"Successfully uploaded: {local_file_path} -> s3://{self.s3_config.bucket}/{s3_key}")
            return True
            
        except ClientError as e:
            self.logger.error(f"Failed to upload file to S3: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to upload file {local_file_path}: {e}")
            return False
    
    def download_file(self, remote_filename: str, local_file_path: str) -> bool:
        """Download a file from S3."""
        try:
            # Ensure local directory exists
            Path(local_file_path).parent.mkdir(parents=True, exist_ok=True)
            
            s3_key = self._get_s3_key(remote_filename)
            
            self._client.download_file(
                self.s3_config.bucket,
                s3_key,
                local_file_path
            )
            
            self.logger.info(f"Downloaded: s3://{self.s3_config.bucket}/{s3_key} -> {local_file_path}")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                self.logger.error(f"File not found in S3: {remote_filename}")
            else:
                self.logger.error(f"Failed to download file from S3: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to download file {remote_filename}: {e}")
            return False
    
    def list_files(self, prefix: str = "") -> List[dict]:
        """List files in S3 bucket."""
        try:
            s3_prefix = self._get_s3_key(prefix) if prefix else self.s3_config.path_prefix
            
            response = self._client.list_objects_v2(
                Bucket=self.s3_config.bucket,
                Prefix=s3_prefix
            )
            
            if 'Contents' not in response:
                return []
            
            files = []
            for obj in response['Contents']:
                # Remove path prefix from key for cleaner display
                key = obj['Key']
                if self.s3_config.path_prefix and key.startswith(self.s3_config.path_prefix):
                    display_name = key[len(self.s3_config.path_prefix):].lstrip('/')
                else:
                    display_name = key
                
                files.append({
                    'key': key,
                    'filename': display_name,
                    'size': obj['Size'],
                    'last_modified': obj['LastModified']
                })
            
            return files
            
        except ClientError as e:
            self.logger.error(f"Failed to list files in S3: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Failed to list files: {e}")
            return []
    
    def delete_file(self, remote_filename: str) -> bool:
        """Delete a file from S3."""
        try:
            s3_key = self._get_s3_key(remote_filename)
            
            self._client.delete_object(
                Bucket=self.s3_config.bucket,
                Key=s3_key
            )
            
            self.logger.info(f"Deleted file from S3: {s3_key}")
            return True
            
        except ClientError as e:
            self.logger.error(f"Failed to delete file from S3: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to delete file {remote_filename}: {e}")
            return False
    
    def cleanup_old_files(self, retention_days: int = 7, pattern: str = "*.tar.gz") -> List[str]:
        """Clean up old backup files based on retention policy."""
        try:
            files = self.list_files()
            deleted_files = []
            
            cutoff_date = datetime.now(files[0]['last_modified'].tzinfo) - timedelta(days=retention_days) if files else datetime.now()
            
            for file_info in files:
                # Check if file matches pattern (simple check)
                if pattern != "*" and not file_info['filename'].endswith(pattern.replace("*", "")):
                    continue
                
                if file_info['last_modified'] < cutoff_date:
                    if self.delete_file(file_info['filename']):
                        deleted_files.append(file_info['filename'])
                        self.logger.info(f"Deleted old backup from S3: {file_info['filename']}")
                    else:
                        self.logger.warning(f"Failed to delete old backup: {file_info['filename']}")
            
            return deleted_files
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old files in S3: {e}")
            return []
    
    def get_file_url(self, remote_filename: str, expiration: int = 3600) -> Optional[str]:
        """Generate a presigned URL for temporary access to a file."""
        try:
            s3_key = self._get_s3_key(remote_filename)
            
            url = self._client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.s3_config.bucket,
                    'Key': s3_key
                },
                ExpiresIn=expiration
            )
            
            self.logger.info(f"Generated presigned URL for: {remote_filename}")
            return url
            
        except ClientError as e:
            self.logger.error(f"Failed to generate presigned URL: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to generate presigned URL for {remote_filename}: {e}")
            return None
