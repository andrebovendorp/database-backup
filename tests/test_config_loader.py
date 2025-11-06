"""
Unit tests for ConfigLoader.
"""
import pytest
import tempfile
import os
from pathlib import Path
import yaml

from config_loader import ConfigLoader


class TestConfigLoader:
    """Test cases for ConfigLoader."""
    
    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary config file."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        temp_file.close()  # Close the file immediately on Windows
        yield temp_file.name
        # Clean up - use try/except for Windows compatibility
        try:
            os.unlink(temp_file.name)
        except PermissionError:
            pass  # File might still be in use on Windows
    
    @pytest.fixture
    def new_format_config(self, temp_config_file):
        """Create a config file with new format (sources/targets/notifications)."""
        config = {
            'sources': {
                'pgsql': [
                    {
                        'id': 'test-pgsql',
                        'host': 'localhost',
                        'port': 5432,
                        'database': 'testdb',
                        'username': 'testuser',
                        'password': 'testpass'
                    }
                ],
                'mongodb': [
                    {
                        'id': 'test-mongo',
                        'host': 'localhost',
                        'port': 27017,
                        'database': 'testdb',
                        'uri': 'mongodb://localhost:27017/testdb'
                    }
                ]
            },
            'targets': {
                'ftp': {
                    'enabled': True,
                    'host': 'ftp.example.com',
                    'port': 21,
                    'username': 'ftpuser',
                    'password': 'ftppass',
                    'remote_dir': '/backup',
                    'ssl': False
                },
                's3': {
                    'enabled': True,
                    'bucket': 'my-bucket',
                    'region': 'us-east-1',
                    'access_key': 'AKIAIOSFODNN7EXAMPLE',
                    'secret_key': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
                    'endpoint_url': 'https://s3.amazonaws.com',
                    'path_prefix': 'backups/'
                }
            },
            'notifications': {
                'telegram': {
                    'enabled': True,
                    'bot_token': '123456:ABC-DEF',
                    'chat_id': '-1001234567890'
                }
            },
            'backup': {
                'directory': './backups',
                'retention_days': 7,
                'compression': True
            }
        }
        
        with open(temp_config_file, 'w') as f:
            yaml.dump(config, f)
        
        return temp_config_file
    
    @pytest.fixture
    def old_format_config(self, temp_config_file):
        """Create a config file with old format (deprecated)."""
        config = {
            'pgsql': [
                {
                    'id': 'old-pgsql',
                    'host': 'localhost',
                    'port': 5432,
                    'database': 'olddb',
                    'username': 'olduser',
                    'password': 'oldpass'
                }
            ],
            'mongodb': [
                {
                    'id': 'old-mongo',
                    'host': 'localhost',
                    'port': 27017,
                    'database': 'olddb',
                    'uri': 'mongodb://localhost:27017/olddb'
                }
            ],
            'ftp': {
                'host': 'old-ftp.example.com',
                'port': 21,
                'username': 'oldftpuser',
                'password': 'oldftppass',
                'remote_dir': '/old-backup',
                'ssl': False
            },
            'telegram': {
                'bot_token': 'old-token',
                'chat_id': 'old-chat-id',
                'enabled': True
            },
            'backup': {
                'directory': './old-backups',
                'retention_days': 14,
                'compression': True
            }
        }
        
        with open(temp_config_file, 'w') as f:
            yaml.dump(config, f)
        
        return temp_config_file
    
    @pytest.fixture
    def mixed_format_config(self, temp_config_file):
        """Create a config file with Telegram in old location (targets.telegram)."""
        config = {
            'sources': {
                'pgsql': [
                    {
                        'id': 'mixed-pgsql',
                        'host': 'localhost',
                        'port': 5432,
                        'database': 'mixeddb',
                        'username': 'mixeduser',
                        'password': 'mixedpass'
                    }
                ]
            },
            'targets': {
                'ftp': {
                    'enabled': True,
                    'host': 'ftp.example.com',
                    'port': 21,
                    'username': 'ftpuser',
                    'password': 'ftppass',
                    'remote_dir': '/backup',
                    'ssl': False
                },
                'telegram': {  # Old location
                    'enabled': True,
                    'bot_token': 'old-location-token',
                    'chat_id': '-1001111111111'
                }
            },
            'backup': {
                'directory': './backups',
                'retention_days': 7,
                'compression': True
            }
        }
        
        with open(temp_config_file, 'w') as f:
            yaml.dump(config, f)
        
        return temp_config_file
    
    def test_load_databases_new_format(self, new_format_config):
        """Test loading databases from new format config."""
        loader = ConfigLoader(new_format_config)
        databases = loader.load_databases()
        
        assert len(databases) == 2
        
        # Check PostgreSQL
        pgsql = [db for db in databases if db['type'] == 'postgresql'][0]
        assert pgsql['id'] == 'test-pgsql'
        assert pgsql['host'] == 'localhost'
        assert pgsql['port'] == 5432
        assert pgsql['database'] == 'testdb'
        assert pgsql['username'] == 'testuser'
        
        # Check MongoDB
        mongo = [db for db in databases if db['type'] == 'mongodb'][0]
        assert mongo['id'] == 'test-mongo'
        assert mongo['host'] == 'localhost'
        assert mongo['port'] == 27017
        assert mongo['database'] == 'testdb'
    
    def test_load_databases_old_format(self, old_format_config):
        """Test loading databases from old format config (backward compatibility)."""
        loader = ConfigLoader(old_format_config)
        databases = loader.load_databases()
        
        assert len(databases) == 2
        
        # Check PostgreSQL
        pgsql = [db for db in databases if db['type'] == 'postgresql'][0]
        assert pgsql['id'] == 'old-pgsql'
        assert pgsql['database'] == 'olddb'
        
        # Check MongoDB
        mongo = [db for db in databases if db['type'] == 'mongodb'][0]
        assert mongo['id'] == 'old-mongo'
        assert mongo['database'] == 'olddb'
    
    def test_load_ftp_config_new_format(self, new_format_config):
        """Test loading FTP config from new format."""
        loader = ConfigLoader(new_format_config)
        ftp_config = loader.load_ftp_config()
        
        assert ftp_config is not None
        assert ftp_config['enabled'] == True
        assert ftp_config['host'] == 'ftp.example.com'
        assert ftp_config['port'] == 21
        assert ftp_config['username'] == 'ftpuser'
        assert ftp_config['remote_dir'] == '/backup'
    
    def test_load_ftp_config_old_format(self, old_format_config):
        """Test loading FTP config from old format."""
        loader = ConfigLoader(old_format_config)
        ftp_config = loader.load_ftp_config()
        
        assert ftp_config is not None
        assert ftp_config['host'] == 'old-ftp.example.com'
        assert ftp_config['username'] == 'oldftpuser'
    
    def test_load_ftp_config_disabled(self, temp_config_file):
        """Test that disabled FTP config returns None."""
        config = {
            'targets': {
                'ftp': {
                    'enabled': False,
                    'host': 'ftp.example.com',
                    'port': 21
                }
            }
        }
        
        with open(temp_config_file, 'w') as f:
            yaml.dump(config, f)
        
        loader = ConfigLoader(temp_config_file)
        ftp_config = loader.load_ftp_config()
        
        assert ftp_config is None
    
    def test_load_s3_config_new_format(self, new_format_config):
        """Test loading S3 config from new format."""
        loader = ConfigLoader(new_format_config)
        s3_config = loader.load_s3_config()
        
        assert s3_config is not None
        assert s3_config['enabled'] == True
        assert s3_config['bucket'] == 'my-bucket'
        assert s3_config['region'] == 'us-east-1'
        assert s3_config['access_key'] == 'AKIAIOSFODNN7EXAMPLE'
        assert s3_config['endpoint_url'] == 'https://s3.amazonaws.com'
        assert s3_config['path_prefix'] == 'backups/'
    
    def test_load_s3_config_disabled(self, temp_config_file):
        """Test that disabled S3 config returns None."""
        config = {
            'targets': {
                's3': {
                    'enabled': False,
                    'bucket': 'my-bucket',
                    'region': 'us-east-1'
                }
            }
        }
        
        with open(temp_config_file, 'w') as f:
            yaml.dump(config, f)
        
        loader = ConfigLoader(temp_config_file)
        s3_config = loader.load_s3_config()
        
        assert s3_config is None
    
    def test_load_s3_config_old_format(self, old_format_config):
        """Test that S3 config returns None for old format (no S3 support)."""
        loader = ConfigLoader(old_format_config)
        s3_config = loader.load_s3_config()
        
        assert s3_config is None
    
    def test_load_telegram_config_new_format(self, new_format_config):
        """Test loading Telegram config from new format (notifications section)."""
        loader = ConfigLoader(new_format_config)
        telegram_config = loader.load_telegram_config()
        
        assert telegram_config is not None
        assert telegram_config['enabled'] == True
        assert telegram_config['bot_token'] == '123456:ABC-DEF'
        assert telegram_config['chat_id'] == '-1001234567890'
    
    def test_load_telegram_config_old_format(self, old_format_config):
        """Test loading Telegram config from old format (root level)."""
        loader = ConfigLoader(old_format_config)
        telegram_config = loader.load_telegram_config()
        
        assert telegram_config is not None
        assert telegram_config['bot_token'] == 'old-token'
        assert telegram_config['chat_id'] == 'old-chat-id'
        assert telegram_config['enabled'] == True
    
    def test_load_telegram_config_mixed_format(self, mixed_format_config):
        """Test loading Telegram config from targets (fallback)."""
        loader = ConfigLoader(mixed_format_config)
        telegram_config = loader.load_telegram_config()
        
        assert telegram_config is not None
        assert telegram_config['bot_token'] == 'old-location-token'
        assert telegram_config['chat_id'] == '-1001111111111'
    
    def test_load_backup_config(self, new_format_config):
        """Test loading backup config."""
        loader = ConfigLoader(new_format_config)
        backup_config = loader.load_backup_config()
        
        assert backup_config is not None
        assert backup_config['directory'] == './backups'
        assert backup_config['retention_days'] == 7
        assert backup_config['compression'] == True
    
    def test_create_database_configs(self, new_format_config):
        """Test creating database config objects."""
        loader = ConfigLoader(new_format_config)
        configs = loader.create_database_configs()
        
        assert len(configs) == 2
        
        # Each config is a tuple of (config_object, controller_id)
        for config, controller_id in configs:
            assert controller_id is not None
            assert hasattr(config, 'host')
            assert hasattr(config, 'database')
    
    def test_missing_config_file(self):
        """Test handling of missing config file."""
        loader = ConfigLoader('nonexistent.yaml')
        
        with pytest.raises(ValueError, match="Configuration file not found"):
            loader.load_databases()
    
    def test_no_config_file_specified(self):
        """Test handling when no config file is specified."""
        loader = ConfigLoader(None)
        
        with pytest.raises(ValueError, match="Configuration file path is required"):
            loader.load_databases()
    
    def test_empty_config_file(self, temp_config_file):
        """Test handling of empty config file."""
        with open(temp_config_file, 'w') as f:
            f.write('')
        
        loader = ConfigLoader(temp_config_file)
        databases = loader.load_databases()
        
        assert databases == []
    
    def test_auto_generated_ids(self, temp_config_file):
        """Test auto-generation of IDs when not specified."""
        config = {
            'sources': {
                'pgsql': [
                    {
                        'host': 'localhost',
                        'port': 5432,
                        'database': 'db1',
                        'username': 'user1',
                        'password': 'pass1'
                    },
                    {
                        'host': 'localhost',
                        'port': 5432,
                        'database': 'db2',
                        'username': 'user2',
                        'password': 'pass2'
                    }
                ]
            }
        }
        
        with open(temp_config_file, 'w') as f:
            yaml.dump(config, f)
        
        loader = ConfigLoader(temp_config_file)
        databases = loader.load_databases()
        
        assert len(databases) == 2
        # Check that IDs were auto-generated
        assert databases[0]['id'] == 'pgsql_0'
        assert databases[1]['id'] == 'pgsql_1'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
