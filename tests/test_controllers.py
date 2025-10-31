"""
Unit tests for controllers.
"""
import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from pathlib import Path

from models.database_config import MongoDBConfig, PostgreSQLConfig, BackupConfig
from controllers.mongodb_controller import MongoDBBackupController
from controllers.postgresql_controller import PostgreSQLBackupController
from controllers.backup_manager import BackupManager


class TestMongoDBController:
    """Test MongoDB backup controller."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.db_config = MongoDBConfig(
            host="localhost",
            port=27017,
            database="testdb"
        )
        self.backup_config = BackupConfig(
            backup_dir=tempfile.mkdtemp(),
            retention_days=7
        )
        self.controller = MongoDBBackupController(self.db_config, self.backup_config)
    
    def teardown_method(self):
        """Cleanup test fixtures."""
        # Clean up temporary directory
        import shutil
        if os.path.exists(self.backup_config.backup_dir):
            shutil.rmtree(self.backup_config.backup_dir)
    
    def test_controller_initialization(self):
        """Test controller initialization."""
        assert self.controller.db_config == self.db_config
        assert self.controller.backup_config == self.backup_config
        assert self.controller.logger is not None
    
    @patch('controllers.mongodb_controller.subprocess.run')
    def test_create_backup_success(self, mock_run):
        """Test successful backup creation."""
        # Mock successful mongodump
        mock_run.return_value = Mock(returncode=0, stdout="Success", stderr="")
        
        result = self.controller.create_backup()
        
        assert result.status.value == "success"
        assert result.database_type == "mongodb"
        assert result.database_name == "testdb"
        assert result.is_successful is True
    
    @patch('controllers.mongodb_controller.subprocess.run')
    def test_create_backup_failure(self, mock_run):
        """Test backup creation failure."""
        # Mock failed mongodump
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="Connection failed")
        
        result = self.controller.create_backup()
        
        assert result.status.value == "failed"
        assert result.is_successful is False
        assert "Connection failed" in result.error_message
    
    def test_generate_backup_filename(self):
        """Test backup filename generation."""
        filename = self.controller._generate_backup_filename()
        
        assert filename.startswith("backup_testdb_")
        assert filename.endswith(".tar.gz")
        assert "testdb" in filename
    
    def test_get_backup_file_path(self):
        """Test backup file path generation."""
        filename = "test_backup.tar.gz"
        path = self.controller._get_backup_file_path(filename)
        
        expected_path = Path(self.backup_config.backup_dir) / filename
        assert path == str(expected_path)
    
    def test_build_mongodump_command(self):
        """Test mongodump command building."""
        output_dir = "/tmp/dump"
        cmd = self.controller._build_mongodump_command(output_dir)
        
        assert "mongodump" in cmd
        assert "--out" in cmd
        assert output_dir in cmd
        assert "--host" in cmd
        assert "localhost:27017" in cmd
        assert "--db" in cmd
        assert "testdb" in cmd
    
    def test_build_mongodump_command_with_uri(self):
        """Test mongodump command with URI."""
        self.db_config.uri = "mongodb://localhost:27017/testdb"
        output_dir = "/tmp/dump"
        cmd = self.controller._build_mongodump_command(output_dir)
        
        assert "--uri" in cmd
        assert "mongodb://localhost:27017/testdb" in cmd
    
    def test_build_mongorestore_command(self):
        """Test mongorestore command building."""
        input_dir = "/tmp/dump"
        cmd = self.controller._build_mongorestore_command(input_dir)
        
        assert "mongorestore" in cmd
        assert input_dir in cmd
        assert "--host" in cmd
        assert "localhost:27017" in cmd


class TestPostgreSQLController:
    """Test PostgreSQL backup controller."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.db_config = PostgreSQLConfig(
            host="localhost",
            port=5432,
            database="testdb",
            username="user",
            password="pass"
        )
        self.backup_config = BackupConfig(
            backup_dir=tempfile.mkdtemp(),
            retention_days=7
        )
        self.controller = PostgreSQLBackupController(self.db_config, self.backup_config)
    
    def teardown_method(self):
        """Cleanup test fixtures."""
        # Clean up temporary directory
        import shutil
        if os.path.exists(self.backup_config.backup_dir):
            shutil.rmtree(self.backup_config.backup_dir)
    
    def test_controller_initialization(self):
        """Test controller initialization."""
        assert self.controller.db_config == self.db_config
        assert self.controller.backup_config == self.backup_config
        assert self.controller.logger is not None
    
    @patch('controllers.postgresql_controller.subprocess.run')
    def test_create_backup_success(self, mock_run):
        """Test successful backup creation."""
        # Mock successful pg_dump
        mock_run.return_value = Mock(returncode=0, stdout="Success", stderr="")
        
        result = self.controller.create_backup()
        
        assert result.status.value == "success"
        assert result.database_type == "postgresql"
        assert result.database_name == "testdb"
        assert result.is_successful is True
    
    @patch('controllers.postgresql_controller.subprocess.run')
    def test_create_backup_failure(self, mock_run):
        """Test backup creation failure."""
        # Mock failed pg_dump
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="Connection failed")
        
        result = self.controller.create_backup()
        
        assert result.status.value == "failed"
        assert result.is_successful is False
        assert "Connection failed" in result.error_message
    
    def test_build_pg_dump_command(self):
        """Test pg_dump command building."""
        output_file = "/tmp/backup.sql"
        cmd = self.controller._build_pg_dump_command(output_file)
        
        assert "pg_dumpall" in cmd
        assert "--file" in cmd
        assert output_file in cmd
        assert "--host" in cmd
        assert "localhost" in cmd
        assert "--port" in cmd
        assert "5432" in cmd
        assert "--username" in cmd
        assert "user" in cmd
        assert "--dbname" in cmd
        assert "testdb" in cmd
    
    def test_build_psql_command(self):
        """Test psql command building."""
        input_file = "/tmp/backup.sql"
        cmd = self.controller._build_psql_command(input_file)
        
        assert "psql" in cmd
        assert "--file" in cmd
        assert input_file in cmd
        assert "--host" in cmd
        assert "localhost" in cmd


