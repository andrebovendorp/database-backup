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

    def test_database_entry_timeouts_and_default(self):
        config_yaml = """
pgsql:
  - host: localhost
    database: slow_db
    timeout_seconds: 900
  - host: localhost
    database: default_db
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            config_path.write_text(config_yaml, encoding="utf-8")

            configs = ConfigLoader(str(config_path)).create_database_configs()

        config_map = {config.database: config for config, _ in configs}
        assert config_map["slow_db"].timeout_seconds == 900
        assert config_map["default_db"].timeout_seconds == 300

    def test_loads_configmap_wrapped_yaml(self):
        """Load config when YAML content is nested under a file-name key."""
        config_yaml = """
config.yaml: |
  pgsql:
    - id: pg-main
      host: localhost
      port: 5432
      database: pgdb
      username: pguser
      password: pgpass

  ftp:
    host: ftp.example.com
    port: 21
    username: ftpuser
    password: ftppass
    remote_dir: /backup
    ssl: false

  backup:
    directory: ./backups
    retention_days: 14
    compression: true
"""

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            config_path.write_text(config_yaml, encoding="utf-8")

            loader = ConfigLoader(str(config_path))
            configs = loader.create_database_configs()

            assert len(configs) == 1
            assert configs[0][1] == "pg-main"
            assert loader.load_ftp_config()["host"] == "ftp.example.com"
            assert loader.load_backup_config()["retention_days"] == 14
