import json
import sqlite3
from datetime import datetime
from pathlib import Path

from utils.logging import get_logger

logger = get_logger(__name__)

DB_PATH = Path(__file__).parent.parent / "app.db"

def init_db():
    """Initialise the metadata database for chat history."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            file_name TEXT,
            table_name TEXT,
            row_count INTEGER,
            schema_text TEXT,
            dataset_domain TEXT,
            kpi_json TEXT,
            created_at TEXT
        )
    """)

    # Messages table
    # We do NOT store SQL here because the user explicitly requested it to be hidden from frontend/history.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            content TEXT,
            insight TEXT,
            recommendation TEXT,
            chart_json TEXT,
            result_preview TEXT,
            columns_json TEXT,
            rows_json TEXT,
            created_at TEXT,
            FOREIGN KEY(session_id) REFERENCES sessions(session_id)
        )
    """)
    
    # Try to add recommendation column if migrating from older schema
    try:
        cursor.execute("ALTER TABLE messages ADD COLUMN recommendation TEXT")
    except sqlite3.OperationalError:
        pass # Column already exists

    conn.commit()
    conn.close()
    logger.info("Metadata database initialized at app.db")

def create_session(session_id: str, file_name: str, table_name: str, row_count: int, schema_text: str, dataset_domain: str, kpi_dict: dict):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sessions (session_id, file_name, table_name, row_count, schema_text, dataset_domain, kpi_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (session_id, file_name, table_name, row_count, schema_text, dataset_domain, json.dumps(kpi_dict), datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def add_message(session_id: str, role: str, content: str, insight: str = None, recommendation: str = None, chart_json: str = None, result_preview: str = None, columns: list = None, rows: list = None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO messages (session_id, role, content, insight, recommendation, chart_json, result_preview, columns_json, rows_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        session_id, 
        role, 
        content, 
        insight, 
        recommendation,
        chart_json, 
        result_preview,
        json.dumps(columns) if columns is not None else None,
        json.dumps(rows) if rows is not None else None,
        datetime.utcnow().isoformat()
    ))
    conn.commit()
    conn.close()

def get_sessions() -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_session(session_id: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_session_messages(session_id: str) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM messages WHERE session_id = ? ORDER BY id ASC", (session_id,))
    rows = cursor.fetchall()
    conn.close()
    
    messages = []
    for r in rows:
        msg = dict(r)
        if msg.get("kpi_json"):
            msg["kpi_json"] = json.loads(msg["kpi_json"])
        if msg.get("columns_json"):
            msg["columns"] = json.loads(msg["columns_json"])
        else:
            msg["columns"] = []
            
        if msg.get("rows_json"):
            msg["rows"] = json.loads(msg["rows_json"])
        else:
            msg["rows"] = []
            
        # Clean up raw json strings from output
        msg.pop("columns_json", None)
        msg.pop("rows_json", None)
        messages.append(msg)
        
    return messages
