/* ─────────────────────────────────────────────────────────────────────
   AI Business Intelligence Copilot — app.js
   Industry-grade frontend: business-only guard, KPI bar, suggestion chips,
   toast notifications, typing indicator, CSV export, domain modal, Ctrl+Enter
   ───────────────────────────────────────────────────────────────────── */

"use strict";

/* ── State ─────────────────────────────────────────────────────────── */
const state = {
    sessionId:      null,
    currentColumns: [],
    currentRows:    [],
    lastQuestion:   "",
    uploadedFileName: "",
    lastChartData:  null,
};

/* ── Element refs ───────────────────────────────────────────────────── */
const el = {
    csvFile:           document.getElementById("csvFile"),
    uploadButton:      document.getElementById("uploadButton"),
    uploadMeta:        document.getElementById("uploadMeta"),
    uploadZone:        document.getElementById("uploadZone"),
    schemaPreview:     document.getElementById("schemaPreview"),
    sessionBadge:      document.getElementById("sessionBadge"),
    kpiBar:            document.getElementById("kpiBar"),
    kpiRows:           document.getElementById("kpiRows"),
    kpiCols:           document.getElementById("kpiCols"),
    kpiNumeric:        document.getElementById("kpiNumeric"),
    kpiDate:           document.getElementById("kpiDate"),
    suggestionsSection:document.getElementById("suggestionsSection"),
    suggestionChips:   document.getElementById("suggestionChips"),
    chatFeed:          document.getElementById("chatFeed"),
    queryForm:         document.getElementById("queryForm"),
    questionInput:     document.getElementById("questionInput"),
    charCounter:       document.getElementById("charCounter"),
    submitBtn:         document.getElementById("submitBtn"),
    insightCard:       document.getElementById("insightCard"),
    recommendationCard: document.getElementById("recommendationCard"),
    chartContainer:    document.getElementById("chartContainer"),
    tableContainer:    document.getElementById("tableContainer"),
    rowCountBadge:     document.getElementById("rowCountBadge"),
    exportBtn:         document.getElementById("exportBtn"),
    toastContainer:    document.getElementById("toastContainer"),
    domainModal:       document.getElementById("domainModal"),
    modalDismiss:      document.getElementById("modalDismiss"),
    successModal:      document.getElementById("successModal"),
    successModalDismiss: document.getElementById("successModalDismiss"),
    successModalFileName: document.getElementById("successModalFileName"),
    modelBadge:        document.getElementById("modelBadge"),
    
    // View Toggles & Dashboard
    viewChatBtn:       document.getElementById("viewChatBtn"),
    viewDashboardBtn:  document.getElementById("viewDashboardBtn"),
    chatView:          document.getElementById("chatView"),
    dashboardView:     document.getElementById("dashboardView"),
    healthPanel:       document.getElementById("healthPanel"),
    healthIcon:        document.getElementById("healthIcon"),
    healthMessage:     document.getElementById("healthMessage"),
    chartTypeToggles:  document.getElementById("chartTypeToggles"),
    pinChartBtn:       document.getElementById("pinChartBtn"),
    dashboardGrid:     document.getElementById("dashboardGrid"),
    dashboardEmpty:    document.getElementById("dashboardEmpty"),

    // History
    toggleHistoryBtn:  document.getElementById("toggleHistoryBtn"),
    historySidebar:    document.getElementById("historySidebar"),
    historyList:       document.getElementById("historyList"),
};

/* ══════════════════════════════════════════════════════════════════════
   TOAST SYSTEM
   ══════════════════════════════════════════════════════════════════════ */
