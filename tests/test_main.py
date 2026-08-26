"""
Unit tests for main application.
"""
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from main import DatabaseBackupApp, main


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
    @patch('main.TelegramService')
    def test_app_initialization(self, mock_telegram, mock_backup_manager):
        """Test application initialization."""
        app = DatabaseBackupApp()
        
        assert app.backup_manager is not None
        assert app.backup_targets == []
        assert app.telegram_service is None  # No Telegram config by default
        assert app.view is not None
        assert app.report_view is not None
        assert app.logger is not None
    
    @patch('main.TelegramService')
    def test_environment_targets_are_not_loaded(self, mock_telegram):
        """Target configuration comes only from the YAML file."""
        os.environ['FTP_HOST'] = 'ftp.example.com'
        os.environ['FTP_USERNAME'] = 'user'
        os.environ['FTP_PASSWORD'] = 'pass'
        os.environ['FTP_REMOTE_DIR'] = '/backup'
        os.environ['TELEGRAM_BOT_TOKEN'] = '123456789:ABCdefGHIjklMNOpqrsTUVwxyz'
        os.environ['TELEGRAM_CHAT_ID'] = '-1001234567890'
        
        app = DatabaseBackupApp()
        
        assert app.backup_targets == []
        assert app.telegram_service is not None

    def test_load_services_requires_targets(self):
        """Loading a YAML file without targets raises an error."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as config_file:
            config_file.write("backup:\n  directory: ./backups\n")
            config_path = config_file.name
        try:
            app = DatabaseBackupApp(config_path)
            with pytest.raises(ValueError, match="At least one backup target"):
                app.load_services_from_config()
        finally:
            os.unlink(config_path)

        def test_load_services_from_yaml_targets(self):
                config_path = Path(self.temp_dir) / "config.yaml"
                config_path.write_text("""
targets:
    - type: ftp
        host: ftp.example.com
        username: user
        password: pass
        remote_dir: /backup
telegram:
    enabled: false
backup:
    directory: ./yaml-backups
    retention_days: 3
""", encoding="utf-8")
                app = DatabaseBackupApp(str(config_path))
                app.load_services_from_config()
                assert len(app.backup_targets) == 1
                assert app.backup_config.retention_days == 3

        def test_load_databases_from_config(self):
                config_path = Path(self.temp_dir) / "config.yaml"
                config_path.write_text("""
targets:
    - type: ftp
        host: ftp.example.com
        username: user
        password: pass
        remote_dir: /backup
mysql:
    - id: mysql-one
        host: localhost
        database: testdb
