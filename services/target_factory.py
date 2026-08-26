"""Factory for configured backup destinations."""
from typing import Any, Dict

from models.database_config import FTPConfig, SMBConfig
from services.ftp_target import FTPBackupTarget
from services.smb_service import SMBService


def create_backup_target(target_config: Dict[str, Any]):
    """Create a backup target from a ``type``-based configuration mapping."""
    target_type = target_config.get("type", "ftp").lower()
    if target_type == "ftp":
        return FTPBackupTarget(FTPConfig(
            host=target_config.get("host", ""),
            port=target_config.get("port", 21),
            username=target_config.get("username", ""),
            password=target_config.get("password", ""),
            remote_dir=target_config.get("remote_dir", "/"),
            ssl_enabled=target_config.get("ssl", False)
        ))
    if target_type == "smb":
        return SMBService(SMBConfig(
            host=target_config.get("host", ""),
            share=target_config.get("share", ""),
            username=target_config.get("username", ""),
            password=target_config.get("password", ""),
            remote_dir=target_config.get("remote_dir", ""),
            port=target_config.get("port", 445)
        ))
    raise ValueError(f"Unsupported backup target type: {target_type}")