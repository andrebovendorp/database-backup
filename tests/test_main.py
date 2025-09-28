"""
Unit tests for main application.
"""
import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from main import DatabaseBackupApp


class TestDatabaseBackupApp:
    """Test main application."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        os.environ['BACKUP_DIR'] = self.temp_dir
        os.environ['LOG_LEVEL'] = 'DEBUG'
    
    def teardown_method(self):
        """Cleanup test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @patch('main.BackupManager')
    @patch('main.FTPService')
    @patch('main.TelegramService')
    def test_app_initialization(self, mock_telegram, mock_ftp, mock_backup_manager):
        """Test application initialization."""
        app = DatabaseBackupApp()
        
        assert app.backup_manager is not None
        assert app.ftp_service is None  # No FTP config by default
        assert app.telegram_service is None  # No Telegram config by default
        assert app.view is not None
        assert app.report_view is not None
        assert app.logger is not None
    
    @patch('main.FTPService')
    @patch('main.TelegramService')
    def test_app_initialization_with_services(self, mock_telegram, mock_ftp):
        """Test application initialization with services."""
        os.environ['FTP_HOST'] = 'ftp.example.com'
        os.environ['FTP_USERNAME'] = 'user'
        os.environ['FTP_PASSWORD'] = 'pass'
        os.environ['FTP_REMOTE_DIR'] = '/backup'
        os.environ['TELEGRAM_BOT_TOKEN'] = '123456789:ABCdefGHIjklMNOpqrsTUVwxyz'
        os.environ['TELEGRAM_CHAT_ID'] = '-1001234567890'
        
        app = DatabaseBackupApp()
        
        assert app.ftp_service is not None
        assert app.telegram_service is not None
    
    def test_add_mongodb_database(self):
        """Test adding MongoDB database."""
        app = DatabaseBackupApp()
        
        controller_id = app.add_mongodb_database(
            host="localhost",
            port=27017,
            database="testdb",
            uri="mongodb://localhost:27017/testdb"
        )
        
        assert controller_id == "mongodb_testdb"
        assert controller_id in app.backup_manager.controllers
    
    def test_add_postgresql_database(self):
        """Test adding PostgreSQL database."""
        app = DatabaseBackupApp()
        
        controller_id = app.add_postgresql_database(
            host="localhost",
            port=5432,
            database="testdb",
            username="user",
            password="pass"
        )
        
        assert controller_id == "postgresql_testdb"
        assert controller_id in app.backup_manager.controllers
    
    @patch('main.BackupManager.backup_database')
    @patch('main.FTPService')
    @patch('main.TelegramService')
    def test_backup_database_success(self, mock_telegram, mock_ftp, mock_backup):
        """Test successful database backup."""
        # Setup mocks
        mock_result = Mock()
        mock_result.is_successful = True
        mock_result.backup_file_path = "/tmp/backup.tar.gz"
        mock_backup.return_value = mock_result
        
        app = DatabaseBackupApp()
        app.ftp_service = Mock()
        app.telegram_service = Mock()
        
        # Add a database
        controller_id = app.add_mongodb_database("localhost", 27017, "testdb")
        
        # Mock the backup manager
        app.backup_manager.backup_database = mock_backup
        
        result = app.backup_database(controller_id)
        
        assert result is True
        mock_backup.assert_called_once_with(controller_id)
        app.telegram_service.notify_backup_started.assert_called_once()
        app.telegram_service.notify_backup_completed.assert_called_once()
    
    @patch('main.BackupManager.backup_database')
    @patch('main.TelegramService')
    def test_backup_database_failure(self, mock_telegram, mock_backup):
        """Test failed database backup."""
        # Setup mocks
        mock_result = Mock()
        mock_result.is_successful = False
        mock_result.error_message = "Connection failed"
        mock_backup.return_value = mock_result
        
        app = DatabaseBackupApp()
        app.telegram_service = Mock()
        
        # Add a database
        controller_id = app.add_mongodb_database("localhost", 27017, "testdb")
        
        # Mock the backup manager
        app.backup_manager.backup_database = mock_backup
        
        result = app.backup_database(controller_id)
        
        assert result is False
        app.telegram_service.notify_backup_completed.assert_called_once()
    
    @patch('main.BackupManager.backup_all_databases')
    @patch('main.TelegramService')
    def test_backup_all_databases(self, mock_telegram, mock_backup_all):
        """Test backing up all databases."""
        # Setup mocks
        mock_results = [Mock(), Mock()]
        mock_backup_all.return_value = mock_results
        
        app = DatabaseBackupApp()
        app.telegram_service = Mock()
        
        # Add some databases
        app.add_mongodb_database("localhost", 27017, "testdb1")
        app.add_postgresql_database("localhost", 5432, "testdb2", "user", "pass")
        
        # Mock the backup manager
        app.backup_manager.backup_all_databases = mock_backup_all
        
        results = app.backup_all_databases()
        
        assert results == mock_results
        mock_backup_all.assert_called_once()
        app.telegram_service.notify_backup_summary.assert_called_once()
    
    @patch('main.FTPService')
    def test_upload_to_ftp_success(self, mock_ftp_class):
        """Test successful FTP upload."""
        mock_ftp = Mock()
        mock_ftp_class.return_value = mock_ftp
        mock_ftp.__enter__ = Mock(return_value=mock_ftp)
        mock_ftp.__exit__ = Mock(return_value=None)
        mock_ftp.upload_file.return_value = True
        
        app = DatabaseBackupApp()
        app.ftp_service = mock_ftp
        
        result = app.upload_to_ftp("/tmp/backup.tar.gz")
        
        assert result is True
        mock_ftp.upload_file.assert_called_once_with("/tmp/backup.tar.gz")
    
    @patch('main.FTPService')
    def test_upload_to_ftp_failure(self, mock_ftp_class):
        """Test failed FTP upload."""
        mock_ftp = Mock()
        mock_ftp_class.return_value = mock_ftp
        mock_ftp.__enter__ = Mock(return_value=mock_ftp)
        mock_ftp.__exit__ = Mock(return_value=None)
        mock_ftp.upload_file.return_value = False
        
        app = DatabaseBackupApp()
        app.ftp_service = mock_ftp
        
        result = app.upload_to_ftp("/tmp/backup.tar.gz")
        
        assert result is False
    
    def test_upload_to_ftp_no_ftp_service(self):
        """Test FTP upload without FTP service."""
        app = DatabaseBackupApp()
        
        result = app.upload_to_ftp("/tmp/backup.tar.gz")
        
        assert result is False
    
    @patch('main.BackupManager.cleanup_all_backups')
    def test_cleanup_old_backups(self, mock_cleanup):
        """Test cleanup of old backups."""
        mock_cleanup.return_value = {"mongodb_testdb": ["old1.tar.gz", "old2.tar.gz"]}
        
        app = DatabaseBackupApp()
        app.backup_manager.cleanup_all_backups = mock_cleanup
        
        app.cleanup_old_backups()
        
        mock_cleanup.assert_called_once()
    
    @patch('main.BackupManager.list_backup_files')
    def test_list_backup_files(self, mock_list_files):
        """Test listing backup files."""
        mock_files = [
            {'filename': 'backup1.tar.gz', 'size_bytes': 1024},
            {'filename': 'backup2.tar.gz', 'size_bytes': 2048}
        ]
        mock_list_files.return_value = mock_files
        
        app = DatabaseBackupApp()
        app.backup_manager.list_backup_files = mock_list_files
        
        app.list_backup_files("mongodb_testdb")
        
        mock_list_files.assert_called_once_with("mongodb_testdb")
    
    @patch('main.BackupManager.get_backup_summary')
    @patch('main.BackupManager.backup_history')
    def test_generate_report(self, mock_history, mock_summary):
        """Test report generation."""
        mock_summary.return_value = Mock()
        mock_history = [Mock(), Mock()]
        
        app = DatabaseBackupApp()
        app.backup_manager.get_backup_summary = mock_summary
        app.backup_manager.backup_history = mock_history
        
        with patch('builtins.print') as mock_print:
            app.generate_report()
            
            mock_summary.assert_called_once()
            mock_print.assert_called()
    
    @patch('main.FTPService')
    @patch('main.TelegramService')
    def test_test_connections(self, mock_telegram, mock_ftp):
        """Test connection testing."""
        mock_ftp_instance = Mock()
        mock_ftp.return_value = mock_ftp_instance
        mock_ftp_instance.__enter__ = Mock(return_value=mock_ftp_instance)
        mock_ftp_instance.__exit__ = Mock(return_value=None)
        
        mock_telegram_instance = Mock()
        mock_telegram.return_value = mock_telegram_instance
        mock_telegram_instance.test_connection.return_value = True
        
        os.environ['FTP_HOST'] = 'ftp.example.com'
        os.environ['FTP_USERNAME'] = 'user'
        os.environ['FTP_PASSWORD'] = 'pass'
        os.environ['FTP_REMOTE_DIR'] = '/backup'
        os.environ['TELEGRAM_BOT_TOKEN'] = '123456789:ABCdefGHIjklMNOpqrsTUVwxyz'
        os.environ['TELEGRAM_CHAT_ID'] = '-1001234567890'
        
        app = DatabaseBackupApp()
        
        with patch('builtins.print') as mock_print:
            app.test_connections()
            
            mock_print.assert_called()
            mock_telegram_instance.test_connection.assert_called_once()

