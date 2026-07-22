/**
 * app.js — Indian Kanoon Judgement Downloader
 * Handles: form interaction, SSE progress streaming, UI updates
 */

// ─── State ───────────────────────────────────────────────
let currentTaskId = null;
let eventSource = null;
let selectedFormat = "pdf";
let downloadedCount = 0;
let skippedCount = 0;
let failedCount = 0;
let totalAvailable = 0;

// ─── DOM Refs ─────────────────────────────────────────────
const form         = document.getElementById("download-form");
const downloadBtn  = document.getElementById("download-btn");
const cancelBtn    = document.getElementById("cancel-btn");
const openFolderBtn= document.getElementById("open-folder-btn");

const statusIcon   = document.getElementById("status-icon");
const statusTitle  = document.getElementById("status-title");
const statusSub    = document.getElementById("status-sub");
const statusCount  = document.getElementById("status-count");
const countDone    = document.getElementById("count-done");
const countTotal   = document.getElementById("count-total");

const progressWrap = document.getElementById("progress-wrap");
const progressFill = document.getElementById("progress-fill");
const progressPct  = document.getElementById("progress-pct");

const currentFileEl   = document.getElementById("current-file");
const currentFileName = document.getElementById("current-file-name");

const resultsHeader = document.getElementById("results-header");
const fileList      = document.getElementById("file-list");
const emptyState    = document.getElementById("empty-state");
const tagSuccess    = document.getElementById("tag-success");
const tagError      = document.getElementById("tag-error");
const toast         = document.getElementById("toast");

const maxCountSlider  = document.getElementById("max-count");
const maxCountDisplay = document.getElementById("max-count-display");
const btnPdf   = document.getElementById("btn-pdf");
const btnHtml  = document.getElementById("btn-html");
const formatNote = document.getElementById("format-note");

const yearSelect = document.getElementById("year-select");
const monthSelect = document.getElementById("month-select");
const courtSelect = document.getElementById("court-select");
const totalCountValue = document.getElementById("total-count-value");

// ─── Init ─────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  // Enable download button only when form is valid
  enableDownloadBtn();

  // Slider live display
  maxCountSlider.addEventListener("input", () => {
    maxCountDisplay.textContent = maxCountSlider.value;
  });

  // Format toggle
  btnPdf.addEventListener("click", () => setFormat("pdf"));
  btnHtml.addEventListener("click", () => setFormat("html"));

  // Form submit
  form.addEventListener("submit", onFormSubmit);

  // Cancel
  cancelBtn.addEventListener("click", onCancel);

  // Open folder
  openFolderBtn.addEventListener("click", onOpenFolder);

  // Dynamic count updates
  yearSelect.addEventListener("change", fetchCount);
  monthSelect.addEventListener("change", fetchCount);
  courtSelect.addEventListener("change", fetchCount);

  // Initial fetch
  fetchCount();
});

function fetchCount() {
  if (!totalCountValue) return;
  totalCountValue.innerHTML = '<div class="spinner" style="width:14px;height:14px;border-width:2px;display:inline-block;margin-right:6px"></div><span style="font-size:14px">Calculating...</span>';
  
  const year = parseInt(yearSelect.value);
  const month = monthSelect.value;
  const court = courtSelect.value;
  
  fetch("/api/count", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ year, month, court })
  })
  .then(res => res.json())
  .then(data => {
    if(data.error) {
      totalCountValue.textContent = "Error";
    } else {
      totalCountValue.textContent = data.count.toLocaleString();
    }
  })
  .catch(err => {
    totalCountValue.textContent = "Failed";
  });
}

function enableDownloadBtn() {
  downloadBtn.disabled = false;
}

function setFormat(fmt) {
  selectedFormat = fmt;
  btnPdf.classList.toggle("active", fmt === "pdf");
  btnHtml.classList.toggle("active", fmt === "html");
  formatNote.textContent = fmt === "pdf"
    ? "PDF requires wkhtmltopdf installed."
    : "HTML files open directly in your browser.";
}

