# AI Business Intelligence Copilot

AI-powered business intelligence app that turns uploaded CSV files into SQLite-backed analysis with natural language querying, validated SQL generation, interactive visualizations, and concise AI insights.

## Features

- Upload CSV data and convert it into SQLite automatically
- Ask business questions in natural language
- Generate schema-aware SQL using Groq + Llama
- Validate and safely execute read-only SQL
- Return concise AI summaries
- Render interactive Plotly visualizations
- Support follow-up questions with conversational context
- Serve a custom FastAPI-based web UI

## Project Structure

```text
.
├── main.py
├── app.py
├── config.py
├── requirements.txt
├── .env.example
├── db.py
├── agent.py
├── db/
│   ├── __init__.py
│   └── database.py
├── llm/
│   ├── __init__.py
│   ├── sql_generator.py
│   └── insight_generator.py
├── services/
│   ├── __init__.py
│   ├── query_executor.py
│   └── visualization_service.py
├── static/
│   ├── app.js
│   └── styles.css
├── templates/
│   └── index.html
└── utils/
    ├── __init__.py
    ├── logging.py
    └── schema_extractor.py
```

## Tech Stack

- Python
- FastAPI
- Plotly
- Pandas
- SQLite
- LangChain
- Groq API

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a local `.env` from `.env.example` and add your Groq API key:

```env
GROQ_API_KEY=your_groq_api_key
GROQ_SQL_MODEL=llama-3.3-70b-versatile
GROQ_INSIGHT_MODEL=llama-3.3-70b-versatile
APP_TITLE=AI Business Intelligence Copilot
SQLITE_TEMP_PREFIX=sql_analyst_
SAMPLE_PREVIEW_ROWS=5
MAX_SQL_RETRIES=2
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=
```

## Run

Start the web app:

```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

## Usage

1. Upload a CSV file.
2. Ask a business question such as:
   - `Show revenue trend by date`
   - `What are the top products by revenue?`
   - `Why did it drop?`
3. Review the generated SQL, insight summary, table output, and chart.

## Notes

- Only safe read-only SQL queries are allowed.
- Follow-up questions use recent conversation context.
- For best dependency stability, Python 3.11 or 3.12 is recommended.

## GitHub Push

Typical Git workflow:

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin <your-repo-url>
git push -u origin main
```
