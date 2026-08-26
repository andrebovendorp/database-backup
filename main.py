"""
Main application entry point for database backup system.

A comprehensive, cross-platform database backup solution with Windows-optimized
tempfile handling, smart tool detection, and native compression support.

Features:
- Multi-database support (PostgreSQL, MongoDB)
- Cross-platform compatibility (Windows, Linux, macOS)
- Automatic database tool detection
- Windows-compatible tempfile and compression handling
- FTP upload with SSL support
- Telegram notifications
- Retention management and cleanup
- Comprehensive error handling and logging
"""
import os
import sys
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from models.database_config import (
    MongoDBConfig, PostgreSQLConfig, MySQLConfig, BackupConfig,
    TelegramConfig
)
from controllers.backup_manager import BackupManager
from config_loader import ConfigLoader
from services.target_factory import create_backup_target

try:
    from services.telegram_service import TelegramService
except ImportError:
    TelegramService = None
from views.backup_view import BackupView, BackupReportView


class DatabaseBackupApp:
    """Main application class for database backup system."""
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize the application."""
        self.config_file = config_file
        self.setup_logging()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Load configuration
        self.load_config(config_file)
        
        # Initialize components
        self.backup_manager = BackupManager(self.backup_config)
        self.backup_targets = []
        self.telegram_service = TelegramService(self.telegram_config) if (self.telegram_config and TelegramService) else None
        self.view = BackupView(verbose=self.verbose)
        self.report_view = BackupReportView()
        
        self.logger.info("Database backup application initialized")
    
    def load_databases_from_config(self):
        """Load databases from configuration file or environment variables."""
        try:
            config_loader = ConfigLoader(self.config_file)
            database_configs = config_loader.create_database_configs()
            
            for config, controller_id in database_configs:
                self.backup_manager.add_database(config, controller_id)
                self.logger.info(f"Loaded database: {controller_id}")
            
            if database_configs:
                self.logger.info(f"Loaded {len(database_configs)} databases from configuration")
            else:
                self.logger.warning("No databases found in configuration")
                
        except Exception as e:
            self.logger.error(f"Failed to load databases from configuration: {e}")
            raise
    
    def load_services_from_config(self):
        """Load backup targets and Telegram service from configuration file."""
        try:
            config_loader = ConfigLoader(self.config_file)
            
            # Load all configured targets from YAML.
            target_configs = config_loader.load_target_configs()
            if not target_configs:
                self.logger.warning("No backup targets configured in %s", self.config_file)
                raise ValueError("At least one backup target must be configured in the YAML file")

            self.backup_targets = [create_backup_target(config) for config in target_configs]
            for target_config in target_configs:
                self.logger.info("Loaded %s backup target from YAML", target_config.get('type', 'unknown'))
            
            # Load Telegram configuration
            telegram_config_data = config_loader.load_telegram_config()
            if telegram_config_data and telegram_config_data.get('enabled', False):
                from models.database_config import TelegramConfig
                telegram_config = TelegramConfig(
                    bot_token=telegram_config_data.get('bot_token', ''),
                    chat_id=telegram_config_data.get('chat_id', ''),
                    enabled=telegram_config_data.get('enabled', False)
                )
                self.telegram_config = telegram_config
                self.telegram_service = TelegramService(telegram_config) if TelegramService else None
                self.logger.info("Loaded Telegram configuration from YAML")
            
            # Load backup configuration
            backup_config_data = config_loader.load_backup_config()
            if backup_config_data:
                from models.database_config import BackupConfig
                backup_config = BackupConfig(
                    backup_dir=backup_config_data.get('directory', './backups'),
                    retention_days=backup_config_data.get('retention_days', 7),
                    compression=backup_config_data.get('compression', True)
                )
                self.backup_config = backup_config
                self.logger.info("Loaded backup configuration from YAML")
                
        except Exception as e:
            self.logger.error(f"Failed to load services from configuration: {e}")
            raise
    
    def setup_logging(self):
        """Setup logging configuration."""
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        logging.basicConfig(
            level=getattr(logging, log_level),
            format=log_format,
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('logs/backup.log')
            ]
        )
    
    def load_config(self, config_file: Optional[str] = None):
        """Load configuration from environment variables and config file."""
        # Backup configuration
        self.backup_config = BackupConfig(
            backup_dir=os.getenv('BACKUP_DIR', './backups'),
            retention_days=int(os.getenv('RETENTION_DAYS', '7')),
            compression=os.getenv('COMPRESSION', 'true').lower() == 'true'
        )
        
        # Telegram configuration
        telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if telegram_token:
            self.telegram_config = TelegramConfig(
                bot_token=telegram_token,
                chat_id=os.getenv('TELEGRAM_CHAT_ID', ''),
                enabled=os.getenv('TELEGRAM_ENABLED', 'true').lower() == 'true'
            )
        else:
            self.telegram_config = None
        
        # Application settings
        self.verbose = os.getenv('VERBOSE', 'false').lower() == 'true'

    def add_mongodb_database(self, host: str, port: int, database: str,
                             username: str = None, password: str = None,
                             uri: str = None) -> str:
        """Add a MongoDB database controller."""
        config = MongoDBConfig(
            host=host,
            port=port,
            database=database,
            username=username,
            password=password,
            uri=uri
        )
        return self.backup_manager.add_database(config)

    def add_postgresql_database(self, host: str, port: int, database: str,
                                username: str = None, password: str = None) -> str:
        """Add a PostgreSQL database controller."""
        config = PostgreSQLConfig(
            host=host,
            port=port,
            database=database,
            username=username,
            password=password
        )
        return self.backup_manager.add_database(config)

    def add_mysql_database(self, host: str, port: int, database: str,
                           username: str = None, password: str = None) -> str:
        """Add a MySQL database controller."""
        config = MySQLConfig(
            host=host,
            port=port,
            database=database,
            username=username,
            password=password
        )
        return self.backup_manager.add_database(config)
    
    
    def backup_database(self, controller_id: str) -> bool:
        """Backup a specific database."""
        try:
            self.view.display_backup_started(
                self.backup_manager.controllers[controller_id].db_config.database,
                self.backup_manager.controllers[controller_id].db_config.db_type.value
            )
            
            # Notify Telegram
            if self.telegram_service:
                self.telegram_service.notify_backup_started(
                    self.backup_manager.controllers[controller_id].db_config.database,
                    self.backup_manager.controllers[controller_id].db_config.db_type.value
                )
            
            # Perform backup
            result = self.backup_manager.backup_database(controller_id)
            
            # Display result
            self.view.display_backup_result(result)
            
            # Upload to every configured backup target.
            if result.is_successful and result.backup_file_path and self.backup_targets:
                self.upload_to_targets(result.backup_file_path)
            
            # Notify Telegram
            if self.telegram_service:
                self.telegram_service.notify_backup_completed(result)
            
            return result.is_successful
            
        except Exception as e:
            self.view.display_error(str(e), f"Backing up {controller_id}")
            if self.telegram_service:
                self.telegram_service.notify_error(str(e), f"Backing up {controller_id}")
            return False
    
    def backup_all_databases(self) -> List[bool]:
        """Backup all managed databases."""
        results = []
        
        for controller_id in self.backup_manager.controllers:
            success = self.backup_database(controller_id)
            results.append(success)
        
        # Display summary
        summary = self.backup_manager.get_backup_summary()
        self.view.display_backup_summary(summary)
        
        # Notify Telegram
        if self.telegram_service:
            self.telegram_service.notify_backup_summary(summary)
        
        return results
    
    def upload_to_targets(self, file_path: str) -> bool:
        """Upload a backup to every configured target."""
        targets = list(dict.fromkeys(self.backup_targets))
        if not targets:
            self.view.display_warning("No backup targets configured")
            return False

        results = []
        for target in targets:
            try:
                with target:
                    success = target.upload_file(file_path)
                results.append(success)
                target_name = target.__class__.__name__.replace('Service', '')
                self.view.display_target_upload(Path(file_path).name, target_name, success)
                if self.telegram_service:
                    self.telegram_service.notify_target_upload(Path(file_path).name, target_name, success)
            except Exception as e:
                self.view.display_error(str(e), "Backup target upload")
                results.append(False)
        return all(results)
    
    def cleanup_old_backups(self):
        """Clean up old backup files."""
        try:
            cleanup_results = self.backup_manager.cleanup_all_backups()
            self.view.display_cleanup_results(cleanup_results)
            
            # Calculate total deleted files and size
            total_deleted = sum(len(files) for files in cleanup_results.values())
            
            if self.telegram_service and total_deleted > 0:
                self.telegram_service.notify_cleanup(total_deleted, 0)  # Size calculation would need file stats
            
        except Exception as e:
            self.view.display_error(str(e), "Cleanup")
    
    def list_backup_files(self, controller_id: Optional[str] = None):
        """List backup files."""
        try:
            files = self.backup_manager.list_backup_files(controller_id)
            self.view.display_backup_files(files, controller_id)
        except Exception as e:
            self.view.display_error(str(e), "Listing backup files")
    
    def generate_report(self, output_file: str = None):
        """Generate backup report."""
        try:
            summary = self.backup_manager.get_backup_summary()
            results = self.backup_manager.backup_history
            
            report = self.report_view.generate_text_report(summary, results)
            
            if output_file:
                if self.report_view.save_report(report, output_file):
                    self.view.display_info(f"Report saved to: {output_file}")
                else:
                    self.view.display_error("Failed to save report")
            else:
                print(report)
                
        except Exception as e:
            self.view.display_error(str(e), "Generating report")
    
    def restore_database(self, backup_file_path: str, controller_id: str, target_database: str = None) -> bool:
        """Restore database from backup file to target database."""
        try:
            if controller_id not in self.backup_manager.controllers:
                self.view.display_error(f"Controller '{controller_id}' not found")
                return False
            
            controller = self.backup_manager.controllers[controller_id]
            
            # If target database is specified, temporarily modify the controller's database config
            original_database = None
            if target_database:
                original_database = controller.db_config.database
                controller.db_config.database = target_database
                self.view.display_info(f"Restoring to target database: {target_database}")
            else:
                self.view.display_info(f"Restoring to original database: {controller.db_config.database}")
            
            # Notify start
            if self.telegram_service:
                db_name = target_database or controller.db_config.database
                self.telegram_service.notify_backup_started(db_name, "restore")
            
            # Perform restore
            self.view.display_info(f"Starting restore from: {backup_file_path}")
            success = controller.restore_backup(backup_file_path)
            
            if success:
                self.view.display_info("✅ Restore completed successfully!")
            else:
                self.view.display_error("❌ Restore failed!")
            
            # Notify completion
            if self.telegram_service:
                db_name = target_database or controller.db_config.database
                if success:
                    self.telegram_service.notify_backup_completed(None)  # Could create a restore result object
                else:
                    self.telegram_service.notify_error("Restore operation failed", f"Restoring to {db_name}")
            
            # Restore original database config if it was changed
            if original_database is not None:
                controller.db_config.database = original_database
            
            return success
            
        except Exception as e:
            self.view.display_error(str(e), "Database restore")
            return False
    
    def list_controllers(self):
        """List all available controller IDs."""
        if not self.backup_manager.controllers:
            self.view.display_warning("No controllers configured")
            return
        
        self.view.display_info("Available Controller IDs:")
        for controller_id, controller in self.backup_manager.controllers.items():
            db_config = controller.db_config
            self.view.display_info(f"  • {controller_id}")
            self.view.display_info(f"    Type: {db_config.db_type.value}")
            self.view.display_info(f"    Host: {db_config.host}")
            self.view.display_info(f"    Database: {db_config.database}")
            self.view.display_info("")
    
    def test_connections(self):
        """Test all configured connections."""
        self.view.display_info("Testing connections...")
        
        # Test database connections
        if hasattr(self, 'backup_manager') and self.backup_manager.controllers:
            for controller_id, controller in self.backup_manager.controllers.items():
                try:
                    self.view.display_info(f"Testing {controller.db_config.db_type.value} connection: {controller.db_config.database}")
                    if controller.test_connection():
                        self.view.display_info(f"Database {controller_id} ({controller.db_config.database}): OK")
                    else:
                        self.view.display_error(f"Database {controller_id} ({controller.db_config.database}): FAILED")
                except Exception as e:
                    self.view.display_error(f"Database {controller_id} connection test failed: {e}")
        else:
            self.view.display_warning("No databases configured")
        
        # Test every configured backup target.
        if self.backup_targets:
            for target in self.backup_targets:
                target_name = target.__class__.__name__.replace('Service', '')
                try:
                    with target:
                        self.view.display_info(f"{target_name} connection: OK")
                except Exception as e:
                    self.view.display_error(f"{target_name} connection failed: {e}")
        else:
            self.view.display_warning("No backup targets configured")
        
        # Test Telegram
        if self.telegram_service:
            if self.telegram_service.test_connection():
                self.view.display_info("Telegram connection: OK")
            else:
                self.view.display_error("Telegram connection failed")
        else:
            self.view.display_warning("Telegram not configured")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Database Backup System')
    parser.add_argument('--config', default='config.yaml',
                       help='Configuration file path (default: config.yaml)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--backup-all', action='store_true', help='Backup all databases')
    parser.add_argument('--backup', help='Backup specific database controller ID')
    parser.add_argument('--list-files', help='List backup files for controller ID')
    parser.add_argument('--cleanup', action='store_true', help='Clean up old backups')
    parser.add_argument('--report', help='Generate report (optional output file)')
    parser.add_argument('--test', action='store_true', help='Test connections')
    parser.add_argument('--list-controllers', action='store_true', help='List all available controller IDs')
    parser.add_argument('--restore', help='Restore from backup file path')
    parser.add_argument('--target-controller', help='Target controller ID for restore (required with --restore)')
    parser.add_argument('--target-database', help='Target database name (optional, overrides controller config)')
    
    args = parser.parse_args()
    
    # Set verbose mode
    if args.verbose:
        os.environ['VERBOSE'] = 'true'
    
    try:
        app = DatabaseBackupApp(args.config)
        
        # Always load databases and services from configuration
        app.load_databases_from_config()
        app.load_services_from_config()
        
        if args.backup_all:
            results = app.backup_all_databases()
            if not all(results):
                print("❌ Some backups failed!")
                sys.exit(0)
            else:
                print("✅ All backups completed successfully!")
        
        elif args.backup:
            success = app.backup_database(args.backup)
            if not success:
                print("❌ Backup failed!")
                sys.exit(0)
            else:
                print("✅ Backup completed successfully!")
        
        elif args.restore:
            if not args.target_controller:
                print("❌ --target-controller is required with --restore")
                sys.exit(1)
            
            success = app.restore_database(args.restore, args.target_controller, args.target_database)
            if not success:
                print("❌ Restore failed!")
                sys.exit(1)
            else:
                print("✅ Restore completed successfully!")
        
        elif args.list_files:
            app.list_backup_files(args.list_files)
        
        elif args.cleanup:
            app.cleanup_old_backups()
        
        elif args.report is not None:
            app.generate_report(args.report if args.report else None)
        
        elif args.test:
            app.test_connections()
        
        elif args.list_controllers:
            app.list_controllers()
        
        else:
            parser.print_help()
        
        
    
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Application error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