function showToast(message, type = "info", durationMs = 4000) {
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <span class="toast-dot"></span>
        <span class="toast-msg">${escapeHtml(message)}</span>
        <button class="toast-close" aria-label="Dismiss">&times;</button>`;
    el.toastContainer.appendChild(toast);

    const dismiss = () => {
        toast.style.opacity = "0";
        toast.style.transform = "translateX(40px)";
        toast.style.transition = "opacity 200ms, transform 200ms";
        setTimeout(() => toast.remove(), 220);
    };
    toast.querySelector(".toast-close").addEventListener("click", dismiss);
    if (durationMs > 0) setTimeout(dismiss, durationMs);
    return dismiss;
}

/* ══════════════════════════════════════════════════════════════════════
   DOMAIN MODAL
   ══════════════════════════════════════════════════════════════════════ */
function showDomainModal(fileName) {
    // Inject the filename into the modal so the user sees exactly which file triggered it
    const modalTitle = el.domainModal.querySelector("#modalTitle");
    const modalBody  = el.domainModal.querySelector(".modal-file-name");
    if (modalTitle) modalTitle.textContent = "Non-Business Dataset Detected";
    if (modalBody)  modalBody.textContent  = fileName || "";
    el.domainModal.removeAttribute("hidden");
    el.domainModal.focus();
}
function hideDomainModal() {
    el.domainModal.setAttribute("hidden", "");
}

el.modalDismiss.addEventListener("click", () => {
    hideDomainModal();
    // Full reset — clear file, session, upload zone back to default
    el.csvFile.value = "";
    state.sessionId  = null;
    state.uploadedFileName = "";
    resetUploadZone();
    el.uploadMeta.textContent = "Please upload a business dataset (sales, revenue, operations, etc.)";
    el.schemaPreview.textContent = "";
    el.kpiBar.hidden = true;
    el.suggestionsSection.hidden = true;
    setStatus("Awaiting dataset", "idle");
});

el.successModalDismiss.addEventListener("click", () => {
    el.successModal.hidden = true;
});

/* ══════════════════════════════════════════════════════════════════════
   STATUS & UI HELPERS
   ══════════════════════════════════════════════════════════════════════ */
function setStatus(label, mode = "idle") {
    el.sessionBadge.textContent = label;
    el.sessionBadge.className = `status-pill ${mode === "live" ? "status-live" : "status-idle"}`;
    if (mode === "live") {
        const dot = document.createElement("span");
        dot.className = "live-dot";
        el.sessionBadge.prepend(dot);
    }
}

/** Update the upload zone to show the selected filename visually */
function setUploadZoneFile(file) {
    const sizeKb = (file.size / 1024).toFixed(1);
    el.uploadZone.innerHTML = `
        <div class="upload-file-selected">
            <div class="upload-file-icon">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                    <line x1="16" y1="13" x2="8" y2="13"/>
                    <line x1="16" y1="17" x2="8" y2="17"/>
                    <polyline points="10 9 9 9 8 9"/>
                </svg>
            </div>
            <div class="upload-file-info">
                <span class="upload-file-name">${escapeHtml(file.name)}</span>
                <span class="upload-file-size">${sizeKb} KB &nbsp;·&nbsp; CSV ready to load</span>
            </div>
            <div class="upload-file-check">✓</div>
        </div>`;
    el.uploadZone.classList.add("file-selected");
}

/** Reset upload zone back to the default drop state */
function resetUploadZone() {
    el.uploadZone.innerHTML = `
        <div class="upload-icon">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
        </div>
        <span class="upload-title">Drop your business CSV here</span>
        <span class="upload-subtitle">Sales · Revenue · Operations · Finance · HR</span>`;
    el.uploadZone.classList.remove("file-selected");
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function setInsight(text, style = "normal") {
    el.insightCard.className = "insight-copy";
    if (style === "error")    el.insightCard.classList.add("error-banner");
    if (style === "refusal")  el.insightCard.classList.add("business-refusal-banner");
    
    el.insightCard.textContent = text || "No insights available.";
}

function setRecommendation(text) {
    if (!text) {
        el.recommendationCard.className = "recommendation-copy empty-state";
        el.recommendationCard.innerHTML = `<div class="empty-icon">🚀</div><p>Actionable recommendations will appear here.</p>`;
        return;
    }
    el.recommendationCard.className = "recommendation-copy";
    el.recommendationCard.textContent = text;
}

function resetInsightToEmpty() {
    el.insightCard.className = "insight-copy empty-state";
    el.insightCard.innerHTML = `<div class="empty-icon">🧠</div><p>Your AI business insight will appear here after analysis.</p>`;
    el.recommendationCard.className = "recommendation-copy empty-state";
    el.recommendationCard.innerHTML = `<div class="empty-icon">🚀</div><p>Actionable recommendations will appear here.</p>`;
}

/* ══════════════════════════════════════════════════════════════════════
   CHAT MESSAGES
   ══════════════════════════════════════════════════════════════════════ */
function appendMessage(role, content, style = "normal") {
    const article = document.createElement("article");
    const isUser = role === "user";
    const isRefusal = style === "refusal";
    const isError   = style === "error";

    let cls = `message ${role}`;
    if (isRefusal) cls += " business-refusal";
    if (isError)   cls += " error";
    article.className = cls;

    const avatarHtml = isUser
        ? `<div class="role-avatar user-avatar">You</div><span>You</span>`
        : `<div class="role-avatar assistant-avatar">BI</div><span>Business Copilot</span>`;

    article.innerHTML = `
        <div class="message-role">${avatarHtml}</div>
        <p>${escapeHtml(content)}</p>`;
    el.chatFeed.appendChild(article);
    el.chatFeed.scrollTop = el.chatFeed.scrollHeight;
    return article;
}

function showTypingIndicator() {
    const indicator = document.createElement("div");
    indicator.className = "typing-indicator";
    indicator.id = "typingIndicator";
    indicator.innerHTML = `
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>`;
    el.chatFeed.appendChild(indicator);
    el.chatFeed.scrollTop = el.chatFeed.scrollHeight;
}

function removeTypingIndicator() {
    const ind = document.getElementById("typingIndicator");
    if (ind) ind.remove();
}

/* ══════════════════════════════════════════════════════════════════════
   TABLE RENDERING
   ══════════════════════════════════════════════════════════════════════ */
function renderTable(columns, rows) {
    state.currentColumns = columns;
    state.currentRows    = rows;

    if (!rows || !rows.length) {
        el.tableContainer.className = "table-container empty-state";
        el.tableContainer.innerHTML = `<div class="empty-icon">📋</div><p>No rows returned for this query.</p>`;
        el.rowCountBadge.hidden = true;
        el.exportBtn.hidden = true;
        return;
    }

    const header = columns.map(c => `<th>${escapeHtml(c)}</th>`).join("");
    const body   = rows.map(row =>
        `<tr>${columns.map(c => `<td>${escapeHtml(row[c] ?? "")}</td>`).join("")}</tr>`
    ).join("");

    el.tableContainer.className = "table-container";
    el.tableContainer.innerHTML =
        `<table class="result-table"><thead><tr>${header}</tr></thead><tbody>${body}</tbody></table>`;

    // Row count badge
    el.rowCountBadge.textContent = `${rows.length} row${rows.length !== 1 ? "s" : ""}`;
    el.rowCountBadge.hidden = false;
    el.exportBtn.hidden = false;
}

/* ══════════════════════════════════════════════════════════════════════
   CHART RENDERING
   ══════════════════════════════════════════════════════════════════════ */
function renderChart(chartJson) {
    if (!chartJson) {
        el.chartContainer.className = "chart-container empty-state";
        el.chartContainer.innerHTML = `<div class="empty-icon">📈</div><p>No suitable chart for this result set.</p>`;
        el.chartTypeToggles.hidden = true;
        el.pinChartBtn.hidden = true;
        return;
    }
    try {
        el.chartContainer.className = "chart-container";
        el.chartContainer.innerHTML = "";
        el.chartTypeToggles.hidden = false;
        el.pinChartBtn.hidden = false;
        const spec = JSON.parse(chartJson);

        // Apply dark theme to chart layout
        const layout = {
            ...spec.layout,
            paper_bgcolor: "rgba(0,0,0,0)",
            plot_bgcolor:  "rgba(0,0,0,0)",
            font:  { color: "#b8c5da", family: "Inter, sans-serif", size: 12 },
            xaxis: { ...(spec.layout?.xaxis || {}), gridcolor: "rgba(255,255,255,0.06)", zerolinecolor: "rgba(255,255,255,0.10)" },
            yaxis: { ...(spec.layout?.yaxis || {}), gridcolor: "rgba(255,255,255,0.06)", zerolinecolor: "rgba(255,255,255,0.10)" },
            margin: { l: 48, r: 20, t: 36, b: 48 },
        };

        Plotly.newPlot(el.chartContainer, spec.data, layout, {
            responsive: true,
            displayModeBar: false,
        });
    } catch {
        el.chartContainer.className = "chart-container empty-state";
        el.chartContainer.innerHTML = `<div class="empty-icon">📈</div><p>Could not render chart for this result.</p>`;
    }
}

/* ══════════════════════════════════════════════════════════════════════
   CSV EXPORT
   ══════════════════════════════════════════════════════════════════════ */
function exportTableAsCsv() {
    if (!state.currentColumns.length || !state.currentRows.length) return;

    const header = state.currentColumns.map(c => `"${c}"`).join(",");
    const rows   = state.currentRows.map(row =>
        state.currentColumns.map(c => {
            const val = String(row[c] ?? "").replaceAll('"', '""');
            return `"${val}"`;
        }).join(",")
    );

    const csv  = [header, ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url  = URL.createObjectURL(blob);
    const link = document.createElement("a");
    const name = (state.lastQuestion || "business_analysis").slice(0, 40).replace(/\s+/g, "_").toLowerCase();
    link.href     = url;
    link.download = `${name}_results.csv`;
    link.click();
    URL.revokeObjectURL(url);
    showToast("Results exported as CSV.", "success");
}

/* ══════════════════════════════════════════════════════════════════════
   KPI BAR
   ══════════════════════════════════════════════════════════════════════ */
function renderKpiBar(payload) {
    const numericCount = (payload.numeric_columns || []).length;
    const dateCount    = (payload.date_columns    || []).length;

    el.kpiRows.querySelector(".kpi-num").textContent    = (payload.row_count || 0).toLocaleString();
    el.kpiCols.querySelector(".kpi-num").textContent    = (payload.columns || []).length;
    el.kpiNumeric.querySelector(".kpi-num").textContent = numericCount;
    el.kpiDate.querySelector(".kpi-num").textContent    = dateCount;
    el.kpiBar.hidden = false;
}

/* ══════════════════════════════════════════════════════════════════════
   SUGGESTED QUESTIONS
   ══════════════════════════════════════════════════════════════════════ */
function buildSuggestedQuestions(columns, numericCols) {
    const numeric = numericCols || [];
    const all     = columns || [];
    const suggestions = [];

    // Try to pick meaningful columns for auto-suggestions
    const valueCol   = numeric[0] || all[all.length - 1] || "value";
    const dimCols    = all.filter(c => !numeric.includes(c)).slice(0, 3);
    const dim1       = dimCols[0] || all[0] || "category";
    const dim2       = dimCols[1] || all[1] || "segment";

    suggestions.push(`What is the total ${valueCol} by ${dim1}?`);
    suggestions.push(`Which ${dim1} has the highest ${valueCol}?`);
    suggestions.push(`Show me the top 5 ${dim1}s ranked by ${valueCol}.`);
    if (dim2 && dim2 !== dim1) {
        suggestions.push(`Compare ${valueCol} across different ${dim2}s.`);
    }
    suggestions.push(`What is the overall trend in ${valueCol}?`);

    el.suggestionChips.innerHTML = "";
    suggestions.slice(0, 5).forEach(text => {
        const chip = document.createElement("button");
        chip.className = "suggestion-chip";
        chip.type = "button";
        chip.textContent = text;
        chip.addEventListener("click", () => {
            el.questionInput.value = text;
            el.questionInput.focus();
            updateCharCounter();
        });
        el.suggestionChips.appendChild(chip);
    });

    el.suggestionsSection.hidden = false;
}

/* ══════════════════════════════════════════════════════════════════════
   CHARACTER COUNTER
   ══════════════════════════════════════════════════════════════════════ */
function updateCharCounter() {
    const len = el.questionInput.value.length;
    el.charCounter.textContent = `${len} / 500`;
    el.charCounter.style.color = len > 450 ? "var(--warn)" : "";
}

/* ══════════════════════════════════════════════════════════════════════
   UPLOAD DATASET
   ══════════════════════════════════════════════════════════════════════ */
async function uploadDataset() {
    const file = el.csvFile.files[0];
    if (!file) {
        showToast("Please choose a CSV file before uploading.", "error");
        return;
    }
    if (!file.name.toLowerCase().endsWith(".csv")) {
        showToast("Only CSV files are supported.", "error");
        return;
    }

    state.uploadedFileName = file.name;

    // UI — loading state
    el.uploadButton.disabled = true;
    el.uploadButton.innerHTML = `<span class="skeleton" style="width:100px;height:14px;display:inline-block;border-radius:6px;"></span>`;
    el.uploadMeta.textContent = `Analysing "${file.name}"…`;
    setStatus("Loading…", "idle");

    const formData = new FormData();
    formData.append("file", file);

    try {
        const response = await fetch("/api/upload", { method: "POST", body: formData });
        const payload  = await response.json();

        if (!response.ok) throw new Error(payload.detail || "Upload failed.");

        state.sessionId = payload.session_id;

        // KPI bar
        renderKpiBar(payload);

        // Session badge
        setStatus(`Live: ${payload.table_name}`, "live");
        el.uploadMeta.textContent = `✓ ${(payload.row_count || 0).toLocaleString()} rows · ${(payload.columns || []).length} columns · "${payload.file_name}"`;
        el.modelBadge.textContent = "Groq · LLaMA 3.3";

        // Health check
        if (payload.data_health) {
            const h = payload.data_health;
            el.healthPanel.hidden = false;
            el.healthPanel.className = "health-panel"; 
            if (h.missing_values === 0 && h.duplicate_rows === 0) {
                el.healthPanel.classList.add("health-good");
                el.healthIcon.textContent = "✅";
                el.healthMessage.textContent = `Data is clean (0 duplicates, 0 missing). Ready for analysis.`;
            } else {
                el.healthPanel.classList.add("health-warning");
                el.healthIcon.textContent = "⚠️";
                el.healthMessage.textContent = `Warning: ${h.missing_values} missing values & ${h.duplicate_rows} duplicates detected. Analysis may be skewed.`;
            }
        }

        // Schema
        el.schemaPreview.textContent = payload.schema || "";

        // Table preview
        renderTable(payload.columns, payload.preview);

        // Suggested questions
        buildSuggestedQuestions(payload.columns, payload.numeric_columns);

        // Reset insight and chart
        resetInsightToEmpty();
        el.chartContainer.className = "chart-container empty-state";
        el.chartContainer.innerHTML = `<div class="empty-icon">📈</div><p>Ask a business question to generate a chart.</p>`;

        // Domain check — show red modal for non-business datasets, otherwise show success popup
        if (payload.dataset_domain === "NOT_BUSINESS") {
            showDomainModal(payload.file_name);
        } else {
            el.successModalFileName.textContent = payload.file_name;
            el.successModal.hidden = false;
        }

    } catch (err) {
        showToast(err.message || "Upload failed. Please try again.", "error");
        el.uploadMeta.textContent = "Upload failed. Please try again.";
        resetUploadZone();
        setStatus("Awaiting dataset", "idle");
    } finally {
        el.uploadButton.disabled = false;
        el.uploadButton.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            Load Dataset`;
    }
}

