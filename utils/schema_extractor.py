"""Schema extraction utilities for SQLite-backed uploaded datasets."""

import pandas as pd

from db.database import DatabaseManager


class SchemaExtractor:
    def __init__(self, database: DatabaseManager):
        self.database = database

    def get_schema_dataframe(self) -> pd.DataFrame:
        connection = self.database.get_connection()
        try:
            return pd.read_sql_query(f"PRAGMA table_info('{self.database.table_name}')", connection)
        finally:
            connection.close()

    def format_schema_text(self) -> str:
        schema = self.get_schema_dataframe()
        lines = [f"Table: {self.database.table_name}"]
        for _, row in schema.iterrows():
            lines.append(f"- {row['name']} ({row['type'] or 'TEXT'})")
        return "\n".join(lines)
