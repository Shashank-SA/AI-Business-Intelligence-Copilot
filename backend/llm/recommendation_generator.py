"""LLM-based prescriptive analytics layer for generating actionable business advice."""

import re

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq

from config import get_settings
from utils.logging import get_logger

logger = get_logger(__name__)

class RecommendationGenerator:
    def __init__(self, model_name: str | None = None):
        settings = get_settings()
        self.model_name = model_name or settings.groq_insight_model
        self.llm = ChatGroq(model=self.model_name, temperature=0.3, api_key=settings.groq_api_key or None)
        self.prompt = PromptTemplate.from_template(
            """
You are an elite Management Consultant. Your role is to read a piece of data analysis and prescribe actionable, strategic business steps to increase profitability or efficiency.

Guidelines:
- **Format:** Provide exactly 2 or 3 short, punchy bullet points.
- **Tone:** Authoritative, prescriptive, and action-oriented. Start each bullet with a strong verb (e.g., "Shift", "Invest", "Reduce").
- **Content:** Do NOT summarize the data again. Focus entirely on "what to do next".
- **Terminology:** Use precise business concepts (e.g., ROI, cost-per-acquisition, margin expansion).
- **Concise:** Keep each bullet under 15 words.
- If no data was returned, say: "No data available to form a recommendation."

Conversation context:
{history_text}

User question:
{question}

Data Insight:
{insight}

Result sample:
{result_rows}
""".strip()
        )

    def generate(self, question: str, insight: str, result_rows: str, history_text: str) -> str:
        if not insight or insight == "No matching data was found for this question.":
            return "No actionable recommendation can be generated without valid data."
            
        chain = self.prompt | self.llm | StrOutputParser()
        response = chain.invoke(
            {
                "question": question,
                "insight": insight,
                "result_rows": result_rows,
                "history_text": history_text,
            }
        ).strip()
        logger.info(
            "Recommendation generated from LLM",
            extra={
                "event": "recommendation_generated",
                "question": question,
                "llm_response": response,
            },
        )
        return response
