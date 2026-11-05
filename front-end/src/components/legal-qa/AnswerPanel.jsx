import React, { useState } from "react";
import { QA_API as API_BASE } from "../../config/api";

export default function AnswerPanel({
  data,
  questionText,
  sourceMode, // "external" | "document"
  documentName,
  onResetQuestion,
  darkMode: dm,
  onStatusUpdated,
}) {
  const [status, setStatus] = useState(data.status || "PENDING_REVIEW");
  const [comment, setComment] = useState("");
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState("");
  const [actionSuccess, setActionSuccess] = useState("");
  const [showCitations, setShowCitations] = useState(true);
  const [showChunks, setShowChunks] = useState(false);

  const answerId = data.answer_id;
  const precedents = data.precedents || [];
  const pageRefs = data.page_references || [];
  const chunks = data.retrieved_cases || data.retrieved_chunks || [];
  const confidence = data.uncertainty_score != null ? Math.round(data.uncertainty_score * 100) : null;
  const mode = data.mode || (sourceMode === "document" ? "DOCUMENT_QA" : "EXTERNAL");
  const isDocQA = sourceMode === "document" || data.source === "document" || data.mode === "DOCUMENT_QA" || mode === "DOCUMENT_QA";

  const formattedDate = data.created_at
    ? new Date(data.created_at).toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "numeric",
        minute: "numeric",
        hour12: true,
      })
    : new Date().toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "numeric",
        minute: "numeric",
        hour12: true,
      });

  const handleReview = async (approved) => {
    if (!answerId) {
      setActionError("Missing answer identifier. Cannot persist review.");
      return;
    }
    setActionLoading(true);
    setActionError("");
    setActionSuccess("");

    try {
      const res = await fetch(`${API_BASE}/approve-answer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          answer_id: answerId,
          approved,
          comment: comment.trim(),
        }),
      });

      const resData = await res.json();
      if (!res.ok || resData.error) {
        throw new Error(resData.error || `Server returned error (${res.status})`);
      }

      const newStatus = approved ? "APPROVED" : "REJECTED";
      setStatus(newStatus);
      setActionSuccess(
        approved
          ? "Answer approved successfully!"
          : "Answer rejection recorded. Feedback saved."
      );
      if (onStatusUpdated) {
        onStatusUpdated(answerId, newStatus, comment.trim());
      }
    } catch (err) {
      if (err.name === "TypeError" && (err.message.includes("fetch") || err.message.includes("NetworkError"))) {
        setActionError(`Backend not reachable on ${API_BASE}. Please ensure the Legal QA backend is running on port 8002.`);
      } else {
        setActionError(err.message || "Failed to submit review");
      }
    } finally {
      setActionLoading(false);
    }
  };

  const getStatusBadge = (st) => {
    if (st === "APPROVED") {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
          Approved
        </span>
      );
    }
    if (st === "REJECTED") {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-red-500/15 text-red-600 dark:text-red-400 border border-red-500/30">
          <span className="w-1.5 h-1.5 rounded-full bg-red-500" />
          Rejected
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30">
        <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
        Awaiting Review
      </span>
    );
  };

  // Determine unified mode from data.mode
  const effectiveMode = data.mode || (sourceMode === "document" ? "DOCUMENT_QA" : "EXTERNAL");
  
  const getModeInfo = (m) => {
    switch (m) {
      case "KNOWLEDGE_BASE":
      case "LOCAL_PDF":
        return {
          label: "Legal Knowledge Base",
          pillClass: "bg-blue-500/15 text-blue-700 dark:text-blue-300 border-blue-300 dark:border-blue-500/30"
        };
      case "EXTERNAL":
        return {
          label: "External Web Search (SerpAPI)",
          pillClass: "bg-purple-500/15 text-purple-700 dark:text-purple-300 border-purple-300 dark:border-purple-500/30"
        };
      case "DOCUMENT_QA":
        return {
          label: `Uploaded Document${documentName || data.case_name ? ` • ${documentName || data.case_name}` : ""}`,
          pillClass: "bg-indigo-500/15 text-indigo-700 dark:text-indigo-300 border-indigo-300 dark:border-indigo-500/30"
        };
      case "CACHED":
        return {
          label: "Reused from Approved Answer",
          pillClass: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-300 dark:border-emerald-500/30"
        };
      case "GENERAL_KNOWLEDGE":
        return {
          label: "General Legal Knowledge (Unverified)",
          pillClass: "bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-300 dark:border-amber-500/30"
        };
      case "NO_RESULT":
        return {
          label: "No Sourced Answer Available",
          pillClass: "bg-red-500/15 text-red-700 dark:text-red-300 border-red-300 dark:border-red-500/30"
        };
      default:
        return {
          label: m,
          pillClass: "bg-slate-500/15 text-slate-700 dark:text-slate-300 border-slate-300"
        };
    }
  };

  const modeInfo = getModeInfo(effectiveMode);
  const sourceLabel = modeInfo.label;


  return (
    <div className="space-y-6">
      {/* Top back/reset row */}
      <div className="flex items-center justify-between">
        <button
          onClick={onResetQuestion}
          className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all border shadow-sm ${
            dm
              ? "bg-slate-800 hover:bg-slate-700 text-slate-200 border-slate-700"
              : "bg-white hover:bg-slate-50 text-slate-700 border-slate-200"
          }`}
        >
          <svg className="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 17l-5-5m0 0l5-5m-5 5h12" />
          </svg>
          Ask Another Question
        </button>

        <div className="flex items-center gap-2 text-xs">
          <span className={dm ? "text-slate-400" : "text-slate-500"}>Language:</span>
          <span className="font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-blue-500/10 text-blue-500 border border-blue-500/20 text-[11px]">
            {data.language || "en"}
          </span>
        </div>
      </div>

      {/* Main Grid: 2 columns matching the mockup Bottom-Right */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* Left Column (2 cols): Answer Details */}
        <div
          className={`lg:col-span-2 rounded-2xl border p-6 sm:p-7 shadow-sm ${
            dm ? "bg-slate-800/90 border-slate-700/80" : "bg-white border-slate-200/90"
          }`}
        >
          {/* Top Info Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 pb-5 border-b border-slate-200 dark:border-slate-700/80">
            <div className="flex items-center gap-3">
              {getStatusBadge(status)}
              {answerId && (
                <span className={`text-xs font-mono px-2.5 py-0.5 rounded border ${
                  dm ? "bg-slate-700/60 border-slate-600 text-slate-300" : "bg-slate-50 border-slate-200 text-slate-600"
                }`}>
                  Answer ID: {answerId.slice(0, 12)}
                </span>
              )}
            </div>
            <div className={`text-xs flex items-center gap-1.5 font-medium ${dm ? "text-slate-400" : "text-slate-500"}`}>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              <span>{formattedDate}</span>
            </div>
          </div>

          {/* Question Section */}
          <div className="py-5 border-b border-slate-200 dark:border-slate-700/80">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-6 h-6 rounded-lg bg-blue-500/10 text-blue-500 flex items-center justify-center text-xs font-bold">
                ?
              </div>
              <h3 className={`text-xs font-bold uppercase tracking-wider ${dm ? "text-slate-400" : "text-slate-500"}`}>
                Question
              </h3>
            </div>
            <div className="flex flex-wrap items-center gap-2.5">
              <p className={`text-base sm:text-lg font-bold leading-snug ${dm ? "text-white" : "text-slate-900"}`}>
                {questionText || data.question_text || "Legal Inquiry"}
              </p>
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded text-[11px] font-semibold border ${modeInfo.pillClass}`}>
                {sourceLabel}
              </span>
            </div>
            {effectiveMode === "CACHED" && (
              <div className="mt-2 text-xs text-emerald-600 dark:text-emerald-400 font-medium flex items-center gap-1.5">
                <span>⚡ Reused from a previously approved answer</span>
                {data.matched_question && (
                  <span className="text-slate-500 dark:text-slate-400">
                    (Matched question: "{data.matched_question}")
                  </span>
                )}
              </div>
            )}
            {effectiveMode === "NO_RESULT" && data.reason_code && (
              <div className="mt-2 text-xs text-red-600 dark:text-red-400 font-medium">
                ⚠️ Reason Code: <span className="font-mono font-bold">{data.reason_code}</span>
                {data.reason_message && <span> — {data.reason_message}</span>}
              </div>
            )}
          </div>

          {/* Answer Section */}
          <div className="py-5 border-b border-slate-200 dark:border-slate-700/80">
            <div className="flex items-center gap-2 mb-2.5">
              <div className="w-6 h-6 rounded-lg bg-indigo-500/10 text-indigo-500 flex items-center justify-center text-xs">
                ⚖️
              </div>
              <h3 className={`text-xs font-bold uppercase tracking-wider ${dm ? "text-slate-400" : "text-slate-500"}`}>
                Answer
              </h3>
            </div>
            <div className={`text-sm sm:text-base leading-relaxed whitespace-pre-wrap font-normal ${
              dm ? "text-slate-200" : "text-slate-800"
            }`}>
              {data.conclusion || data.legal_reasoning || "No conclusion returned."}
            </div>
          </div>

          {/* Legal Reasoning Section */}
          {data.legal_reasoning && data.legal_reasoning !== data.conclusion && (
            <div className="py-5 border-b border-slate-200 dark:border-slate-700/80">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-6 h-6 rounded-lg bg-purple-500/10 text-purple-500 flex items-center justify-center text-xs">
                  💡
                </div>
                <h3 className={`text-xs font-bold uppercase tracking-wider ${dm ? "text-slate-400" : "text-slate-500"}`}>
                  Legal Reasoning
                </h3>
              </div>
              <div className={`text-sm leading-relaxed whitespace-pre-wrap ${
                dm ? "text-slate-300" : "text-slate-700"
              }`}>
                {data.legal_reasoning}
              </div>
            </div>
          )}

          {/* Suggested Judicial Approach */}
          {data.suggested_decision && (
            <div className="py-5 border-b border-slate-200 dark:border-slate-700/80">
              <h3 className={`text-xs font-bold uppercase tracking-wider mb-2 ${dm ? "text-slate-400" : "text-slate-500"}`}>
                Suggested Judicial Approach
              </h3>
              <p className={`text-sm leading-relaxed ${dm ? "text-slate-300" : "text-slate-700"}`}>
                {data.suggested_decision}
              </p>
            </div>
          )}

          {/* Ratio Decidendi */}
          {data.ratio_decidendi && (
            <div className="py-5 border-b border-slate-200 dark:border-slate-700/80">
              <h3 className={`text-xs font-bold uppercase tracking-wider mb-2 ${dm ? "text-slate-400" : "text-slate-500"}`}>
                Ratio Decidendi
              </h3>
              <p className={`text-sm leading-relaxed ${dm ? "text-slate-300" : "text-slate-700"}`}>
                {data.ratio_decidendi}
              </p>
            </div>
          )}

          {/* Next Steps */}
          {data.recommended_next_steps && data.recommended_next_steps.length > 0 && (
            <div className="py-5 border-b border-slate-200 dark:border-slate-700/80">
              <h3 className={`text-xs font-bold uppercase tracking-wider mb-2 ${dm ? "text-slate-400" : "text-slate-500"}`}>
                Recommended Next Steps
              </h3>
              <ul className="list-disc list-inside space-y-1 text-sm">
                {data.recommended_next_steps.map((step, idx) => (
                  <li key={idx} className={dm ? "text-slate-300" : "text-slate-700"}>
                    {step}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Collapsible Citations & Sources */}
          {precedents.length > 0 && (
            <div className="pt-4 border-b border-slate-200 dark:border-slate-700/80 pb-4">
              <button
                onClick={() => setShowCitations(!showCitations)}
                className="w-full flex items-center justify-between text-left py-2 font-bold text-sm text-blue-600 dark:text-blue-400 hover:opacity-80 transition"
              >
                <span className="flex items-center gap-2">
                  <span>📚</span>
                  <span>Citations &amp; Sources ({precedents.length})</span>
                </span>
                <span className="text-xs transition-transform duration-200" style={{ transform: showCitations ? "rotate(180deg)" : "rotate(0)" }}>
                  ▼
                </span>
              </button>

              {showCitations && (
                <div className="mt-3 space-y-2">
                  {precedents.map((p, idx) => (
                    <div
                      key={idx}
                      className={`p-3 rounded-xl border text-xs leading-relaxed ${
                        dm ? "bg-slate-900/40 border-slate-700 text-slate-300" : "bg-slate-50 border-slate-200 text-slate-700"
                      }`}
                    >
                      <span className="font-semibold text-blue-500 mr-2">[{idx + 1}]</span>
                      {p}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Collapsible Retrieved Case Chunks */}
          {chunks.length > 0 && (
            <div className="pt-4">
              <button
                onClick={() => setShowChunks(!showChunks)}
                className="w-full flex items-center justify-between text-left py-2 font-bold text-sm text-blue-600 dark:text-blue-400 hover:opacity-80 transition"
              >
                <span className="flex items-center gap-2">
                  <span>📑</span>
                  <span>Retrieved Case Chunks ({chunks.length})</span>
                </span>
                <span className="text-xs transition-transform duration-200" style={{ transform: showChunks ? "rotate(180deg)" : "rotate(0)" }}>
                  ▼
                </span>
              </button>

              {showChunks && (
                <div className="mt-3 space-y-3">
                  {chunks.map((c, idx) => {
                    const sim = c.similarity ? Math.round(c.similarity * 100) : null;
                    return (
                      <div
                        key={idx}
                        className={`p-3.5 rounded-xl border text-xs ${
                          dm ? "bg-slate-900/50 border-slate-700" : "bg-slate-50/80 border-slate-200"
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2 mb-1.5 flex-wrap">
                          <span className="font-bold text-slate-900 dark:text-slate-100">
                            {c.case || c.case_name || `Source Chunk #${idx + 1}`}
                          </span>
                          {sim !== null && (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300">
                              {sim}% match
                            </span>
                          )}
                        </div>
                        <p className={`leading-relaxed italic ${dm ? "text-slate-300" : "text-slate-600"}`}>
                          &ldquo;{c.chunk}&rdquo;
                        </p>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Column (1 col): Review Actions & Source Information */}
        <div className="space-y-6">
          {/* Card 1: Review Actions */}
          <div
            className={`rounded-2xl border p-5 sm:p-6 shadow-sm ${
              dm ? "bg-slate-800/90 border-slate-700/80" : "bg-white border-slate-200/90"
            }`}
          >
            <h3 className={`text-base font-bold mb-4 flex items-center gap-2 ${dm ? "text-white" : "text-slate-900"}`}>
              <svg className="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Review Actions
            </h3>

            {/* Error & Success Alerts */}
            {actionError && (
              <div className="mb-4 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 text-xs font-medium">
                ⚠️ {actionError}
              </div>
            )}
            {actionSuccess && (
              <div className="mb-4 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-xs font-medium">
                ✅ {actionSuccess}
              </div>
            )}

            {/* Approve / Reject Buttons */}
            <div className="space-y-3">
              <button
                onClick={() => handleReview(true)}
                disabled={actionLoading}
                className={`w-full py-3 px-4 rounded-xl font-bold text-sm text-white transition-all flex items-center justify-center gap-2 shadow-sm ${
                  status === "APPROVED"
                    ? "bg-emerald-700 cursor-default"
                    : "bg-emerald-600 hover:bg-emerald-700 active:scale-[0.99] hover:shadow-emerald-500/20 shadow-md"
                } disabled:opacity-50`}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                </svg>
                {status === "APPROVED" ? "Approved" : "Approve Answer"}
              </button>

              <button
                onClick={() => handleReview(false)}
                disabled={actionLoading}
                className={`w-full py-3 px-4 rounded-xl font-bold text-sm text-white transition-all flex items-center justify-center gap-2 shadow-sm ${
                  status === "REJECTED"
                    ? "bg-red-700 cursor-default"
                    : "bg-red-600 hover:bg-red-700 active:scale-[0.99] hover:shadow-red-500/20 shadow-md"
                } disabled:opacity-50`}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
                </svg>
                {status === "REJECTED" ? "Rejected" : "Reject / Request Revision"}
              </button>
            </div>

            {/* Review Comment (optional) */}
            <div className="mt-5 pt-4 border-t border-slate-200 dark:border-slate-700">
              <label className={`block text-xs font-semibold mb-2 ${dm ? "text-slate-300" : "text-slate-600"}`}>
                Review Comment (optional)
              </label>
              <textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="Add your feedback or reason for rejection..."
                rows={3}
                className={`w-full p-3 rounded-xl border text-xs resize-none outline-none transition focus:ring-1 focus:ring-blue-500 ${
                  dm
                    ? "bg-slate-900/80 border-slate-700 text-white placeholder-slate-500"
                    : "bg-slate-50 border-slate-300 text-slate-900 placeholder-slate-400"
                }`}
              />
              <button
                onClick={() => handleReview(status === "APPROVED")}
                disabled={actionLoading || !comment.trim()}
                className={`mt-2 w-full py-2 px-3 rounded-lg text-xs font-semibold transition ${
                  comment.trim() && !actionLoading
                    ? "bg-blue-600 hover:bg-blue-700 text-white"
                    : "bg-slate-200 dark:bg-slate-700 text-slate-400 cursor-not-allowed"
                }`}
              >
                {actionLoading ? "Submitting..." : "Submit Review Comment"}
              </button>
            </div>
          </div>

          {/* Card 2: Source Information */}
          <div
            className={`rounded-2xl border p-5 sm:p-6 shadow-sm ${
              dm ? "bg-slate-800/90 border-slate-700/80" : "bg-white border-slate-200/90"
            }`}
          >
            <h3 className={`text-base font-bold mb-4 flex items-center gap-2 ${dm ? "text-white" : "text-slate-900"}`}>
              <svg className="w-5 h-5 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Source Information
            </h3>

            <div className="space-y-4 text-xs">
              <div>
                <p className={`font-semibold uppercase tracking-wider text-[11px] ${dm ? "text-slate-400" : "text-slate-500"}`}>
                  Source Mode
                </p>
                <p className="font-bold text-sm text-blue-600 dark:text-blue-400 mt-0.5">
                  {sourceLabel}
                </p>
                {isDocQA && (
                  <p className={`text-[11px] mt-0.5 font-medium ${dm ? "text-slate-400" : "text-slate-500"}`}>
                    📄 {documentName || data.case_name || chunks[0]?.case || "Active Document"}
                  </p>
                )}
                {effectiveMode === "CACHED" && data.matched_question && (
                  <p className={`text-[11px] mt-1 font-medium text-emerald-600 dark:text-emerald-400`}>
                    ⚡ Matched: "{data.matched_question}"
                  </p>
                )}
                {effectiveMode === "NO_RESULT" && data.reason_code && (
                  <p className={`text-[11px] mt-1 font-mono text-red-500`}>
                    Status: {data.reason_code}
                  </p>
                )}
              </div>

              {/* Sources List / Retrieved Cases */}
              {(data.sources?.length > 0 || chunks.length > 0) && (
                <div>
                  <p className={`font-semibold uppercase tracking-wider text-[11px] ${dm ? "text-slate-400" : "text-slate-500"}`}>
                    {effectiveMode === "EXTERNAL" ? "Web Sources" : effectiveMode === "DOCUMENT_QA" ? "Active Document" : "Sources Used"}
                  </p>
                  <div className="mt-1 space-y-1">
                    {data.sources && data.sources.length > 0 ? (
                      data.sources.slice(0, 5).map((src, i) => (
                        <div key={i} className={`text-xs truncate ${dm ? "text-slate-300" : "text-slate-700"}`}>
                          {src.startsWith("http") ? (
                            <a
                              href={src}
                              target="_blank"
                              rel="noreferrer"
                              className="text-blue-500 hover:underline truncate block"
                            >
                              🔗 {src}
                            </a>
                          ) : (
                            <span>⚖️ {src}</span>
                          )}
                        </div>
                      ))
                    ) : (
                      <p className={`font-medium ${dm ? "text-slate-200" : "text-slate-800"}`}>
                        {isDocQA
                          ? (documentName || data.case_name || chunks[0].case || chunks[0].case_name || "Uploaded Case")
                          : (chunks[0].case || chunks[0].case_name || "Supreme Court Judgment")}
                      </p>
                    )}
                  </div>
                </div>
              )}

              {pageRefs.length > 0 && (
                <div>
                  <p className={`font-semibold uppercase tracking-wider text-[11px] ${dm ? "text-slate-400" : "text-slate-500"}`}>
                    Relevant Pages
                  </p>
                  <div className="flex flex-wrap gap-1.5 mt-1">
                    {pageRefs.map((pg) => (
                      <span
                        key={pg}
                        className="px-2 py-0.5 rounded text-[11px] font-bold bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300 border border-blue-200 dark:border-blue-700/50"
                      >
                        Page {pg}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {confidence !== null && (
                <div>
                  <p className={`font-semibold uppercase tracking-wider text-[11px] ${dm ? "text-slate-400" : "text-slate-500"}`}>
                    Confidence Score
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    <div className="flex-1 h-2 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          confidence >= 70 ? "bg-emerald-500" : confidence >= 40 ? "bg-amber-500" : "bg-red-500"
                        }`}
                        style={{ width: `${confidence}%` }}
                      />
                    </div>
                    <span className="font-bold text-xs">{confidence}%</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
