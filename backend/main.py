"""FastAPI entrypoint for the AI Business Intelligence Copilot web experience."""

from dataclasses import dataclass, field
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from config import get_settings
from db.database import DatabaseManager
from db import metadata_db
from llm.business_guard import classify_dataset_domain
from services.query_executor import QueryExecutor
from services.visualization_service import chart_to_payload
from utils.logging import get_logger, setup_logging
from utils.schema_extractor import SchemaExtractor


setup_logging()
settings = get_settings()
logger = get_logger(__name__)


@dataclass
class SessionState:
    database: DatabaseManager
    query_executor: QueryExecutor
    messages: list[dict] = field(default_factory=list)


import pathlib
BASE_DIR = pathlib.Path(__file__).parent.parent

app = FastAPI(title=settings.app_title)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "frontend/static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "frontend/templates"))
SESSIONS: dict[str, SessionState] = {}

@app.on_event("startup")
async def startup_event():
    metadata_db.init_db()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"title": settings.app_title},
    )


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": settings.app_title}


@app.post("/api/upload")
async def upload_dataset(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a valid CSV file.")

    session_id = uuid4().hex
    try:
        database = DatabaseManager.from_csv(file.file, file_name=file.filename, session_id=session_id)
    except Exception as exc:
        logger.exception("API upload failed", extra={"event": "api_upload_failed", "file_name": file.filename})
        raise HTTPException(status_code=400, detail=f"Failed to process CSV: {exc}") from exc

    session = SessionState(database=database, query_executor=QueryExecutor(database))
    SESSIONS[session_id] = session
    schema_text = SchemaExtractor(database).format_schema_text()

    logger.info(
        "API dataset uploaded",
        extra={"event": "api_upload_success", "file_name": file.filename, "session_id": session_id, "table_name": database.table_name},
    )

    # Dataset domain classification (heuristic — no LLM call)
    column_names = database.dataframe.columns.tolist()
    dataset_domain = classify_dataset_domain(column_names)

    # KPI Bar data
    numeric_columns = database.dataframe.select_dtypes(include="number").columns.tolist()
    date_columns = [
        col for col in database.dataframe.columns
        if database.dataframe[col].dtype == "object"
        and database.dataframe[col].astype(str).str.match(r"\d{4}[-/]\d{2}", na=False).any()
    ]
    kpi_dict = {
        "row_count": len(database.dataframe),
        "column_count": len(column_names),
        "numeric_count": len(numeric_columns),
        "date_count": len(date_columns),
    }

    # Save to persistent history
    metadata_db.create_session(
        session_id=session_id,
        file_name=file.filename,
        table_name=database.table_name,
        row_count=len(database.dataframe),
        schema_text=schema_text,
        dataset_domain=dataset_domain,
        kpi_dict=kpi_dict
    )

    data_health = {
        "missing_values": int(database.dataframe.isnull().sum().sum()),
        "duplicate_rows": int(database.dataframe.duplicated().sum()),
        "total_cells": int(database.dataframe.size)
    }

    return {
        "session_id": session_id,
        "file_name": file.filename,
        "table_name": database.table_name,
        "preview": database.dataframe.head(12).fillna("").to_dict(orient="records"),
        "columns": column_names,
        "schema": schema_text,
        "row_count": len(database.dataframe),
        "dataset_domain": dataset_domain,
        "numeric_columns": numeric_columns,
        "date_columns": date_columns,
        "data_health": data_health,
    }


@app.get("/api/schema/{session_id}")
async def get_schema(session_id: str):
    session = SESSIONS.get(session_id)
    if session is None:
        # Try to rehydrate
        session_meta = metadata_db.get_session(session_id)
        if session_meta:
            database = DatabaseManager.load_existing(session_id, session_meta["table_name"])
            session = SessionState(database=database, query_executor=QueryExecutor(database))
            SESSIONS[session_id] = session
        else:
            raise HTTPException(status_code=404, detail="Session not found.")

    return {
        "table_name": session.database.table_name,
        "schema": SchemaExtractor(session.database).format_schema_text(),
    }


@app.post("/api/query")
async def run_query(session_id: str = Form(...), question: str = Form(...)):
    session = SESSIONS.get(session_id)
    if session is None:
        # Try to rehydrate
        session_meta = metadata_db.get_session(session_id)
        if session_meta:
            database = DatabaseManager.load_existing(session_id, session_meta["table_name"])
            session = SessionState(database=database, query_executor=QueryExecutor(database))
            SESSIONS[session_id] = session
        else:
            raise HTTPException(status_code=404, detail="Session not found. Upload a dataset first.")

    if not question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    session.messages.append({"role": "user", "content": question})
    result = session.query_executor.run(question, history=session.messages[:-1])
    rows = []
    columns = []
    chart = None

    if result.dataframe is not None:
        dataframe = result.dataframe.fillna("")
        rows = dataframe.to_dict(orient="records")
        columns = dataframe.columns.tolist()
        chart = chart_to_payload(result.dataframe)

    assistant_message = {
        "role": "assistant",
        "content": result.insight or "",
        "insight": result.insight,
        "recommendation": result.recommendation,
        "sql": result.sql,
        "error": result.error,
        "result_preview": result.dataframe.head(8).to_markdown(index=False) if result.dataframe is not None and not result.dataframe.empty else "",
    }
    session.messages.append(assistant_message)

    # Save to history db (Exclude SQL query to keep it hidden from frontend)
    metadata_db.add_message(session_id, "user", question)
    metadata_db.add_message(
        session_id=session_id,
        role="assistant",
        content=result.error if result.error else result.insight,
        insight=result.insight,
        recommendation=result.recommendation,
        chart_json=chart,
        result_preview=assistant_message["result_preview"],
        columns=columns,
        rows=rows
    )

    logger.info(
        "API query completed",
        extra={"event": "api_query_completed", "session_id": session_id, "question": question, "error": result.error},
    )
    return {
        "question": question,
        "sql": result.sql,
        "insight": result.insight,
        "recommendation": result.recommendation,
        "error": result.error,
        "rows": rows,
        "columns": columns,
        "chart": chart,
        "attempts": result.attempts,
        "message_count": len(session.messages),
    }

@app.get("/api/history")
async def get_history():
    return metadata_db.get_sessions()

@app.get("/api/history/{session_id}")
async def get_history_detail(session_id: str):
    session = metadata_db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
        
    messages = metadata_db.get_session_messages(session_id)
    return {
        "session": session,
        "messages": messages
    }
