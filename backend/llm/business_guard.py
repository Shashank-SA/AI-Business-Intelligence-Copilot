"""Business domain guard — classifies whether a user question is business-related.

If the question is outside business analytics scope, the guard returns a branded
refusal message and prevents SQL generation from running at all.
"""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq

from config import get_settings
from utils.logging import get_logger


logger = get_logger(__name__)

REFUSAL_MESSAGE = (
    "I'm an AI Business Intelligence Copilot, purpose-built to assist with "
    "business-related questions only — such as revenue, sales, KPIs, trends, "
    "customer metrics, and operational performance. "
    "Please ask something about your business data and I'll be happy to help."
)

BUSINESS_DOMAINS = (
    "sales, revenue, profit, loss, margin, KPI, orders, customers, inventory, "
    "products, employees, HR, payroll, marketing, finance, budget, forecast, "
    "supply chain, logistics, operations, growth, conversion, churn, retention, "
    "pricing, cost, expenses, transactions, market share, performance"
)

NON_BUSINESS_DOMAINS = (
    "healthcare, medical, clinical, diagnosis, treatment, disease, patient, "
    "weather, climate, geography, sports, entertainment, politics, science, "
    "cooking, personal advice, education grades, legal advice, coding help"
)

_GUARD_PROMPT = PromptTemplate.from_template(
    """You are a strict business analytics domain classifier.

Your only job is to decide if the user's question is related to business analytics
or not. Business analytics includes: {business_domains}.

Non-business topics include: {non_business_domains}.

Dataset columns available (for context): {column_names}

User question: "{question}"

Reply with exactly one word — either BUSINESS or NOT_BUSINESS. No other output."""
)


class BusinessGuard:
    """Lightweight LLM classifier that gates the query pipeline."""

    def __init__(self, model_name: str | None = None):
        settings = get_settings()
        self.model_name = model_name or settings.groq_sql_model
        self.llm = ChatGroq(
            model=self.model_name,
            temperature=0,
            api_key=settings.groq_api_key or None,
            max_tokens=4,
        )
        self._chain = _GUARD_PROMPT | self.llm | StrOutputParser()

    def is_business_question(self, question: str, column_names: list[str]) -> bool:
        """Return True if the question is business-related, False otherwise."""
        columns_text = ", ".join(column_names[:30]) if column_names else "unknown"
        try:
            response = self._chain.invoke(
                {
                    "question": question,
                    "column_names": columns_text,
                    "business_domains": BUSINESS_DOMAINS,
                    "non_business_domains": NON_BUSINESS_DOMAINS,
                }
            ).strip().upper()
            result = response.startswith("BUSINESS") and not response.startswith("NOT_BUSINESS")
            logger.info(
                "Business guard classification",
                extra={
                    "event": "business_guard",
                    "question": question,
                    "llm_response": response,
                    "is_business": result,
                },
            )
            return result
        except Exception as exc:
            # Fail open — if the guard errors, allow the question through
            logger.warning(
                "Business guard failed, allowing question through",
                extra={"event": "business_guard_error", "error": str(exc)},
            )
            return True

    @staticmethod
    def refusal_message() -> str:
        return REFUSAL_MESSAGE