/* ══════════════════════════════════════════════════════════════════════
   SUBMIT QUERY
   ══════════════════════════════════════════════════════════════════════ */
async function submitQuery(event) {
    event.preventDefault();

    const question = el.questionInput.value.trim();
    if (!question) return;

    if (!state.sessionId) {
        showToast("Upload a business CSV before sending a question.", "error");
        return;
    }

    state.lastQuestion = question;

    // Append user message
    appendMessage("user", question);
    el.questionInput.value = "";
    updateCharCounter();

    // Disable form & show typing
    el.submitBtn.disabled = true;
    showTypingIndicator();
    resetInsightToEmpty();
    el.insightCard.innerHTML = `<div class="skeleton" style="height:14px;margin-bottom:8px;"></div><div class="skeleton" style="height:14px;width:70%;"></div>`;

    const formData = new FormData();
    formData.append("session_id", state.sessionId);
    formData.append("question", question);

    try {
        const response = await fetch("/api/query", { method: "POST", body: formData });
        const payload  = await response.json();
        removeTypingIndicator();

        if (!response.ok) throw new Error(payload.detail || "Query failed.");

        const isRefusal = payload.error && payload.error.includes("Business Intelligence Copilot");
        const isError   = !!payload.error && !isRefusal;

        if (isRefusal) {
            // Business domain refusal
            appendMessage("assistant", payload.error, "refusal");
            setInsight(payload.error, "refusal");
            setRecommendation("");
            renderTable([], []);
            renderChart(null);
            showToast("This question is outside the business analytics scope.", "info");
            return;
        }

        if (isError) {
            appendMessage("assistant", payload.error, "error");
            setInsight(payload.error, "error");
            setRecommendation("");
            renderTable([], []);
            renderChart(null);
            showToast("Could not complete the analysis. Try rephrasing.", "error");
            return;
        }

        // Success path
        appendMessage("assistant", payload.insight || "Analysis complete.");
        setInsight(payload.insight || "Analysis complete.");
        setRecommendation(payload.recommendation || "");
        renderTable(payload.columns || [], payload.rows || []);
        renderChart(payload.chart || null);
        showToast("Analysis complete.", "success", 3000);

    } catch (err) {
        removeTypingIndicator();
        appendMessage("assistant", err.message || "An unexpected error occurred.", "error");
        setInsight(err.message || "An unexpected error occurred.", "error");
        showToast("Request failed. Please try again.", "error");
    } finally {
        el.submitBtn.disabled = false;
        el.chatFeed.scrollTop = el.chatFeed.scrollHeight;
    }
}

