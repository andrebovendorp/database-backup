# Database Backup System

A comprehensive Python-based database backup solution supporting MongoDB and PostgreSQL with FTP upload, Telegram notifications, and Kubernetes deployment.

## 🚀 Features

- **Multi-Database Support**: MongoDB and PostgreSQL with full backup/restore capabilities
- **Cross-Platform Compatibility**: Windows, Linux, and macOS support with platform-specific optimizations
- **Windows-Optimized**: Automatic database tool detection, improved tempfile handling, and native compression
- **MVC Architecture**: Clean separation of concerns with extensible controller pattern
- **FTP Upload**: Automatic backup upload to FTP servers with SSL support
- **Telegram Notifications**: Real-time backup status notifications with detailed reporting
- **Retention Management**: Automatic cleanup of old backups with configurable retention policies
- **Comprehensive Logging**: Detailed logging with debug support and file rotation
- **Unit Tests**: Full test coverage for all components and error scenarios
- **CLI Interface**: Easy-to-use command-line interface with comprehensive options
- **Kubernetes Ready**: Complete K8s manifests with CronJob and security policies
- **Docker Support**: Multi-architecture Docker images (AMD64/ARM64)
- **Executable Builds**: Standalone executables for all platforms
- **Configuration-Driven**: YAML-based database configuration with environment variable fallback
- **Smart Tool Detection**: Automatic detection of database tools in common installation paths
- **Robust Error Handling**: Graceful failure handling with detailed error reporting

## 🆕 Recent Improvements

### Windows Compatibility Enhancements (v2.1.0)
- **Fixed Tempfile Issues**: Resolved Windows file locking problems by replacing `tempfile.NamedTemporaryFile` with `tempfile.TemporaryDirectory()`
- **Native Compression**: Implemented `shutil.make_archive()` for Windows-compatible compression with tar command fallback
- **Smart Tool Detection**: Added automatic detection of PostgreSQL and MongoDB tools in common Windows installation paths:
  - `C:\Program Files\PostgreSQL\*\bin`
  - `C:\Program Files (x86)\PostgreSQL\*\bin`
  - `C:\Program Files\MongoDB\Server\*\bin`
- **Enhanced Error Messages**: Added Windows-specific installation guidance and troubleshooting
- **Improved Path Handling**: Proper Windows path separator handling throughout the system
### Cross-Platform Archive Extraction**: Added `shutil.unpack_archive()` for restore operations with tar fallback

### Technical Implementation Details
- **Tempfile Strategy**: Replaced `tempfile.NamedTemporaryFile(delete=False)` with `tempfile.TemporaryDirectory()` to avoid Windows file locking issues
- **Archive Creation**: Primary method uses `shutil.make_archive()` with automatic fallback to system `tar` command
- **Tool Discovery**: Implements glob-based search in common installation directories with intelligent path detection
- **Error Handling**: Provides platform-specific installation guidance and detailed error context
- **Logging**: Enhanced logging shows detected tool paths and platform-specific information

## 📦 Installation

### Prerequisites

**Database Tools Required:**

**For PostgreSQL backups:**
- **Windows**: Install PostgreSQL from https://www.postgresql.org/download/windows/ (includes pg_dump/psql)
- **Linux**: `sudo apt-get install postgresql-client` or `sudo yum install postgresql`
- **macOS**: `brew install postgresql`

**For MongoDB backups:**
- **All Platforms**: Install MongoDB Database Tools from https://www.mongodb.com/docs/database-tools/
- The system will automatically detect tools in common installation paths

### Option 1: Python Package
```bash
# Clone repository
git clone https://github.com/your-username/database-backup.git
cd database-backup

# Install dependencies
pip install -r requirements.txt
```

### Option 2: Docker
```bash
# Pull from GitHub Container Registry
docker pull ghcr.io/your-username/database-backup:latest

# Or build locally
docker build -t database-backup:latest .
```

