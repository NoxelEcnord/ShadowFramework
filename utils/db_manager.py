import os
import sqlite3
from pathlib import Path

class DBManager:
    def __init__(self, db_file):
        """
        Initialize the database manager.

        Args:
            db_file: Path to the SQLite database file.
        """
        self.db_file = db_file
        self.conn = sqlite3.connect(self.db_file)
        self._init_db()

    def _init_db(self):
        """
        Initialize the database tables.
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                ip_address TEXT,
                port INTEGER,
                module_name TEXT,
                output TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS loot (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                type TEXT NOT NULL,
                path TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (id)
            )
        ''')
        self.conn.commit()

    def add_session(self, device_id, ip_address, port, module_name, output):
        """
        Add a new session to the database.

        Args:
            device_id: The device ID.
            ip_address: The device IP address.
            port: The device port.
            module_name: The module name.
            output: The module output.
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO sessions (device_id, ip_address, port, module_name, output)
            VALUES (?, ?, ?, ?, ?)
        ''', (device_id, ip_address, port, module_name, output))
        self.conn.commit()
        return cursor.lastrowid

    def close(self):
        """
        Close the database connection.
        """
        self.conn.close()
