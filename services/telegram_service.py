"""
Telegram notification service for backup operations.
"""
import logging
import requests
from typing import Optional, Dict, Any
from datetime import datetime

from models.database_config import TelegramConfig
from models.backup_result import BackupResult, BackupSummary


class TelegramService:
    """Service for sending Telegram notifications."""
    
    def __init__(self, telegram_config: TelegramConfig):
        """Initialize Telegram service."""
        self.telegram_config = telegram_config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.base_url = f"https://api.telegram.org/bot{self.telegram_config.bot_token}"
    
    def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """Send a message to Telegram."""
        if not self.telegram_config.enabled:
            self.logger.debug("Telegram notifications disabled")
            return True
        
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                "chat_id": self.telegram_config.chat_id,
                "text": message,
                "parse_mode": parse_mode
            }
            
            response = requests.post(url, data=data, timeout=30)
            response.raise_for_status()
            
            self.logger.info("Telegram message sent successfully")
            return True
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to send Telegram message: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sending Telegram message: {e}")
            return False
    
    def notify_backup_started(self, database_name: str, database_type: str) -> bool:
        """Notify that backup has started."""
        message = (
            f"🔄 <b>Backup Started</b>\n"
            f"Database: {database_name}\n"
            f"Type: {database_type}\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        return self.send_message(message)
    
    def notify_backup_completed(self, backup_result: BackupResult) -> bool:
        """Notify that backup has completed."""
        if backup_result.is_successful:
            emoji = "✅"
            status = "Success"
            size_info = ""
            if backup_result.backup_size_bytes:
                size_mb = backup_result.backup_size_bytes / (1024 * 1024)
                size_info = f"\nSize: {size_mb:.2f} MB"
            
            duration_info = ""
            if backup_result.duration_seconds:
                duration_info = f"\nDuration: {backup_result.duration_seconds:.1f}s"
            
            message = (
                f"{emoji} <b>Backup Completed - {status}</b>\n"
                f"Database: {backup_result.database_name}\n"
                f"Type: {backup_result.database_type}\n"
                f"Backup ID: {backup_result.backup_id}{size_info}{duration_info}\n"
                f"Time: {backup_result.end_time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        else:
            emoji = "❌"
            status = "Failed"
            error_info = ""
            if backup_result.error_message:
                error_info = f"\nError: {backup_result.error_message[:200]}..."
            
            message = (
                f"{emoji} <b>Backup Completed - {status}</b>\n"
                f"Database: {backup_result.database_name}\n"
                f"Type: {backup_result.database_type}\n"
                f"Backup ID: {backup_result.backup_id}{error_info}\n"
                f"Time: {backup_result.end_time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        
        return self.send_message(message)
    
    def notify_backup_summary(self, summary: BackupSummary) -> bool:
        """Notify backup summary."""
        success_rate = summary.success_rate
        
        if success_rate >= 90:
            emoji = "🎉"
        elif success_rate >= 70:
            emoji = "⚠️"
        else:
            emoji = "🚨"
        
        total_size_mb = summary.total_size_bytes / (1024 * 1024) if summary.total_size_bytes > 0 else 0
        
        message = (
            f"{emoji} <b>Backup Summary</b>\n"
            f"Total Backups: {summary.total_backups}\n"
            f"Successful: {summary.successful_backups}\n"
            f"Failed: {summary.failed_backups}\n"
            f"Success Rate: {success_rate:.1f}%\n"
            f"Total Size: {total_size_mb:.2f} MB\n"
            f"Avg Duration: {summary.average_duration_seconds:.1f}s"
        )
        
        if summary.last_backup_time:
            message += f"\nLast Backup: {summary.last_backup_time.strftime('%Y-%m-%d %H:%M:%S')}"
        
        return self.send_message(message)
    
    def notify_ftp_upload(self, filename: str, success: bool) -> bool:
        """Notify FTP upload status."""
        if success:
            emoji = "📤"
            status = "Uploaded"
            message = f"{emoji} <b>FTP Upload - {status}</b>\nFile: {filename}"
        else:
            emoji = "❌"
            status = "Failed"
            message = f"{emoji} <b>FTP Upload - {status}</b>\nFile: {filename}"
        
        return self.send_message(message)
    
    def notify_cleanup(self, deleted_files: int, total_size_mb: float) -> bool:
        """Notify cleanup operation."""
        emoji = "🧹"
        message = (
            f"{emoji} <b>Cleanup Completed</b>\n"
            f"Deleted Files: {deleted_files}\n"
            f"Space Freed: {total_size_mb:.2f} MB"
        )
        return self.send_message(message)
    
    def notify_error(self, error_message: str, context: str = "") -> bool:
        """Notify about errors."""
        emoji = "🚨"
        message = f"{emoji} <b>Backup Error</b>\n"
        
        if context:
            message += f"Context: {context}\n"
        
        message += f"Error: {error_message[:500]}"
        
        return self.send_message(message)
    
    def test_connection(self) -> bool:
        """Test Telegram connection."""
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            bot_info = response.json()
            if bot_info.get("ok"):
                self.logger.info(f"Telegram connection test successful. Bot: {bot_info['result']['first_name']}")
                return True
            else:
                self.logger.error("Telegram connection test failed")
                return False
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Telegram connection test failed: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error testing Telegram connection: {e}")
            return False

