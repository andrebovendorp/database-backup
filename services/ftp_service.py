"""
FTP service for uploading backup files.
"""
import logging
import os
from typing import List, Optional
from ftplib import FTP, FTP_TLS
from pathlib import Path

from models.database_config import FTPConfig


class FTPService:
    """Service for FTP operations."""
    
    def __init__(self, ftp_config: FTPConfig):
        """Initialize FTP service."""
        self.ftp_config = ftp_config
        self.logger = logging.getLogger(self.__class__.__name__)
        self._connection: Optional[FTP] = None
    
    def connect(self) -> bool:
        """Connect to FTP server."""
        try:
            if self.ftp_config.ssl_enabled:
                self._connection = FTP_TLS()
            else:
                self._connection = FTP()
            
            self._connection.connect(self.ftp_config.host, self.ftp_config.port)
            self._connection.login(self.ftp_config.username, self.ftp_config.password)
            
            if self.ftp_config.ssl_enabled:
                self._connection.prot_p()  # Enable data connection protection
            
            # Change to remote directory
            self._connection.cwd(self.ftp_config.remote_dir)
            
            self.logger.info(f"Connected to FTP server: {self.ftp_config.host}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to FTP server: {e}")
            self._connection = None  # Reset connection on failure
            return False
    
    def disconnect(self):
        """Disconnect from FTP server."""
        if self._connection:
            try:
                self._connection.quit()
                self.logger.info("Disconnected from FTP server")
            except Exception as e:
                self.logger.warning(f"Error during FTP disconnect: {e}")
            finally:
                self._connection = None
    
    def upload_file(self, local_file_path: str, remote_filename: Optional[str] = None) -> bool:
        """Upload a file to FTP server."""
        if not self._connection:
            self.logger.error("Not connected to FTP server")
            return False
        
        try:
            if not os.path.exists(local_file_path):
                self.logger.error(f"Local file does not exist: {local_file_path}")
                return False
            
            if remote_filename is None:
                remote_filename = Path(local_file_path).name
            
            with open(local_file_path, 'rb') as file:
                self._connection.storbinary(f'STOR {remote_filename}', file)
            
            self.logger.info(f"Uploaded file: {local_file_path} -> {remote_filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to upload file {local_file_path}: {e}")
            return False
    
    def download_file(self, remote_filename: str, local_file_path: str) -> bool:
        """Download a file from FTP server."""
        if not self._connection:
            self.logger.error("Not connected to FTP server")
            return False
        
        try:
            # Ensure local directory exists
            Path(local_file_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(local_file_path, 'wb') as file:
                self._connection.retrbinary(f'RETR {remote_filename}', file.write)
            
            self.logger.info(f"Downloaded file: {remote_filename} -> {local_file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to download file {remote_filename}: {e}")
            return False
    
    def list_files(self, pattern: str = "*") -> List[str]:
        """List files on FTP server."""
        if not self._connection:
            self.logger.error("Not connected to FTP server")
            return []
        
        try:
            files = []
            self._connection.retrlines('LIST', files.append)
            
            # Parse file names from LIST output
            file_names = []
            for line in files:
                parts = line.split()
                if len(parts) >= 9:
                    filename = ' '.join(parts[8:])  # Handle filenames with spaces
                    if pattern == "*" or filename.endswith(pattern.replace("*", "")):
                        file_names.append(filename)
            
            return file_names
            
        except Exception as e:
            self.logger.error(f"Failed to list files: {e}")
            return []
    
    def delete_file(self, remote_filename: str) -> bool:
        """Delete a file from FTP server."""
        if not self._connection:
            self.logger.error("Not connected to FTP server")
            return False
        
        try:
            self._connection.delete(remote_filename)
            self.logger.info(f"Deleted file: {remote_filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete file {remote_filename}: {e}")
            return False
    
    def cleanup_old_files(self, retention_days: int = 7) -> List[str]:
        """Clean up old backup files based on retention policy."""
        if not self._connection:
            self.logger.error("Not connected to FTP server")
            return []
        
        try:
            files = self.list_files("*.tar.gz")
            deleted_files = []
            
            # Get current timestamp for comparison
            import time
            current_time = time.time()
            cutoff_time = current_time - (retention_days * 24 * 3600)
            
            for filename in files:
                try:
                    # Get file modification time
                    mtime = self._connection.voidcmd(f"MDTM {filename}")[4:].strip()
                    # Parse FTP timestamp format (YYYYMMDDHHMMSS)
                    file_time = time.mktime(time.strptime(mtime, "%Y%m%d%H%M%S"))
                    
                    if file_time < cutoff_time:
                        if self.delete_file(filename):
                            deleted_files.append(filename)
                            self.logger.info(f"Deleted old backup: {filename}")
                        else:
                            self.logger.warning(f"Failed to delete old backup: {filename}")
                    else:
                        self.logger.debug(f"Keeping backup: {filename}")
                        
                except Exception as e:
                    self.logger.warning(f"Could not process file {filename}: {e}")
            
            return deleted_files
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old files: {e}")
            return []
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()

