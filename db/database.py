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
    def from_csv(cls, uploaded_file, file_name: str | None = None) -> "DatabaseManager":
        dataframe = pd.read_csv(uploaded_file)
        if dataframe.empty:
            raise ValueError("The uploaded CSV is empty.")

        resolved_file_name = file_name or getattr(uploaded_file, "name", "uploaded_data.csv")
        table_name = _sanitize_table_name(resolved_file_name)
        temp_dir = Path(tempfile.mkdtemp(prefix=get_settings().sqlite_temp_prefix))
        db_path = temp_dir / "data.sqlite"

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

    def get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def preview_rows(self, limit: int | None = None) -> pd.DataFrame:
        limit = limit or get_settings().sample_preview_rows
        connection = self.get_connection()
        try:
            return pd.read_sql_query(f'SELECT * FROM "{self.table_name}" LIMIT {limit}', connection)
        finally:
            connection.close()
