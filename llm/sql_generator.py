"""Schema-aware SQL generation with validation and repair support."""

import re
from dataclasses import dataclass

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq

from config import get_settings
from utils.logging import get_logger


logger = get_logger(__name__)


class SQLValidationError(ValueError):
    """Raised when generated SQL violates safety or schema constraints."""


@dataclass
class SQLGenerationContext:
    table_name: str
    schema_text: str
    sample_rows: str
    history_text: str
    question: str


class SQLGenerator:
    def __init__(self, model_name: str | None = None):
        settings = get_settings()
        self.model_name = model_name or settings.groq_sql_model
        self.llm = ChatGroq(model=self.model_name, temperature=0, api_key=settings.groq_api_key or None)
        self.sql_prompt = PromptTemplate.from_template(
            """
You are a senior analytics engineer generating SQLite SQL for a business intelligence copilot.

Rules:
- Use only the table "{table_name}".
- Use only columns that exist in the schema.
- Return only SQL with no explanation or markdown.
- Generate a single read-only query.
- Prefer explicit columns and clear aliases.
- Use SQLite syntax only.
- Resolve ambiguous follow-up references like "it", "that", "those", "last month", or "the drop" using the conversation context.
- If the user asks a follow-up "why" question, investigate likely drivers using the available dimensions in the data instead of returning NOT_ANSWERABLE when comparative analysis is possible.
- When a prior turn discussed a trend, drop, spike, top performer, or segment, use that as the target of the follow-up unless the user explicitly changes topic.
- If the question cannot be answered from the data, return NOT_ANSWERABLE.

Conversation context:
{history_text}

Available schema:
{schema_text}

Sample rows:
{sample_rows}

User question:
{question}
""".strip()
        )
        self.repair_prompt = PromptTemplate.from_template(
            """
You generated SQLite SQL for a BI copilot, but it failed validation or execution.
Fix the query using the exact schema below.

Rules:
- Use only the table "{table_name}".
- Return only SQL with no explanation or markdown.
- Generate a single read-only query.
- Use SQLite syntax only.
- Resolve ambiguous follow-up references from the conversation context.
- If the user asks "why" after a prior result, investigate likely contributing factors available in the dataset.
- If the question cannot be answered from the data, return NOT_ANSWERABLE.

Conversation context:
{history_text}

Available schema:
{schema_text}

Sample rows:
{sample_rows}

User question:
{question}

Previous SQL:
{failed_sql}

Failure reason:
{error_message}
""".strip()
        )

    def generate_sql(self, context: SQLGenerationContext) -> str:
        chain = self.sql_prompt | self.llm | StrOutputParser()
        response = chain.invoke(context.__dict__)
        logger.info(
            "SQL generated from LLM",
            extra={
                "event": "sql_generated",
                "model_name": self.model_name,
                "question": context.question,
                "table_name": context.table_name,
                "llm_response": response,
            },
        )
        return self._normalize_sql(response)

    def repair_sql(self, context: SQLGenerationContext, failed_sql: str, error_message: str) -> str:
        chain = self.repair_prompt | self.llm | StrOutputParser()
        response = chain.invoke(
            {
                **context.__dict__,
                "failed_sql": failed_sql,
                "error_message": error_message,
            }
        )
        logger.warning(
            "SQL repaired after failure",
            extra={
                "event": "sql_repaired",
                "model_name": self.model_name,
                "question": context.question,
                "failed_sql": failed_sql,
                "repair_error": error_message,
                "llm_response": response,
            },
        )
        return self._normalize_sql(response)

    def validate_sql(self, sql: str, table_name: str) -> str:
        normalized = sql.strip()
        lowered = normalized.lower()

        if normalized == "NOT_ANSWERABLE":
            raise SQLValidationError("I could not map this question to the uploaded dataset.")

        if ";" in normalized[:-1]:
            raise SQLValidationError("Multiple SQL statements are not allowed.")

        if not (lowered.startswith("select") or lowered.startswith("with")):
            raise SQLValidationError("Only SELECT queries are allowed.")

        blocked_patterns = [
            r"\bdrop\b",
            r"\bdelete\b",
            r"\binsert\b",
            r"\bupdate\b",
            r"\balter\b",
            r"\btruncate\b",
            r"\battach\b",
            r"\bdetach\b",
            r"\bpragma\b",
            r"\bcreate\b",
            r"\breplace\b",
        ]
        for pattern in blocked_patterns:
            if re.search(pattern, lowered):
                raise SQLValidationError("Unsafe SQL was blocked before execution.")

        referenced_tables = {
            match.strip('"').strip("'")
            for match in re.findall(r"(?:from|join)\s+([a-zA-Z0-9_\"']+)", normalized, flags=re.IGNORECASE)
        }
        allowed_table = table_name.lower()
        invalid_tables = {table.lower() for table in referenced_tables if table.lower() != allowed_table}
        if invalid_tables:
            raise SQLValidationError("The query referenced tables outside the uploaded dataset.")

        logger.info(
            "SQL validated successfully",
            extra={"event": "sql_validated", "table_name": table_name, "sql": normalized.rstrip(";") + ";"},
        )
        return normalized.rstrip(";") + ";"

    def _normalize_sql(self, response: str) -> str:
        cleaned = response.strip()
        cleaned = re.sub(r"^```sql\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^```\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        return cleaned.strip()
