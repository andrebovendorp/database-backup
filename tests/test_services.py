"""
Unit tests for services.
"""
import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from models.database_config import FTPConfig, TelegramConfig
from services.ftp_service import FTPService
from services.telegram_service import TelegramService


class TestFTPService:
    """Test FTP service."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.ftp_config = FTPConfig(
            host="ftp.example.com",
            port=21,
            username="testuser",
            password="testpass",
            remote_dir="/backup"
        )
        self.ftp_service = FTPService(self.ftp_config)
    
    def test_ftp_service_initialization(self):
        """Test FTP service initialization."""
        assert self.ftp_service.ftp_config == self.ftp_config
        assert self.ftp_service._connection is None
        assert self.ftp_service.logger is not None
    
    @patch('services.ftp_service.FTP')
    def test_connect_success(self, mock_ftp_class):
        """Test successful FTP connection."""
        mock_ftp = Mock()
        mock_ftp_class.return_value = mock_ftp
        
        result = self.ftp_service.connect()
        
        assert result is True
        assert self.ftp_service._connection == mock_ftp
        mock_ftp.connect.assert_called_once_with("ftp.example.com", 21)
        mock_ftp.login.assert_called_once_with("testuser", "testpass")
        mock_ftp.cwd.assert_called_once_with("/backup")
    
    @patch('services.ftp_service.FTP')
    def test_connect_failure(self, mock_ftp_class):
        """Test FTP connection failure."""
        mock_ftp = Mock()
        mock_ftp.connect.side_effect = Exception("Connection failed")
        mock_ftp_class.return_value = mock_ftp
        
        result = self.ftp_service.connect()
        
        assert result is False
        assert self.ftp_service._connection is None
    
    @patch('services.ftp_service.FTP_TLS')
    def test_connect_ssl_success(self, mock_ftp_tls_class):
        """Test successful SSL FTP connection."""
        self.ftp_config.ssl_enabled = True
        self.ftp_service = FTPService(self.ftp_config)
        
        mock_ftp = Mock()
        mock_ftp_tls_class.return_value = mock_ftp
        
        result = self.ftp_service.connect()
        
        assert result is True
        assert self.ftp_service._connection == mock_ftp
        mock_ftp.prot_p.assert_called_once()
    
    def test_disconnect_no_connection(self):
        """Test disconnect with no connection."""
        self.ftp_service.disconnect()
        # Should not raise any exceptions
    
    @patch('services.ftp_service.FTP')
    def test_disconnect_success(self, mock_ftp_class):
        """Test successful disconnect."""
        mock_ftp = Mock()
        mock_ftp_class.return_value = mock_ftp
        self.ftp_service.connect()
        
        self.ftp_service.disconnect()
        
        mock_ftp.quit.assert_called_once()
        assert self.ftp_service._connection is None
    
    @patch('services.ftp_service.FTP')
    def test_upload_file_success(self, mock_ftp_class):
        """Test successful file upload."""
        mock_ftp = Mock()
        mock_ftp_class.return_value = mock_ftp
        self.ftp_service.connect()
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b"test content")
            temp_file_path = temp_file.name
        
        try:
            result = self.ftp_service.upload_file(temp_file_path, "remote_file.tar.gz")
            
            assert result is True
            mock_ftp.storbinary.assert_called_once()
        finally:
            os.unlink(temp_file_path)
    
    @patch('services.ftp_service.FTP')
    def test_upload_file_not_connected(self, mock_ftp_class):
        """Test file upload without connection."""
        result = self.ftp_service.upload_file("/tmp/test.txt")
        
        assert result is False
    
    @patch('services.ftp_service.FTP')
    def test_upload_file_nonexistent(self, mock_ftp_class):
        """Test file upload with nonexistent file."""
        mock_ftp = Mock()
        mock_ftp_class.return_value = mock_ftp
        self.ftp_service.connect()
        
        result = self.ftp_service.upload_file("/nonexistent/file.txt")
        
        assert result is False
    
    @patch('services.ftp_service.FTP')
    def test_download_file_success(self, mock_ftp_class):
        """Test successful file download."""
        mock_ftp = Mock()
        mock_ftp_class.return_value = mock_ftp
        self.ftp_service.connect()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            local_path = os.path.join(temp_dir, "downloaded.txt")
            result = self.ftp_service.download_file("remote_file.txt", local_path)
            
            assert result is True
            mock_ftp.retrbinary.assert_called_once()
    
    @patch('services.ftp_service.FTP')
    def test_list_files_success(self, mock_ftp_class):
        """Test successful file listing."""
        mock_ftp = Mock()
        mock_ftp_class.return_value = mock_ftp
        self.ftp_service.connect()
        
        # Mock LIST response
        mock_ftp.retrlines.side_effect = lambda cmd, callback: [
            callback("drwxr-xr-x 2 user group 4096 Jan 1 12:00 backup1.tar.gz"),
            callback("drwxr-xr-x 2 user group 4096 Jan 1 12:00 backup2.tar.gz")
        ]
        
        files = self.ftp_service.list_files()
        
        assert len(files) == 2
        assert "backup1.tar.gz" in files
        assert "backup2.tar.gz" in files
    
    @patch('services.ftp_service.FTP')
    def test_delete_file_success(self, mock_ftp_class):
        """Test successful file deletion."""
        mock_ftp = Mock()
        mock_ftp_class.return_value = mock_ftp
        self.ftp_service.connect()
        
        result = self.ftp_service.delete_file("remote_file.txt")
        
        assert result is True
        mock_ftp.delete.assert_called_once_with("remote_file.txt")
    
    def test_context_manager(self):
        """Test FTP service as context manager."""
        with patch.object(self.ftp_service, 'connect') as mock_connect, \
             patch.object(self.ftp_service, 'disconnect') as mock_disconnect:
            
            mock_connect.return_value = True
            
            with self.ftp_service:
                pass
            
            mock_connect.assert_called_once()
            mock_disconnect.assert_called_once()


class TestTelegramService:
    """Test Telegram service."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.telegram_config = TelegramConfig(
            bot_token="123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
            chat_id="-1001234567890"
        )
        self.telegram_service = TelegramService(self.telegram_config)
    
    def test_telegram_service_initialization(self):
        """Test Telegram service initialization."""
        assert self.telegram_service.telegram_config == self.telegram_config
        assert self.telegram_service.base_url == f"https://api.telegram.org/bot{self.telegram_config.bot_token}"
        assert self.telegram_service.logger is not None
    
    @patch('services.telegram_service.requests.post')
    def test_send_message_success(self, mock_post):
        """Test successful message sending."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = self.telegram_service.send_message("Test message")
        
        assert result is True
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]['data']['chat_id'] == "-1001234567890"
        assert call_args[1]['data']['text'] == "Test message"
    
    @patch('services.telegram_service.requests.post')
    def test_send_message_failure(self, mock_post):
        """Test message sending failure."""
        mock_post.side_effect = Exception("Network error")
        
        result = self.telegram_service.send_message("Test message")
        
        assert result is False
    
    def test_send_message_disabled(self):
        """Test message sending when disabled."""
        self.telegram_config.enabled = False
        telegram_service = TelegramService(self.telegram_config)
        
        result = telegram_service.send_message("Test message")
        
        assert result is True  # Should return True when disabled
    
    @patch('services.telegram_service.requests.post')
    def test_notify_backup_started(self, mock_post):
        """Test backup started notification."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = self.telegram_service.notify_backup_started("testdb", "mongodb")
        
        assert result is True
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "Backup Started" in call_args[1]['data']['text']
        assert "testdb" in call_args[1]['data']['text']
        assert "mongodb" in call_args[1]['data']['text']
    
    @patch('services.telegram_service.requests.post')
    def test_notify_backup_completed_success(self, mock_post):
        """Test successful backup completion notification."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        from models.backup_result import BackupResult, BackupStatus
        from datetime import datetime
        
        backup_result = BackupResult(
            backup_id="test_123",
            database_type="mongodb",
            database_name="testdb",
            status=BackupStatus.SUCCESS,
            start_time=datetime.now(),
            end_time=datetime.now(),
            backup_size_bytes=1024
        )
        
        result = self.telegram_service.notify_backup_completed(backup_result)
        
        assert result is True
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "Backup Completed - Success" in call_args[1]['data']['text']
        assert "testdb" in call_args[1]['data']['text']
    
    @patch('services.telegram_service.requests.post')
    def test_notify_backup_completed_failure(self, mock_post):
        """Test failed backup completion notification."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        from models.backup_result import BackupResult, BackupStatus
        from datetime import datetime
        
        backup_result = BackupResult(
            backup_id="test_123",
            database_type="mongodb",
            database_name="testdb",
            status=BackupStatus.FAILED,
            start_time=datetime.now(),
            end_time=datetime.now(),
            error_message="Connection failed"
        )
        
        result = self.telegram_service.notify_backup_completed(backup_result)
        
        assert result is True
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "Backup Completed - Failed" in call_args[1]['data']['text']
        assert "Connection failed" in call_args[1]['data']['text']
    
    @patch('services.telegram_service.requests.post')
    def test_notify_backup_summary(self, mock_post):
        """Test backup summary notification."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        from models.backup_result import BackupSummary
        from datetime import datetime
        
        summary = BackupSummary(
            total_backups=10,
            successful_backups=8,
            failed_backups=2,
            total_size_bytes=1024000,
            average_duration_seconds=30.5,
            last_backup_time=datetime.now()
        )
        
        result = self.telegram_service.notify_backup_summary(summary)
        
        assert result is True
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "Backup Summary" in call_args[1]['data']['text']
        assert "Total Backups: 10" in call_args[1]['data']['text']
        assert "Success Rate: 80.0%" in call_args[1]['data']['text']
    
    @patch('services.telegram_service.requests.post')
    def test_notify_ftp_upload(self, mock_post):
        """Test FTP upload notification."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = self.telegram_service.notify_ftp_upload("backup.tar.gz", True)
        
        assert result is True
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "FTP Upload - Uploaded" in call_args[1]['data']['text']
        assert "backup.tar.gz" in call_args[1]['data']['text']
    
    @patch('services.telegram_service.requests.post')
    def test_notify_cleanup(self, mock_post):
        """Test cleanup notification."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = self.telegram_service.notify_cleanup(5, 1024.5)
        
        assert result is True
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "Cleanup Completed" in call_args[1]['data']['text']
        assert "Deleted Files: 5" in call_args[1]['data']['text']
        assert "Space Freed: 1024.50 MB" in call_args[1]['data']['text']
    
    @patch('services.telegram_service.requests.post')
    def test_notify_error(self, mock_post):
        """Test error notification."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = self.telegram_service.notify_error("Database connection failed", "Backup operation")
        
        assert result is True
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "Backup Error" in call_args[1]['data']['text']
        assert "Database connection failed" in call_args[1]['data']['text']
        assert "Backup operation" in call_args[1]['data']['text']
    
    @patch('services.telegram_service.requests.get')
    def test_test_connection_success(self, mock_get):
        """Test successful connection test."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "ok": True,
            "result": {"first_name": "TestBot"}
        }
        mock_get.return_value = mock_response
        
        result = self.telegram_service.test_connection()
        
        assert result is True
        mock_get.assert_called_once()
    
    @patch('services.telegram_service.requests.get')
    def test_test_connection_failure(self, mock_get):
        """Test connection test failure."""
        mock_get.side_effect = Exception("Network error")
        
        result = self.telegram_service.test_connection()
        
        assert result is False

