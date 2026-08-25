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
