import os
import random
import sqlite3
from pathlib import Path

# 50 short English codenames (≤6 chars) for auto-assigning to scoped devices
CODENAMES = [
    'Ace',    'Ada',    'Alfa',   'Apex',   'Ash',
    'Atlas',  'Axel',   'Blade',  'Blaze',  'Bolt',
    'Bravo',  'Cairo',  'Clash',  'Cobra',  'Comet',
    'Crank',  'Cruz',   'Cyber',  'Dante',  'Delta',
    'Drift',  'Echo',   'Edge',   'Ember',  'Fable',
    'Fang',   'Flare',  'Flux',   'Ghost',  'Glide',
    'Hawk',   'Helix',  'Ivy',    'Jade',   'Knox',
    'Lance',  'Luna',   'Maven',  'Nano',   'Neon',
    'Nova',   'Onyx',   'Orbit',  'Pulse',  'Raven',
    'Razor',  'Rex',    'Sage',   'Storm',  'Venom',
]


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
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scope (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL UNIQUE,
                nickname TEXT UNIQUE,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
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

    def auto_nickname(self):
        """Pick a random unused codename from the pool."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT nickname FROM scope WHERE nickname IS NOT NULL')
        used = {row[0] for row in cursor.fetchall()}
        available = [n for n in CODENAMES if n not in used]
        if available:
            return random.choice(available)
        # Fallback if all 50 used
        return f"Dev{random.randint(100, 999)}"

    def add_to_scope(self, device_id, nickname=None):
        """Add a device to the scope. Auto-assigns a codename if no nickname given."""
        if nickname is None:
            nickname = self.auto_nickname()
        cursor = self.conn.cursor()
        try:
            cursor.execute('INSERT INTO scope (device_id, nickname) VALUES (?, ?)', (device_id, nickname))
            self.conn.commit()
            return nickname
        except sqlite3.IntegrityError:
            cursor.execute('UPDATE scope SET nickname = ? WHERE device_id = ?', (nickname, device_id))
            self.conn.commit()
            return nickname

    def remove_from_scope(self, identifier):
        """Remove from scope by ID, device_id, or nickname."""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM scope WHERE id = ? OR device_id = ? OR nickname = ?', (identifier, identifier, identifier))
        self.conn.commit()
        return cursor.rowcount > 0

    def get_scope(self):
        """Get all devices in the scope."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT id, device_id, nickname FROM scope ORDER BY id ASC')
        return cursor.fetchall()

    def clear_scope(self):
        """Remove all devices from the scope."""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM scope')
        self.conn.commit()

    def close(self):
        """
        Close the database connection.
        """
        self.conn.close()
