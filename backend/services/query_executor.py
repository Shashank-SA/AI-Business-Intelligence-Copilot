"""Query orchestration service with validation, retries, execution, and AI insights."""

from dataclasses import dataclass
from typing import Any

import pandas as pd

from config import get_settings
from db.database import DatabaseManager
from llm.business_guard import BusinessGuard
from llm.insight_generator import InsightGenerator
from llm.recommendation_generator import RecommendationGenerator
from llm.sql_generator import SQLGenerationContext, SQLGenerator, SQLValidationError
from utils.logging import get_logger
from utils.schema_extractor import SchemaExtractor


logger = get_logger(__name__)


@dataclass
class QueryResult:
    question: str
    sql: str
    dataframe: pd.DataFrame | None
    insight: str | None
    recommendation: str | None
    error: str | None
    attempts: int


class QueryExecutor:
    def __init__(
        self,
        database: DatabaseManager,
        sql_generator: SQLGenerator | None = None,
        insight_generator: InsightGenerator | None = None,
        recommendation_generator: RecommendationGenerator | None = None,
        business_guard: BusinessGuard | None = None,
    ):
        self.database = database
        self.sql_generator = sql_generator or SQLGenerator()
        self.insight_generator = insight_generator or InsightGenerator()
        self.recommendation_generator = recommendation_generator or RecommendationGenerator()
        self.business_guard = business_guard or BusinessGuard()
        self.schema_extractor = SchemaExtractor(database)

    def run(self, question: str, history: list[dict[str, Any]] | None = None, max_attempts: int | None = None) -> QueryResult:
        settings = get_settings()
        max_attempts = max_attempts or settings.max_sql_retries
        prepared_question = self._prepare_question(question, history or [])

        # --- Business domain guard (runs before SQL generation) ---
        column_names = list(self.database.dataframe.columns)
        if not self.business_guard.is_business_question(question, column_names):
            logger.info(
                "Business guard blocked non-business question",
                extra={"event": "business_guard_blocked", "question": question},
            )
            return QueryResult(
                question=question,
                sql="",
                dataframe=None,
                insight=None,
                recommendation=None,
                error=BusinessGuard.refusal_message(),
                attempts=0,
            )

        logger.info(
            "User query received",
            extra={
                "event": "user_query",
                "question": question,
                "prepared_question": prepared_question,
                "table_name": self.database.table_name,
                "history_turns": len(history or []),
                "max_attempts": max_attempts,
            },
        )
        context = SQLGenerationContext(
            table_name=self.database.table_name,
            schema_text=self.schema_extractor.format_schema_text(),
            sample_rows=self.database.preview_rows().to_csv(index=False),
            history_text=self._build_history_text(history or []),
            question=prepared_question,
        )

        sql = ""
        last_error = ""

        for attempt in range(1, max_attempts + 1):
            try:
                sql = (
                    self.sql_generator.generate_sql(context)
                    if attempt == 1
                    else self.sql_generator.repair_sql(context, failed_sql=sql, error_message=last_error)
                )
                sql = self.sql_generator.validate_sql(sql, self.database.table_name)
                dataframe = self._execute_sql(sql)
                insight = self._build_insight(question, sql, dataframe, context.history_text)
                
                result_rows_str = dataframe.head(20).to_markdown(index=False) if not dataframe.empty else ""
                recommendation = self.recommendation_generator.generate(question, insight, result_rows_str, context.history_text)
                
                logger.info(
                    "Query executed successfully",
                    extra={
                        "event": "query_success",
                        "question": question,
                        "sql": sql,
                        "attempt": attempt,
                        "row_count": len(dataframe),
                        "column_count": len(dataframe.columns),
                    },
                )
                return QueryResult(
                    question=question,
                    sql=sql,
                    dataframe=dataframe,
                    insight=insight,
                    recommendation=recommendation,
                    error=None,
                    attempts=attempt,
                )
            except (SQLValidationError, Exception) as exc:
                last_error = str(exc)
                logger.warning(
                    "Query attempt failed",
                    extra={
                        "event": "query_attempt_failed",
                        "question": question,
                        "sql": sql,
                        "attempt": attempt,
                        "error": last_error,
                    },
                )

        friendly_error = self._friendly_error(last_error)
        logger.error(
            "Query failed after retries",
            extra={
                "event": "query_failed",
                "question": question,
                "sql": sql,
                "attempts": max_attempts,
                "error": last_error,
                "friendly_error": friendly_error,
            },
        )
        return QueryResult(
            question=question,
            sql=sql,
            dataframe=None,
            insight=None,
            recommendation=None,
            error=friendly_error,
            attempts=max_attempts,
        )

    def _execute_sql(self, sql: str) -> pd.DataFrame:
        connection = self.database.get_connection()
        try:
            connection.execute(f"EXPLAIN QUERY PLAN {sql}")
            return pd.read_sql_query(sql, connection)
        finally:
            connection.close()

    def _build_insight(self, question: str, sql: str, dataframe: pd.DataFrame, history_text: str) -> str:
        if dataframe.empty:
            return "No matching data was found for this question."

        result_rows = dataframe.head(20).to_markdown(index=False)
        try:
            return self.insight_generator.generate(question, sql, result_rows, history_text)
        except Exception:
            return f"Returned {len(dataframe)} row(s) across {len(dataframe.columns)} column(s)."

    def _build_history_text(self, history: list[dict[str, Any]], turns: int = 4) -> str:
        if not history:
            return "No prior conversation."

        recent_history = history[-turns:]
        lines = []
        for item in recent_history:
            role = item.get("role", "user").capitalize()
            if role == "Assistant":
                answer = item.get("insight") or item.get("content") or ""
                sql = item.get("sql", "")
                preview = item.get("result_preview", "")
                lines.append(f"{role}: {answer}")
                if sql:
                    lines.append(f"SQL used: {sql}")
                if preview:
                    lines.append(f"Result preview:\n{preview}")
            else:
                lines.append(f"{role}: {item.get('content', '')}")
        return "\n".join(lines)

    def _prepare_question(self, question: str, history: list[dict[str, Any]]) -> str:
        normalized = question.strip()
        lowered = normalized.lower()
        followup_markers = ("why", "how", "what about", "show last", "show previous", "compare", "it", "that", "those", "them")
        is_followup = len(normalized.split()) <= 10 or any(marker in lowered for marker in followup_markers)
        if not is_followup or not history:
            return normalized

        recent_user = next((item.get("content", "") for item in reversed(history) if item.get("role") == "user"), "")
        recent_assistant = next((item for item in reversed(history) if item.get("role") == "assistant" and not item.get("error")), None)
        if recent_assistant is None:
            return normalized

        context_lines = []
        if recent_user:
            context_lines.append(f"Previous user question: {recent_user}")
        if recent_assistant.get("insight"):
            context_lines.append(f"Previous answer: {recent_assistant['insight']}")
        if recent_assistant.get("sql"):
            context_lines.append(f"Previous SQL: {recent_assistant['sql']}")
        if recent_assistant.get("result_preview"):
            context_lines.append(f"Previous result preview:\n{recent_assistant['result_preview']}")

        if not context_lines:
            return normalized

        return (
            f"{normalized}\n\n"
            "Interpret this as a follow-up request using the prior conversation below.\n"
            + "\n".join(context_lines)
        )

    def _friendly_error(self, error_message: str) -> str:
        lowered = error_message.lower()
        if "no such column" in lowered:
            return "I could not find one of the referenced columns in your business dataset. Try rephrasing your question with the exact field names."
        if "syntax error" in lowered or "validation" in lowered:
            return "I could not build a valid query for that business request. Please try rephrasing with more specific metrics or dimensions."
        if "not answerable" in lowered:
            return "That question does not appear to be answerable from the uploaded business dataset. Try a different angle or check the schema."
        if "unsafe sql" in lowered:
            return "The generated query was blocked for data safety reasons."
        return f"I could not complete that business analysis. Please rephrase your question or try a different metric."