class TestBackupManager:
    """Test backup manager."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.backup_config = BackupConfig(
            backup_dir=tempfile.mkdtemp(),
            retention_days=7
        )
        self.manager = BackupManager(self.backup_config)
    
    def teardown_method(self):
        """Cleanup test fixtures."""
        # Clean up temporary directory
        import shutil
        if os.path.exists(self.backup_config.backup_dir):
            shutil.rmtree(self.backup_config.backup_dir)
    
    def test_manager_initialization(self):
        """Test manager initialization."""
        assert self.manager.backup_config == self.backup_config
        assert self.manager.controllers == {}
        assert self.manager.backup_history == []
    
    def test_add_mongodb_database(self):
        """Test adding MongoDB database."""
        db_config = MongoDBConfig(
            host="localhost",
            port=27017,
            database="testdb"
        )
        
        controller_id = self.manager.add_database(db_config)
        
        assert controller_id == "mongodb_testdb"
        assert controller_id in self.manager.controllers
        assert isinstance(self.manager.controllers[controller_id], MongoDBBackupController)
    
    def test_add_postgresql_database(self):
        """Test adding PostgreSQL database."""
        db_config = PostgreSQLConfig(
            host="localhost",
            port=5432,
            database="testdb",
            username="user",
            password="pass"
        )
        
        controller_id = self.manager.add_database(db_config)
        
        assert controller_id == "postgresql_testdb"
        assert controller_id in self.manager.controllers
        assert isinstance(self.manager.controllers[controller_id], PostgreSQLBackupController)
    
    def test_add_unsupported_database(self):
        """Test adding unsupported database type."""
        # Create a mock database config with unsupported type
        db_config = Mock()
        db_config.db_type.value = "unsupported"
        
        with pytest.raises(ValueError, match="Unsupported database type"):
            self.manager.add_database(db_config)
    
    def test_backup_database_not_found(self):
        """Test backing up non-existent database."""
        with pytest.raises(ValueError, match="Controller not found"):
            self.manager.backup_database("nonexistent")
    
    @patch('controllers.backup_manager.MongoDBBackupController.create_backup')
    def test_backup_database_success(self, mock_create_backup):
        """Test successful database backup."""
        # Add a database
        db_config = MongoDBConfig(host="localhost", port=27017, database="testdb")
        controller_id = self.manager.add_database(db_config)
        
        # Mock successful backup
        mock_result = Mock()
        mock_result.is_successful = True
        mock_result.backup_size_bytes = 1024
        mock_create_backup.return_value = mock_result
        
        result = self.manager.backup_database(controller_id)
        
        assert result.is_successful is True
        assert len(self.manager.backup_history) == 1
        assert self.manager.backup_history[0] == mock_result
    
    def test_get_backup_summary_empty(self):
        """Test backup summary with no backups."""
        summary = self.manager.get_backup_summary()
        
        assert summary.total_backups == 0
        assert summary.successful_backups == 0
        assert summary.failed_backups == 0
        assert summary.success_rate == 0.0
        assert summary.last_backup_time is None
    
    def test_get_backup_summary_with_backups(self):
        """Test backup summary with backups."""
        # Add mock backup results
        mock_result1 = Mock()
        mock_result1.is_successful = True
        mock_result1.backup_size_bytes = 1024
        mock_result1.duration_seconds = 10.0
        mock_result1.start_time = datetime.now()
        
        mock_result2 = Mock()
        mock_result2.is_successful = False
        mock_result2.backup_size_bytes = 0
        mock_result2.duration_seconds = 5.0
        mock_result2.start_time = datetime.now()
        
        self.manager.backup_history = [mock_result1, mock_result2]
        
        summary = self.manager.get_backup_summary()
        
        assert summary.total_backups == 2
        assert summary.successful_backups == 1
        assert summary.failed_backups == 1
        assert summary.success_rate == 50.0
        assert summary.total_size_bytes == 1024
        assert summary.average_duration_seconds == 7.5
    
    def test_list_backup_files(self):
        """Test listing backup files."""
        # Create some test files
        backup_dir = Path(self.backup_config.backup_dir)
        backup_dir.mkdir(exist_ok=True)
        
        test_file1 = backup_dir / "backup_test1.tar.gz"
        test_file1.touch()
        
        test_file2 = backup_dir / "backup_test2.tar.gz"
        test_file2.touch()
        
        files = self.manager.list_backup_files()
        
        assert len(files) == 2
        assert any(f['filename'] == "backup_test1.tar.gz" for f in files)
        assert any(f['filename'] == "backup_test2.tar.gz" for f in files)
    
    def test_cleanup_all_backups(self):
        """Test cleanup of all backups."""
        # Add a controller
        db_config = MongoDBConfig(host="localhost", port=27017, database="testdb")
        controller_id = self.manager.add_database(db_config)
        
        # Mock cleanup method
        with patch.object(self.manager.controllers[controller_id], 'cleanup_old_backups') as mock_cleanup:
            mock_cleanup.return_value = ["old_file1.tar.gz", "old_file2.tar.gz"]
            
            results = self.manager.cleanup_all_backups()
            
            assert controller_id in results
            assert len(results[controller_id]) == 2
            mock_cleanup.assert_called_once()