/* ══════════════════════════════════════════════════════════════════════
   DRAG-AND-DROP
   ══════════════════════════════════════════════════════════════════════ */
el.uploadZone.addEventListener("dragover", e => {
    e.preventDefault();
    el.uploadZone.classList.add("drag-over");
});
el.uploadZone.addEventListener("dragleave", () => {
    el.uploadZone.classList.remove("drag-over");
});
el.uploadZone.addEventListener("drop", e => {
    e.preventDefault();
    el.uploadZone.classList.remove("drag-over");
    const files = e.dataTransfer?.files;
    if (files && files.length) {
        // Manually set the file and update the zone
        const dt = new DataTransfer();
        dt.items.add(files[0]);
        el.csvFile.files = dt.files;
        setUploadZoneFile(files[0]);
        el.uploadMeta.textContent = `Ready to load: ${files[0].name}`;
    }
});

/* ══════════════════════════════════════════════════════════════════════
   EVENT LISTENERS
   ══════════════════════════════════════════════════════════════════════ */
el.uploadButton.addEventListener("click", uploadDataset);
el.queryForm.addEventListener("submit", submitQuery);
el.exportBtn.addEventListener("click", exportTableAsCsv);
el.questionInput.addEventListener("input", updateCharCounter);

// Ctrl+Enter to submit
el.questionInput.addEventListener("keydown", e => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        el.queryForm.requestSubmit();
    }
});

