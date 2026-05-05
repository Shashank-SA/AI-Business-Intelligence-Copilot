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


app = FastAPI(title=settings.app_title)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
SESSIONS: dict[str, SessionState] = {}


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

    try:
        database = DatabaseManager.from_csv(file.file, file_name=file.filename)
    except Exception as exc:
        logger.exception("API upload failed", extra={"event": "api_upload_failed", "file_name": file.filename})
        raise HTTPException(status_code=400, detail=f"Failed to process CSV: {exc}") from exc

    session_id = uuid4().hex
    session = SessionState(database=database, query_executor=QueryExecutor(database))
    SESSIONS[session_id] = session
    schema_text = SchemaExtractor(database).format_schema_text()

    logger.info(
        "API dataset uploaded",
        extra={"event": "api_upload_success", "file_name": file.filename, "session_id": session_id, "table_name": database.table_name},
    )
    return {
        "session_id": session_id,
        "file_name": file.filename,
        "table_name": database.table_name,
        "preview": database.dataframe.head(12).fillna("").to_dict(orient="records"),
        "columns": database.dataframe.columns.tolist(),
        "schema": schema_text,
        "row_count": len(database.dataframe),
    }


@app.get("/api/schema/{session_id}")
async def get_schema(session_id: str):
    session = SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found. Upload a dataset first.")

    return {
        "table_name": session.database.table_name,
        "schema": SchemaExtractor(session.database).format_schema_text(),
    }


@app.post("/api/query")
async def run_query(session_id: str = Form(...), question: str = Form(...)):
    session = SESSIONS.get(session_id)
    if session is None:
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
        "sql": result.sql,
        "error": result.error,
        "result_preview": result.dataframe.head(8).to_markdown(index=False) if result.dataframe is not None and not result.dataframe.empty else "",
    }
    session.messages.append(assistant_message)

    logger.info(
        "API query completed",
        extra={"event": "api_query_completed", "session_id": session_id, "question": question, "error": result.error},
    )
    return {
        "question": question,
        "sql": result.sql,
        "insight": result.insight,
        "error": result.error,
        "rows": rows,
        "columns": columns,
        "chart": chart,
        "attempts": result.attempts,
        "message_count": len(session.messages),
    }
