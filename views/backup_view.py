"""
View classes for backup operations output and formatting.
"""
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from models.backup_result import BackupResult, BackupSummary


class BackupView:
    """View class for backup operations output."""
    
    def __init__(self, verbose: bool = False):
        """Initialize backup view."""
        self.verbose = verbose
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def display_backup_started(self, database_name: str, database_type: str):
        """Display backup started message."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] Starting backup for {database_type} database: {database_name}")
        if self.verbose:
            self.logger.info(f"Backup started for {database_type} database: {database_name}")
    
    def display_backup_result(self, result: BackupResult):
        """Display backup result."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if result.is_successful:
            status_icon = "✅"
            status_text = "SUCCESS"
            size_info = ""
            if result.backup_size_bytes:
                size_mb = result.backup_size_bytes / (1024 * 1024)
                size_info = f" ({size_mb:.2f} MB)"
            
            duration_info = ""
            if result.duration_seconds:
                duration_info = f" in {result.duration_seconds:.1f}s"
            
            print(f"[{timestamp}] {status_icon} Backup {status_text} for {result.database_name}{size_info}{duration_info}")
            print(f"  Backup ID: {result.backup_id}")
            print(f"  File: {result.backup_file_path}")
            
        else:
            status_icon = "❌"
            status_text = "FAILED"
            print(f"[{timestamp}] {status_icon} Backup {status_text} for {result.database_name}")
            print(f"  Backup ID: {result.backup_id}")
            if result.error_message:
                print(f"  Error: {result.error_message}")
        
        if self.verbose:
            self.logger.info(f"Backup result: {result.status.value} for {result.database_name}")
    
    def display_backup_summary(self, summary: BackupSummary):
        """Display backup summary."""
        print("\n" + "="*60)
        print("BACKUP SUMMARY")
        print("="*60)
        print(f"Total Backups: {summary.total_backups}")
        print(f"Successful: {summary.successful_backups}")
        print(f"Failed: {summary.failed_backups}")
        print(f"Success Rate: {summary.success_rate:.1f}%")
        
        if summary.total_size_bytes > 0:
            total_size_mb = summary.total_size_bytes / (1024 * 1024)
            print(f"Total Size: {total_size_mb:.2f} MB")
        
        if summary.average_duration_seconds > 0:
            print(f"Average Duration: {summary.average_duration_seconds:.1f}s")
        
        if summary.last_backup_time:
            print(f"Last Backup: {summary.last_backup_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        print("="*60)
    
    def display_ftp_upload(self, filename: str, success: bool):
        """Display FTP upload status."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if success:
            status_icon = "📤"
            status_text = "UPLOADED"
            print(f"[{timestamp}] {status_icon} FTP {status_text}: {filename}")
        else:
            status_icon = "❌"
            status_text = "UPLOAD FAILED"
            print(f"[{timestamp}] {status_icon} FTP {status_text}: {filename}")
    
    def display_cleanup_results(self, cleanup_results: Dict[str, List[str]]):
        """Display cleanup results."""
        print("\n" + "="*60)
        print("CLEANUP RESULTS")
        print("="*60)
        
        total_deleted = 0
        for controller_id, deleted_files in cleanup_results.items():
            if deleted_files:
                print(f"{controller_id}: {len(deleted_files)} files deleted")
                total_deleted += len(deleted_files)
                if self.verbose:
                    for file in deleted_files:
                        print(f"  - {file}")
            else:
                print(f"{controller_id}: No files to delete")
        
        print(f"Total files deleted: {total_deleted}")
        print("="*60)
    
    def display_backup_files(self, files: List[Dict[str, Any]], controller_id: Optional[str] = None):
        """Display list of backup files."""
        if not files:
            print("No backup files found.")
            return
        
        print("\n" + "="*80)
        if controller_id:
            print(f"BACKUP FILES - {controller_id}")
        else:
            print("ALL BACKUP FILES")
        print("="*80)
        print(f"{'Filename':<40} {'Size (MB)':<12} {'Created':<20} {'Modified':<20}")
        print("-"*80)
        
        for file_info in files:
            size_mb = file_info['size_bytes'] / (1024 * 1024)
            created_str = file_info['created_time'].strftime('%Y-%m-%d %H:%M:%S')
            modified_str = file_info['modified_time'].strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"{file_info['filename']:<40} {size_mb:<12.2f} {created_str:<20} {modified_str:<20}")
        
        print("="*80)
    
    def display_error(self, error_message: str, context: str = ""):
        """Display error message."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] ❌ ERROR: {error_message}")
        if context:
            print(f"  Context: {context}")
    
    def display_info(self, message: str):
        """Display info message."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] ℹ️  INFO: {message}")
    
    def display_warning(self, message: str):
        """Display warning message."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] ⚠️  WARNING: {message}")
    
    def display_debug(self, message: str):
        """Display debug message."""
        if self.verbose:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"[{timestamp}] 🐛 DEBUG: {message}")
    
    def display_progress(self, current: int, total: int, operation: str = "Processing"):
        """Display progress indicator."""
        if total > 0:
            percentage = (current / total) * 100
            bar_length = 30
            filled_length = int(bar_length * current // total)
            bar = '█' * filled_length + '-' * (bar_length - filled_length)
            print(f"\r{operation}: |{bar}| {percentage:.1f}% ({current}/{total})", end='', flush=True)
            
            if current == total:
                print()  # New line when complete


class BackupReportView:
    """View class for generating backup reports."""
    
    def __init__(self):
        """Initialize backup report view."""
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def generate_text_report(self, summary: BackupSummary, results: List[BackupResult]) -> str:
        """Generate text report."""
        report = []
        report.append("DATABASE BACKUP REPORT")
        report.append("=" * 50)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Summary section
        report.append("SUMMARY")
        report.append("-" * 20)
        report.append(f"Total Backups: {summary.total_backups}")
        report.append(f"Successful: {summary.successful_backups}")
        report.append(f"Failed: {summary.failed_backups}")
        report.append(f"Success Rate: {summary.success_rate:.1f}%")
        
        if summary.total_size_bytes > 0:
            total_size_mb = summary.total_size_bytes / (1024 * 1024)
            report.append(f"Total Size: {total_size_mb:.2f} MB")
        
        if summary.average_duration_seconds > 0:
            report.append(f"Average Duration: {summary.average_duration_seconds:.1f}s")
        
        if summary.last_backup_time:
            report.append(f"Last Backup: {summary.last_backup_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        report.append("")
        
        # Detailed results
        report.append("DETAILED RESULTS")
        report.append("-" * 20)
        
        for result in results:
            status = "SUCCESS" if result.is_successful else "FAILED"
            report.append(f"Backup ID: {result.backup_id}")
            report.append(f"Database: {result.database_name} ({result.database_type})")
            report.append(f"Status: {status}")
            report.append(f"Start Time: {result.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if result.end_time:
                report.append(f"End Time: {result.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if result.duration_seconds:
                report.append(f"Duration: {result.duration_seconds:.1f}s")
            
            if result.backup_file_path:
                report.append(f"File: {result.backup_file_path}")
            
            if result.backup_size_bytes:
                size_mb = result.backup_size_bytes / (1024 * 1024)
                report.append(f"Size: {size_mb:.2f} MB")
            
            if result.error_message:
                report.append(f"Error: {result.error_message}")
            
            report.append("")
        
        return "\n".join(report)
    
    def save_report(self, report: str, file_path: str) -> bool:
        """Save report to file."""
        try:
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(report)
            self.logger.info(f"Report saved to: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save report: {e}")
            return False