// ─── Form Submit ──────────────────────────────────────────
async function onFormSubmit(e) {
  e.preventDefault();

  const year      = parseInt(document.getElementById("year-select").value);
  const month     = document.getElementById("month-select").value;
  const court     = document.getElementById("court-select").value;
  const maxCount  = parseInt(maxCountSlider.value);
  const usePdf    = selectedFormat === "pdf";

  resetUI();
  setStatus("running", "🔍", "Searching...", `Fetching ${month} ${year} judgements from ${court}...`);

  downloadBtn.style.display = "none";
  cancelBtn.style.display = "block";
  progressWrap.style.display = "flex";
  statusCount.style.display = "flex";

  try {
    const res = await fetch("/api/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ year, month, court, max_count: maxCount, use_pdf: usePdf }),
    });

    if (!res.ok) throw new Error("Failed to start download task");
    const { task_id } = await res.json();
    currentTaskId = task_id;

    // Open SSE stream
    subscribeToTask(task_id);

  } catch (err) {
    setStatus("error", "❌", "Error", err.message);
    resetButtons();
    showToast("❌ Could not start download: " + err.message);
  }
}

// ─── SSE Streaming ───────────────────────────────────────
function subscribeToTask(taskId) {
  if (eventSource) eventSource.close();

  eventSource = new EventSource(`/api/stream/${taskId}`);

  eventSource.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      handleEvent(data);
    } catch (err) {
      console.error("Failed to parse SSE event:", err);
    }
  };

  eventSource.onerror = () => {
    console.warn("SSE connection lost");
    eventSource.close();
  };
}

function handleEvent(data) {
  switch (data.type) {

    case "start":
      setStatus("running", "🔍", "Searching...", data.message);
      break;

    case "search_progress":
      setStatus("running", "🔍", "Searching...", data.message);
      countTotal.textContent = data.total;
      break;

    case "search_done":
      countTotal.textContent = data.total;
      totalAvailable = data.total;
      setStatus("running", "⬇", "Downloading...", data.message);
      if (data.total > 0) {
        resultsHeader.style.display = "flex";
        emptyState.style.display = "none";
      }
      break;

    case "download_progress":
      updateProgress(data.current, data.total, data.percentage);
      currentFileEl.style.display = "flex";
      currentFileName.textContent = data.title;
      setStatus("running", "⬇", `Downloading ${data.current} / ${data.total}`, data.title);
      countDone.textContent = data.current;
      break;

    case "file_done":
      if (data.skipped) {
        skippedCount++;
      } else {
        downloadedCount++;
        addFileCard(data, false);
      }
      tagSuccess.textContent = `${downloadedCount} saved`;
      countDone.textContent = downloadedCount + skippedCount;
      updateSummary();
      break;

    case "file_error":
      failedCount++;
      addFileCard(data, true);
      tagError.style.display = "inline";
      tagError.textContent = `${failedCount} failed`;
      updateSummary();
      break;

    case "done":
      onDownloadDone(data);
      break;

    case "error":
      setStatus("error", "❌", "Error", data.message);
      resetButtons();
      showToast("❌ " + data.message);
      break;

    case "cancelled":
      setStatus("idle", "⏸", "Cancelled", data.message);
      resetButtons();
      showToast("⏸ Download cancelled.");
      break;
  }
}

// ─── Event Handlers ──────────────────────────────────────
function onDownloadDone(data) {
  eventSource && eventSource.close();
  currentFileEl.style.display = "none";
  updateProgress(100, 100, 100);

  let title = `Complete! ${downloadedCount} downloaded`;
  let sub = `${data.failed > 0 ? data.failed + " failed" : ""}`;

  if (skippedCount > 0 && downloadedCount === 0) {
    title = `Complete! 0 downloaded, ${skippedCount} skipped`;
    sub = `All ${skippedCount} judgements already exist. No new files were downloaded.`;
    
    emptyState.innerHTML = `
      <div class="empty-icon" aria-hidden="true" style="margin-bottom: 16px;">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="color: #4a5568;"><path d="M22 12h-6l-2 3h-4l-2-3H2"></path><path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"></path><line x1="9" y1="15" x2="15" y2="15"></line></svg>
      </div>
      <h3 style="font-size: 18px; margin-bottom: 8px;">No newly downloaded files</h3>
      <p style="color: var(--text-secondary); max-width: 300px; margin: 0 auto; line-height: 1.5;">All available judgements for the selected filters<br>have already been downloaded.</p>
    `;
    emptyState.style.display = "flex";
  } else if (skippedCount > 0 && downloadedCount > 0) {
    title = `Complete! ${downloadedCount} downloaded, ${skippedCount} skipped`;
  } else if (totalAvailable === 0) {
    title = `0 judgements found`;
  }

  setStatus(
    "done", "✅",
    title,
    sub
  );
  resetButtons();
  
  if (totalAvailable === 0 && data.failed === 0) {
    showToast(`⚠️ 0 judgements found for the selected criteria.`);
  } else if (data.failed > 0) {
    showToast(`⚠️ ${downloadedCount} downloaded, ${data.failed} failed. (Check console or server logs for blocks)`);
  }
}

