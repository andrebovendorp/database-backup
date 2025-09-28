"""
MongoDB backup controller implementation.
"""
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List

from .base_controller import BaseBackupController
from models.database_config import MongoDBConfig
from models.backup_result import BackupResult, BackupStatus


class MongoDBBackupController(BaseBackupController):
    """MongoDB specific backup controller."""
    
    def __init__(self, db_config: MongoDBConfig, backup_config):
        """Initialize MongoDB backup controller."""
        super().__init__(db_config, backup_config)
        self.db_config: MongoDBConfig = db_config
    
    def create_backup(self) -> BackupResult:
        """Create MongoDB backup using mongodump."""
        backup_id = f"mongo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.now()
        
        backup_result = BackupResult(
            backup_id=backup_id,
            database_type="mongodb",
            database_name=self.db_config.database,
            status=BackupStatus.IN_PROGRESS,
            start_time=start_time
        )
        
        try:
            # Create temporary directory for dump
            with tempfile.TemporaryDirectory() as temp_dir:
                dump_dir = Path(temp_dir) / "dump"
                dump_dir.mkdir()
                
                # Build mongodump command
                mongodump_cmd = self._build_mongodump_command(str(dump_dir))
                
                # Execute mongodump
                success, stdout, stderr = self._execute_command(mongodump_cmd)
                
                if not success:
                    backup_result.status = BackupStatus.FAILED
                    backup_result.error_message = stderr
                    backup_result.end_time = datetime.now()
                    return backup_result
                
                # Create compressed archive
                backup_filename = self._generate_backup_filename()
                backup_file_path = self._get_backup_file_path(backup_filename)
                
                tar_cmd = ["tar", "-czf", backup_file_path, "-C", str(dump_dir), "."]
                success, stdout, stderr = self._execute_command(tar_cmd)
                
                if not success:
                    backup_result.status = BackupStatus.FAILED
                    backup_result.error_message = f"Failed to create archive: {stderr}"
                    backup_result.end_time = datetime.now()
                    return backup_result
                
                # Update backup result
                backup_result.status = BackupStatus.SUCCESS
                backup_result.backup_file_path = backup_file_path
                backup_result.backup_size_bytes = self._get_file_size(backup_file_path)
                backup_result.end_time = datetime.now()
                
                self.logger.info(f"MongoDB backup completed successfully: {backup_file_path}")
                
        except Exception as e:
            backup_result.status = BackupStatus.FAILED
            backup_result.error_message = str(e)
            backup_result.end_time = datetime.now()
            self.logger.error(f"MongoDB backup failed: {e}")
        
        return backup_result
    
    def restore_backup(self, backup_file_path: str) -> bool:
        """Restore MongoDB from backup file."""
        try:
            # Extract backup
            with tempfile.TemporaryDirectory() as temp_dir:
                extract_cmd = ["tar", "-xzf", backup_file_path, "-C", temp_dir]
                success, stdout, stderr = self._execute_command(extract_cmd)
                
                if not success:
                    self.logger.error(f"Failed to extract backup: {stderr}")
                    return False
                
                # Find the dump directory
                dump_dir = Path(temp_dir)
                for item in dump_dir.iterdir():
                    if item.is_dir():
                        dump_dir = item
                        break
                
                # Build mongorestore command
                mongorestore_cmd = self._build_mongorestore_command(str(dump_dir))
                
                # Execute mongorestore
                success, stdout, stderr = self._execute_command(mongorestore_cmd)
                
                if success:
                    self.logger.info("MongoDB restore completed successfully")
                    return True
                else:
                    self.logger.error(f"MongoDB restore failed: {stderr}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"MongoDB restore failed: {e}")
            return False
    
    def _build_mongodump_command(self, output_dir: str) -> List[str]:
        """Build mongodump command with appropriate parameters."""
        cmd = ["mongodump", "--out", output_dir]
        
        if self.db_config.uri:
            cmd.extend(["--uri", self.db_config.uri])
        else:
            # Build connection string from individual parameters
            if self.db_config.host:
                cmd.extend(["--host", f"{self.db_config.host}:{self.db_config.port}"])
            
            if self.db_config.database:
                cmd.extend(["--db", self.db_config.database])
            
            if self.db_config.username:
                cmd.extend(["--username", self.db_config.username])
            
            if self.db_config.password:
                cmd.extend(["--password", self.db_config.password])
        
        # Add additional parameters
        if self.db_config.additional_params:
            for key, value in self.db_config.additional_params.items():
                if isinstance(value, bool) and value:
                    cmd.append(f"--{key}")
                elif not isinstance(value, bool):
                    cmd.extend([f"--{key}", str(value)])
        
        return cmd
    
    def _build_mongorestore_command(self, input_dir: str) -> List[str]:
        """Build mongorestore command with appropriate parameters."""
        cmd = ["mongorestore", input_dir]
        
        if self.db_config.uri:
            cmd.extend(["--uri", self.db_config.uri])
        else:
            # Build connection string from individual parameters
            if self.db_config.host:
                cmd.extend(["--host", f"{self.db_config.host}:{self.db_config.port}"])
            
            if self.db_config.database:
                cmd.extend(["--db", self.db_config.database])
            
            if self.db_config.username:
                cmd.extend(["--username", self.db_config.username])
            
            if self.db_config.password:
                cmd.extend(["--password", self.db_config.password])
        
        # Add additional parameters
        if self.db_config.additional_params:
            for key, value in self.db_config.additional_params.items():
                if isinstance(value, bool) and value:
                    cmd.append(f"--{key}")
                elif not isinstance(value, bool):
                    cmd.extend([f"--{key}", str(value)])
        
        return cmd

