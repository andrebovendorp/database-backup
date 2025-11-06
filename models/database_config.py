"""
Database configuration models for backup system.
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum


class DatabaseType(Enum):
    """Supported database types."""
    MONGODB = "mongodb"
    POSTGRESQL = "postgresql"


@dataclass
class DatabaseConfig:
    """Base database configuration."""
    db_type: DatabaseType
    host: str
    port: int
    database: str
    username: Optional[str] = None
    password: Optional[str] = None
    uri: Optional[str] = None
    additional_params: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.host:
            raise ValueError("Host is required")
        if not self.database:
            raise ValueError("Database name is required")
        if self.port <= 0 or self.port > 65535:
            raise ValueError("Port must be between 1 and 65535")


@dataclass
class MongoDBConfig(DatabaseConfig):
    """MongoDB specific configuration."""
    
    def __init__(self, host: str, database: str, port: int = 27017, 
                 username: Optional[str] = None, password: Optional[str] = None, uri: Optional[str] = None,
                 additional_params: Optional[Dict[str, Any]] = None):
        super().__init__(
            db_type=DatabaseType.MONGODB,
            host=host,
            port=port,
            database=database,
            username=username,
            password=password,
            uri=uri,
            additional_params=additional_params or {}
        )


@dataclass
class PostgreSQLConfig(DatabaseConfig):
    """PostgreSQL specific configuration."""
    
    def __init__(self, host: str, database: str, port: int = 5432,
                 username: Optional[str] = None, password: Optional[str] = None, uri: Optional[str] = None,
                 additional_params: Optional[Dict[str, Any]] = None):
        super().__init__(
            db_type=DatabaseType.POSTGRESQL,
            host=host,
            port=port,
            database=database,
            username=username,
            password=password,
            uri=uri,
            additional_params=additional_params or {}
        )


@dataclass
class BackupConfig:
    """Backup configuration settings."""
    backup_dir: str
    retention_days: int = 7
    compression: bool = True
    timestamp_format: str = "%Y-%m-%d-%H-%M-%S"
    
    def __post_init__(self):
        """Validate backup configuration."""
        if self.retention_days < 1:
            raise ValueError("Retention days must be at least 1")
        if not self.backup_dir:
            raise ValueError("Backup directory is required")


@dataclass
class FTPConfig:
    """FTP server configuration."""
    host: str
    username: str
    password: str
    remote_dir: str
    port: int = 21
    ssl_enabled: bool = False
    
    def __post_init__(self):
        """Validate FTP configuration."""
        if not self.host:
            raise ValueError("FTP host is required")
        if not self.username:
            raise ValueError("FTP username is required")
        if not self.password:
            raise ValueError("FTP password is required")
        if not self.remote_dir:
            raise ValueError("FTP remote directory is required")


@dataclass
class TelegramConfig:
    """Telegram notification configuration."""
    bot_token: str
    chat_id: str
    enabled: bool = True
    
    def __post_init__(self):
        """Validate Telegram configuration."""
        if self.enabled:
            if not self.bot_token:
                raise ValueError("Telegram bot token is required when enabled")
            if not self.chat_id:
                raise ValueError("Telegram chat ID is required when enabled")


@dataclass
class S3Config:
    """S3 storage configuration for S3-compatible services."""
    bucket: str
    region: str = "us-east-1"
    access_key: Optional[str] = None
    secret_key: Optional[str] = None
    endpoint_url: Optional[str] = None  # For S3-compatible services like MinIO, DigitalOcean Spaces, etc.
    path_prefix: str = ""  # Optional prefix for organizing backups in bucket
    enabled: bool = True
    
    def __post_init__(self):
        """Validate S3 configuration."""
        if self.enabled:
            if not self.bucket:
                raise ValueError("S3 bucket is required when enabled")
            if not self.access_key:
                raise ValueError("S3 access key is required when enabled")
            if not self.secret_key:
                raise ValueError("S3 secret key is required when enabled")
