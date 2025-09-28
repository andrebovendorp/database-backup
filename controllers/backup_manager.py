"""
Backup manager for orchestrating backup operations.
"""
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

from controllers.base_controller import BaseBackupController
from controllers.mongodb_controller import MongoDBBackupController
from controllers.postgresql_controller import PostgreSQLBackupController
from models.database_config import DatabaseConfig, MongoDBConfig, PostgreSQLConfig, BackupConfig
from models.backup_result import BackupResult, BackupSummary


class BackupManager:
    """Manages backup operations for multiple databases."""
    
    def __init__(self, backup_config: BackupConfig):
        """Initialize backup manager."""
        self.backup_config = backup_config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.controllers: Dict[str, BaseBackupController] = {}
        self.backup_history: List[BackupResult] = []
    
    def add_database(self, db_config: DatabaseConfig) -> str:
        """Add a database to backup management."""
        controller_id = f"{db_config.db_type.value}_{db_config.database}"
        
        if db_config.db_type.value == "mongodb":
            controller = MongoDBBackupController(db_config, self.backup_config)
        elif db_config.db_type.value == "postgresql":
            controller = PostgreSQLBackupController(db_config, self.backup_config)
        else:
            raise ValueError(f"Unsupported database type: {db_config.db_type}")
        
        self.controllers[controller_id] = controller
        self.logger.info(f"Added database controller: {controller_id}")
        return controller_id
    
    def backup_database(self, controller_id: str) -> BackupResult:
        """Backup a specific database."""
        if controller_id not in self.controllers:
            raise ValueError(f"Controller not found: {controller_id}")
        
        controller = self.controllers[controller_id]
        backup_result = controller.create_backup()
        
        # Add to history
        self.backup_history.append(backup_result)
        
        # Clean up old backups
        controller.cleanup_old_backups()
        
        return backup_result
    
    def backup_all_databases(self) -> List[BackupResult]:
        """Backup all managed databases."""
        results = []
        
        for controller_id in self.controllers:
            try:
                result = self.backup_database(controller_id)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Failed to backup {controller_id}: {e}")
                # Create failed result
                failed_result = BackupResult(
                    backup_id=f"failed_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    database_type=controller_id.split('_')[0],
                    database_name=controller_id.split('_', 1)[1],
                    status=BackupResult.BackupStatus.FAILED,
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    error_message=str(e)
                )
                results.append(failed_result)
        
        return results
    
    def restore_database(self, controller_id: str, backup_file_path: str) -> bool:
        """Restore a specific database from backup."""
        if controller_id not in self.controllers:
            raise ValueError(f"Controller not found: {controller_id}")
        
        controller = self.controllers[controller_id]
        return controller.restore_backup(backup_file_path)
    
    def get_backup_summary(self) -> BackupSummary:
        """Get summary of backup operations."""
        if not self.backup_history:
            return BackupSummary(
                total_backups=0,
                successful_backups=0,
                failed_backups=0,
                total_size_bytes=0,
                average_duration_seconds=0.0,
                last_backup_time=None
            )
        
        successful_backups = sum(1 for r in self.backup_history if r.is_successful)
        failed_backups = len(self.backup_history) - successful_backups
        total_size = sum(r.backup_size_bytes or 0 for r in self.backup_history)
        
        durations = [r.duration_seconds for r in self.backup_history if r.duration_seconds is not None]
        avg_duration = sum(durations) / len(durations) if durations else 0.0
        
        last_backup = max(self.backup_history, key=lambda r: r.start_time) if self.backup_history else None
        
        return BackupSummary(
            total_backups=len(self.backup_history),
            successful_backups=successful_backups,
            failed_backups=failed_backups,
            total_size_bytes=total_size,
            average_duration_seconds=avg_duration,
            last_backup_time=last_backup.start_time if last_backup else None
        )
    
    def list_backup_files(self, controller_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available backup files."""
        backup_dir = Path(self.backup_config.backup_dir)
        backup_files = []
        
        for backup_file in backup_dir.glob("*.tar.gz"):
            try:
                stat = backup_file.stat()
                file_info = {
                    'filename': backup_file.name,
                    'path': str(backup_file),
                    'size_bytes': stat.st_size,
                    'created_time': datetime.fromtimestamp(stat.st_ctime),
                    'modified_time': datetime.fromtimestamp(stat.st_mtime)
                }
                
                # Filter by controller if specified
                if controller_id:
                    if controller_id in backup_file.name:
                        backup_files.append(file_info)
                else:
                    backup_files.append(file_info)
                    
            except OSError as e:
                self.logger.warning(f"Could not stat backup file {backup_file}: {e}")
        
        return sorted(backup_files, key=lambda x: x['created_time'], reverse=True)
    
    def cleanup_all_backups(self) -> Dict[str, List[str]]:
        """Clean up old backups for all controllers."""
        cleanup_results = {}
        
        for controller_id, controller in self.controllers.items():
            try:
                deleted_files = controller.cleanup_old_backups()
                cleanup_results[controller_id] = deleted_files
                self.logger.info(f"Cleaned up {len(deleted_files)} old backups for {controller_id}")
            except Exception as e:
                self.logger.error(f"Failed to cleanup backups for {controller_id}: {e}")
                cleanup_results[controller_id] = []
        
        return cleanup_results

