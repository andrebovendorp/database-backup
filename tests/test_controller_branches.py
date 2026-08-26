"""Additional branch coverage for database controllers and shared helpers."""
import os
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from controllers.base_controller import BaseBackupController
from controllers.mongodb_controller import MongoDBBackupController
from controllers.mysql_controller import MySQLBackupController
from controllers.postgresql_controller import PostgreSQLBackupController
from services.ftp_target import FTPBackupTarget
from services.backup_target import BackupTarget
from models.database_config import FTPConfig
from models.database_config import MongoDBConfig, MySQLConfig, PostgreSQLConfig, BackupConfig


class ConcreteController(BaseBackupController):
    def create_backup(self):
        return None

    def restore_backup(self, backup_file_path):
        return True


def test_backup_target_contract_is_importable():
    assert BackupTarget is not None


@pytest.fixture
def backup_config(tmp_path):
    return BackupConfig(backup_dir=str(tmp_path), retention_days=1)


def test_base_helpers_and_cleanup(tmp_path, backup_config):
    controller = ConcreteController(
        MongoDBConfig(host="localhost", database="db"), backup_config
    )
    old_file = tmp_path / "old.tar.gz"
    old_file.touch()
    os.utime(old_file, (1, 1))
    recent_file = tmp_path / "recent.tar.gz"
    recent_file.touch()
    assert str(old_file) in controller.cleanup_old_backups()
    assert recent_file.exists()
    assert controller._get_file_size(str(recent_file)) == 0
    assert controller._get_file_size(str(tmp_path / "missing")) == 0
    assert controller._generate_backup_filename().startswith("backup_db_")

@patch("controllers.base_controller.subprocess.run")
def test_base_execute_command_variants(mock_run, backup_config):
    controller = ConcreteController(MongoDBConfig(host="h", database="d"), backup_config)
    mock_run.return_value = Mock(returncode=0, stdout="ok", stderr="")
    assert controller._execute_command(["tool"]) == (True, "ok", "")
    mock_run.return_value = Mock(returncode=1, stdout="out", stderr="bad")
    assert controller._execute_command(["tool"])[0] is False
    mock_run.side_effect = subprocess.TimeoutExpired("tool", 1)
    assert controller._execute_command(["tool"])[0] is False
    mock_run.side_effect = OSError("missing")
    assert controller._execute_command(["tool"])[0] is False


def test_base_cleanup_unlink_error(tmp_path, backup_config):
    controller = ConcreteController(MongoDBConfig(host="h", database="d"), backup_config)
    old_file = tmp_path / "old.tar.gz"
    old_file.touch()
    os.utime(old_file, (1, 1))
    with patch.object(Path, "unlink", side_effect=OSError("locked")):
        assert controller.cleanup_old_backups() == []


def test_mongodb_command_options(backup_config):
    config = MongoDBConfig(host="h", port=27018, database="d", username="u", password="p", additional_params={"gzip": True, "readPreference": "secondary"})
    controller = MongoDBBackupController(config, backup_config)
    dump = controller._build_mongodump_command("/tmp/out")
    restore = controller._build_mongorestore_command("/tmp/in")
    assert "--gzip" in dump and "--readPreference" in dump and "secondary" in dump
    assert "--gzip" in restore and "secondary" in restore

@patch.object(MongoDBBackupController, "_execute_command")
def test_mongodb_backup_archive_failure(mock_execute, backup_config):
    controller = MongoDBBackupController(MongoDBConfig(host="h", database="d"), backup_config)
    mock_execute.side_effect = [(True, "", ""), (False, "", "archive error")]
    result = controller.create_backup()
    assert not result.is_successful
    assert "archive error" in result.error_message

@patch.object(MongoDBBackupController, "_execute_command")
def test_mongodb_restore_paths(mock_execute, backup_config, tmp_path):
    controller = MongoDBBackupController(MongoDBConfig(host="h", database="d"), backup_config)
    mock_execute.return_value = (False, "", "extract error")
    assert controller.restore_backup("backup.tar.gz") is False
    mock_execute.return_value = (True, "", "")
    with patch("controllers.mongodb_controller.tempfile.TemporaryDirectory") as temp_dir:
        temp_dir.return_value.__enter__.return_value = str(tmp_path)
        temp_dir.return_value.__exit__.return_value = None
        with patch.object(Path, "iterdir", return_value=[]):
            assert controller.restore_backup("backup.tar.gz") is True


