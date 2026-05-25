# AI Business Intelligence Copilot

An enterprise-grade, Multi-Agent AI Business Intelligence platform that allows non-technical users to analyze their data using natural language. It instantly translates plain English into executable SQL queries, dynamically renders interactive charts (via Plotly), and generates proactive strategic business recommendations.

## 🚀 Key Features

*   **Multi-Agent Pipeline:**
    *   **Business Guard:** Validates user prompts to prevent non-business queries and AI abuse.
    *   **SQL Generator:** Dynamically converts natural language into SQLite queries based on dataset schema.
    *   **Insight Summarizer (Descriptive):** Analyzes the exact output data and summarizes *what happened*.
    *   **Action Plan Consultant (Prescriptive):** Uses insights to formulate a strategic plan on *what to do next*.
*   **Data Health Panel:** Automatically audits uploaded CSVs, flagging missing values (`NaN`) and duplicate rows instantly.
*   **Dynamic Visualizations:** Automatically selects optimal chart types (Bar, Line, Pie) with full manual overrides and interactive Plotly controls.
*   **My Dashboard & Memory:** Allows users to "Pin" visualizations to a customizable dashboard. Saves session history seamlessly.

## 🏗 System Architecture

The project has been meticulously split into decoupled Frontend and Backend services for high performance.

*   **Frontend:** Vanilla JavaScript, HTML5, CSS3, and Plotly.js. Features a modern, glassmorphism enterprise UI.
*   **Backend:** Python 3, FastAPI, Pandas, and SQLite.
*   **LLM Integration:** LangChain orchestrated with LLaMA 3.3 (via Groq API) for ultra-fast reasoning.

## 🛠 Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Shashank-SA/AI-Business-Intelligence-Copilot.git
   cd AI-Business-Intelligence-Copilot
   ```

2. **Set up your environment:**
   Create a `.env` file in the root of the project with your Groq API key:
   ```
   GROQ_API_KEY=your_groq_api_key_here
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Project:**
   The entire project (both backend API and frontend static files) is served concurrently via FastAPI.
   ```bash
   cd backend
   python -m uvicorn main:app --host 0.0.0.0 --port 8000
   ```

5. **Access the Application:**
   Open your browser and navigate to `http://localhost:8000`.

## 📁 Repository Structure
```
├── backend/
│   ├── main.py              # FastAPI entry point & API routes
│   ├── config.py            # Environment configurations
│   ├── db/
│   │   ├── database.py      # Pandas to SQLite ingestion engine
│   │   └── metadata_db.py   # Chat history & session management
│   ├── llm/                 # Multi-Agent prompt chains & parsers
│   └── services/            # Core business logic & query execution
├── frontend/
│   ├── templates/
│   │   └── index.html       # Single-page application UI
│   └── static/
│       ├── app.js           # Frontend logic & API interfacing
│       └── styles.css       # Enterprise UI styling
└── requirements.txt         # Python dependencies
```

## 🔒 Security & Privacy
Uploaded CSV files are securely processed locally into ephemeral SQLite database tables. Only the table schema and the necessary aggregated outputs are sent to the LLM; your raw, entire dataset is never blindly exposed.