// When file is chosen — update upload zone UI AND meta text
el.csvFile.addEventListener("change", () => {
    const file = el.csvFile.files[0];
    if (file) {
        setUploadZoneFile(file);
        el.uploadMeta.textContent = `Ready to load: ${file.name}`;
    }
});

/* ══════════════════════════════════════════════════════════════════════
   VIEW TOGGLES & UI CONTROLS
   ══════════════════════════════════════════════════════════════════════ */
el.viewChatBtn?.addEventListener("click", () => {
    el.viewChatBtn.classList.add("active");
    el.viewDashboardBtn.classList.remove("active");
    el.chatView.hidden = false;
    el.dashboardView.hidden = true;
});
el.viewDashboardBtn?.addEventListener("click", () => {
    el.viewDashboardBtn.classList.add("active");
    el.viewChatBtn.classList.remove("active");
    el.chatView.hidden = true;
    el.dashboardView.hidden = false;
});

// Chart Type Toggles
document.querySelectorAll(".chart-type-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        if (!state.currentRows || state.currentRows.length === 0) return;
        document.querySelectorAll(".chart-type-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        
        const type = btn.dataset.type;
        try {
            const xCol = state.currentColumns[0];
            const yCols = state.currentColumns.filter(c => c !== xCol && state.currentRows[0][c] !== null && state.currentRows[0][c] !== "" && !isNaN(Number(state.currentRows[0][c])));
            
            if (yCols.length === 0) {
                console.warn("No numeric column found for manual charting.");
                return;
            }
            const yCol = yCols[0];
            
            const xData = state.currentRows.map(r => r[xCol]);
            const yData = state.currentRows.map(r => Number(r[yCol]));
            
            let data = [];
            if (type === "pie") {
                data = [{ labels: xData, values: yData, type: "pie", hole: 0.4, textinfo: "percent" }];
            } else {
                data = [{ x: xData, y: yData, type: type, marker: { color: "#3ecf8e" } }];
            }
            
            const layout = {
                paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
                font: { color: "#b8c5da", family: "Inter, sans-serif" }, margin: { l: 40, r: 20, t: 20, b: 40 },
                xaxis: { gridcolor: "rgba(255,255,255,0.06)" }, yaxis: { gridcolor: "rgba(255,255,255,0.06)" }
            };
            
            Plotly.newPlot(el.chartContainer, data, layout, { responsive: true, displayModeBar: false });
        } catch (e) {
            console.error(e);
        }
    });
});