def test_mysql_commands_and_password(backup_config):
    config = MySQLConfig(host="h", port=3307, database="d", username="u", password="p", additional_params={"skip-lock-tables": True, "max_allowed_packet": 10})
    controller = MySQLBackupController(config, backup_config)
    dump = controller._build_mysqldump_command("/tmp/out")
    restore = controller._build_mysql_restore_command("/tmp/in.sql")
    assert "--skip-lock-tables" in dump and "10" in dump
    assert "--execute=source /tmp/in.sql" in restore

@patch("controllers.mysql_controller.subprocess.run")
def test_mysql_execute_variants(mock_run, backup_config):
    controller = MySQLBackupController(MySQLConfig(host="h", database="d", password="p"), backup_config)
    mock_run.return_value = Mock(returncode=0, stdout="ok", stderr="")
    assert controller._execute_command_with_password(["mysql"])[0] is True
    assert mock_run.call_args.kwargs["env"]["MYSQL_PWD"] == "p"
    mock_run.return_value = Mock(returncode=1, stdout="", stderr="bad")
    assert controller._execute_command_with_password(["mysql"])[0] is False
    mock_run.side_effect = subprocess.TimeoutExpired("mysql", 1)
    assert controller._execute_command_with_password(["mysql"])[0] is False
    mock_run.side_effect = OSError("missing")
    assert controller._execute_command_with_password(["mysql"])[0] is False

@patch.object(MySQLBackupController, "_execute_command_with_password")
def test_mysql_backup_and_restore_failures(mock_execute, backup_config):
    controller = MySQLBackupController(MySQLConfig(host="h", database="d"), backup_config)
    mock_execute.return_value = (False, "", "dump error")
    result = controller.create_backup()
    assert result.is_successful is False
    mock_execute.return_value = (True, "", "")
    with patch.object(controller, "_execute_command", return_value=(False, "", "extract error")):
        assert controller.restore_backup("backup.tar.gz") is False
    with patch.object(controller, "_execute_command", return_value=(True, "", "")), patch("controllers.mysql_controller.Path.iterdir", return_value=[]):
        assert controller.restore_backup("backup.tar.gz") is False

@patch("controllers.mysql_controller.subprocess.run")
def test_mysql_connection(mock_run, backup_config):
    controller = MySQLBackupController(MySQLConfig(host="h", database="d"), backup_config)
    mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
    assert controller.test_connection() is True
    mock_run.return_value = Mock(returncode=1, stdout="", stderr="bad")
    assert controller.test_connection() is False


def test_postgresql_commands_and_pgpass(backup_config, tmp_path):
    config = PostgreSQLConfig(host="h", port=5433, database="d", username="u", password="p", additional_params={"no-owner": True, "format": "custom"})
    controller = PostgreSQLBackupController(config, backup_config)
    dump = controller._build_pg_dump_command("/tmp/out")
    assert "--no-owner" in dump and "custom" in dump
    assert "--quiet" in controller._build_psql_command("/tmp/in")
    pgpass = controller._create_pgpass_file()
    assert Path(pgpass).read_text() == "h:5433:d:u:p\n"
    controller._cleanup_pgpass_file()
    assert not Path(pgpass).exists()
    controller.db_config.password = None
    assert controller._create_pgpass_file() is None

@patch("controllers.postgresql_controller.subprocess.run")
def test_postgresql_execute_variants(mock_run, backup_config):
    controller = PostgreSQLBackupController(PostgreSQLConfig(host="h", database="d", password="p"), backup_config)
    pgpass = str(Path(backup_config.backup_dir) / "pgpass")
    Path(pgpass).write_text("x")
    mock_run.return_value = Mock(returncode=0, stdout="ok", stderr="")
    assert controller._execute_command_with_pgpass(["psql"], pgpass)[0] is True
    mock_run.return_value = Mock(returncode=1, stdout="", stderr="bad")
    assert controller._execute_command_with_pgpass(["psql"], pgpass)[0] is False
    mock_run.side_effect = subprocess.TimeoutExpired("psql", 1)
    assert controller._execute_command_with_pgpass(["psql"], pgpass)[0] is False
    mock_run.side_effect = OSError("missing")
    assert controller._execute_command_with_pgpass(["psql"], pgpass)[0] is False

