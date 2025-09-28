"""
Pytest configuration and fixtures for database backup system tests.
"""
import pytest
import tempfile
import os
import shutil
from datetime import datetime
from pathlib import Path

from models.database_config import MongoDBConfig, PostgreSQLConfig, BackupConfig
from models.backup_result import BackupResult, BackupStatus


@pytest.fixture
def temp_backup_dir():
    """Create a temporary backup directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mongodb_config():
    """Create a MongoDB configuration for tests."""
    return MongoDBConfig(
        host="localhost",
        port=27017,
        database="testdb"
    )


@pytest.fixture
def postgresql_config():
    """Create a PostgreSQL configuration for tests."""
    return PostgreSQLConfig(
        host="localhost",
        port=5432,
        database="testdb",
        username="testuser",
        password="testpass"
    )


@pytest.fixture
def backup_config(temp_backup_dir):
    """Create a backup configuration for tests."""
    return BackupConfig(
        backup_dir=temp_backup_dir,
        retention_days=7
    )


@pytest.fixture
def successful_backup_result():
    """Create a successful backup result for tests."""
    return BackupResult(
        backup_id="test_123",
        database_type="mongodb",
        database_name="testdb",
        status=BackupStatus.SUCCESS,
        start_time=datetime.now(),
        end_time=datetime.now(),
        backup_file_path="/tmp/backup.tar.gz",
        backup_size_bytes=1024
    )


@pytest.fixture
def failed_backup_result():
    """Create a failed backup result for tests."""
    return BackupResult(
        backup_id="test_456",
        database_type="postgresql",
        database_name="testdb",
        status=BackupStatus.FAILED,
        start_time=datetime.now(),
        end_time=datetime.now(),
        error_message="Connection failed"
    )


@pytest.fixture
def mock_environment():
    """Set up mock environment variables for tests."""
    env_vars = {
        'BACKUP_DIR': '/tmp/test_backups',
        'RETENTION_DAYS': '7',
        'COMPRESSION': 'true',
        'LOG_LEVEL': 'DEBUG',
        'VERBOSE': 'false'
    }
    
    # Store original values
    original_values = {}
    for key, value in env_vars.items():
        original_values[key] = os.environ.get(key)
        os.environ[key] = value
    
    yield env_vars
    
    # Restore original values
    for key, original_value in original_values.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


@pytest.fixture
def mock_ftp_config():
    """Create mock FTP configuration for tests."""
    return {
        'FTP_HOST': 'ftp.example.com',
        'FTP_PORT': '21',
        'FTP_USERNAME': 'testuser',
        'FTP_PASSWORD': 'testpass',
        'FTP_REMOTE_DIR': '/backup',
        'FTP_SSL': 'false'
    }


@pytest.fixture
def mock_telegram_config():
    """Create mock Telegram configuration for tests."""
    return {
        'TELEGRAM_BOT_TOKEN': '123456789:ABCdefGHIjklMNOpqrsTUVwxyz',
        'TELEGRAM_CHAT_ID': '-1001234567890',
        'TELEGRAM_ENABLED': 'true'
    }


@pytest.fixture
def sample_backup_files(temp_backup_dir):
    """Create sample backup files for tests."""
    backup_dir = Path(temp_backup_dir)
    backup_dir.mkdir(exist_ok=True)
    
    # Create sample backup files
    files = [
        "backup_mongodb_testdb_2023-01-01-12-00-00.tar.gz",
        "backup_mongodb_testdb_2023-01-02-12-00-00.tar.gz",
        "backup_postgresql_testdb_2023-01-01-12-00-00.tar.gz"
    ]
    
    for filename in files:
        file_path = backup_dir / filename
        file_path.touch()
        # Set file modification time to different dates
        if "2023-01-01" in filename:
            file_path.touch()
        elif "2023-01-02" in filename:
            file_path.touch()
    
    return files


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment before each test."""
    # Ensure we're in a clean state
    os.environ.setdefault('LOG_LEVEL', 'DEBUG')
    os.environ.setdefault('VERBOSE', 'false')
    
    yield
    
    # Cleanup after each test
    pass


@pytest.fixture
def mock_subprocess_success():
    """Mock subprocess.run for successful operations."""
    with pytest.MonkeyPatch().context() as m:
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Success"
        mock_result.stderr = ""
        m.setattr('subprocess.run', Mock(return_value=mock_result))
        yield mock_result


@pytest.fixture
def mock_subprocess_failure():
    """Mock subprocess.run for failed operations."""
    with pytest.MonkeyPatch().context() as m:
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Command failed"
        m.setattr('subprocess.run', Mock(return_value=mock_result))
        yield mock_result


# Pytest configuration
def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers."""
    for item in items:
        # Add unit marker to all tests by default
        item.add_marker(pytest.mark.unit)
        
        # Add slow marker to tests that take longer
        if "test_backup" in item.name or "test_ftp" in item.name:
            item.add_marker(pytest.mark.slow)
        
        # Add integration marker to tests that require external services
        if "test_ftp" in item.name or "test_telegram" in item.name:
            item.add_marker(pytest.mark.integration)