### Option 3: Executable
Download pre-built executables from [GitHub Releases](https://github.com/your-username/database-backup/releases).

### Option 4: Kubernetes
```bash
# Deploy using GitHub Container Registry
kubectl apply -k k8s/
```

## ⚙️ Configuration

### YAML Configuration (Recommended)

Create `config.yaml`:
```yaml
# PostgreSQL Databases
pgsql:
  - host: localhost
    port: 5432
    database: database
    username: myusername
    password: mysecretpassword
  - host: localhost
    port: 5432
    database: testdb
    username: testuser
    password: testpass

# MongoDB Databases  
mongodb:
  - host: localhost
    port: 27017
    database: database
    uri: mongodb://localhost:27017/database
  - host: localhost
    port: 27017
    database: testdb
    uri: mongodb://localhost:27017/testdb

# FTP Configuration (optional)
ftp:
  host: storage.nullservers.com
  port: 21
  username: kube
  password: your_ftp_password
  remote_dir: /backup/mongodb-cron
  ssl: false

# Telegram Configuration (optional)
telegram:
  bot_token: your_bot_token
  chat_id: your_chat_id
  enabled: true

# Backup Configuration
backup:
  directory: ./backups
  retention_days: 7
  compression: true
  log_level: INFO
  verbose: false
```

### Environment Variables

Copy `env.example` to `.env` and configure:

```bash
# Backup Configuration
BACKUP_DIR=./backups
RETENTION_DAYS=7
COMPRESSION=true
LOG_LEVEL=INFO
VERBOSE=false

# FTP Configuration (optional)
FTP_HOST=storage.nullservers.com
FTP_PORT=21
FTP_USERNAME=kube
FTP_PASSWORD=your_ftp_password
FTP_REMOTE_DIR=/backup/mongodb-cron
FTP_SSL=false

# Telegram Configuration (optional)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
TELEGRAM_ENABLED=true
```

## 🎯 Quick Start

### 1. Install Database Tools (if not already installed)

**Windows:**
```powershell
# Install PostgreSQL (includes pg_dump, psql)
# Download from: https://www.postgresql.org/download/windows/
# Or use chocolatey:
choco install postgresql

# Install MongoDB Database Tools
# Download from: https://www.mongodb.com/docs/database-tools/
```

**Linux:**
```bash
# Ubuntu/Debian
sudo apt-get install postgresql-client mongodb-database-tools

# CentOS/RHEL
sudo yum install postgresql mongodb-database-tools
```

**macOS:**
```bash
# Using Homebrew
brew install postgresql mongodb/brew/mongodb-database-tools
```

### 2. Configure Your Databases
```bash
# Linux/macOS
cp config.yaml.example config.yaml

# Windows PowerShell
Copy-Item config.yaml.example config.yaml

# Edit config.yaml with your databases (use any text editor)
```

### 3. Test Configuration
```bash
# Test database connections and tool availability
python main.py --test

# Verbose testing to see tool detection
python main.py --verbose --test
```

### 4. Run Backups
```bash
# Backup all databases
python main.py --backup

# List backup files
python main.py --list-files

# Generate report
python main.py --report backup_report.txt

# Clean old backups
python main.py --cleanup
```

## 📋 Command Line Interface

```bash
# Backup operations
python main.py --backup                        # Backup all configured databases
python main.py --config custom.yaml --backup  # Use custom configuration file

# File management
python main.py --list-files                    # List all backup files
python main.py --list-files postgresql_db      # List files for specific database
python main.py --cleanup                       # Clean old backups based on retention policy

# Reporting and monitoring
python main.py --report                        # Generate report to console
python main.py --report report.txt            # Generate report to file

# Testing and debugging
python main.py --test                          # Test all connections (DB, FTP, Telegram)
python main.py --verbose --backup             # Verbose output showing tool detection
python main.py --verbose --test               # Verbose testing with detailed info

# Configuration options
python main.py --config production.yaml --backup  # Use specific config file
python main.py --verbose --backup                 # Enable verbose logging
```

### Command Line Arguments

| Argument | Description | Example |
|----------|-------------|---------|
| `--config FILE` | Specify configuration file | `--config production.yaml` |
| `--verbose, -v` | Enable verbose output | `--verbose` |
| `--backup` | Backup all databases | `--backup` |
| `--list-files [ID]` | List backup files | `--list-files postgresql_db` |
| `--cleanup` | Clean old backups | `--cleanup` |
| `--report [FILE]` | Generate report | `--report backup_summary.txt` |
| `--test` | Test all connections | `--test` |

## 🏗️ Architecture

### MVC Pattern
- **Models**: Database configurations, backup results, and data structures
- **Views**: Output formatting, reporting, and user interface  
- **Controllers**: Business logic for backup operations with platform-specific optimizations

### Components
- **BackupManager**: Orchestrates backup operations across multiple databases
- **Database Controllers**: MongoDB and PostgreSQL specific backup logic with Windows compatibility
  - **BaseController**: Common functionality with smart tool detection
  - **PostgreSQLController**: pg_dump integration with Windows path detection
  - **MongoDBController**: mongodump integration with cross-platform support
- **FTP Service**: File upload and management with SSL support
- **Telegram Service**: Notification system with comprehensive status reporting
- **View Classes**: Output formatting and reporting with cross-platform console support

### Windows Compatibility Features
- **Smart Tool Detection**: Automatically finds database tools in common Windows paths
- **Tempfile Optimization**: Uses `tempfile.TemporaryDirectory()` for Windows file locking compatibility
- **Native Compression**: Uses `shutil.make_archive()` with tar fallback for reliable compression
- **Path Handling**: Proper Windows path separator handling throughout the system
- **Error Messages**: Windows-specific installation guidance and troubleshooting

## 🐳 Docker Deployment

### Run with Docker
```bash
# Run with environment variables
docker run -e FTP_HOST=storage.example.com \
           -e FTP_USERNAME=backup \
           -e FTP_PASSWORD=secret \
           -v $(pwd)/backups:/app/backups \
           database-backup:latest --backup-all
```

### Docker Compose
```yaml
version: '3.8'
services:
  database-backup:
    image: ghcr.io/your-username/database-backup:latest
    environment:
      - FTP_HOST=storage.example.com
      - FTP_USERNAME=backup
      - FTP_PASSWORD=secret
    volumes:
      - ./backups:/app/backups
      - ./config.yaml:/app/config.yaml
    command: ["--backup-all"]
```

## ☸️ Kubernetes Deployment

### Deploy to Kubernetes
```bash
# Apply all manifests
kubectl apply -k k8s/

# Check deployment status
kubectl get all -n database-backup

# Check logs
kubectl logs -n database-backup -l app=database-backup -f
```

### Kubernetes Features
- **CronJob**: Scheduled daily backups at 2 AM
- **External Secrets**: Secure credential management
- **Network Policies**: Cilium CNP for secure communication
- **Persistent Storage**: Backup file retention
- **Resource Limits**: CPU and memory constraints

### Configuration Files
- `k8s/namespace.yaml` - Namespace definition
- `k8s/configmap.yaml` - Application configuration
- `k8s/external-secret.yaml` - External Secrets Operator
- `k8s/cronjob.yaml` - Scheduled backup job
- `k8s/network-policy.yaml` - Network security
- `k8s/rbac.yaml` - Service account and permissions

## 🔧 Building from Source

### Build Executable
```bash
# Using PyInstaller
pip install pyinstaller
pyinstaller --onefile --name=database-backup main.py

# Using Nuitka (faster)
pip install nuitka
python -m nuitka --onefile --standalone main.py
```

### Build Docker Image
```bash
# Build multi-architecture image
docker buildx build --platform linux/amd64,linux/arm64 -t database-backup:latest .
```

### GitHub Actions
The repository includes GitHub Actions workflows for:
- **Multi-platform builds**: Linux, Windows, macOS
- **Docker image builds**: AMD64 + ARM64
- **Automatic releases**: With downloadable executables
- **Security scanning**: Trivy vulnerability scanning
- **GitHub Container Registry**: Automatic image publishing
- **GitHub Releases**: Binary artifacts for all platforms

## 🧪 Testing

### Run Test Suite
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test modules
python run_tests.py models
python run_tests.py controllers
python run_tests.py services
```

### Test Configuration
```bash
# Test database connections
python3 main.py --test

# Test with verbose output
python3 main.py --verbose --test
```

## 📊 Monitoring and Logging

### Logging
- **Console Output**: Real-time status updates
- **File Logging**: Detailed logs saved to `backup.log`
- **Debug Mode**: Use `--verbose` for detailed debugging information

### Telegram Notifications
Get real-time updates on:
- **Backup Start**: When backups begin
- **Backup Completion**: Success/failure status
- **FTP Upload**: Upload confirmation
- **Errors**: Immediate error notifications
- **Summary Reports**: Periodic backup summaries

### Error Handling
- **Graceful Failures**: Individual database failures don't stop other backups
- **Detailed Error Messages**: Clear error reporting with context
- **Telegram Notifications**: Error alerts sent to configured chat
- **Logging**: All errors logged with full stack traces

## 🔒 Security

### Network Policies
The system includes Cilium Network Policies for secure communication:
- **PostgreSQL**: Access to `pgsql` namespace
- **MongoDB**: Access to `mongodb.nullservers.com`
- **FTP**: Access to `storage.nullservers.com`
- **Telegram**: Access to `api.telegram.org`
- **DNS**: Required for service discovery

### External Secrets
- **Vault Integration**: Secure credential storage
- **AWS Secrets Manager**: Cloud-native secret management
- **Kubernetes Secrets**: Automatic secret injection

## 📈 Performance

### Resource Management
- **CPU Limits**: Configurable CPU constraints
- **Memory Limits**: Memory usage optimization
- **Concurrent Backups**: Parallel database processing
- **Compression**: Efficient backup file compression

### Scalability
- **Multiple Databases**: Support for many database instances
- **Horizontal Scaling**: Kubernetes-based scaling
- **Load Balancing**: Distributed backup processing

## 🚨 Troubleshooting

### Common Issues

1. **Database Tools Not Found (Windows)**
   ```
   Error: Command 'pg_dump' not found. Please ensure it's installed and in your PATH.
   ```
   **Solutions:**
   - Install PostgreSQL from https://www.postgresql.org/download/windows/
   - The system automatically searches common paths: `C:\Program Files\PostgreSQL\*\bin`
   - Add PostgreSQL bin directory to your system PATH
   - Verify installation: `where pg_dump.exe`

2. **Tempfile Issues (Windows)**
   - **Fixed in latest version**: Now uses `tempfile.TemporaryDirectory()` for Windows compatibility
   - Uses `shutil.make_archive()` instead of tar command for better Windows support
   - Automatic fallback to tar command if shutil fails

3. **Database Connection Failed**
   - Check database credentials and connectivity
   - Verify database is running and accessible
   - Test with `python main.py --test`
   - Check firewall settings and network connectivity

4. **FTP Upload Failed**
   - Verify FTP credentials and server accessibility
   - Check firewall and network connectivity
   - Test FTP connection manually
   - Enable SSL if required: `ssl: true` in config

5. **Telegram Notifications Not Working**
   - Verify bot token and chat ID
   - Ensure bot is added to the chat
   - Check network connectivity to Telegram API
   - Test with `python main.py --test`

6. **Backup Archive Creation Failed**
   - **Windows**: Ensure sufficient disk space in temp directory
   - **All Platforms**: Check backup directory permissions
   - **Linux/macOS**: Ensure tar command is available

7. **Kubernetes Deployment Issues**
   - Check External Secrets status: `kubectl get externalsecret`
   - Verify network policies: `kubectl get networkpolicy`
   - Check pod logs: `kubectl logs -n database-backup -l app=database-backup`

### Debug Mode
```bash
# Verbose debugging
python main.py --verbose --test

# Check logs (Linux/macOS)
tail -f backup.log

# Check logs (Windows PowerShell)
Get-Content backup.log -Wait

# Test database tool detection
python main.py --verbose --backup  # Shows tool paths found
```

### Platform-Specific Notes

**Windows:**
- Database tools are automatically detected in common installation paths
- Uses native Python compression (shutil) instead of tar command
- Supports both PowerShell and Command Prompt
- Temporary files handled with Windows-compatible methods

**Linux/macOS:**
- Standard tar command used for compression with shutil fallback
- Follows Unix conventions for temporary file handling
- Standard package manager installation supported

## 📚 Examples

### Basic Usage
```bash
# Configure databases in config.yaml
python3 main.py --backup-all
```

### Advanced Usage
```bash
# With custom configuration
python3 main.py --config production.yaml --backup-all

# With cleanup and reporting
python3 main.py --backup-all --cleanup --report daily_report.txt
```

### Programmatic Usage
```python
from main import DatabaseBackupApp

# Initialize app
app = DatabaseBackupApp()

# Load databases from config
app.load_databases_from_config()

# Perform backups
results = app.backup_all_databases()

# Generate report
app.generate_report('backup_report.txt')
```

## 🤝 Contributing

1. Follow the MVC architecture pattern
2. Add unit tests for new features
3. Update documentation for new functionality
4. Ensure backward compatibility
5. Test with multiple database types

## � Changelog

### Version 2.1.0 (Latest) - Windows Compatibility Release
- **🔧 Fixed**: Windows tempfile handling issues with `tempfile.TemporaryDirectory()`
- **🔧 Fixed**: Archive creation using `shutil.make_archive()` with tar fallback
- **✨ Added**: Automatic database tool detection in Windows installation paths
- **✨ Added**: Enhanced error messages with Windows-specific installation guidance
- **✨ Added**: Cross-platform archive extraction with `shutil.unpack_archive()`
- **🐛 Fixed**: Path separator handling across different operating systems
- **📚 Improved**: Documentation with Windows-specific troubleshooting and setup instructions

### Version 2.0.0 - Major Architecture Update
- **✨ Added**: MVC architecture implementation
- **✨ Added**: Multi-database configuration support
- **✨ Added**: Kubernetes deployment manifests
- **✨ Added**: Docker multi-architecture builds
- **✨ Added**: Comprehensive test suite
- **✨ Added**: Advanced CLI interface

### Version 1.0.0 - Initial Release
- **✨ Added**: Basic PostgreSQL and MongoDB backup support
- **✨ Added**: FTP upload functionality
- **✨ Added**: Telegram notifications
- **✨ Added**: Basic retention management

## �📄 License

This project is licensed under the MIT License.

## 🆘 Support

- **Documentation**: See this README for comprehensive guides
- **Issues**: Report bugs and feature requests on GitHub
- **Discussions**: Join community discussions for help
- **Security**: Report security issues privately

---

**Database Backup System** - Reliable, scalable, and secure database backup solution for modern infrastructure.