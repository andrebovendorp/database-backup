# Database Backup System

A comprehensive Python-based database backup solution supporting MongoDB and PostgreSQL with FTP upload, Telegram notifications, and Kubernetes deployment.

## 🚀 Features

- **Multi-Database Support**: MongoDB and PostgreSQL
- **MVC Architecture**: Clean separation of concerns
- **FTP Upload**: Automatic backup upload to FTP servers
- **Telegram Notifications**: Real-time backup status notifications
- **Retention Management**: Automatic cleanup of old backups
- **Comprehensive Logging**: Detailed logging with debug support
- **Unit Tests**: Full test coverage for all components
- **CLI Interface**: Easy-to-use command-line interface
- **Kubernetes Ready**: Complete K8s manifests with CronJob
- **Docker Support**: Multi-architecture Docker images
- **Executable Builds**: Standalone executables for all platforms
- **Configuration-Driven**: YAML-based database configuration

## 📦 Installation

### Option 1: Python Package
```bash

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

### 1. Configure Your Databases
```bash
# Copy example configuration
cp config.yaml.example config.yaml
# Edit config.yaml with your databases
```

### 2. Test Configuration
```bash
python3 main.py --test
```

### 3. Run Backups
```bash
# Backup all databases
python3 main.py --backup-all

# Backup specific database
python3 main.py --backup postgresql_database

# Generate report
python3 main.py --report backup_report.txt
```

## 📋 Command Line Interface

```bash
# Backup operations
python3 main.py --backup-all                    # Backup all databases
python3 main.py --backup <controller-id>        # Backup specific database

# File management
python3 main.py --list-files                   # List backup files
python3 main.py --cleanup                      # Clean old backups

# Reporting
python3 main.py --report                       # Generate report to console
python3 main.py --report report.txt           # Generate report to file

# Testing and debugging
python3 main.py --test                         # Test all connections
python3 main.py --verbose --backup-all        # Verbose output
```

## 🏗️ Architecture

### MVC Pattern
- **Models**: Database configurations, backup results, and data structures
- **Views**: Output formatting, reporting, and user interface
- **Controllers**: Business logic for backup operations

### Components
- **BackupManager**: Orchestrates backup operations
- **Database Controllers**: MongoDB and PostgreSQL specific backup logic
- **FTP Service**: File upload and management
- **Telegram Service**: Notification system
- **View Classes**: Output formatting and reporting

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

1. **Database Connection Failed**
   - Check database credentials and connectivity
   - Verify database is running and accessible
   - Test with `python3 main.py --test`

2. **FTP Upload Failed**
   - Verify FTP credentials and server accessibility
   - Check firewall and network connectivity
   - Test FTP connection manually

3. **Telegram Notifications Not Working**
   - Verify bot token and chat ID
   - Ensure bot is added to the chat
   - Check network connectivity to Telegram API

4. **Kubernetes Deployment Issues**
   - Check External Secrets status: `kubectl get externalsecret`
   - Verify network policies: `kubectl get networkpolicy`
   - Check pod logs: `kubectl logs -n database-backup -l app=database-backup`

### Debug Mode
```bash
# Verbose debugging
python3 main.py --verbose --test

# Check logs
tail -f backup.log
```

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

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

- **Documentation**: See this README for comprehensive guides
- **Issues**: Report bugs and feature requests on GitHub
- **Discussions**: Join community discussions for help
- **Security**: Report security issues privately

---

**Database Backup System** - Reliable, scalable, and secure database backup solution for modern infrastructure.