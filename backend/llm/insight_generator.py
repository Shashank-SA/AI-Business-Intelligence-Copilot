"""LLM-based explanation layer for turning query output into analyst-style insights."""

import re

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq

from config import get_settings
from utils.logging import get_logger


logger = get_logger(__name__)


class InsightGenerator:
    def __init__(self, model_name: str | None = None):
        settings = get_settings()
        self.model_name = model_name or settings.groq_insight_model
        self.llm = ChatGroq(model=self.model_name, temperature=0.1, api_key=settings.groq_api_key or None)
        self.prompt = PromptTemplate.from_template(
            """
You are a senior business intelligence analyst. Your role is to turn query results into a structured, executive-level business insight.

Guidelines:
- **Format:** Start with a bold one-sentence summary, followed by 2-3 short bullet points highlighting key trends or outliers.
- **Tone:** Professional, direct, and straightforward.
- **No Preamble:** Never say "Here is the insight". Start immediately.
- **Terminology:** Use precise business terms (revenue, growth, margin).
- **No Technical Jargon:** Do NOT mention SQL, tables, or column names.
- **Actionable:** Conclude with a brief business recommendation if applicable.
- If no rows are returned, say: "No matching business data was found for this period or filter."

Conversation context:
{history_text}

User question:
{question}

SQL query:
{sql}

Result sample:
{result_rows}
""".strip()
        )

    def generate(self, question: str, sql: str, result_rows: str, history_text: str) -> str:
        chain = self.prompt | self.llm | StrOutputParser()
        response = chain.invoke(
            {
                "question": question,
                "sql": sql,
                "result_rows": result_rows,
                "history_text": history_text,
            }
        ).strip()
        logger.info(
            "Insight generated from LLM",
            extra={
                "event": "insight_generated",
                "model_name": self.model_name,
                "question": question,
                "sql": sql,
                "llm_response": response,
            },
        )
        return response
