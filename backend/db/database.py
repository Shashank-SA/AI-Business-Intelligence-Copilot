"""Database manager for CSV ingestion and SQLite lifecycle."""

import re
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from config import get_settings
from utils.logging import get_logger


logger = get_logger(__name__)


def _sanitize_table_name(file_name: str) -> str:
    stem = Path(file_name).stem.strip().lower()
    sanitized = re.sub(r"[^a-zA-Z0-9_]+", "_", stem)
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    return sanitized or "uploaded_data"


@dataclass
class DatabaseManager:
    db_path: str
    table_name: str
    dataframe: pd.DataFrame

    @classmethod
    def from_csv(cls, uploaded_file, file_name: str | None = None, session_id: str | None = None) -> "DatabaseManager":
        try:
            dataframe = pd.read_csv(uploaded_file, encoding="utf-8")
        except UnicodeDecodeError:
            uploaded_file.seek(0)
            dataframe = pd.read_csv(uploaded_file, encoding="ISO-8859-1")
            
        if dataframe.empty:
            raise ValueError("The uploaded CSV is empty.")

        resolved_file_name = file_name or getattr(uploaded_file, "name", "uploaded_data.csv")
        table_name = _sanitize_table_name(resolved_file_name)
        
        # Use a permanent directory for database files
        data_store_dir = Path(__file__).parent.parent / "data_store"
        data_store_dir.mkdir(exist_ok=True)
        
        db_filename = f"{session_id}.sqlite" if session_id else "data.sqlite"
        db_path = data_store_dir / db_filename

        connection = sqlite3.connect(db_path)
        try:
            dataframe.to_sql(table_name, connection, if_exists="replace", index=False)
        finally:
            connection.close()

        logger.info(
            "CSV uploaded and loaded into SQLite",
            extra={
                "event": "csv_ingested",
                "file_name": resolved_file_name,
                "table_name": table_name,
                "row_count": len(dataframe),
                "column_count": len(dataframe.columns),
                "db_path": str(db_path),
            },
        )

        return cls(db_path=str(db_path), table_name=table_name, dataframe=dataframe)

    @classmethod
    def load_existing(cls, session_id: str, table_name: str) -> "DatabaseManager":
        db_path = Path(__file__).parent.parent / "data_store" / f"{session_id}.sqlite"
        if not db_path.exists():
            raise FileNotFoundError(f"Database for session {session_id} not found.")
        
        connection = sqlite3.connect(str(db_path))
        try:
            # Load the dataframe back into memory for pandas operations (KPIs, schemas, etc.)
            dataframe = pd.read_sql_query(f'SELECT * FROM "{table_name}"', connection)
        finally:
            connection.close()
            
        return cls(db_path=str(db_path), table_name=table_name, dataframe=dataframe)

    def get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def preview_rows(self, limit: int | None = None) -> pd.DataFrame:
        limit = limit or get_settings().sample_preview_rows
        connection = self.get_connection()
        try:
            return pd.read_sql_query(f'SELECT * FROM "{self.table_name}" LIMIT {limit}', connection)
        finally:
            connection.close()
