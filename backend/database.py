import sqlite3
from contextlib import contextmanager
from typing import Generator
import os

DATABASE_PATH = "cameras.db"

@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """Get database connection with SpatiaLite loaded"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.enable_load_extension(True)
    try:
        conn.load_extension("mod_spatialite")
    except Exception as e:
        print(f"Warning: Could not load SpatiaLite extension: {e}")
    conn.enable_load_extension(False)
    try:
        yield conn
    finally:
        conn.close()

def init_database():
    """Initialize database with spatial support and create tables"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Initialize spatial metadata
        try:
            cursor.execute("SELECT InitSpatialMetadata(1)")
        except:
            pass
        
        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                totp_secret TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                is_2fa_validated BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # Create cameras table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cameras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                g_sheet_row_id TEXT UNIQUE,
                name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Active',
                camera_type TEXT NOT NULL DEFAULT 'Fixed',
                description TEXT,
                direction REAL,
                field_of_view REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Add geometry column for camera location
        try:
            cursor.execute("""
                SELECT AddGeometryColumn('cameras', 'geometry', 4326, 'POINT', 'XY')
            """)
        except:
            pass
        
        # Create spatial index
        try:
            cursor.execute("""
                SELECT CreateSpatialIndex('cameras', 'geometry')
            """)
        except:
            pass
        
        # Create indexes for filtering
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_camera_status ON cameras(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_camera_type ON cameras(camera_type)")
        
        conn.commit()
        print("Database initialized successfully")

if __name__ == "__main__":
    init_database()