function updateSummary() {
  const summaryBlock = document.getElementById("download-summary");
  if (summaryBlock) {
    summaryBlock.style.display = "block";
    document.getElementById("summary-total").textContent = totalAvailable;
    document.getElementById("summary-downloaded").textContent = downloadedCount;
    document.getElementById("summary-skipped").textContent = skippedCount;
  }
}

async function onCancel() {
  if (!currentTaskId) return;
  try {
    await fetch(`/api/cancel/${currentTaskId}`, { method: "POST" });
    showToast("Cancelling...");
  } catch (err) {
    console.error("Cancel failed:", err);
  }
}

async function onOpenFolder() {
  try {
    await fetch("/api/open_folder", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
  } catch (err) {
    showToast("❌ Could not open folder: " + err.message);
  }
}

// ─── UI Helpers ──────────────────────────────────────────
function resetUI() {
  downloadedCount = 0;
  skippedCount = 0;
  failedCount = 0;
  totalAvailable = 0;
  fileList.innerHTML = "";
  fileList.appendChild(emptyState);
  emptyState.innerHTML = `
    <div class="empty-icon" aria-hidden="true"></div>
    <h3>No downloads yet</h3>
    <p>Choose your filters and click <strong>Start Download</strong> to begin fetching judgements.</p>
  `;
  emptyState.style.display = "none";
  tagSuccess.textContent = "0 processed";
  tagError.style.display = "none";
  tagError.textContent = "0 failed";
  resultsHeader.style.display = "none";
  
  const summaryBlock = document.getElementById("download-summary");
  if (summaryBlock) {
    summaryBlock.style.display = "none";
  }
  
  updateProgress(0, 0, 0);
  currentFileEl.style.display = "none";
  countDone.textContent = "0";
  countTotal.textContent = "0";
}

function resetButtons() {
  downloadBtn.style.display = "flex";
  cancelBtn.style.display = "none";
}

function setStatus(state, icon, title, sub) {
  statusIcon.textContent = icon;
  statusTitle.textContent = title;
  statusSub.textContent = sub;

  const colors = { running: "#63b3ed", done: "#68d391", error: "#fc8181", idle: "#94a3b8" };
  statusTitle.style.color = colors[state] || colors.idle;
}

function updateProgress(current, total, pct) {
  const p = Math.min(100, Math.max(0, pct));
  progressFill.style.width = p + "%";
  progressPct.textContent = p + "%";
  progressWrap.setAttribute("aria-valuenow", p);
}

function addFileCard(data, isError) {
  // Remove empty state if still showing
  emptyState.style.display = "none";

  const card = document.createElement("div");
  card.className = `file-card ${isError ? "error" : ""}`;
  card.setAttribute("role", "listitem");

  const icon = isError ? "❌" : (data.file_type === "PDF" ? "📄" : "🌐");
  const meta = [];

  if (data.court && !isError) meta.push(data.court);
  if (data.date && !isError)  meta.push(data.date);
  if (data.file_type && !isError)  meta.push(`<span class="file-type-badge">${data.file_type}</span>`);
  if (data.skipped)           meta.push('<span style="color:#f6ad55;font-size:10px">↩ Skipped (cached)</span>');

  card.innerHTML = `
    <div class="file-card-icon">${icon}</div>
    <div class="file-card-body">
      <div class="file-card-title">${escapeHtml(data.title || data.filename || "Unknown")}</div>
      ${meta.length ? `<div class="file-card-meta">${meta.join('<span>·</span>')}</div>` : ""}
      ${isError ? `<div class="file-card-error">${escapeHtml(data.error || "Unknown error")}</div>` : ""}
    </div>
  `;

  // Prepend newest files at top
  fileList.insertBefore(card, fileList.firstChild);
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

let toastTimer = null;
function showToast(message) {
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("show"), 3500);
}
