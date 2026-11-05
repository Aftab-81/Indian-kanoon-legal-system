import React, { useState, useEffect, useCallback } from "react";
import { QA_API as API_BASE } from "../../config/api";

export default function HistoryTab({ darkMode: dm, onStatsChanged }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [sourceFilter, setSourceFilter] = useState("ALL");
  const [expandedId, setExpandedId] = useState(null);
  const [actionLoading, setActionLoading] = useState({});
  const [actionErrors, setActionErrors] = useState({});

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/history?source=all`);
      const data = await res.json();
      if (!res.ok || data.error) {
        throw new Error(data.error || `Failed to load history (${res.status})`);
      }
      setHistory(data.history || []);
    } catch (err) {
      if (err.name === "TypeError" && (err.message.includes("fetch") || err.message.includes("NetworkError"))) {
        setError(`Backend not reachable on ${API_BASE}. Please ensure the Legal QA backend is running on port 8002.`);
      } else {
        setError(err.message || "Failed to load question history");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const handleDelete = async (e, questionId) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this inquiry from history?")) return;

    try {
      const res = await fetch(`${API_BASE}/delete-history`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question_id: questionId }),
      });
      const data = await res.json();
      if (res.ok && data.status === "deleted") {
        setHistory((prev) => prev.filter((item) => item.question_id !== questionId));
        if (onStatsChanged) onStatsChanged();
      }
    } catch {
      /* ignore */
    }
  };

  const handleReview = async (answerId, approved, questionId) => {
    if (!answerId) return;
    setActionLoading((prev) => ({ ...prev, [answerId]: true }));
    setActionErrors((prev) => ({ ...prev, [answerId]: "" }));

    try {
      const res = await fetch(`${API_BASE}/approve-answer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          answer_id: answerId,
          approved,
          comment: "",
        }),
      });

      const d = await res.json();
      if (!res.ok || d.error) {
        throw new Error(d.error || `Server error (${res.status})`);
      }

      const newStatus = approved ? "APPROVED" : "REJECTED";
      setHistory((prev) =>
        prev.map((item) =>
          item.question_id === questionId
            ? { ...item, status: newStatus }
            : item
        )
      );
      if (onStatsChanged) onStatsChanged();
    } catch (err) {
      setActionErrors((prev) => ({ ...prev, [answerId]: err.message }));
    } finally {
      setActionLoading((prev) => ({ ...prev, [answerId]: false }));
    }
  };

  const clearFilters = () => {
    setSearchTerm("");
    setStatusFilter("ALL");
    setSourceFilter("ALL");
  };

  const filteredHistory = history.filter((item) => {
    // Search query match in question, answer/conclusion, or document name
    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      const qText = (item.question || "").toLowerCase();
      const ansText = (item.conclusion || item.legal_reasoning || "").toLowerCase();
      const docName = (item.case_name || "").toLowerCase();
      if (!qText.includes(q) && !ansText.includes(q) && !docName.includes(q)) {
        return false;
      }
    }

    // Status filter
    if (statusFilter !== "ALL") {
      const itemStatus = (item.status || "PENDING_REVIEW").toUpperCase();
      if (statusFilter === "APPROVED" && itemStatus !== "APPROVED") return false;
      if (statusFilter === "REJECTED" && itemStatus !== "REJECTED") return false;
      if (statusFilter === "PENDING_REVIEW" && itemStatus !== "PENDING_REVIEW") return false;
    }

    // Source filter
    if (sourceFilter !== "ALL") {
      const itemSource = item.source || "external";
      if (sourceFilter === "EXTERNAL" && itemSource !== "external") return false;
      if (sourceFilter === "DOCUMENT" && itemSource !== "document") return false;
    }

    return true;
  });

  const formatDate = (isoStr) => {
    if (!isoStr) return "—";
    try {
      const d = new Date(isoStr);
      return d.toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "numeric",
        minute: "numeric",
        hour12: true,
      });
    } catch {
      return isoStr;
    }
  };

  const getStatusPill = (status) => {
    const s = (status || "PENDING_REVIEW").toUpperCase();
    if (s === "APPROVED") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30">
          Approved
        </span>
      );
    }
    if (s === "REJECTED") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-500/15 text-red-600 dark:text-red-400 border border-red-500/30">
          Rejected
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30">
        Pending Review
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Question History Container matching Bottom-Left mockup */}
      <div
        className={`rounded-2xl border shadow-sm p-6 sm:p-7 transition-all ${
          dm ? "bg-slate-800/90 border-slate-700/80" : "bg-white border-slate-200/90"
        }`}
      >
        {/* Header Title */}
        <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-blue-500/15 text-blue-600 dark:text-blue-400 flex items-center justify-center font-bold text-base flex-shrink-0">
              📋
            </div>
            <div>
              <h2 className={`text-lg sm:text-xl font-bold ${dm ? "text-white" : "text-slate-900"}`}>
                Question History
              </h2>
              <p className={`text-xs mt-0.5 ${dm ? "text-slate-400" : "text-slate-500"}`}>
                View all your past questions, answers and review decisions.
              </p>
            </div>
          </div>

          <button
            onClick={fetchHistory}
            className={`p-2 rounded-xl text-xs font-semibold transition border flex items-center gap-1.5 ${
              dm
                ? "bg-slate-700 hover:bg-slate-600 text-slate-300 border-slate-600"
                : "bg-slate-50 hover:bg-slate-100 text-slate-600 border-slate-200"
            }`}
            title="Refresh history"
          >
            <span>↻</span>
            <span className="hidden sm:inline">Refresh</span>
          </button>
        </div>

        {/* Search & Filters Bar matching Bottom-Left mockup */}
        <div className="grid grid-cols-1 sm:grid-cols-12 gap-3 mb-6 items-center">
          {/* Search Input */}
          <div className="sm:col-span-5 relative">
            <span className="absolute left-3.5 top-2.5 text-slate-400 text-xs">🔍</span>
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search questions, answers or documents..."
              className={`w-full pl-9 pr-4 py-2 rounded-xl text-xs border outline-none transition focus:border-blue-500 ${
                dm
                  ? "bg-slate-900/80 border-slate-700 text-white placeholder-slate-500"
                  : "bg-slate-50 border-slate-200 text-slate-900 placeholder-slate-400"
              }`}
            />
          </div>

          {/* Status Dropdown */}
          <div className="sm:col-span-3">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className={`w-full py-2 px-3 rounded-xl text-xs font-medium border outline-none cursor-pointer ${
                dm
                  ? "bg-slate-900/80 border-slate-700 text-white"
                  : "bg-slate-50 border-slate-200 text-slate-800"
              }`}
            >
              <option value="ALL">All Status</option>
              <option value="APPROVED">Approved</option>
              <option value="REJECTED">Rejected</option>
              <option value="PENDING_REVIEW">Pending Review</option>
            </select>
          </div>

          {/* Source Dropdown */}
          <div className="sm:col-span-3">
            <select
              value={sourceFilter}
              onChange={(e) => setSourceFilter(e.target.value)}
              className={`w-full py-2 px-3 rounded-xl text-xs font-medium border outline-none cursor-pointer ${
                dm
                  ? "bg-slate-900/80 border-slate-700 text-white"
                  : "bg-slate-50 border-slate-200 text-slate-800"
              }`}
            >
              <option value="ALL">All Sources</option>
              <option value="EXTERNAL">Legal Knowledge Base</option>
              <option value="DOCUMENT">Uploaded Document</option>
            </select>
          </div>

          {/* Clear Filters */}
          <div className="sm:col-span-1 text-right">
            {(searchTerm || statusFilter !== "ALL" || sourceFilter !== "ALL") && (
              <button
                onClick={clearFilters}
                className="text-xs font-semibold text-blue-600 dark:text-blue-400 hover:underline inline-flex items-center gap-1 whitespace-nowrap"
              >
                <span>✕</span> Clear
              </button>
            )}
          </div>
        </div>

        {/* Error message */}
        {error && (
          <div className="mb-4 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 text-xs">
            ⚠️ {error}
          </div>
        )}

        {/* Content list */}
        {loading ? (
          <div className="py-16 text-center flex flex-col items-center justify-center">
            <div className="w-10 h-10 border-3 border-blue-500/20 border-t-blue-600 rounded-full animate-spin mb-3" />
            <p className={`text-xs ${dm ? "text-slate-400" : "text-slate-500"}`}>Loading questions history...</p>
          </div>
        ) : filteredHistory.length === 0 ? (
          <div className="py-16 text-center">
            <div className="text-3xl mb-2">📑</div>
            <p className={`text-sm font-semibold ${dm ? "text-slate-300" : "text-slate-700"}`}>
              No questions found
            </p>
            <p className={`text-xs mt-1 ${dm ? "text-slate-500" : "text-slate-400"}`}>
              {searchTerm || statusFilter !== "ALL" || sourceFilter !== "ALL"
                ? "Try adjusting your search query or filters."
                : "Ask questions in the Ask Question or Upload Case tabs to build history."}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {filteredHistory.map((item) => {
              const isExpanded = expandedId === item.question_id;
              const sourceLabel =
                item.source === "document"
                  ? `Uploaded Document${item.case_name ? ` • ${item.case_name}` : ""}`
                  : "Legal Knowledge Base";

              return (
                <div
                  key={item.question_id}
                  className={`rounded-xl border transition-all overflow-hidden ${
                    isExpanded
                      ? dm
                        ? "bg-slate-700/50 border-blue-500/50 shadow-md"
                        : "bg-blue-50/20 border-blue-300 shadow-md"
                      : dm
                      ? "bg-slate-800/60 border-slate-700/70 hover:border-slate-600 hover:bg-slate-800"
                      : "bg-slate-50/70 border-slate-200/90 hover:border-slate-300 hover:bg-white"
                  }`}
                >
                  {/* Card Header row matching mockup Bottom-Left */}
                  <div
                    onClick={() => setExpandedId(isExpanded ? null : item.question_id)}
                    className="p-4 sm:p-4.5 flex items-center justify-between gap-4 cursor-pointer select-none"
                  >
                    {/* Left: Document icon + Question text + Source */}
                    <div className="flex items-center gap-3.5 min-w-0 flex-1">
                      <div className="w-9 h-9 rounded-xl bg-blue-500/10 text-blue-600 dark:text-blue-400 flex items-center justify-center flex-shrink-0">
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                      </div>

                      <div className="min-w-0 flex-1">
                        <p className={`font-bold text-sm sm:text-base leading-snug truncate ${dm ? "text-white" : "text-slate-900"}`}>
                          {item.question}
                        </p>
                        <p className={`text-xs mt-0.5 truncate ${dm ? "text-slate-400" : "text-slate-500"}`}>
                          {sourceLabel}
                        </p>
                      </div>
                    </div>

                    {/* Right: Status badge + Date/time + Chevron */}
                    <div className="flex items-center gap-3 sm:gap-4 flex-shrink-0">
                      <div className="text-right">
                        <div>{getStatusPill(item.status)}</div>
                        <p className={`text-[11px] mt-1 hidden sm:block ${dm ? "text-slate-400" : "text-slate-500"}`}>
                          {formatDate(item.asked_at)}
                        </p>
                      </div>

                      <span
                        className={`text-slate-400 transition-transform duration-200 text-sm ${
                          isExpanded ? "rotate-90 text-blue-500" : ""
                        }`}
                      >
                        ›
                      </span>
                    </div>
                  </div>

                  {/* Expanded Full Record */}
                  {isExpanded && (
                    <div className="p-5 pt-3 border-t border-slate-200 dark:border-slate-700 bg-white/50 dark:bg-slate-900/50 space-y-4 text-xs">
                      {/* Full Answer */}
                      {item.conclusion && (
                        <div>
                          <p className={`font-bold uppercase tracking-wider mb-1.5 ${dm ? "text-slate-400" : "text-slate-500"}`}>
                            Generated Answer &amp; Conclusion
                          </p>
                          <div className={`p-3.5 rounded-xl border text-sm leading-relaxed whitespace-pre-wrap ${
                            dm ? "bg-slate-800 border-slate-700 text-slate-200" : "bg-white border-slate-200 text-slate-800"
                          }`}>
                            {item.conclusion}
                          </div>
                        </div>
                      )}

                      {/* Legal Reasoning */}
                      {item.legal_reasoning && item.legal_reasoning !== item.conclusion && (
                        <div>
                          <p className={`font-bold uppercase tracking-wider mb-1.5 ${dm ? "text-slate-400" : "text-slate-500"}`}>
                            Legal Reasoning
                          </p>
                          <p className={`p-3 rounded-xl border leading-relaxed whitespace-pre-wrap ${
                            dm ? "bg-slate-800 border-slate-700 text-slate-300" : "bg-white border-slate-200 text-slate-700"
                          }`}>
                            {item.legal_reasoning}
                          </p>
                        </div>
                      )}

                      {/* Precedents */}
                      {item.precedents && item.precedents.length > 0 && (
                        <div>
                          <p className={`font-bold uppercase tracking-wider mb-1.5 ${dm ? "text-slate-400" : "text-slate-500"}`}>
                            Cited Precedents ({item.precedents.length})
                          </p>
                          <ul className="space-y-1">
                            {item.precedents.map((p, idx) => (
                              <li key={idx} className="pl-2 border-l-2 border-blue-500">
                                {p}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Review Comment if present */}
                      {item.review_comment && (
                        <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-700 dark:text-amber-300">
                          <span className="font-bold">Review Comment:</span> {item.review_comment}
                        </div>
                      )}

                      {/* Action error */}
                      {actionErrors[item.answer_id] && (
                        <div className="p-2.5 rounded-lg bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 font-medium">
                          ⚠️ {actionErrors[item.answer_id]}
                        </div>
                      )}

                      {/* Bottom row: Review Buttons + Delete Button */}
                      <div className="flex items-center justify-between pt-2 border-t border-slate-200 dark:border-slate-700">
                        <div className="flex items-center gap-2">
                          {item.answer_id && (
                            <>
                              <button
                                onClick={() => handleReview(item.answer_id, true, item.question_id)}
                                disabled={actionLoading[item.answer_id]}
                                className={`px-3 py-1.5 rounded-lg font-bold transition flex items-center gap-1 shadow-sm ${
                                  item.status === "APPROVED"
                                    ? "bg-emerald-600 text-white"
                                    : "bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-600 hover:text-white"
                                } disabled:opacity-50`}
                              >
                                {actionLoading[item.answer_id] ? "⏳" : "✓"} Approve
                              </button>

                              <button
                                onClick={() => handleReview(item.answer_id, false, item.question_id)}
                                disabled={actionLoading[item.answer_id]}
                                className={`px-3 py-1.5 rounded-lg font-bold transition flex items-center gap-1 shadow-sm ${
                                  item.status === "REJECTED"
                                    ? "bg-red-600 text-white"
                                    : "bg-red-500/20 text-red-600 dark:text-red-400 hover:bg-red-600 hover:text-white"
                                } disabled:opacity-50`}
                              >
                                {actionLoading[item.answer_id] ? "⏳" : "✕"} Reject
                              </button>
                            </>
                          )}
                        </div>

                        <button
                          onClick={(e) => handleDelete(e, item.question_id)}
                          className="px-3 py-1.5 rounded-lg text-red-500 hover:bg-red-500/10 transition border border-red-500/20 flex items-center gap-1.5 font-medium"
                          title="Delete this history entry"
                        >
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                          Delete
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
