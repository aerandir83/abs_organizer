from typing import List, Dict, Optional
import threading

class QueueItem:
    def __init__(self, dirpath: str, files: List[str], metadata=None, status="pending"):
        self.id = str(hash(dirpath)) # Simple ID
        self.dirpath = dirpath
        self.files = files
        self.metadata = metadata
        self.status = status # pending, processing, approved, rejected, completed

    def to_dict(self):
        return {
            "id": self.id,
            "dirpath": self.dirpath,
            "files": self.files,
            "metadata": self.metadata.__dict__ if self.metadata else None,
            "status": self.status
        }

class QueueManager:
    def __init__(self):
        self._queue: Dict[str, QueueItem] = {}
        self._lock = threading.Lock()

    def add_item(self, dirpath: str, files: List[str], metadata=None) -> str:
        with self._lock:
            item = QueueItem(dirpath, files, metadata)
            # Prevent duplicates?
            self._queue[item.id] = item
            return item.id

    def get_items(self) -> List[Dict]:
        with self._lock:
            return [item.to_dict() for item in self._queue.values()]

    def get_item(self, item_id: str) -> Optional[QueueItem]:
        with self._lock:
            return self._queue.get(item_id)

    def update_item(self, item_id: str, **kwargs):
        with self._lock:
            item = self._queue.get(item_id)
            if item:
                for k, v in kwargs.items():
                    setattr(item, k, v)
                return True
            return False

    def remove_item(self, item_id: str):
        with self._lock:
            if item_id in self._queue:
                del self._queue[item_id]

queue_manager = QueueManager()
