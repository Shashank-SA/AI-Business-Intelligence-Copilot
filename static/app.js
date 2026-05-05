const state = {
    sessionId: null,
};

const elements = {
    csvFile: document.getElementById("csvFile"),
    uploadButton: document.getElementById("uploadButton"),
    uploadMeta: document.getElementById("uploadMeta"),
    schemaPreview: document.getElementById("schemaPreview"),
    sessionBadge: document.getElementById("sessionBadge"),
    chatFeed: document.getElementById("chatFeed"),
    queryForm: document.getElementById("queryForm"),
    questionInput: document.getElementById("questionInput"),
    insightCard: document.getElementById("insightCard"),
    sqlCard: document.getElementById("sqlCard"),
    chartContainer: document.getElementById("chartContainer"),
    tableContainer: document.getElementById("tableContainer"),
};

function setStatus(label, mode = "idle") {
    elements.sessionBadge.textContent = label;
    elements.sessionBadge.className = `status-pill ${mode === "live" ? "status-live" : "status-idle"}`;
}

function appendMessage(role, content) {
    const article = document.createElement("article");
    article.className = `message ${role}`;
    article.innerHTML = `<div class="message-role">${role === "user" ? "You" : "Assistant"}</div><p>${content}</p>`;
    elements.chatFeed.appendChild(article);
    elements.chatFeed.scrollTop = elements.chatFeed.scrollHeight;
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function renderTable(columns, rows) {
    if (!rows.length) {
        elements.tableContainer.className = "table-container empty-state";
        elements.tableContainer.textContent = "No rows returned for this query.";
        return;
    }

    const header = columns.map((column) => `<th>${escapeHtml(column)}</th>`).join("");
    const body = rows
        .map((row) => `<tr>${columns.map((column) => `<td>${escapeHtml(row[column] ?? "")}</td>`).join("")}</tr>`)
        .join("");

    elements.tableContainer.className = "table-container";
    elements.tableContainer.innerHTML = `<table class="result-table"><thead><tr>${header}</tr></thead><tbody>${body}</tbody></table>`;
}

function renderChart(chartJson) {
    if (!chartJson) {
        elements.chartContainer.className = "chart-container empty-state";
        elements.chartContainer.textContent = "No suitable chart detected for this result.";
        return;
    }

    elements.chartContainer.className = "chart-container";
    const chartSpec = JSON.parse(chartJson);
    Plotly.newPlot(elements.chartContainer, chartSpec.data, chartSpec.layout, {
        responsive: true,
        displayModeBar: false,
    });
}

function setInsight(text, isError = false) {
    elements.insightCard.className = isError ? "insight-copy error-banner" : "insight-copy";
    elements.insightCard.textContent = text;
}

function setSql(text) {
    elements.sqlCard.className = "sql-card";
    elements.sqlCard.textContent = text || "No SQL generated yet.";
}

async function uploadDataset() {
    const file = elements.csvFile.files[0];
    if (!file) {
        setInsight("Choose a CSV file before uploading.", true);
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    elements.uploadButton.disabled = true;
    elements.uploadButton.textContent = "Loading...";
    elements.uploadMeta.textContent = "Ingesting dataset and preparing schema...";

    try {
        const response = await fetch("/api/upload", { method: "POST", body: formData });
        const payload = await response.json();
        if (!response.ok) {
            throw new Error(payload.detail || "Upload failed.");
        }

        state.sessionId = payload.session_id;
        setStatus(`Dataset live: ${payload.table_name}`, "live");
        elements.uploadMeta.textContent = `${payload.row_count} rows loaded from ${payload.file_name}`;
        elements.schemaPreview.textContent = payload.schema;
        setInsight("Dataset uploaded successfully. Ask your first question to start the analysis flow.");
        renderTable(payload.columns, payload.preview);
        elements.chartContainer.className = "chart-container empty-state";
        elements.chartContainer.textContent = "Ask a question to generate a chart.";
        setSql("No SQL generated yet.");
    } catch (error) {
        setInsight(error.message, true);
        elements.uploadMeta.textContent = "Upload failed.";
        setStatus("Awaiting dataset", "idle");
    } finally {
        elements.uploadButton.disabled = false;
        elements.uploadButton.textContent = "Load Dataset";
    }
}

async function submitQuery(event) {
    event.preventDefault();

    const question = elements.questionInput.value.trim();
    if (!question) {
        return;
    }
    if (!state.sessionId) {
        setInsight("Upload a dataset before sending a question.", true);
        return;
    }

    appendMessage("user", escapeHtml(question));
    elements.questionInput.value = "";
    elements.queryForm.classList.add("loading");
    setInsight("Analyzing your dataset...");

    const formData = new FormData();
    formData.append("session_id", state.sessionId);
    formData.append("question", question);

    try {
        const response = await fetch("/api/query", { method: "POST", body: formData });
        const payload = await response.json();
        if (!response.ok) {
            throw new Error(payload.detail || "Query failed.");
        }

        if (payload.error) {
            appendMessage("assistant", escapeHtml(payload.error));
            setInsight(payload.error, true);
            setSql(payload.sql || "No SQL generated.");
            renderTable([], []);
            renderChart(null);
            return;
        }

        appendMessage("assistant", escapeHtml(payload.insight || "Analysis complete."));
        setInsight(payload.insight || "Analysis complete.");
        setSql(payload.sql);
        renderTable(payload.columns, payload.rows);
        renderChart(payload.chart);
    } catch (error) {
        appendMessage("assistant", escapeHtml(error.message));
        setInsight(error.message, true);
    } finally {
        elements.queryForm.classList.remove("loading");
    }
}

elements.uploadButton.addEventListener("click", uploadDataset);
elements.queryForm.addEventListener("submit", submitQuery);
