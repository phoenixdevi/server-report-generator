import sqlite3
import os
from pathlib import Path

# Path to the database file (persisted in /app/data volume)
DB_PATH = Path("/app/data/settings.db")

def init_db():
    """Initialise the database and create tables if they don't exist."""
    # Ensure directory exists for local development
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # AI Configurations table
    # is_active: 1 means this is the currently selected config
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            provider TEXT NOT NULL,
            model_id TEXT NOT NULL,
            api_key TEXT NOT NULL,
            is_active INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Check if we need to seed initial config from environment variables
    cursor.execute("SELECT COUNT(*) FROM ai_configs")
    if cursor.fetchone()[0] == 0:
        provider = os.getenv("AI_PROVIDER", "claude")
        model = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        
        if api_key:
            cursor.execute("""
                INSERT INTO ai_configs (name, provider, model_id, api_key, is_active)
                VALUES (?, ?, ?, ?, 1)
            """, ("Default Config", provider, model, api_key))
    
    conn.commit()
    conn.close()

def get_configs():
    """Return all saved AI configurations."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ai_configs ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_active_config():
    """Return the currently selected configuration."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ai_configs WHERE is_active = 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def add_config(name, provider, model_id, api_key):
    """Add a new AI configuration."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO ai_configs (name, provider, model_id, api_key, is_active)
            VALUES (?, ?, ?, ?, 0)
        """, (name, provider, model_id, api_key))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def set_active_config(config_id):
    """Switch the active configuration."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Reset all to inactive
    cursor.execute("UPDATE ai_configs SET is_active = 0")
    # Set chosen one to active
    cursor.execute("UPDATE ai_configs SET is_active = 1 WHERE id = ?", (config_id,))
    conn.commit()
    conn.close()

def delete_config(config_id):
    """Delete a configuration."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ai_configs WHERE id = ? AND is_active = 0", (config_id,))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    # Test/Init
    init_db()
    print("Database initialised.")
