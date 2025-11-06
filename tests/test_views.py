"""
Unit tests for views.
"""
import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from datetime import datetime
from pathlib import Path

from models.backup_result import BackupResult, BackupStatus, BackupSummary
from views.backup_view import BackupView, BackupReportView


class TestBackupView:
    """Test backup view."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.view = BackupView(verbose=False)
    
    def test_view_initialization(self):
        """Test view initialization."""
        assert self.view.verbose is False
        assert self.view.logger is not None
    
    def test_view_initialization_verbose(self):
        """Test view initialization with verbose mode."""
        view = BackupView(verbose=True)
        assert view.verbose is True
    
    @patch('builtins.print')
    def test_display_backup_started(self, mock_print):
        """Test display backup started message."""
        self.view.display_backup_started("testdb", "mongodb")
        
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "Starting backup for mongodb database: testdb" in call_args
    
    @patch('builtins.print')
    def test_display_backup_result_success(self, mock_print):
        """Test display successful backup result."""
        backup_result = BackupResult(
            backup_id="test_123",
            database_type="mongodb",
            database_name="testdb",
            status=BackupStatus.SUCCESS,
            start_time=datetime.now(),
            end_time=datetime.now(),
            backup_file_path="/tmp/backup.tar.gz",
            backup_size_bytes=1024
        )
        
        self.view.display_backup_result(backup_result)
        
        # Should call print multiple times
        assert mock_print.call_count >= 2
        call_args = [call[0][0] for call in mock_print.call_args_list]
        assert any("SUCCESS" in arg for arg in call_args)
        assert any("testdb" in arg for arg in call_args)
        assert any("test_123" in arg for arg in call_args)
    
    @patch('builtins.print')
    def test_display_backup_result_failure(self, mock_print):
        """Test display failed backup result."""
        backup_result = BackupResult(
            backup_id="test_123",
            database_type="mongodb",
            database_name="testdb",
            status=BackupStatus.FAILED,
            start_time=datetime.now(),
            end_time=datetime.now(),
            error_message="Connection failed"
        )
        
        self.view.display_backup_result(backup_result)
        
        # Should call print multiple times
        assert mock_print.call_count >= 2
        call_args = [call[0][0] for call in mock_print.call_args_list]
        assert any("FAILED" in arg for arg in call_args)
        assert any("Connection failed" in arg for arg in call_args)
    
    @patch('builtins.print')
    def test_display_backup_summary(self, mock_print):
        """Test display backup summary."""
        summary = BackupSummary(
            total_backups=10,
            successful_backups=8,
            failed_backups=2,
            total_size_bytes=1024000,
            average_duration_seconds=30.5,
            last_backup_time=datetime.now()
        )
        
        self.view.display_backup_summary(summary)
        
        # Should call print multiple times
        assert mock_print.call_count >= 5
        call_args = [call[0][0] for call in mock_print.call_args_list]
        assert any("BACKUP SUMMARY" in arg for arg in call_args)
        assert any("Total Backups: 10" in arg for arg in call_args)
        assert any("Success Rate: 80.0%" in arg for arg in call_args)
    
    @patch('builtins.print')
    def test_display_ftp_upload_success(self, mock_print):
        """Test display successful FTP upload."""
        self.view.display_ftp_upload("backup.tar.gz", True)
        
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "FTP UPLOADED: backup.tar.gz" in call_args
    
    @patch('builtins.print')
    def test_display_ftp_upload_failure(self, mock_print):
        """Test display failed FTP upload."""
        self.view.display_ftp_upload("backup.tar.gz", False)
        
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "FTP UPLOAD FAILED: backup.tar.gz" in call_args
    
    @patch('builtins.print')
    def test_display_cleanup_results(self, mock_print):
        """Test display cleanup results."""
        cleanup_results = {
            "mongodb_testdb": ["old1.tar.gz", "old2.tar.gz"],
            "postgresql_testdb": []
        }
        
        self.view.display_cleanup_results(cleanup_results)
        
        # Should call print multiple times
        assert mock_print.call_count >= 3
        call_args = [call[0][0] for call in mock_print.call_args_list]
        assert any("CLEANUP RESULTS" in arg for arg in call_args)
        assert any("mongodb_testdb: 2 files deleted" in arg for arg in call_args)
        assert any("postgresql_testdb: No files to delete" in arg for arg in call_args)
        assert any("Total files deleted: 2" in arg for arg in call_args)
    
    @patch('builtins.print')
    def test_display_backup_files(self, mock_print):
        """Test display backup files."""
        files = [
            {
                'filename': 'backup1.tar.gz',
                'size_bytes': 1024,
                'created_time': datetime.now(),
                'modified_time': datetime.now()
            },
            {
                'filename': 'backup2.tar.gz',
                'size_bytes': 2048,
                'created_time': datetime.now(),
                'modified_time': datetime.now()
            }
        ]
        
        self.view.display_backup_files(files)
        
        # Should call print multiple times
        assert mock_print.call_count >= 3
        call_args = [call[0][0] for call in mock_print.call_args_list]
        assert any("BACKUP FILES" in arg for arg in call_args)
        assert any("backup1.tar.gz" in arg for arg in call_args)
        assert any("backup2.tar.gz" in arg for arg in call_args)
    
    @patch('builtins.print')
    def test_display_backup_files_empty(self, mock_print):
        """Test display empty backup files list."""
        self.view.display_backup_files([])
        
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "No backup files found." in call_args
    
    @patch('builtins.print')
    def test_display_error(self, mock_print):
        """Test display error message."""
        self.view.display_error("Database connection failed", "Backup operation")
        
        assert mock_print.call_count == 2  # Error message + context
        first_call = mock_print.call_args_list[0][0][0]
        assert "ERROR: Database connection failed" in first_call
        second_call = mock_print.call_args_list[1][0][0]
        assert "Context: Backup operation" in second_call
    
    @patch('builtins.print')
    def test_display_info(self, mock_print):
        """Test display info message."""
        self.view.display_info("Backup completed successfully")
        
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "INFO: Backup completed successfully" in call_args
    
    @patch('builtins.print')
    def test_display_warning(self, mock_print):
        """Test display warning message."""
        self.view.display_warning("Low disk space")
        
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "WARNING: Low disk space" in call_args
    
    @patch('builtins.print')
    def test_display_debug_verbose(self, mock_print):
        """Test display debug message in verbose mode."""
        view = BackupView(verbose=True)
        view.display_debug("Debug information")
        
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "DEBUG: Debug information" in call_args
    
    @patch('builtins.print')
    def test_display_debug_not_verbose(self, mock_print):
        """Test display debug message when not verbose."""
        self.view.display_debug("Debug information")
        
        mock_print.assert_not_called()
    
    @patch('builtins.print')
    def test_display_progress(self, mock_print):
        """Test display progress indicator."""
        self.view.display_progress(5, 10, "Processing")
        
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "Processing:" in call_args
        assert "50.0%" in call_args
        assert "(5/10)" in call_args
    
    @patch('builtins.print')
    def test_display_progress_complete(self, mock_print):
        """Test display progress when complete."""
        self.view.display_progress(10, 10, "Processing")
        
        # Should call print twice (progress + newline)
        assert mock_print.call_count == 2


class TestBackupReportView:
    """Test backup report view."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.report_view = BackupReportView()
    
    def test_report_view_initialization(self):
        """Test report view initialization."""
        assert self.report_view.logger is not None
    
    def test_generate_text_report(self):
        """Test text report generation."""
        summary = BackupSummary(
            total_backups=5,
            successful_backups=4,
            failed_backups=1,
            total_size_bytes=512000,
            average_duration_seconds=25.0,
            last_backup_time=datetime.now()
        )
        
        results = [
            BackupResult(
                backup_id="test_1",
                database_type="mongodb",
                database_name="testdb",
                status=BackupStatus.SUCCESS,
                start_time=datetime.now(),
                end_time=datetime.now(),
                backup_size_bytes=1024
            ),
            BackupResult(
                backup_id="test_2",
                database_type="postgresql",
                database_name="testdb",
                status=BackupStatus.FAILED,
                start_time=datetime.now(),
                end_time=datetime.now(),
                error_message="Connection failed"
            )
        ]
        
        report = self.report_view.generate_text_report(summary, results)
        
        assert "DATABASE BACKUP REPORT" in report
        assert "SUMMARY" in report
        assert "Total Backups: 5" in report
        assert "Success Rate: 80.0%" in report
        assert "DETAILED RESULTS" in report
        assert "test_1" in report
        assert "test_2" in report
        assert "Connection failed" in report
    
    def test_save_report_success(self):
        """Test successful report saving."""
        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = os.path.join(temp_dir, "test_report.txt")
            report_content = "Test report content"
            
            result = self.report_view.save_report(report_content, report_path)
            
            assert result is True
            assert os.path.exists(report_path)
            
            with open(report_path, 'r') as f:
                content = f.read()
            assert content == report_content
    
    @patch('builtins.open', side_effect=PermissionError("Access denied"))
    def test_save_report_failure(self, mock_open):
        """Test report saving failure."""
        # Mock open to raise PermissionError
        invalid_path = "c:/invalid/path/report.txt"
        
        result = self.report_view.save_report("Test content", invalid_path)
        
        assert result is False

