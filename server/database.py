import sqlite3

DATABASE_URL = "oauth2.db"

def get_db():
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        client_id TEXT PRIMARY KEY,
        client_secret TEXT NOT NULL,
        redirect_uri TEXT NOT NULL
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS auth_codes (
        code TEXT PRIMARY KEY,
        client_id TEXT NOT NULL,
        expires_at INTEGER NOT NULL
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS device_codes (
        device_code TEXT PRIMARY KEY,
        user_code TEXT NOT NULL,
        client_id TEXT NOT NULL,
        approved BOOLEAN NOT NULL,
        code_challenge TEXT NOT NULL,
        expires_at INTEGER NOT NULL
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tokens (
        access_token TEXT PRIMARY KEY,
        client_id TEXT NOT NULL,
        expires_at INTEGER NOT NULL
    )
    """)
    # Pre-populate clients
    cursor.execute(
        "INSERT OR IGNORE INTO clients (client_id, client_secret, redirect_uri) VALUES (?, ?, ?)",
        ("browser-client", "secret", "http://localhost:8000/client/callback"),
    )
    cursor.execute(
        "INSERT OR IGNORE INTO clients (client_id, client_secret, redirect_uri) VALUES (?, ?, ?)",
        ("cli-client", "secret", "http://localhost:8081/callback"),
    )
    conn.commit()
    conn.close()
