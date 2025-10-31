"""
Configuration loader for database backup system.
Supports both environment variables and YAML configuration files.
"""
import os
from typing import Dict, List, Optional, Any
from pathlib import Path

# Try to import yaml, make it optional
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from models.database_config import MongoDBConfig, PostgreSQLConfig


class ConfigLoader:
    """Loads database configurations from environment variables or YAML files."""
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize configuration loader."""
        self.config_file = config_file
        self.databases = []
    
    def load_databases(self) -> List[Dict[str, Any]]:
        """Load database configurations from YAML config file."""
        if not self.config_file:
            raise ValueError("Configuration file path is required")
        
        if not Path(self.config_file).exists():
            raise ValueError(f"Configuration file not found: {self.config_file}")
        
        return self._load_from_yaml()
    
    
    def _load_from_yaml(self) -> List[Dict[str, Any]]:
        """Load database configurations from YAML file."""
        if not YAML_AVAILABLE:
            raise ValueError("YAML module not available. Install with: pip install pyyaml")
        
        try:
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f)
            
            databases = []
            
            # Load PostgreSQL databases
            if 'pgsql' in config:
                pgsql_configs = config['pgsql']
                if isinstance(pgsql_configs, list):
                    # Multiple PostgreSQL databases
                    for i, pgsql in enumerate(pgsql_configs):
                        pgsql['type'] = 'postgresql'
                        # Use explicit ID if provided, otherwise generate one
                        if 'id' not in pgsql:
                            pgsql['id'] = f"pgsql_{i}"  # Fallback to auto-generated ID
                        databases.append(pgsql)
            
            # Load MongoDB databases
            if 'mongodb' in config:
                mongo_configs = config['mongodb']
                if isinstance(mongo_configs, list):
                    # Multiple MongoDB databases
                    for i, mongo in enumerate(mongo_configs):
                        mongo['type'] = 'mongodb'
                        # Use explicit ID if provided, otherwise generate one
                        if 'id' not in mongo:
                            mongo['id'] = f"mongodb_{i}"  # Fallback to auto-generated ID
                        databases.append(mongo)
            
            return databases
            
        except Exception as e:
            raise ValueError(f"Failed to load configuration from {self.config_file}: {e}")
    
    def load_ftp_config(self) -> Optional[Dict[str, Any]]:
        """Load FTP configuration from YAML file."""
        if not YAML_AVAILABLE:
            return None
        
        try:
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f)
            
            return config.get('ftp')
        except Exception:
            return None
    
    def load_telegram_config(self) -> Optional[Dict[str, Any]]:
        """Load Telegram configuration from YAML file."""
        if not YAML_AVAILABLE:
            return None
        
        try:
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f)
            
            return config.get('telegram')
        except Exception:
            return None
    
    def load_backup_config(self) -> Optional[Dict[str, Any]]:
        """Load backup configuration from YAML file."""
        if not YAML_AVAILABLE:
            return None
        
        try:
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f)
            
            return config.get('backup')
        except Exception:
            return None
    
    def create_database_configs(self) -> List[tuple]:
        """Create database configuration objects and return (config, controller_id) tuples."""
        database_configs = self.load_databases()
        configs = []
        
        for db_config in database_configs:
            try:
                # Use the unique ID from the config, or generate one
                controller_id = db_config.get('id', f"{db_config['type']}_{db_config['database']}")
                
                if db_config['type'] == 'postgresql':
                    config = PostgreSQLConfig(
                        host=db_config['host'],
                        port=db_config.get('port', 5432),
                        database=db_config['database'],
                        username=db_config.get('username', ''),
                        password=db_config.get('password', '')
                    )
                
                elif db_config['type'] == 'mongodb':
                    config = MongoDBConfig(
                        host=db_config['host'],
                        port=db_config.get('port', 27017),
                        database=db_config['database'],
                        username=db_config.get('username', ''),
                        password=db_config.get('password', ''),
                        uri=db_config.get('uri', '')
                    )
                
                else:
                    raise ValueError(f"Unsupported database type: {db_config['type']}")
                
                configs.append((config, controller_id))
                
            except Exception as e:
                print(f"Warning: Failed to create config for {db_config.get('type', 'unknown')} database: {e}")
                continue
        
        return configs
