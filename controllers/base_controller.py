"""
Base controller for database backup operations.
"""
import os
import subprocess
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List
from pathlib import Path

from models.database_config import DatabaseConfig, BackupConfig
from models.backup_result import BackupResult, BackupStatus


class BaseBackupController(ABC):
    """Base class for database backup controllers."""
    
    def __init__(self, db_config: DatabaseConfig, backup_config: BackupConfig):
        """Initialize the backup controller."""
        self.db_config = db_config
        self.backup_config = backup_config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Ensure backup directory exists
        Path(self.backup_config.backup_dir).mkdir(parents=True, exist_ok=True)
    
    @abstractmethod
    def create_backup(self) -> BackupResult:
        """Create a database backup."""
        pass
    
    @abstractmethod
    def restore_backup(self, backup_file_path: str) -> bool:
        """Restore database from backup file."""
        pass
    
    def cleanup_old_backups(self) -> List[str]:
        """Clean up old backup files based on retention policy."""
        backup_dir = Path(self.backup_config.backup_dir)
        cutoff_date = datetime.now().timestamp() - (self.backup_config.retention_days * 24 * 3600)
        
        deleted_files = []
        
        for backup_file in backup_dir.glob("*.tar.gz"):
            if backup_file.stat().st_mtime < cutoff_date:
                try:
                    backup_file.unlink()
                    deleted_files.append(str(backup_file))
                    self.logger.info(f"Deleted old backup: {backup_file}")
                except OSError as e:
                    self.logger.error(f"Failed to delete old backup {backup_file}: {e}")
        
        return deleted_files
    
    def _generate_backup_filename(self) -> str:
        """Generate backup filename with timestamp."""
        timestamp = datetime.now().strftime(self.backup_config.timestamp_format)
        return f"backup_{self.db_config.database}_{timestamp}.tar.gz"
    
    def _get_backup_file_path(self, filename: str) -> str:
        """Get full path for backup file."""
        return str(Path(self.backup_config.backup_dir) / filename)
    
    def _execute_command(self, command: List[str], timeout: int = 300) -> tuple:
        """Execute shell command and return (success, output, error)."""
        try:
            self.logger.debug(f"Executing command: {' '.join(command)}")
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            
            if result.returncode == 0:
                self.logger.debug(f"Command successful: {result.stdout}")
                return True, result.stdout, result.stderr
            else:
                self.logger.error(f"Command failed with return code {result.returncode}: {result.stderr}")
                return False, result.stdout, result.stderr
                
        except subprocess.TimeoutExpired as e:
            self.logger.error(f"Command timed out after {timeout} seconds: {e}")
            return False, "", str(e)
        except Exception as e:
            self.logger.error(f"Command execution failed: {e}")
            return False, "", str(e)
    
    def _get_file_size(self, file_path: str) -> int:
        """Get file size in bytes."""
        try:
            return os.path.getsize(file_path)
        except OSError:
            return 0

