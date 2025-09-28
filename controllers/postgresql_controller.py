"""
PostgreSQL backup controller implementation.
"""
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List

from .base_controller import BaseBackupController
from models.database_config import PostgreSQLConfig
from models.backup_result import BackupResult, BackupStatus


class PostgreSQLBackupController(BaseBackupController):
    """PostgreSQL specific backup controller."""
    
    def __init__(self, db_config: PostgreSQLConfig, backup_config):
        """Initialize PostgreSQL backup controller."""
        super().__init__(db_config, backup_config)
        self.db_config: PostgreSQLConfig = db_config
    
    def create_backup(self) -> BackupResult:
        """Create PostgreSQL backup using pg_dump."""
        backup_id = f"pgsql_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.now()
        
        backup_result = BackupResult(
            backup_id=backup_id,
            database_type="postgresql",
            database_name=self.db_config.database,
            status=BackupStatus.IN_PROGRESS,
            start_time=start_time
        )
        
        try:
            # Create temporary file for dump
            with tempfile.NamedTemporaryFile(mode='w+b', suffix='.sql', delete=False) as temp_file:
                temp_file_path = temp_file.name
                
                # Build pg_dump command
                pg_dump_cmd = self._build_pg_dump_command(temp_file_path)
                
                # Execute pg_dump
                success, stdout, stderr = self._execute_command(pg_dump_cmd)
                
                if not success:
                    backup_result.status = BackupStatus.FAILED
                    backup_result.error_message = stderr
                    backup_result.end_time = datetime.now()
                    return backup_result
                
                # Create compressed archive
                backup_filename = self._generate_backup_filename()
                backup_file_path = self._get_backup_file_path(backup_filename)
                
                tar_cmd = ["tar", "-czf", backup_file_path, "-C", str(Path(temp_file_path).parent), 
                          Path(temp_file_path).name]
                success, stdout, stderr = self._execute_command(tar_cmd)
                
                if not success:
                    backup_result.status = BackupStatus.FAILED
                    backup_result.error_message = f"Failed to create archive: {stderr}"
                    backup_result.end_time = datetime.now()
                    return backup_result
                
                # Clean up temporary file
                try:
                    os.unlink(temp_file_path)
                except OSError:
                    pass
                
                # Update backup result
                backup_result.status = BackupStatus.SUCCESS
                backup_result.backup_file_path = backup_file_path
                backup_result.backup_size_bytes = self._get_file_size(backup_file_path)
                backup_result.end_time = datetime.now()
                
                self.logger.info(f"PostgreSQL backup completed successfully: {backup_file_path}")
                
        except Exception as e:
            backup_result.status = BackupStatus.FAILED
            backup_result.error_message = str(e)
            backup_result.end_time = datetime.now()
            self.logger.error(f"PostgreSQL backup failed: {e}")
        
        return backup_result
    
    def restore_backup(self, backup_file_path: str) -> bool:
        """Restore PostgreSQL from backup file."""
        try:
            # Extract backup
            with tempfile.TemporaryDirectory() as temp_dir:
                extract_cmd = ["tar", "-xzf", backup_file_path, "-C", temp_dir]
                success, stdout, stderr = self._execute_command(extract_cmd)
                
                if not success:
                    self.logger.error(f"Failed to extract backup: {stderr}")
                    return False
                
                # Find the SQL file
                sql_file = None
                for item in Path(temp_dir).iterdir():
                    if item.suffix == '.sql':
                        sql_file = item
                        break
                
                if not sql_file:
                    self.logger.error("No SQL file found in backup")
                    return False
                
                # Build psql command
                psql_cmd = self._build_psql_command(str(sql_file))
                
                # Execute psql
                success, stdout, stderr = self._execute_command(psql_cmd)
                
                if success:
                    self.logger.info("PostgreSQL restore completed successfully")
                    return True
                else:
                    self.logger.error(f"PostgreSQL restore failed: {stderr}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"PostgreSQL restore failed: {e}")
            return False
    
    def _build_pg_dump_command(self, output_file: str) -> List[str]:
        """Build pg_dump command with appropriate parameters."""
        cmd = ["pg_dump"]
        
        # Add connection parameters
        if self.db_config.host:
            cmd.extend(["--host", self.db_config.host])
        
        if self.db_config.port:
            cmd.extend(["--port", str(self.db_config.port)])
        
        if self.db_config.username:
            cmd.extend(["--username", self.db_config.username])
        
        if self.db_config.database:
            cmd.extend(["--dbname", self.db_config.database])
        
        # Add output file
        cmd.extend(["--file", output_file])
        
        # Add format and options
        cmd.extend(["--verbose", "--no-password"])
        
        # Add additional parameters
        if self.db_config.additional_params:
            for key, value in self.db_config.additional_params.items():
                if isinstance(value, bool) and value:
                    cmd.append(f"--{key}")
                elif not isinstance(value, bool):
                    cmd.extend([f"--{key}", str(value)])
        
        return cmd
    
    def _build_psql_command(self, input_file: str) -> List[str]:
        """Build psql command for restore."""
        cmd = ["psql"]
        
        # Add connection parameters
        if self.db_config.host:
            cmd.extend(["--host", self.db_config.host])
        
        if self.db_config.port:
            cmd.extend(["--port", str(self.db_config.port)])
        
        if self.db_config.username:
            cmd.extend(["--username", self.db_config.username])
        
        if self.db_config.database:
            cmd.extend(["--dbname", self.db_config.database])
        
        # Add input file
        cmd.extend(["--file", input_file])
        
        # Add options
        cmd.extend(["--verbose", "--no-password"])
        
        return cmd
