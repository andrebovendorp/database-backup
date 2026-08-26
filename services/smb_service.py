"""SMB service for uploading backup files."""
import logging
import os
from pathlib import Path
from typing import Optional

from models.database_config import SMBConfig

try:
    import smbclient
except ImportError:
    smbclient = None


class SMBService:
    """Upload backup files to an SMB share."""

    def __init__(self, smb_config: SMBConfig):
        self.smb_config = smb_config
        self.logger = logging.getLogger(self.__class__.__name__)
        self._connected = False

    @property
    def base_path(self) -> str:
        """Return the share path in the format expected by smbclient."""
        remote_dir = self.smb_config.remote_dir.strip("/\\")
        parts = [self.smb_config.host, self.smb_config.share]
        if remote_dir:
            parts.append(remote_dir.replace("/", "\\"))
        return "\\\\" + "\\".join(parts)

    def connect(self) -> bool:
        """Register an authenticated SMB session."""
        if smbclient is None:
            self.logger.error("SMB support requires the smbprotocol package")
            return False
        try:
            smbclient.register_session(
                self.smb_config.host,
                username=self.smb_config.username,
                password=self.smb_config.password,
                port=self.smb_config.port
            )
            self._connected = True
            self.logger.info("Connected to SMB share: %s", self.base_path)
            return True
        except Exception as e:
            self.logger.error("Failed to connect to SMB share: %s", e)
            self._connected = False
            return False

    def disconnect(self):
        """Close the SMB session."""
        if smbclient is not None and self._connected:
            try:
                smbclient.delete_session(self.smb_config.host)
            except Exception as e:
                self.logger.warning("Error during SMB disconnect: %s", e)
            finally:
                self._connected = False

    def upload_file(self, local_file_path: str, remote_filename: Optional[str] = None) -> bool:
        """Upload a local file to the configured SMB directory."""
        if smbclient is None or not self._connected:
            self.logger.error("Not connected to SMB share")
            return False
        if not os.path.exists(local_file_path):
            self.logger.error("Local file does not exist: %s", local_file_path)
            return False

        remote_filename = remote_filename or Path(local_file_path).name
        remote_path = "\\".join([self.base_path.rstrip("\\"), remote_filename])
        try:
            with open(local_file_path, "rb") as source, smbclient.open_file(remote_path, mode="wb") as target:
                while chunk := source.read(1024 * 1024):
                    target.write(chunk)
            self.logger.info("Uploaded file: %s -> %s", local_file_path, remote_path)
            return True
        except Exception as e:
            self.logger.error("Failed to upload file %s: %s", local_file_path, e)
            return False

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()