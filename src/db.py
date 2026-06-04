import sqlite3
import os
from pathlib import Path
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path="runic_stream.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Initializes the database schema if it doesn't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS media_library (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    type TEXT NOT NULL CHECK(type IN ('video', 'audio')),
                    file_path TEXT NOT NULL,
                    url TEXT,
                    quality TEXT,
                    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Check if quality column exists (for existing databases)
            cursor.execute("PRAGMA table_info(media_library)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'quality' not in columns:
                cursor.execute("ALTER TABLE media_library ADD COLUMN quality TEXT")
            conn.commit()

    def add_media(self, title: str, media_type: str, file_path: str, url: str = None, quality: str = None) -> int:
        """Adds a new media record to the library."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO media_library (title, type, file_path, url, quality) VALUES (?, ?, ?, ?, ?)",
                (title, media_type, file_path, url, quality)
            )
            conn.commit()
            return cursor.lastrowid

    def get_media_by_url(self, url: str):
        """Retrieves media records matching a specific URL."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM media_library WHERE url = ?", (url,))
            return [dict(row) for row in cursor.fetchall()]

    def get_all_media(self, media_type: str = None):
        """Retrieves all media, optionally filtered by type ('video' or 'audio')."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if media_type:
                cursor.execute("SELECT * FROM media_library WHERE type = ? ORDER BY date_added DESC", (media_type,))
            else:
                cursor.execute("SELECT * FROM media_library ORDER BY date_added DESC")
                
            return [dict(row) for row in cursor.fetchall()]

    def sync_library(self):
        """Removes records from the database if the physical file no longer exists."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, file_path FROM media_library")
            records = cursor.fetchall()
            
            to_delete = []
            for record_id, file_path in records:
                if not file_path or not os.path.exists(file_path):
                    to_delete.append(record_id)
            
            if to_delete:
                cursor.executemany("DELETE FROM media_library WHERE id = ?", [(rid,) for rid in to_delete])
                conn.commit()
            return len(to_delete)

    def delete_media(self, media_id: int):
        """Deletes a media record by ID and also removes the physical file if it exists."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # First, get the file path
            cursor.execute("SELECT file_path FROM media_library WHERE id = ?", (media_id,))
            result = cursor.fetchone()
            
            if result:
                file_path = result[0]
                # Delete from database
                cursor.execute("DELETE FROM media_library WHERE id = ?", (media_id,))
                conn.commit()
                
                # Delete physical file
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        return True
                    except OSError as e:
                        print(f"Error deleting file {file_path}: {e}")
                        return False
            return False

# Global singleton instance for easier imports
db = DatabaseManager()
