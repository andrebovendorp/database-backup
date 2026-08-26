"""
Unit tests for configuration loader.
"""
import tempfile
from pathlib import Path

from config_loader import ConfigLoader
from models.database_config import MySQLConfig


class TestConfigLoader:
    """Test YAML config loader behavior."""

    def test_create_database_configs_with_mysql(self):
        """Create typed database configs including MySQL from one config file."""
        config_yaml = """
pgsql:
  - id: pg-main
    host: localhost
    port: 5432
    database: pgdb
    username: pguser
    password: pgpass

mongodb:
  - id: mongo-main
    host: localhost
    port: 27017
    database: mongodb
    uri: mongodb://localhost:27017/mongodb

mysql:
  - id: mysql-main
    host: localhost
    port: 3306
    database: mysqldb
    username: mysqluser
    password: mysqlpass
"""

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            config_path.write_text(config_yaml, encoding="utf-8")

            loader = ConfigLoader(str(config_path))
            configs = loader.create_database_configs()

            assert len(configs) == 3
            config_map = {controller_id: config for config, controller_id in configs}

            assert "mysql-main" in config_map
            assert isinstance(config_map["mysql-main"], MySQLConfig)
            assert config_map["mysql-main"].database == "mysqldb"

    def test_load_target_configs_supports_smb_and_legacy_ftp(self):
        config_yaml = """
targets:
  - type: ftp
    host: ftp.example.com
    username: ftp-user
    password: ftp-pass
    remote_dir: /backup
  - type: smb
    host: nas.example.com
    share: backups
    username: smb-user
    password: smb-pass
    remote_dir: database-backup
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            config_path.write_text(config_yaml, encoding="utf-8")

            targets = ConfigLoader(str(config_path)).load_target_configs()

            assert [target['type'] for target in targets] == ['ftp', 'smb']

    def test_load_target_configs_supports_mapping_format(self):
        config_yaml = """
targets:
  ftp:
    enabled: true
    host: ftp.example.com
    username: ftp-user
    password: ftp-pass
    remote_dir: /backup
  s3:
    enabled: false
    bucket: ignored
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            config_path.write_text(config_yaml, encoding="utf-8")

            targets = ConfigLoader(str(config_path)).load_target_configs()

            assert targets == [{
                'type': 'ftp',
                'enabled': True,
                'host': 'ftp.example.com',
                'username': 'ftp-user',
                'password': 'ftp-pass',
                'remote_dir': '/backup'
            }]

    def test_load_target_configs_ignores_disabled_list_targets(self):
        config_yaml = """
targets:
  - type: ftp
    enabled: false
    host: ftp.example.com
    username: user
    password: pass
    remote_dir: /backup
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            config_path.write_text(config_yaml, encoding="utf-8")

            assert ConfigLoader(str(config_path)).load_target_configs() == []