def classify_dataset_domain(column_names: list[str]) -> str:
    """Heuristic classifier for uploaded dataset domain (no LLM call needed).

    Detects all known non-business domains including insurance, healthcare,
    sports, weather, education, legal, scientific, etc.
    Returns 'BUSINESS' or 'NOT_BUSINESS'.
    """

    # ── Pure business keywords (positively reinforce BUSINESS verdict) ──
    business_keywords = {
        "revenue", "sales", "profit", "loss", "order", "orders", "customer",
        "customers", "product", "products", "quantity", "price", "amount",
        "total", "cost", "margin", "discount", "employee", "employees",
        "department", "region", "category", "transaction", "invoice",
        "budget", "forecast", "inventory", "stock", "shipment", "supplier",
        "vendor", "payment", "tax", "expense", "income", "conversion",
        "churn", "retention", "lead", "pipeline", "deal", "opportunity",
        "kpi", "metric", "campaign", "channel", "acquisition",
    }

    # ── Non-business keyword pool — covers all domains to reject ─────────
    non_business_keywords = {
        # ── Insurance / Actuarial ─────────────────────────────────────
        "policy", "policyholder", "premium", "claim", "claims", "insured",
        "insurer", "beneficiary", "deductible", "coverage", "underwriter",
        "actuary", "reinsurance", "annuity", "indemnity", "liability",
        "copay", "coinsurance", "endorsement", "rider", "lapse",
        # ── Healthcare / Medical ──────────────────────────────────────
        "patient", "patients", "diagnosis", "diagnoses", "medication",
        "prescription", "symptom", "symptoms", "disease", "diseases",
        "treatment", "treatments", "doctor", "hospital", "clinical",
        "blood", "pressure", "glucose", "icd", "admission", "discharge",
        "bmi", "smoker", "smoking", "cholesterol", "heartrate", "pulse",
        "surgery", "procedure", "allergy", "allergies", "dosage", "vaccine",
        "pathology", "radiology", "pharmacy", "physician", "nurse",
        "icu", "ehr", "emr", "lab", "specimen", "vitals",
        # ── Sports / Athletics ────────────────────────────────────────
        "player", "players", "team", "teams", "match", "matches", "goal",
        "goals", "score", "scores", "league", "tournament", "season",
        "wicket", "runs", "innings", "batting", "bowling", "striker",
        "goalkeeper", "assist", "assists", "foul", "penalty", "referee",
        "halftime", "quarterback", "touchdown", "homerun", "pitcher",
        # ── Weather / Climate / Environment ───────────────────────────
        "temperature", "rainfall", "humidity", "wind", "precipitation",
        "forecast" "weather", "climate", "storm", "hurricane", "drought",
        "latitude", "longitude", "elevation", "seismic", "earthquake",
        "tsunami", "flood", "wildfire", "co2", "ozone", "pollutant",
        # ── Education / Academic ──────────────────────────────────────
        "student", "students", "grade", "grades", "gpa", "score",
        "marks", "subject", "subjects", "teacher", "course", "courses",
        "semester", "enrollment", "attendance", "exam", "examination",
        "university", "college", "school", "classroom", "lecture",
        "assignment", "thesis", "dissertation", "curriculum",
        # ── Science / Research ────────────────────────────────────────
        "species", "genus", "organism", "chromosome", "gene", "dna",
        "rna", "protein", "cell", "neuron", "atom", "molecule",
        "compound", "element", "isotope", "experiment", "hypothesis",
        "specimen", "sample", "trial", "placebo", "control",
        # ── Legal / Criminal Justice ──────────────────────────────────
        "crime", "crimes", "arrest", "arrests", "offence", "offense",
        "conviction", "sentence", "parole", "probation", "prison",
        "court", "judge", "lawyer", "attorney", "verdict", "plaintiff",
        "defendant", "case", "docket",
        # ── Demographic / Survey ──────────────────────────────────────
        "respondent", "survey", "questionnaire", "likert",
        "population", "census", "household", "ethnicity", "nationality",
    }

    # Tokenise column names
    lowered = {col.lower().replace("_", " ").replace("-", " ") for col in column_names}
    tokens: set[str] = set()
    for col in lowered:
        tokens.update(col.split())
    # Also check full column names as phrases (e.g. "bmi", "icd10")
    tokens |= lowered

    non_business_hits = len(tokens & non_business_keywords)
    business_hits     = len(tokens & business_keywords)

    # Any non-business signal with no stronger business signal → reject
    if non_business_hits > 0 and non_business_hits >= business_hits:
        return "NOT_BUSINESS"
    return "BUSINESS"
