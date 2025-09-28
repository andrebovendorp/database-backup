"""
Backup result models for tracking backup operations.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from enum import Enum


class BackupStatus(Enum):
    """Backup operation status."""
    SUCCESS = "success"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"
    CANCELLED = "cancelled"


@dataclass
class BackupResult:
    """Result of a backup operation."""
    backup_id: str
    database_type: str
    database_name: str
    status: BackupStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    backup_file_path: Optional[str] = None
    backup_size_bytes: Optional[int] = None
    error_message: Optional[str] = None
    ftp_uploaded: bool = False
    telegram_notified: bool = False
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate backup duration in seconds."""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def is_successful(self) -> bool:
        """Check if backup was successful."""
        return self.status == BackupStatus.SUCCESS
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'backup_id': self.backup_id,
            'database_type': self.database_type,
            'database_name': self.database_name,
            'status': self.status.value,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'backup_file_path': self.backup_file_path,
            'backup_size_bytes': self.backup_size_bytes,
            'error_message': self.error_message,
            'ftp_uploaded': self.ftp_uploaded,
            'telegram_notified': self.telegram_notified,
            'duration_seconds': self.duration_seconds
        }


@dataclass
class BackupSummary:
    """Summary of backup operations."""
    total_backups: int
    successful_backups: int
    failed_backups: int
    total_size_bytes: int
    average_duration_seconds: float
    last_backup_time: Optional[datetime]
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_backups == 0:
            return 0.0
        return (self.successful_backups / self.total_backups) * 100
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'total_backups': self.total_backups,
            'successful_backups': self.successful_backups,
            'failed_backups': self.failed_backups,
            'total_size_bytes': self.total_size_bytes,
            'average_duration_seconds': self.average_duration_seconds,
            'last_backup_time': self.last_backup_time.isoformat() if self.last_backup_time else None,
            'success_rate': self.success_rate
        }

