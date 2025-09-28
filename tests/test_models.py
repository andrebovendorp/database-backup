"""
Unit tests for models.
"""
import unittest
from datetime import datetime
from pathlib import Path

from models.database_config import (
    DatabaseType, DatabaseConfig, MongoDBConfig, PostgreSQLConfig,
    BackupConfig, FTPConfig, TelegramConfig
)
from models.backup_result import (
    BackupResult, BackupStatus, BackupSummary
)


class TestDatabaseConfig:
    """Test database configuration models."""
    
    def test_mongodb_config_creation(self):
        """Test MongoDB configuration creation."""
        config = MongoDBConfig(
            host="localhost",
            port=27017,
            database="testdb"
        )
        
        assert config.db_type == DatabaseType.MONGODB
        assert config.host == "localhost"
        assert config.port == 27017
        assert config.database == "testdb"
        assert config.username is None
        assert config.password is None
    
    def test_mongodb_config_with_auth(self):
        """Test MongoDB configuration with authentication."""
        config = MongoDBConfig(
            host="localhost",
            port=27017,
            database="testdb",
            username="user",
            password="pass"
        )
        
        assert config.username == "user"
        assert config.password == "pass"
    
    def test_mongodb_config_with_uri(self):
        """Test MongoDB configuration with URI."""
        config = MongoDBConfig(
            host="localhost",
            port=27017,
            database="testdb",
            uri="mongodb://user:pass@localhost:27017/testdb"
        )
        
        assert config.uri == "mongodb://user:pass@localhost:27017/testdb"
    
    def test_postgresql_config_creation(self):
        """Test PostgreSQL configuration creation."""
        config = PostgreSQLConfig(
            host="localhost",
            port=5432,
            database="testdb",
            username="user",
            password="pass"
        )
        
        assert config.db_type == DatabaseType.POSTGRESQL
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.database == "testdb"
        assert config.username == "user"
        assert config.password == "pass"
    
    def test_database_config_validation(self):
        """Test database configuration validation."""
        with self.assertRaises(ValueError):
            MongoDBConfig(host="", port=27017, database="testdb")
        
        with self.assertRaises(ValueError):
            MongoDBConfig(host="localhost", port=27017, database="")
        
        with self.assertRaises(ValueError):
            MongoDBConfig(host="localhost", port=0, database="testdb")
    
    def test_backup_config_creation(self):
        """Test backup configuration creation."""
        config = BackupConfig(
            backup_dir="/tmp/backups",
            retention_days=7
        )
        
        assert config.backup_dir == "/tmp/backups"
        assert config.retention_days == 7
        assert config.compression is True
        assert config.timestamp_format == "%Y-%m-%d-%H-%M-%S"
    
    def test_backup_config_validation(self):
        """Test backup configuration validation."""
        with self.assertRaises(ValueError):
            BackupConfig(backup_dir="/tmp", retention_days=0)
        
        with self.assertRaises(ValueError):
            BackupConfig(backup_dir="", retention_days=7)
    
    def test_ftp_config_creation(self):
        """Test FTP configuration creation."""
        config = FTPConfig(
            host="ftp.example.com",
            port=21,
            username="user",
            password="pass",
            remote_dir="/backup"
        )
        
        assert config.host == "ftp.example.com"
        assert config.port == 21
        assert config.username == "user"
        assert config.password == "pass"
        assert config.remote_dir == "/backup"
        assert config.ssl_enabled is False
    
    def test_ftp_config_validation(self):
        """Test FTP configuration validation."""
        with self.assertRaises(ValueError):
            FTPConfig(host="", username="user", password="pass", remote_dir="/backup")
    
    def test_telegram_config_creation(self):
        """Test Telegram configuration creation."""
        config = TelegramConfig(
            bot_token="123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
            chat_id="-1001234567890"
        )
        
        assert config.bot_token == "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
        assert config.chat_id == "-1001234567890"
        assert config.enabled is True
    
    def test_telegram_config_disabled(self):
        """Test Telegram configuration when disabled."""
        config = TelegramConfig(
            bot_token="",
            chat_id="",
            enabled=False
        )
        
        assert config.enabled is False


class TestBackupResult:
    """Test backup result models."""
    
    def test_backup_result_creation(self):
        """Test backup result creation."""
        start_time = datetime.now()
        result = BackupResult(
            backup_id="test_123",
            database_type="mongodb",
            database_name="testdb",
            status=BackupStatus.SUCCESS,
            start_time=start_time
        )
        
        assert result.backup_id == "test_123"
        assert result.database_type == "mongodb"
        assert result.database_name == "testdb"
        assert result.status == BackupStatus.SUCCESS
        assert result.start_time == start_time
        assert result.is_successful is True
    
    def test_backup_result_with_end_time(self):
        """Test backup result with end time."""
        start_time = datetime.now()
        end_time = datetime.now()
        result = BackupResult(
            backup_id="test_123",
            database_type="mongodb",
            database_name="testdb",
            status=BackupStatus.SUCCESS,
            start_time=start_time,
            end_time=end_time
        )
        
        assert result.end_time == end_time
        assert result.duration_seconds is not None
        assert result.duration_seconds >= 0
    
    def test_backup_result_failed(self):
        """Test failed backup result."""
        result = BackupResult(
            backup_id="test_123",
            database_type="mongodb",
            database_name="testdb",
            status=BackupStatus.FAILED,
            start_time=datetime.now(),
            error_message="Connection failed"
        )
        
        assert result.is_successful is False
        assert result.error_message == "Connection failed"
    
    def test_backup_result_to_dict(self):
        """Test backup result serialization."""
        start_time = datetime.now()
        result = BackupResult(
            backup_id="test_123",
            database_type="mongodb",
            database_name="testdb",
            status=BackupStatus.SUCCESS,
            start_time=start_time,
            backup_size_bytes=1024
        )
        
        data = result.to_dict()
        
        assert data['backup_id'] == "test_123"
        assert data['database_type'] == "mongodb"
        assert data['database_name'] == "testdb"
        assert data['status'] == "success"
        assert data['backup_size_bytes'] == 1024
        assert 'start_time' in data
    
    def test_backup_summary_creation(self):
        """Test backup summary creation."""
        summary = BackupSummary(
            total_backups=10,
            successful_backups=8,
            failed_backups=2,
            total_size_bytes=1024000,
            average_duration_seconds=30.5,
            last_backup_time=datetime.now()
        )
        
        assert summary.total_backups == 10
        assert summary.successful_backups == 8
        assert summary.failed_backups == 2
        assert summary.success_rate == 80.0
        assert summary.total_size_bytes == 1024000
        assert summary.average_duration_seconds == 30.5
    
    def test_backup_summary_zero_backups(self):
        """Test backup summary with zero backups."""
        summary = BackupSummary(
            total_backups=0,
            successful_backups=0,
            failed_backups=0,
            total_size_bytes=0,
            average_duration_seconds=0.0,
            last_backup_time=None
        )
        
        assert summary.success_rate == 0.0
    
    def test_backup_summary_to_dict(self):
        """Test backup summary serialization."""
        summary = BackupSummary(
            total_backups=5,
            successful_backups=4,
            failed_backups=1,
            total_size_bytes=512000,
            average_duration_seconds=25.0,
            last_backup_time=datetime.now()
        )
        
        data = summary.to_dict()
        
        assert data['total_backups'] == 5
        assert data['successful_backups'] == 4
        assert data['failed_backups'] == 1
        assert data['success_rate'] == 80.0
        assert data['total_size_bytes'] == 512000
        assert data['average_duration_seconds'] == 25.0