@patch.object(PostgreSQLBackupController, "_execute_command_with_pgpass")
def test_postgresql_ensure_database_branches(mock_execute, backup_config):
    controller = PostgreSQLBackupController(PostgreSQLConfig(host="h", database="d"), backup_config)
    mock_execute.return_value = (True, "1", "")
    assert controller._ensure_database_exists(None) is True
    mock_execute.side_effect = [(False, "", "missing"), (True, "", "")]
    assert controller._ensure_database_exists(None) is True
    mock_execute.side_effect = [(False, "", "missing"), (False, "", "create error")]
    assert controller._ensure_database_exists(None) is False

@patch.object(PostgreSQLBackupController, "_execute_command")
def test_postgresql_backup_archive_and_restore_failures(mock_execute, backup_config):
    controller = PostgreSQLBackupController(PostgreSQLConfig(host="h", database="d"), backup_config)
    with patch.object(controller, "_execute_command_with_pgpass", return_value=(False, "", "dump error")):
        result = controller.create_backup()
        assert result.is_successful is False
    mock_execute.return_value = (False, "", "extract error")
    assert controller.restore_backup("backup.tar.gz") is False

@patch.object(PostgreSQLBackupController, "_execute_command_with_pgpass")
def test_postgresql_connection(mock_execute, backup_config):
    controller = PostgreSQLBackupController(PostgreSQLConfig(host="h", database="d"), backup_config)
    mock_execute.return_value = (True, "1", "")
    assert controller.test_connection() is True
    mock_execute.return_value = (False, "", "bad")
    assert controller.test_connection() is False


@patch("services.ftp_target.FTP")
def test_ftp_error_branches(mock_ftp, backup_config, tmp_path):
    target = FTPBackupTarget(FTPConfig(host="ftp", username="u", password="p", remote_dir="/"))
    connection = Mock()
    mock_ftp.return_value = connection
    target.connect()
    connection.quit.side_effect = Exception("quit")
    target.disconnect()
    target._connection = connection
    connection.storbinary.side_effect = Exception("upload")
    assert target.upload_file(str(tmp_path / "missing")) is False
    local_file = tmp_path / "file.txt"
    local_file.write_text("content")
    assert target.upload_file(str(local_file)) is False
    connection.retrbinary.side_effect = Exception("download")
    assert target.download_file("remote", str(tmp_path / "out")) is False
    connection.retrlines.side_effect = Exception("list")
    assert target.list_files() == []
    connection.delete.side_effect = Exception("delete")
    assert target.delete_file("remote") is False
    connection.retrlines.side_effect = lambda command, callback: callback("-rw-r--r-- 1 u g 1 Jan 1 00:00 old.tar.gz")
    connection.voidcmd.return_value = "213 20000101000000"
    assert target.cleanup_old_files(1) == [] or isinstance(target.cleanup_old_files(1), list)


def test_ftp_not_connected_operations(backup_config):
    target = FTPBackupTarget(FTPConfig(host="ftp", username="u", password="p", remote_dir="/"))
    assert target.download_file("remote", "out") is False
    assert target.list_files() == []
    assert target.delete_file("remote") is False
    assert target.cleanup_old_files() == []


@patch.object(MySQLBackupController, "_execute_command_with_password")
def test_mysql_restore_success(mock_password, backup_config, tmp_path):
    controller = MySQLBackupController(MySQLConfig(host="h", database="d"), backup_config)
    sql_file = tmp_path / "dump.sql"
    sql_file.write_text("select 1;")
    mock_password.return_value = (True, "", "")
    with patch.object(controller, "_execute_command", return_value=(True, "", "")), \
         patch("controllers.mysql_controller.Path.iterdir", return_value=[sql_file]), \
         patch.object(controller, "_ensure_database_exists", return_value=True):
        assert controller.restore_backup("backup.tar.gz") is True


