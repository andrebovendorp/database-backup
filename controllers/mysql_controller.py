"""
MySQL backup controller implementation.
"""
import os
import tempfile
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List

from .base_controller import BaseBackupController
from models.database_config import MySQLConfig
from models.backup_result import BackupResult, BackupStatus


class MySQLBackupController(BaseBackupController):
    """MySQL specific backup controller."""

    def __init__(self, db_config: MySQLConfig, backup_config):
        """Initialize MySQL backup controller."""
        super().__init__(db_config, backup_config)
        self.db_config: MySQLConfig = db_config

    def _execute_command_with_password(self, command: List[str], timeout: int = 300) -> tuple:
        """Execute MySQL command with MYSQL_PWD when password is configured."""
        try:
            env = os.environ.copy()
            if self.db_config.password:
                env["MYSQL_PWD"] = self.db_config.password

            self.logger.debug(f"Executing MySQL command: {' '.join(command)}")
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                env=env
            )

            if result.returncode == 0:
                return True, result.stdout, result.stderr

            return False, result.stdout, result.stderr

        except subprocess.TimeoutExpired as e:
            self.logger.error(f"MySQL command timed out after {timeout} seconds: {e}")
            return False, "", str(e)
        except Exception as e:
            self.logger.error(f"MySQL command execution failed: {e}")
            return False, "", str(e)

    def create_backup(self) -> BackupResult:
        """Create MySQL backup using mysqldump."""
        backup_id = f"mysql_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.now()

        backup_result = BackupResult(
            backup_id=backup_id,
            database_type="mysql",
            database_name=self.db_config.database,
            status=BackupStatus.IN_PROGRESS,
            start_time=start_time
        )

        try:
            with tempfile.NamedTemporaryFile(mode="w+b", suffix=".sql", delete=False) as temp_file:
                temp_file_path = temp_file.name

            try:
                mysqldump_cmd = self._build_mysqldump_command(temp_file_path)
                success, stdout, stderr = self._execute_command_with_password(mysqldump_cmd)

                if not success:
                    backup_result.status = BackupStatus.FAILED
                    backup_result.error_message = stderr
                    backup_result.end_time = datetime.now()
                    return backup_result

                backup_filename = self._generate_backup_filename()
                backup_file_path = self._get_backup_file_path(backup_filename)

                tar_cmd = ["tar", "-czf", backup_file_path, "-C", str(Path(temp_file_path).parent), Path(temp_file_path).name]
                success, stdout, stderr = self._execute_command(tar_cmd)

                if not success:
                    backup_result.status = BackupStatus.FAILED
                    backup_result.error_message = f"Failed to create archive: {stderr}"
                    backup_result.end_time = datetime.now()
                    return backup_result

                backup_result.status = BackupStatus.SUCCESS
                backup_result.backup_file_path = backup_file_path
                backup_result.backup_size_bytes = self._get_file_size(backup_file_path)
                backup_result.end_time = datetime.now()

                self.logger.info(f"MySQL backup completed successfully: {backup_file_path}")

            finally:
                try:
                    os.unlink(temp_file_path)
                except OSError:
                    pass

        except Exception as e:
            backup_result.status = BackupStatus.FAILED
            backup_result.error_message = str(e)
            backup_result.end_time = datetime.now()
            self.logger.error(f"MySQL backup failed: {e}")

        return backup_result

    def restore_backup(self, backup_file_path: str) -> bool:
        """Restore MySQL from backup file."""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                extract_cmd = ["tar", "-xzf", backup_file_path, "-C", temp_dir]
                success, stdout, stderr = self._execute_command(extract_cmd)

                if not success:
                    self.logger.error(f"Failed to extract backup: {stderr}")
                    return False

                sql_file = None
                for item in Path(temp_dir).iterdir():
                    if item.suffix == ".sql":
                        sql_file = item
                        break

                if not sql_file:
                    self.logger.error("No SQL file found in backup")
                    return False

                if not self._ensure_database_exists():
                    self.logger.error(f"Failed to ensure database {self.db_config.database} exists")
                    return False

                mysql_cmd = self._build_mysql_restore_command(str(sql_file))
                success, stdout, stderr = self._execute_command_with_password(mysql_cmd)

                if success:
                    self.logger.info("MySQL restore completed successfully")
                    return True

                self.logger.error(f"MySQL restore failed: {stderr}")
                return False

        except Exception as e:
            self.logger.error(f"MySQL restore failed: {e}")
            return False

    def _build_mysqldump_command(self, output_file: str) -> List[str]:
        """Build mysqldump command with appropriate parameters."""
        cmd = ["mysqldump"]

        if self.db_config.host:
            cmd.extend(["--host", self.db_config.host])
        if self.db_config.port:
            cmd.extend(["--port", str(self.db_config.port)])
        if self.db_config.username:
            cmd.extend(["--user", self.db_config.username])

        cmd.extend(["--result-file", output_file])
        cmd.extend(["--single-transaction", "--routines", "--triggers"])
        cmd.append(self.db_config.database)

        if self.db_config.additional_params:
            for key, value in self.db_config.additional_params.items():
                if isinstance(value, bool) and value:
                    cmd.append(f"--{key}")
                elif not isinstance(value, bool):
                    cmd.extend([f"--{key}", str(value)])

        return cmd

    def _build_mysql_restore_command(self, input_file: str) -> List[str]:
        """Build mysql command for restore."""
        cmd = ["mysql"]

        if self.db_config.host:
            cmd.extend(["--host", self.db_config.host])
        if self.db_config.port:
            cmd.extend(["--port", str(self.db_config.port)])
        if self.db_config.username:
            cmd.extend(["--user", self.db_config.username])

        cmd.extend([self.db_config.database, f"--execute=source {input_file}"])
        return cmd

    def _ensure_database_exists(self) -> bool:
        """Ensure target database exists, create it if missing."""
        cmd = ["mysql"]

        if self.db_config.host:
            cmd.extend(["--host", self.db_config.host])
        if self.db_config.port:
            cmd.extend(["--port", str(self.db_config.port)])
        if self.db_config.username:
            cmd.extend(["--user", self.db_config.username])

        cmd.extend(["--execute", f"CREATE DATABASE IF NOT EXISTS `{self.db_config.database}`;"])
        success, stdout, stderr = self._execute_command_with_password(cmd, timeout=30)
        return success

    def test_connection(self) -> bool:
        """Test MySQL database connection."""
        cmd = ["mysql"]

        if self.db_config.host:
            cmd.extend(["--host", self.db_config.host])
        if self.db_config.port:
            cmd.extend(["--port", str(self.db_config.port)])
        if self.db_config.username:
            cmd.extend(["--user", self.db_config.username])

        cmd.extend([self.db_config.database, "--execute", "SELECT 1;"])

        success, stdout, stderr = self._execute_command_with_password(cmd, timeout=10)
        if not success:
            self.logger.error(f"MySQL connection test failed: {stderr}")
        return success
