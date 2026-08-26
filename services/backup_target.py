"""Common contract for backup destinations."""
from contextlib import AbstractContextManager
from typing import Protocol, Optional


class BackupTarget(AbstractContextManager, Protocol):  # pragma: no cover
    """Destination capable of receiving a backup file."""

    def upload_file(self, local_file_path: str, remote_filename: Optional[str] = None) -> bool:
        """Upload a local backup file."""
        ...