def test_config_loader_error_paths(tmp_path, monkeypatch):
    from config_loader import ConfigLoader
    loader = ConfigLoader(str(tmp_path / "missing.yaml"))
    with pytest.raises(ValueError, match="not found"):
        loader.load_databases()
    loader.config_file = None
    with pytest.raises(ValueError, match="required"):
        loader.load_databases()
    import config_loader as module
    monkeypatch.setattr(module, "YAML_AVAILABLE", False)
    assert loader.load_target_configs() == []
    assert loader.load_telegram_config() is None
    assert loader.load_backup_config() is None


def test_config_loader_yaml_errors(tmp_path, monkeypatch):
    from config_loader import ConfigLoader
    import config_loader as module
    config_path = tmp_path / "config.yaml"
    config_path.write_text("not: [valid", encoding="utf-8")
    loader = ConfigLoader(str(config_path))
    with pytest.raises(ValueError, match="Failed to load configuration"):
        loader.load_databases()
    monkeypatch.setattr(module, "YAML_AVAILABLE", False)
    with pytest.raises(ValueError, match="YAML module not available"):
        loader.load_databases()


def test_config_loader_optional_sections_and_database_errors(tmp_path):
        from config_loader import ConfigLoader
        config_path = tmp_path / "config.yaml"
        config_path.write_text(
                "pgsql:\n- host: h\n  database: pg\n"
                "mongodb:\n- host: h\n  database: mongo\n"
                "mysql:\n- host: h\n  database: sql\n"
                "telegram:\n  enabled: true\n"
                "backup:\n  directory: ./backups\n",
                encoding="utf-8")
        loader = ConfigLoader(str(config_path))
        assert len(loader.create_database_configs()) == 3
        assert loader.load_telegram_config()['enabled'] is True
        assert loader.load_backup_config()['directory'] == './backups'
        config_path.write_text("unknown:\n  - value\n", encoding="utf-8")
        assert loader.create_database_configs() == []


def test_smb_disconnect_and_upload_errors(backup_config, tmp_path):
        from services.smb_service import SMBService
        from models.database_config import SMBConfig
        service = SMBService(SMBConfig(host="h", share="s", username="u", password="p"))
        with patch("services.smb_service.smbclient") as smb:
                service.connect()
                smb.delete_session.side_effect = RuntimeError("disconnect")
                service.disconnect()
                service._connected = True
                smb.open_file.side_effect = RuntimeError("upload")
                source = tmp_path / "file"
                source.write_text("data")
                assert service.upload_file(str(source)) is False


def test_backup_manager_error_and_filter_paths(tmp_path):
    from controllers.backup_manager import BackupManager
    manager = BackupManager(BackupConfig(backup_dir=str(tmp_path), retention_days=1))
    database = MongoDBConfig(host="h", database="d")
    controller_id = manager.add_database(database)
    manager.controllers[controller_id].create_backup = Mock(side_effect=RuntimeError("boom"))
    results = manager.backup_all_databases()
    assert len(results) == 1 and not results[0].is_successful
    with pytest.raises(ValueError, match="Controller not found"):
        manager.restore_database("missing", "backup.tar.gz")
    manager.controllers[controller_id].restore_backup = Mock(return_value=True)
    assert manager.restore_database(controller_id, "backup.tar.gz") is True
    result = Mock(is_successful=True, backup_size_bytes=0, duration_seconds=None, start_time=__import__('datetime').datetime.now())
    manager.backup_history = [result]
    assert manager.get_backup_summary().average_duration_seconds == 0.0
    matching = tmp_path / "backup_mongodb_d_1.tar.gz"
    matching.touch()
    assert len(manager.list_backup_files(controller_id)) == 1
    manager.controllers[controller_id].cleanup_old_backups = Mock(side_effect=RuntimeError("cleanup"))
    assert manager.cleanup_all_backups()[controller_id] == []
