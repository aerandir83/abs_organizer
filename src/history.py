
import sqlite3
import json
import os
import hashlib
import time
import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

class HistoryManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS file_history (
                        path TEXT PRIMARY KEY,
                        content_hash TEXT,
                        status TEXT,
                        last_updated REAL,
                        file_list TEXT,
                        metadata TEXT
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize history database: {e}")

    def calculate_hash(self, dirpath: str, files: List[str]) -> str:
        """
        Calculates a hash based on the file paths (relative to dirpath), sizes, and mtimes.
        """
        hasher = hashlib.sha256()
        # Sort files to ensure deterministic hash
        sorted_files = sorted(files)
        
        for filepath in sorted_files:
            try:
                if not os.path.exists(filepath):
                    continue
                stat = os.stat(filepath)
                # Use relative path + size + mtime
                rel_path = os.path.relpath(filepath, dirpath)
                # Combine attributes
                data = f"{rel_path}|{stat.st_size}|{stat.st_mtime}"
                hasher.update(data.encode('utf-8'))
            except Exception:
                # File might have disappeared or permission issue
                continue
                
        return hasher.hexdigest()

    def get_state(self, path: str):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM file_history WHERE path = ?", (path,))
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error(f"Error reading history for {path}: {e}")
            return None

    def get_all_pending(self) -> List[Dict[str, Any]]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM file_history WHERE status = 'pending'")
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error reading pending items: {e}")
            return []

    def update_state(self, path: str, content_hash: str, status: str, files: List[str] = None, metadata: Any = None):
        try:
            meta_json = json.dumps(metadata.__dict__) if hasattr(metadata, '__dict__') else json.dumps(metadata) if metadata else None
            files_json = json.dumps(files) if files else None
            
            # If files/metadata not provided, retain existing if updating status? 
            # For simplicity, we assume we update everything or we need to fetch first.
            # But usually we have full context when updating.
            
            with sqlite3.connect(self.db_path) as conn:
                # Upsert logic
                # SQLite 3.24+ supports ON CONFLICT DO UPDATE, but let's be safe with simple logic
                # or just REPLACE (which deletes and inserts, fine for this)
                 
                # If we use REPLACE, we wipe columns if we pass None.
                # So we should probably do a smart update or just always provide all data.
                
                # Let's try to get existing data if we are missing some fields?
                existing = self.get_state(path)
                if existing:
                    if files_json is None: files_json = existing['file_list']
                    if meta_json is None: meta_json = existing['metadata']

                conn.execute("""
                    INSERT OR REPLACE INTO file_history (path, content_hash, status, last_updated, file_list, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (path, content_hash, status, time.time(), files_json, meta_json))
                conn.commit()
        except Exception as e:
            logger.error(f"Error updating history for {path}: {e}")

    def remove_state(self, path: str):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM file_history WHERE path = ?", (path,))
                conn.commit()
        except Exception as e:
            logger.error(f"Error removing history for {path}: {e}")
