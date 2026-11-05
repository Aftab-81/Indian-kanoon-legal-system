import React, { useState, useEffect, useRef } from "react";
import AnswerPanel from "./AnswerPanel";
import { QA_API as API_BASE } from "../../config/api";

const STEPS = [
  "File uploaded successfully",
  "Extracting text from PDF...",
  "Smart chunking text...",
  "Generating embeddings...",
  "Indexing document in vector store...",
];

export default function UploadCaseTab({
  language,
  darkMode: dm,
  activeDoc,
  setActiveDoc,
  onDocIndexed,
}) {
  const [file, setFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [progressStep, setProgressStep] = useState(0);
  const [uploadError, setUploadError] = useState("");
  const [indexingSuccess, setIndexingSuccess] = useState(false);
  const [showDocDetails, setShowDocDetails] = useState(false);

  // Document-specific Q&A state
  const [docQuestion, setDocQuestion] = useState("");
  const [docLoading, setDocLoading] = useState(false);
  const [docError, setDocError] = useState("");
  const [docAnswer, setDocAnswer] = useState(null);

  // Available indexed documents
  const [indexedDocs, setIndexedDocs] = useState([]);
  const fileInputRef = useRef(null);

  useEffect(() => {
    fetchIndexedDocuments();
  }, []);

  const fetchIndexedDocuments = async () => {
    try {
      const res = await fetch(`${API_BASE}/documents`);
      const d = await res.json();
      if (d.documents) {
        setIndexedDocs(d.documents);
        // If no active doc is set yet but documents exist, we can select the latest one
        if (!activeDoc && d.documents.length > 0) {
          const latest = d.documents[d.documents.length - 1];
          setActiveDoc({
            caseId: latest.case_id,
            caseName: latest.case_name,
            chunks: latest.chunks_count,
            status: "Indexed & Ready",
          });
        }
      }
    } catch {
      /* ignore */
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(e.type === "dragenter" || e.type === "dragover");
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    const f = e.dataTransfer.files?.[0];
    if (f) {
      validateAndSetFile(f);
    }
  };

  const handleFileChange = (e) => {
    const f = e.target.files?.[0];
    if (f) {
      validateAndSetFile(f);
    }
  };

  const validateAndSetFile = (f) => {
    setUploadError("");
    setIndexingSuccess(false);
    if (!f.name.toLowerCase().endsWith(".pdf")) {
      setUploadError("Invalid file type. Only PDF files are supported.");
      return;
    }
    if (f.size > 50 * 1024 * 1024) {
      setUploadError("File size exceeds 50 MB limit.");
      return;
    }
    setFile(f);
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploadError("");
    setLoading(true);
    setProgressStep(0);
    setIndexingSuccess(false);

    // Realistic progress animation tracking backend processing
    let currentStep = 0;
    const progressTimer = setInterval(() => {
      if (currentStep < 3) {
        currentStep++;
        setProgressStep(currentStep);
      }
    }, 700);

    const fd = new FormData();
    fd.append("file", file);
    fd.append("case_name", file.name.replace(/\.pdf$/i, ""));

    try {
      const res = await fetch(`${API_BASE}/upload-pdf`, {
        method: "POST",
        body: fd,
      });

      clearInterval(progressTimer);
      const data = await res.json();

      if (!res.ok || data.error) {
        setUploadError(data.error || `Upload failed (${res.status})`);
        setLoading(false);
        setProgressStep(0);
        return;
      }

      setProgressStep(4);
      setIndexingSuccess(true);

      const newDoc = {
        caseId: data.case_id,
        caseName: data.case_name || file.name,
        date: new Date().toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }),
        pages: data.page_count != null ? data.page_count : "—",
        size: `${data.file_size_mb != null ? data.file_size_mb : (file.size / (1024 * 1024)).toFixed(2)} MB`,
        chunks: data.chunks_created != null ? data.chunks_created : "—",
        status: "Indexed & Ready",
      };

      setActiveDoc(newDoc);
      fetchIndexedDocuments();
      if (onDocIndexed) onDocIndexed();

      setTimeout(() => {
        setLoading(false);
      }, 600);
    } catch (err) {
      clearInterval(progressTimer);
      setUploadError("Network connection error: " + err.message);
      setLoading(false);
      setProgressStep(0);
    }
  };

  const handleDocQuestionSubmit = async () => {
    if (!docQuestion.trim() || !activeDoc?.caseId) return;
    setDocError("");
    setDocLoading(true);

    try {
      const res = await fetch(`${API_BASE}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: docQuestion.trim(),
          language,
          source: "document",
          case_id: activeDoc.caseId,
        }),
      });

      const data = await res.json();
      if (!res.ok || data.error) {
        throw new Error(data.error || `Server error (${res.status})`);
      }

      setDocAnswer({
        data,
        questionText: docQuestion.trim(),
      });
    } catch (err) {
      if (err.name === "TypeError" && (err.message.includes("fetch") || err.message.includes("NetworkError"))) {
        setDocError(`Backend not reachable on ${API_BASE}. Please ensure the Legal QA backend is running on port 8002.`);
      } else {
        setDocError(err.message || "Failed to query document");
      }
    } finally {
      setDocLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Upload Card matching Top-Right mockup */}
      <div
        className={`rounded-2xl border shadow-sm p-6 sm:p-7 transition-all ${
          dm ? "bg-slate-800/90 border-slate-700/80" : "bg-white border-slate-200/90"
        }`}
      >
        {/* Card Header */}
        <div className="flex items-start gap-3 mb-6">
          <div className="w-9 h-9 rounded-xl bg-blue-500/15 text-blue-600 dark:text-blue-400 flex items-center justify-center font-bold text-lg flex-shrink-0">
            📄
          </div>
          <div>
            <h2 className={`text-lg sm:text-xl font-bold ${dm ? "text-white" : "text-slate-900"}`}>
              Upload a Document to Add to Legal Knowledge Base
            </h2>
            <p className={`text-xs sm:text-sm mt-0.5 ${dm ? "text-slate-400" : "text-slate-500"}`}>
              Upload a PDF file to extract, process and index it for legal search and Q&amp;A.
            </p>
          </div>
        </div>

        {/* Error Alert */}
        {uploadError && (
          <div className="mb-5 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 text-xs font-medium flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span>⚠️</span>
              <span>{uploadError}</span>
            </div>
            <button onClick={() => setUploadError("")} className="font-bold text-red-500">
              ✕
            </button>
          </div>
        )}

        {/* Drag and Drop Zone */}
        {!loading && (
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-2xl p-8 sm:p-12 text-center transition-all ${
              isDragging
                ? "border-blue-500 bg-blue-50/15 scale-[1.005]"
                : dm
                ? "border-slate-700 hover:border-slate-600 bg-slate-900/40"
                : "border-blue-200 hover:border-blue-300 bg-blue-50/20"
            }`}
          >
            <input
              type="file"
              ref={fileInputRef}
              accept=".pdf"
              className="hidden"
              onChange={handleFileChange}
            />

            <div className="flex flex-col items-center">
              {/* Cloud Upload Icon */}
              <div className="w-16 h-16 rounded-full bg-blue-500/10 text-blue-500 flex items-center justify-center mb-3">
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
              </div>

              <p className={`text-base font-bold ${dm ? "text-slate-200" : "text-slate-800"}`}>
                Drag and drop your PDF file here
              </p>
              <p className={`text-xs mt-1 ${dm ? "text-slate-400" : "text-slate-500"}`}>
                or
              </p>

              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="mt-3 px-5 py-2 rounded-xl text-xs font-bold bg-blue-600 hover:bg-blue-700 text-white shadow-sm transition active:scale-95"
              >
                Choose PDF
              </button>

              <p className={`text-xs mt-3 ${dm ? "text-slate-500" : "text-slate-400"}`}>
                Supports PDF files only (Max 50MB)
              </p>
            </div>
          </div>
        )}

        {/* Selected File Banner */}
        {file && !loading && (
          <div className="mt-4 p-3.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/60 flex items-center justify-between">
            <div className="flex items-center gap-3 min-w-0">
              <span className="text-xl">📕</span>
              <div className="truncate">
                <p className={`text-xs font-bold truncate ${dm ? "text-white" : "text-slate-900"}`}>
                  {file.name}
                </p>
                <p className={`text-[11px] ${dm ? "text-slate-400" : "text-slate-500"}`}>
                  {(file.size / (1024 * 1024)).toFixed(2)} MB
                </p>
              </div>
            </div>

            <button
              onClick={() => {
                setFile(null);
                setIndexingSuccess(false);
              }}
              className="p-1.5 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-600"
              title="Remove selected file"
            >
              ✕
            </button>
          </div>
        )}

        {/* Upload & Index Button */}
        {file && !loading && !indexingSuccess && (
          <button
            onClick={handleUpload}
            className="w-full mt-4 py-3.5 rounded-xl font-bold text-sm bg-blue-600 hover:bg-blue-700 text-white shadow-md shadow-blue-500/20 transition active:scale-[0.99]"
          >
            Upload &amp; Index Document
          </button>
        )}

        {/* Progress & Checklist during/after upload matching Top-Right mockup */}
        {(loading || indexingSuccess) && (
          <div className="mt-6 pt-5 border-t border-slate-200 dark:border-slate-700">
            {/* Top Green Progress Bar */}
            <div className="w-full h-2 rounded-full bg-slate-100 dark:bg-slate-700 overflow-hidden mb-6">
              <div
                className="h-full bg-emerald-500 transition-all duration-500 rounded-full"
                style={{ width: `${((progressStep + 1) / STEPS.length) * 100}%` }}
              />
            </div>

            {/* Checklist & Completion Box side-by-side */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
              {/* Checklist */}
              <div className="space-y-2.5">
                {STEPS.map((stepName, idx) => {
                  const isDone = idx <= progressStep;
                  return (
                    <div
                      key={stepName}
                      className={`flex items-center gap-2.5 text-xs font-semibold transition-all ${
                        isDone
                          ? "text-emerald-600 dark:text-emerald-400"
                          : dm
                          ? "text-slate-600"
                          : "text-slate-300"
                      }`}
                    >
                      <span className="text-sm">
                        {isDone ? "✓" : "○"}
                      </span>
                      <span>{stepName}</span>
                    </div>
                  );
                })}
              </div>

              {/* Right Box: Completion or In Progress Card */}
              {indexingSuccess && (
                <div className="p-5 rounded-2xl border border-emerald-500/30 bg-emerald-50/60 dark:bg-emerald-950/20 text-center flex flex-col items-center justify-center">
                  <div className="w-10 h-10 rounded-full bg-emerald-500 text-white flex items-center justify-center text-lg font-bold mb-2 shadow-sm">
                    ✓
                  </div>
                  <h3 className="font-bold text-base text-emerald-800 dark:text-emerald-300">
                    Indexing completed!
                  </h3>
                  <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-0.5 mb-3">
                    Document is ready for Q&amp;A.
                  </p>
                  <button
                    onClick={() => setShowDocDetails(!showDocDetails)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 shadow-sm hover:bg-slate-50"
                  >
                    <span>👁</span>
                    <span>{showDocDetails ? "Hide Details" : "View Document Details"}</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Active Document Info Card */}
      {activeDoc && (
        <div
          className={`rounded-2xl border shadow-sm p-6 transition-all ${
            dm ? "bg-slate-800/90 border-slate-700/80" : "bg-white border-slate-200/90"
          }`}
        >
          <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-200 dark:border-slate-700">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center text-lg font-bold">
                ✓
              </div>
              <div>
                <h3 className={`font-bold text-base ${dm ? "text-white" : "text-slate-900"}`}>
                  {activeDoc.caseName}
                </h3>
                <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                  {activeDoc.status || "Indexed & Ready"}
                </span>
              </div>
            </div>

            {/* Switch / Select from other indexed documents */}
            {indexedDocs.length > 1 && (
              <div className="flex items-center gap-2">
                <span className={`text-xs ${dm ? "text-slate-400" : "text-slate-500"}`}>Switch Doc:</span>
                <select
                  value={activeDoc.caseId}
                  onChange={(e) => {
                    const found = indexedDocs.find((d) => d.case_id === e.target.value);
                    if (found) {
                      setActiveDoc({
                        caseId: found.case_id,
                        caseName: found.case_name,
                        chunks: found.chunks_count,
                        status: "Indexed & Ready",
                      });
                      setDocAnswer(null);
                    }
                  }}
                  className={`text-xs font-medium py-1.5 px-3 rounded-lg border ${
                    dm ? "bg-slate-900 border-slate-700 text-slate-200" : "bg-slate-50 border-slate-200 text-slate-800"
                  }`}
                >
                  {indexedDocs.map((doc) => (
                    <option key={doc.case_id} value={doc.case_id}>
                      {doc.case_name}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          {/* Details grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-4 text-xs">
            <div>
              <p className={dm ? "text-slate-400" : "text-slate-500"}>Document ID</p>
              <p className="font-mono font-semibold mt-0.5 truncate">{activeDoc.caseId ? activeDoc.caseId.slice(0, 12) : "—"}</p>
            </div>
            <div>
              <p className={dm ? "text-slate-400" : "text-slate-500"}>Indexed Chunks</p>
              <p className="font-bold text-sm mt-0.5">{activeDoc.chunks || "Indexed"}</p>
            </div>
            <div>
              <p className={dm ? "text-slate-400" : "text-slate-500"}>Mode</p>
              <p className="font-bold text-blue-500 mt-0.5">Isolated Document QA</p>
            </div>
            <div>
              <p className={dm ? "text-slate-400" : "text-slate-500"}>Source Separation</p>
              <p className="font-semibold text-emerald-500 mt-0.5">Enforced</p>
            </div>
          </div>
        </div>
      )}

      {/* Document-Specific Question Answering Section */}
      {activeDoc && (
        <div className="space-y-6">
          {docAnswer ? (
            <AnswerPanel
              data={docAnswer.data}
              questionText={docAnswer.questionText}
              sourceMode="document"
              documentName={activeDoc.caseName}
              onResetQuestion={() => {
                setDocAnswer(null);
                setDocQuestion("");
              }}
              darkMode={dm}
              onStatusUpdated={() => {
                if (onDocIndexed) onDocIndexed();
              }}
            />
          ) : (
            <div
              className={`rounded-2xl border shadow-sm p-6 sm:p-7 transition-all ${
                dm ? "bg-slate-800/90 border-slate-700/80" : "bg-white border-slate-200/90"
              }`}
            >
              <div className="flex items-center gap-2.5 mb-4">
                <span className="text-lg">💬</span>
                <div>
                  <h3 className={`text-base font-bold ${dm ? "text-white" : "text-slate-900"}`}>
                    Ask a Question About This Document
                  </h3>
                  <p className={`text-xs ${dm ? "text-slate-400" : "text-slate-500"}`}>
                    Answers are strictly grounded in &ldquo;{activeDoc.caseName}&rdquo; with exact page citations
                  </p>
                </div>
              </div>

              {docError && (
                <div className="mb-4 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 text-xs font-medium">
                  ⚠️ {docError}
                </div>
              )}

              <div className="relative">
                <textarea
                  value={docQuestion}
                  onChange={(e) => setDocQuestion(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      if (!docLoading) handleDocQuestionSubmit();
                    }
                  }}
                  disabled={docLoading}
                  rows={3}
                  placeholder={`Ask a question specifically about ${activeDoc.caseName}...`}
                  className={`w-full p-4 rounded-xl border text-sm outline-none resize-none transition leading-relaxed ${
                    dm
                      ? "bg-slate-900/80 border-slate-700 text-white placeholder-slate-500 focus:border-blue-500"
                      : "bg-slate-50 border-slate-200 text-slate-900 placeholder-slate-400 focus:border-blue-500 focus:bg-white"
                  }`}
                />

                <div className="mt-3 flex items-center justify-between flex-wrap gap-2">
                  <span className={`text-[11px] ${dm ? "text-slate-500" : "text-slate-400"}`}>
                    Only searches chunks extracted from this PDF document
                  </span>

                  <button
                    onClick={handleDocQuestionSubmit}
                    disabled={docLoading || !docQuestion.trim()}
                    className={`inline-flex items-center gap-2 px-6 py-2 rounded-xl text-xs font-bold text-white transition ${
                      docLoading || !docQuestion.trim()
                        ? "bg-slate-300 dark:bg-slate-700 text-slate-400 cursor-not-allowed"
                        : "bg-blue-600 hover:bg-blue-700 shadow-md shadow-blue-500/20"
                    }`}
                  >
                    {docLoading ? (
                      <>
                        <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        <span>Searching Document...</span>
                      </>
                    ) : (
                      <>
                        <span>Ask Document Question</span>
                        <span>➤</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Suggestions for document query */}
              <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-700 flex flex-wrap gap-2">
                {[
                  "Summarize the key findings of this judgment",
                  "What legal provisions and sections are cited?",
                  "Explain the reasoning behind the court's decision",
                  "What were the arguments raised by the petitioner?",
                ].map((sugg) => (
                  <button
                    key={sugg}
                    onClick={() => {
                      setDocQuestion(sugg);
                    }}
                    className={`text-xs px-2.5 py-1.5 rounded-lg border transition ${
                      dm
                        ? "bg-slate-900/50 border-slate-700 text-slate-300 hover:text-white hover:border-blue-500"
                        : "bg-slate-50 border-slate-200 text-slate-600 hover:text-slate-900 hover:border-blue-400"
                    }`}
                  >
                    &ldquo;{sugg}&rdquo;
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
