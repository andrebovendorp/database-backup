"""
PostgreSQL backup controller implementation.
"""
import os
import tempfile
import stat
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .base_controller import BaseBackupController
from models.database_config import PostgreSQLConfig
from models.backup_result import BackupResult, BackupStatus


class PostgreSQLBackupController(BaseBackupController):
    """PostgreSQL specific backup controller."""
    
    def __init__(self, db_config: PostgreSQLConfig, backup_config):
        """Initialize PostgreSQL backup controller."""
        super().__init__(db_config, backup_config)
        self.db_config: PostgreSQLConfig = db_config
        self._pgpass_file: Optional[str] = None
    
    def _create_pgpass_file(self) -> Optional[str]:
        """Create a temporary .pgpass file for authentication."""
        if not self.db_config.password:
            self.logger.warning("No password configured, skipping .pgpass file creation")
            return None
        
        try:
            # Create temporary file for .pgpass
            fd, pgpass_path = tempfile.mkstemp(prefix='pgpass_', suffix='.tmp')
            
            # Format: hostname:port:database:username:password
            # Use '*' for wildcards where appropriate
            host = self.db_config.host or 'localhost'
            port = self.db_config.port or 5432
            database = self.db_config.database or '*'
            username = self.db_config.username or '*'
            password = self.db_config.password
            
            pgpass_line = f"{host}:{port}:{database}:{username}:{password}\n"
            
            # Write to the file
            with os.fdopen(fd, 'w') as f:
                f.write(pgpass_line)
            
            # Set proper permissions (600 - owner read/write only)
            os.chmod(pgpass_path, stat.S_IRUSR | stat.S_IWUSR)
            
            self.logger.info(f"Created .pgpass file: {pgpass_path} for {username}@{host}:{port}/{database}")
            self._pgpass_file = pgpass_path
            return pgpass_path
            
        except Exception as e:
            self.logger.error(f"Failed to create .pgpass file: {e}")
            return None
    
    def _cleanup_pgpass_file(self):
        """Remove the temporary .pgpass file."""
        if self._pgpass_file and os.path.exists(self._pgpass_file):
            try:
                os.unlink(self._pgpass_file)
                self.logger.debug(f"Removed .pgpass file: {self._pgpass_file}")
                self._pgpass_file = None
            except Exception as e:
                self.logger.warning(f"Failed to remove .pgpass file {self._pgpass_file}: {e}")
    
    def _execute_command_with_pgpass(self, command: List[str], pgpass_path: Optional[str], timeout: int = 300) -> tuple:
        """Execute PostgreSQL command with .pgpass file environment."""
        import subprocess
        
        try:
            # Prepare environment with PGPASSFILE and other PG environment variables
            env = os.environ.copy()
            if pgpass_path and os.path.exists(pgpass_path):
                env['PGPASSFILE'] = pgpass_path
                self.logger.info(f"Using .pgpass file: {pgpass_path}")
            else:
                self.logger.warning("No .pgpass file available, command may prompt for password")
            
            # Set additional PostgreSQL environment variables for authentication
            if self.db_config.host:
                env['PGHOST'] = self.db_config.host
            if self.db_config.port:
                env['PGPORT'] = str(self.db_config.port)
            if self.db_config.username:
                env['PGUSER'] = self.db_config.username
            if self.db_config.database:
                env['PGDATABASE'] = self.db_config.database
            
            # CRITICAL: Also set PGPASSWORD as a fallback (more reliable than .pgpass)
            if self.db_config.password:
                env['PGPASSWORD'] = self.db_config.password
                self.logger.info("Set PGPASSWORD environment variable for authentication")
            
            self.logger.debug(f"Executing command with .pgpass: {' '.join(command)}")
            self.logger.debug(f"PGPASSFILE env var: {env.get('PGPASSFILE', 'NOT SET')}")
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                env=env
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
        
        # Create .pgpass file for authentication
        pgpass_path = self._create_pgpass_file()
        
        try:
            # Create temporary file for dump
            with tempfile.NamedTemporaryFile(mode='w+b', suffix='.sql', delete=False) as temp_file:
                temp_file_path = temp_file.name
                
                # Build pg_dump command
                pg_dump_cmd = self._build_pg_dump_command(temp_file_path)
                
                # Execute pg_dump with .pgpass file
                success, stdout, stderr = self._execute_command_with_pgpass(pg_dump_cmd, pgpass_path)
                
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
        finally:
            # Always cleanup .pgpass file
            self._cleanup_pgpass_file()
        
        return backup_result
    
    def restore_backup(self, backup_file_path: str) -> bool:
        """Restore PostgreSQL from backup file."""
        # Create .pgpass file for authentication
        pgpass_path = self._create_pgpass_file()
        
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
                
                # Check if target database exists, create if it doesn't
                if not self._ensure_database_exists(pgpass_path):
                    self.logger.error(f"Failed to ensure database {self.db_config.database} exists")
                    return False
                
                # Build psql command
                psql_cmd = self._build_psql_command(str(sql_file))
                
                # Execute psql with .pgpass file
                success, stdout, stderr = self._execute_command_with_pgpass(psql_cmd, pgpass_path)
                
                if success:
                    self.logger.info("PostgreSQL restore completed successfully")
                    return True
                else:
                    self.logger.error(f"PostgreSQL restore failed: {stderr}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"PostgreSQL restore failed: {e}")
            return False
        finally:
            # Always cleanup .pgpass file
            self._cleanup_pgpass_file()
    
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
        cmd.extend(["--no-privileges", "--no-owner"])
        
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
        
        # Add options (removed --verbose as it's not supported in all psql versions)
        cmd.extend(["--quiet"])
        
        return cmd
    
    def _ensure_database_exists(self, pgpass_path: Optional[str]) -> bool:
        """Ensure the target database exists, create if it doesn't."""
        try:
            # First, check if database exists by connecting to postgres database
            original_db = self.db_config.database
            self.db_config.database = 'postgres'  # Connect to default postgres db
            
            # Build command to check if database exists
            check_cmd = ["psql"]
            
            if self.db_config.host:
                check_cmd.extend(["--host", self.db_config.host])
            if self.db_config.port:
                check_cmd.extend(["--port", str(self.db_config.port)])
            if self.db_config.username:
                check_cmd.extend(["--username", self.db_config.username])
            
            check_cmd.extend(["--dbname", "postgres"])
            check_cmd.extend(["--command", f"SELECT 1 FROM pg_database WHERE datname='{original_db}';"])
            
            # Check if database exists
            success, stdout, stderr = self._execute_command_with_pgpass(check_cmd, pgpass_path, timeout=10)
            
            if success and "1" in stdout:
                self.logger.info(f"Database {original_db} already exists")
                self.db_config.database = original_db  # Restore original database name
                return True
            
            # Database doesn't exist, create it
            self.logger.info(f"Creating database: {original_db}")
            create_cmd = ["psql"]
            
            if self.db_config.host:
                create_cmd.extend(["--host", self.db_config.host])
            if self.db_config.port:
                create_cmd.extend(["--port", str(self.db_config.port)])
            if self.db_config.username:
                create_cmd.extend(["--username", self.db_config.username])
            
            create_cmd.extend(["--dbname", "postgres"])
            create_cmd.extend(["--command", f"CREATE DATABASE \"{original_db}\";"])
            
            success, stdout, stderr = self._execute_command_with_pgpass(create_cmd, pgpass_path, timeout=30)
            
            # Restore original database name
            self.db_config.database = original_db
            
            if success:
                self.logger.info(f"Database {original_db} created successfully")
                return True
            else:
                self.logger.error(f"Failed to create database {original_db}: {stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error ensuring database exists: {e}")
            # Make sure to restore original database name even on error
            self.db_config.database = original_db if 'original_db' in locals() else self.db_config.database
            return False
    
    def test_connection(self) -> bool:
        """Test PostgreSQL database connection."""
        # Create .pgpass file for authentication
        pgpass_path = self._create_pgpass_file()
        
        try:
            # Build a simple connection test command using psql
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
            
            # Add simple query to test connection
            cmd.extend(["--command", "SELECT 1;"])
            
            # Execute the test command with .pgpass file
            success, stdout, stderr = self._execute_command_with_pgpass(cmd, pgpass_path, timeout=10)
            
            if success:
                self.logger.info(f"PostgreSQL connection test successful for database: {self.db_config.database}")
                return True
            else:
                self.logger.error(f"PostgreSQL connection test failed: {stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"PostgreSQL connection test failed with exception: {e}")
            return False
        finally:
            # Always cleanup .pgpass file
            self._cleanup_pgpass_file()
