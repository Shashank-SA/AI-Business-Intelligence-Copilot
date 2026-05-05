"""Streamlit app for the upgraded AI BI copilot."""

import streamlit as st

from config import get_settings
from db.database import DatabaseManager
from services.query_executor import QueryExecutor
from services.visualization_service import build_chart
from utils.logging import get_logger, setup_logging
from utils.schema_extractor import SchemaExtractor


setup_logging()
settings = get_settings()
logger = get_logger(__name__)

st.set_page_config(page_title=settings.app_title, layout="wide")


def initialize_session_state():
    st.session_state.setdefault("database", None)
    st.session_state.setdefault("query_executor", None)
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("uploaded_file_token", None)


def reset_session_state():
    for key in ("database", "query_executor", "messages", "uploaded_file_token"):
        st.session_state.pop(key, None)


def load_uploaded_file(uploaded_file):
    file_token = f"{uploaded_file.name}:{uploaded_file.size}"
    if st.session_state.get("uploaded_file_token") == file_token:
        return

    database = DatabaseManager.from_csv(uploaded_file)
    st.session_state["database"] = database
    st.session_state["query_executor"] = QueryExecutor(database)
    st.session_state["messages"] = []
    st.session_state["uploaded_file_token"] = file_token
    logger.info(
        "Streamlit session loaded dataset",
        extra={"event": "streamlit_dataset_loaded", "file_name": uploaded_file.name, "table_name": database.table_name},
    )


def render_assistant_message(message: dict):
    if message.get("error"):
        st.error(message["error"])
        if message.get("sql"):
            st.code(message["sql"], language="sql")
        return

    if message.get("insight"):
        st.write(message["insight"])

    if message.get("sql"):
        with st.expander("Generated SQL", expanded=False):
            st.code(message["sql"], language="sql")

    dataframe = message.get("dataframe")
    if dataframe is not None:
        with st.expander("Query Result", expanded=True):
            st.dataframe(dataframe, use_container_width=True)

        chart = build_chart(dataframe)
        if chart is not None:
            st.plotly_chart(chart, use_container_width=True)
        else:
            st.caption("No suitable chart detected for this result.")


def render_chat_history():
    for message in st.session_state["messages"]:
        with st.chat_message(message["role"]):
            if message["role"] == "user":
                st.write(message["content"])
            else:
                render_assistant_message(message)


def main():
    initialize_session_state()

    st.title(settings.app_title)
    st.caption("Upload a CSV, ask business questions in natural language, and get SQL-backed answers, charts, and insights.")

    with st.sidebar:
        st.subheader("Workspace")
        st.write(f"GROQ_API_KEY: {'Configured' if settings.groq_api_key else 'Missing'}")
        st.write(f"SQL model: `{settings.groq_sql_model}`")
        st.write(f"Insight model: `{settings.groq_insight_model}`")
        if st.button("Reset Session"):
            logger.info("Streamlit session reset", extra={"event": "streamlit_reset"})
            reset_session_state()
            st.rerun()

    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

    if uploaded_file is not None:
        try:
            load_uploaded_file(uploaded_file)
            database: DatabaseManager = st.session_state["database"]
            schema_text = SchemaExtractor(database).format_schema_text()
            st.success(f"Loaded `{uploaded_file.name}` into SQLite table `{database.table_name}`.")
            with st.expander("Dataset Preview", expanded=False):
                st.dataframe(database.dataframe.head(20), use_container_width=True)
            with st.expander("Detected Schema", expanded=False):
                st.text(schema_text)
        except Exception as exc:
            logger.exception("Failed to process uploaded CSV", extra={"event": "streamlit_upload_failed", "file_name": uploaded_file.name})
            st.error(f"Failed to process CSV: {exc}")
            return

    render_chat_history()

    question = st.chat_input("Ask a business question about the uploaded data")
    if not question:
        return

    st.session_state["messages"].append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)

    if st.session_state.get("query_executor") is None:
        with st.chat_message("assistant"):
            st.warning("Upload a CSV before starting the analysis.")
        st.session_state["messages"].append(
            {"role": "assistant", "content": "", "sql": "", "dataframe": None, "insight": None, "error": "Upload a CSV before starting the analysis."}
        )
        return

    if not settings.groq_api_key:
        with st.chat_message("assistant"):
            st.error("Set the GROQ_API_KEY environment variable before running analysis.")
        st.session_state["messages"].append(
            {
                "role": "assistant",
                "content": "",
                "sql": "",
                "dataframe": None,
                "insight": None,
                "error": "Set the GROQ_API_KEY environment variable before running analysis.",
            }
        )
        return

    with st.chat_message("assistant"):
        with st.spinner("Analyzing your data..."):
            result = st.session_state["query_executor"].run(question, history=st.session_state["messages"][:-1])

        assistant_message = {
            "role": "assistant",
            "content": result.insight or "",
            "sql": result.sql,
            "dataframe": result.dataframe,
            "insight": result.insight,
            "error": result.error,
            "attempts": result.attempts,
            "result_preview": result.dataframe.head(8).to_markdown(index=False) if result.dataframe is not None and not result.dataframe.empty else "",
        }
        render_assistant_message(assistant_message)
        st.session_state["messages"].append(assistant_message)


if __name__ == "__main__":
    main()
