"""Compatibility wrapper for the upgraded database package."""

from db.database import DatabaseManager


def create_sqlite_from_csv(uploaded_file):
    database = DatabaseManager.from_csv(uploaded_file)
    return database.db_path, database.table_name, database.dataframe