// Pin to Dashboard
el.pinChartBtn?.addEventListener("click", () => {
    const existingData = el.chartContainer.data;
    const existingLayout = el.chartContainer.layout;
    if (!existingData || !existingLayout) return;
    
    const card = document.createElement("div");
    card.className = "dashboard-card";
    
    const title = document.createElement("div");
    title.className = "dashboard-card-title";
    title.textContent = state.lastQuestion || "Pinned Visualization";
    
    const chartDiv = document.createElement("div");
    chartDiv.className = "dashboard-card-chart";
    const id = "pinned-" + Math.random().toString(36).substr(2, 9);
    chartDiv.id = id;
    
    card.appendChild(title);
    card.appendChild(chartDiv);
    
    if (!el.dashboardEmpty.hidden) el.dashboardEmpty.hidden = true;
    el.dashboardGrid.appendChild(card);
    
    Plotly.newPlot(id, existingData, existingLayout, { responsive: true, displayModeBar: false });
    showToast("Chart pinned to dashboard!", "success");
});

/* ══════════════════════════════════════════════════════════════════════
   CHAT HISTORY
   ══════════════════════════════════════════════════════════════════════ */
async function loadHistoryList() {
    try {
        const response = await fetch("/api/history");
        if (!response.ok) throw new Error("Failed to load history");
        const sessions = await response.json();
        
        if (sessions.length === 0) {
            el.historyList.innerHTML = `<div class="history-empty">No previous sessions found.</div>`;
            return;
        }
        
        el.historyList.innerHTML = "";
        sessions.forEach(session => {
            const date = new Date(session.created_at).toLocaleDateString(undefined, {
                month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
            });
            const item = document.createElement("div");
            item.className = "history-item";
            item.innerHTML = `
                <div class="history-filename">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
                    </svg>
                    ${escapeHtml(session.file_name)}
                </div>
                <div class="history-date">${date} · ${(session.row_count || 0).toLocaleString()} rows</div>
            `;
            item.addEventListener("click", () => loadSession(session.session_id, item));
            el.historyList.appendChild(item);
        });
    } catch (err) {
        console.error(err);
        el.historyList.innerHTML = `<div class="history-empty">Failed to load history.</div>`;
    }
}

