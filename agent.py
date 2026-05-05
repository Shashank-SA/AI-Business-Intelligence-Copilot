"""Compatibility wrapper for the upgraded query execution service."""

import pandas as pd

from db.database import DatabaseManager
from services.query_executor import QueryExecutor


class SQLAnalystAgent:
    def __init__(self, db_path: str, table_name: str):
        connection = DatabaseManager(db_path=db_path, table_name=table_name, dataframe=pd.DataFrame()).get_connection()
        try:
            dataframe = pd.read_sql_query(f'SELECT * FROM "{table_name}" LIMIT 1000', connection)
        finally:
            connection.close()

        self.database = DatabaseManager(db_path=db_path, table_name=table_name, dataframe=dataframe)
        self.query_executor = QueryExecutor(self.database)

    def run(self, question: str):
        result = self.query_executor.run(question)
        return {
            "answer": result.insight,
            "sql": result.sql,
            "dataframe": result.dataframe,
            "error": result.error,
        }
