from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class DownloadTask:
    id: Optional[int] = None
    url: str = ""
    filename: str = ""
    save_path: str = ""
    total_size: int = 0
    downloaded_size: int = 0
    status: str = "waiting"   # waiting, downloading, paused, completed, error
    speed: float = 0.0        # KB/s
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    error_msg: str = ""

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'url': self.url,
            'filename': self.filename,
            'save_path': self.save_path,
            'total_size': self.total_size,
            'downloaded_size': self.downloaded_size,
            'status': self.status,
            'speed': self.speed,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'error_msg': self.error_msg
        }