""", encoding="utf-8")
                app = DatabaseBackupApp(str(config_path))
                app.load_databases_from_config()
                assert "mysql-one" in app.backup_manager.controllers
    
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

    def test_add_mysql_database(self):
        """Test adding MySQL database."""
        app = DatabaseBackupApp()

        controller_id = app.add_mysql_database(
            host="localhost",
            port=3306,
            database="testdb",
            username="user",
            password="pass"
        )

        assert controller_id == "mysql_testdb"
        assert controller_id in app.backup_manager.controllers
    
    @patch('main.BackupManager.backup_database')
    @patch('main.TelegramService')
    def test_backup_database_success(self, mock_telegram, mock_backup):
        """Test successful database backup."""
        # Setup mocks
        mock_result = Mock()
        mock_result.is_successful = True
        mock_result.backup_id = "test_123"
        mock_result.database_name = "testdb"
        mock_result.status.value = "success"
        mock_result.backup_size_bytes = 1024
        mock_result.duration_seconds = 1.2
        mock_result.backup_file_path = "/tmp/backup.tar.gz"
        mock_backup.return_value = mock_result
        
        app = DatabaseBackupApp()
        app.telegram_service = Mock()
        app.backup_targets = [Mock()]
        app.backup_targets[0].__enter__ = Mock(return_value=app.backup_targets[0])
        app.backup_targets[0].__exit__ = Mock(return_value=None)
        app.backup_targets[0].upload_file.return_value = True
        
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
    
    @patch('main.TelegramService')
    def test_backup_all_databases(self, mock_telegram):
        """Test backing up all databases."""
        app = DatabaseBackupApp()
        app.telegram_service = Mock()
        
        # Add some databases
        app.add_mongodb_database("localhost", 27017, "testdb1")
        app.add_postgresql_database("localhost", 5432, "testdb2", "user", "pass")

        # Mock app-level backup_database calls used by backup_all_databases implementation
        with patch.object(app, 'backup_database', side_effect=[True, False]) as mock_backup_db:
            results = app.backup_all_databases()
        
        assert results == [True, False]
        assert mock_backup_db.call_count == 2
        app.telegram_service.notify_backup_summary.assert_called_once()
    
    def test_upload_to_targets_success(self):
        """Test successful target upload."""
        mock_ftp = Mock()
        mock_ftp.__enter__ = Mock(return_value=mock_ftp)
        mock_ftp.__exit__ = Mock(return_value=None)
        mock_ftp.upload_file.return_value = True
        
        app = DatabaseBackupApp()
        app.backup_targets = [mock_ftp]
        
        result = app.upload_to_targets("/tmp/backup.tar.gz")
        
        assert result is True
        mock_ftp.upload_file.assert_called_once_with("/tmp/backup.tar.gz")
    
    def test_upload_to_targets_failure(self):
        """Test failed target upload."""
        mock_ftp = Mock()
        mock_ftp.__enter__ = Mock(return_value=mock_ftp)
        mock_ftp.__exit__ = Mock(return_value=None)
        mock_ftp.upload_file.return_value = False
        
        app = DatabaseBackupApp()
        app.backup_targets = [mock_ftp]
        
        result = app.upload_to_targets("/tmp/backup.tar.gz")
        
        assert result is False
    
    def test_upload_to_targets_without_targets(self):
        """Test target upload without configured targets."""
        app = DatabaseBackupApp()
        
        result = app.upload_to_targets("/tmp/backup.tar.gz")
        
        assert result is False

    def test_upload_to_targets_includes_ftp_and_smb(self):
        """Upload to every configured target without removing FTP support."""
        app = DatabaseBackupApp()
        ftp_target = Mock()
        smb_target = Mock()
        ftp_target.__enter__ = Mock(return_value=ftp_target)
        ftp_target.__exit__ = Mock(return_value=None)
        smb_target.__enter__ = Mock(return_value=smb_target)
        smb_target.__exit__ = Mock(return_value=None)
        ftp_target.upload_file.return_value = True
        smb_target.upload_file.return_value = True
        app.backup_targets = [ftp_target, smb_target]

        assert app.upload_to_targets("/tmp/backup.tar.gz") is True
        ftp_target.upload_file.assert_called_once_with("/tmp/backup.tar.gz")
        smb_target.upload_file.assert_called_once_with("/tmp/backup.tar.gz")

    def test_upload_to_targets_handles_exception(self):
        app = DatabaseBackupApp()
        target = Mock()
        target.__enter__ = Mock(side_effect=RuntimeError("offline"))
        target.__exit__ = Mock(return_value=None)
        app.backup_targets = [target]
        assert app.upload_to_targets("/tmp/backup.tar.gz") is False

    @patch('main.BackupManager.backup_database', side_effect=RuntimeError("failed"))
    def test_backup_database_handles_exception(self, mock_backup):
        app = DatabaseBackupApp()
        controller_id = app.add_mongodb_database("localhost", 27017, "testdb")
        assert app.backup_database(controller_id) is False

    def test_list_controllers_and_no_target_connections(self):
        app = DatabaseBackupApp()
        app.add_mongodb_database("localhost", 27017, "testdb")
        with patch.object(app.view, 'display_info') as display_info:
            app.list_controllers()
            assert display_info.call_count > 0
        with patch.object(app.view, 'display_warning') as warning:
            app.test_connections()
            warning.assert_called_once_with("No backup targets configured")

    def test_restore_database_missing_controller(self):
        app = DatabaseBackupApp()
        assert app.restore_database("backup.tar.gz", "missing") is False

    def test_restore_database_success_and_target_database(self, monkeypatch):
        monkeypatch.delenv('TELEGRAM_BOT_TOKEN', raising=False)
        app = DatabaseBackupApp()
        controller_id = app.add_mongodb_database("localhost", 27017, "original")
        controller = app.backup_manager.controllers[controller_id]
        with patch.object(controller, 'restore_backup', return_value=True):
            assert app.restore_database("backup.tar.gz", controller_id, "target") is True
        assert controller.db_config.database == "original"

    def test_generate_report_save_and_failure(self):
        app = DatabaseBackupApp()
        with patch.object(app.report_view, 'generate_text_report', return_value="report"):
            with patch.object(app.report_view, 'save_report', return_value=True):
                app.generate_report(str(Path(self.temp_dir) / "report.txt"))
            with patch.object(app.report_view, 'save_report', return_value=False):
                app.generate_report(str(Path(self.temp_dir) / "report.txt"))

    def test_list_backup_files_handles_failure(self):
        app = DatabaseBackupApp()
        with patch.object(app.backup_manager, 'list_backup_files', side_effect=RuntimeError("failed")):
            app.list_backup_files()

    def test_cleanup_and_list_empty_paths(self):
        app = DatabaseBackupApp()
        with patch.object(app.backup_manager, 'cleanup_all_backups', side_effect=RuntimeError("cleanup")):
            app.cleanup_old_backups()
        with patch.object(app.view, 'display_warning') as warning:
            app.list_controllers()
            warning.assert_called_once_with("No controllers configured")

    def test_restore_failure_and_exception_paths(self):
        app = DatabaseBackupApp()
        controller_id = app.add_mongodb_database("localhost", 27017, "testdb")
        controller = app.backup_manager.controllers[controller_id]
        app.telegram_service = Mock()
        with patch.object(controller, 'restore_backup', return_value=False):
            assert app.restore_database("backup.tar.gz", controller_id) is False
            app.telegram_service.notify_error.assert_called_once()
        with patch.object(controller, 'restore_backup', side_effect=RuntimeError("restore")):
            assert app.restore_database("backup.tar.gz", controller_id) is False

    def test_test_connections_reports_database_and_target_failures(self):
        app = DatabaseBackupApp()
        controller_id = app.add_mongodb_database("localhost", 27017, "testdb")
        controller = app.backup_manager.controllers[controller_id]
        controller.test_connection = Mock(return_value=False)
        target = Mock()
        target.__class__ = type("SMBService", (), {})
        target.__enter__ = Mock(side_effect=RuntimeError("target"))
        app.backup_targets = [target]
        app.telegram_service = Mock()
        app.telegram_service.test_connection.return_value = False
        app.test_connections()
        controller.test_connection.assert_called_once()
        app.telegram_service.test_connection.assert_called_once()

    def test_test_connections_reports_successes(self):
        app = DatabaseBackupApp()
        controller_id = app.add_mongodb_database("localhost", 27017, "testdb")
        app.backup_manager.controllers[controller_id].test_connection = Mock(return_value=True)
        target = Mock()
        target.__class__ = type("SMBService", (), {})
        target.__enter__ = Mock(return_value=target)
        target.__exit__ = Mock(return_value=None)
        app.backup_targets = [target]
        app.test_connections()

    def test_test_connections_without_telegram(self, monkeypatch):
        monkeypatch.delenv('TELEGRAM_BOT_TOKEN', raising=False)
        app = DatabaseBackupApp()
        app.test_connections()

    def test_main_verbose_flag(self, monkeypatch):
        monkeypatch.setattr('sys.argv', ['main.py', '--verbose'])
        app = Mock()
        monkeypatch.setattr('main.DatabaseBackupApp', Mock(return_value=app))
        main()

    def test_generate_report_prints_without_output_file(self):
        app = DatabaseBackupApp()
        with patch.object(app.report_view, 'generate_text_report', return_value="report"), patch('builtins.print') as output:
            app.generate_report()
        output.assert_called_once_with("report")

    def test_restore_success_notifies_telegram(self):
        app = DatabaseBackupApp()
        controller_id = app.add_mongodb_database("localhost", 27017, "testdb")
        app.telegram_service = Mock()
        with patch.object(app.backup_manager.controllers[controller_id], 'restore_backup', return_value=True):
            assert app.restore_database("backup.tar.gz", controller_id) is True
        app.telegram_service.notify_backup_completed.assert_called_once_with(None)

    @pytest.mark.parametrize("arguments, method, return_value", [
        (["--backup-all"], "backup_all_databases", [True]),
        (["--backup" , "db"], "backup_database", True),
        (["--list-files", "db"], "list_backup_files", None),
        (["--cleanup"], "cleanup_old_backups", None),
        (["--report", "report.txt"], "generate_report", None),
        (["--test"], "test_connections", None),
        (["--list-controllers"], "list_controllers", None),
    ])
    def test_main_dispatches_commands(self, monkeypatch, arguments, method, return_value):
        monkeypatch.setattr('sys.argv', ['main.py'] + arguments)
        app = Mock()
        app.backup_all_databases.return_value = return_value
        app.backup_database.return_value = return_value
        monkeypatch.setattr('main.DatabaseBackupApp', Mock(return_value=app))
        main()
        app.load_databases_from_config.assert_called_once()
        app.load_services_from_config.assert_called_once()
        getattr(app, method).assert_called_once()

    def test_main_restore_requires_controller(self, monkeypatch):
        monkeypatch.setattr('sys.argv', ['main.py', '--restore', 'backup.tar.gz'])
        monkeypatch.setattr('main.DatabaseBackupApp', Mock())
        with pytest.raises(SystemExit) as error:
            main()
        assert error.value.code == 1

    @pytest.mark.parametrize("arguments, result, message", [
        (["--backup", "db"], False, "Backup failed"),
        (["--restore", "backup.tar.gz", "--target-controller", "db"], False, "Restore failed"),
        (["--backup-all"], [False], "Some backups failed"),
    ])
    def test_main_reports_failed_operations(self, monkeypatch, arguments, result, message):
        monkeypatch.setattr('sys.argv', ['main.py'] + arguments)
        app = Mock()
        app.backup_database.return_value = result
        app.restore_database.return_value = result
        app.backup_all_databases.return_value = result
        monkeypatch.setattr('main.DatabaseBackupApp', Mock(return_value=app))
        with patch('builtins.print') as output, pytest.raises(SystemExit):
            main()
        assert message in output.call_args[0][0]

    def test_main_handles_keyboard_interrupt(self, monkeypatch):
        monkeypatch.setattr('sys.argv', ['main.py'])
        app = Mock()
        app.load_databases_from_config.side_effect = KeyboardInterrupt
        monkeypatch.setattr('main.DatabaseBackupApp', Mock(return_value=app))
        with patch('builtins.print') as output, pytest.raises(SystemExit):
            main()
        assert "Operation cancelled" in output.call_args[0][0]
    
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
    
    @patch('main.TelegramService')
    def test_test_connections(self, mock_telegram):
        """Test connection testing."""
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