async function loadSession(sessionId, itemElement) {
    try {
        showToast("Loading past session...", "info", 2000);
        
        // Highlight active item
        document.querySelectorAll(".history-item").forEach(i => i.classList.remove("active"));
        if (itemElement) itemElement.classList.add("active");
        
        const response = await fetch(`/api/history/${sessionId}`);
        if (!response.ok) throw new Error("Failed to load session details.");
        const data = await response.json();
        
        const session = data.session;
        const messages = data.messages;
        
        state.sessionId = session.session_id;
        state.uploadedFileName = session.file_name;
        
        // Restore UI State
        setStatus(`Live: ${session.table_name}`, "live");
        el.uploadMeta.textContent = `✓ ${(session.row_count || 0).toLocaleString()} rows · "${session.file_name}"`;
        el.schemaPreview.textContent = session.schema_text || "";
        
        // Render KPI if it exists
        if (session.kpi_json) {
            el.kpiRows.querySelector(".kpi-num").textContent    = (session.kpi_json.row_count || 0).toLocaleString();
            el.kpiCols.querySelector(".kpi-num").textContent    = session.kpi_json.column_count;
            el.kpiNumeric.querySelector(".kpi-num").textContent = session.kpi_json.numeric_count;
            el.kpiDate.querySelector(".kpi-num").textContent    = session.kpi_json.date_count;
            el.kpiBar.hidden = false;
        }
        
        // Clear chat and restore messages
        el.chatFeed.innerHTML = "";
        
        // Intro message
        appendMessage("assistant", "Welcome back. I've reloaded your session. You can continue asking questions about this dataset.");
        
        let lastChart = null;
        let lastRows = [];
        let lastCols = [];
        let lastInsight = "";
        let lastRec = "";
        
        messages.forEach(msg => {
            if (msg.role === "user") {
                appendMessage("user", msg.content);
            } else {
                appendMessage("assistant", msg.content, msg.content.includes("Business Intelligence Copilot") ? "refusal" : (msg.insight ? "normal" : "error"));
                
                if (msg.insight) lastInsight = msg.insight;
                if (msg.recommendation) lastRec = msg.recommendation;
                if (msg.chart_json) lastChart = msg.chart_json;
                if (msg.rows && msg.rows.length > 0) lastRows = msg.rows;
                if (msg.columns && msg.columns.length > 0) lastCols = msg.columns;
            }
        });
        
        // Restore the last analysis output
        if (lastInsight) {
            setInsight(lastInsight);
            setRecommendation(lastRec);
        } else {
            resetInsightToEmpty();
        }
        
        renderTable(lastCols, lastRows);
        renderChart(lastChart ? lastChart : null);
        
        // Mobile sidebar collapse after selection
        if (window.innerWidth <= 720) {
            el.historySidebar.classList.add("collapsed");
        }
        
        showToast("Session restored.", "success");
        
    } catch (err) {
        showToast(err.message, "error");
    }
}

el.toggleHistoryBtn.addEventListener("click", () => {
    el.historySidebar.classList.toggle("collapsed");
});

// Init counter
updateCharCounter();
loadHistoryList();
