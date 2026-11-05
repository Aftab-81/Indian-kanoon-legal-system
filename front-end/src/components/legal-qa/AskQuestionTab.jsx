import React, { useState } from "react";
import AnswerPanel from "./AnswerPanel";
import { QA_API as API_BASE } from "../../config/api";

const SUGGESTIONS = [
  "What are the legal grounds for bail in India?",
  "Explain NDPS Section 37 provisions and exceptions",
  "When can a court grant anticipatory bail under CrPC 438?",
  "What is the difference between ratio decidendi and obiter dicta?",
];

export default function AskQuestionTab({
  language,
  setLanguage,
  darkMode: dm,
  onQuestionCompleted,
}) {
  const [question, setQuestion] = useState("");
  const [context, setContext] = useState("");
  const [showContext, setShowContext] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [currentAnswer, setCurrentAnswer] = useState(null);

  const handleSubmit = async (qOverride) => {
    const textToSubmit = (qOverride || question).trim();
    if (!textToSubmit) {
      setError("Please enter a legal question.");
      return;
    }

    setError("");
    setLoading(true);

    try {
      const fullQuestion = context.trim()
        ? `${textToSubmit}\n\nAdditional Context:\n${context.trim()}`
        : textToSubmit;

      const res = await fetch(`${API_BASE}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: fullQuestion,
          language,
          source: "external",
        }),
      });

      const data = await res.json();
      if (!res.ok || data.error) {
        throw new Error(data.error || `Server error (${res.status})`);
      }

      setCurrentAnswer({
        data,
        questionText: textToSubmit,
      });

      if (onQuestionCompleted) {
        onQuestionCompleted();
      }
    } catch (err) {
      if (err.name === "TypeError" && (err.message.includes("fetch") || err.message.includes("NetworkError"))) {
        setError(`Backend not reachable on ${API_BASE}. Please ensure the Legal QA backend is running on port 8002.`);
      } else {
        setError(err.message || "Failed to process legal question");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!loading) handleSubmit();
    }
  };

  return (
    <div className="space-y-6">
      {/* If an answer is currently active, display AnswerPanel */}
      {currentAnswer ? (
        <AnswerPanel
          data={currentAnswer.data}
          questionText={currentAnswer.questionText}
          sourceMode="external"
          onResetQuestion={() => {
            setCurrentAnswer(null);
            setQuestion("");
            setContext("");
            setShowContext(false);
          }}
          darkMode={dm}
          onStatusUpdated={() => {
            if (onQuestionCompleted) onQuestionCompleted();
          }}
        />
      ) : (
        <>
          {/* Answer Language row matching mockup */}
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-2">
              <span className="text-sm">🌐</span>
              <label className={`text-xs font-semibold uppercase tracking-wider ${dm ? "text-slate-400" : "text-slate-600"}`}>
                Answer Language:
              </label>
              <div className="relative inline-flex items-center">
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className={`text-xs font-semibold py-1.5 pl-3 pr-8 rounded-lg border appearance-none cursor-pointer focus:outline-none focus:ring-1 focus:ring-blue-500 ${
                    dm
                      ? "bg-slate-800 border-slate-700 text-white"
                      : "bg-white border-slate-200 text-slate-800 shadow-sm"
                  }`}
                >
                  <option value="en">English</option>
                  <option value="mr">मराठी (Marathi)</option>
                  <option value="hi">हिन्दी (Hindi)</option>
                </select>
                <span className="absolute right-2.5 text-[10px] text-slate-400 pointer-events-none">▼</span>
              </div>
            </div>

            <span className={`text-xs ${dm ? "text-slate-400" : "text-slate-500"}`}>
              General Legal Research · Precedent Search
            </span>
          </div>

          {/* Error Banner */}
          {error && (
            <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 text-sm font-medium flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span>⚠️</span>
                <span>{error}</span>
              </div>
              <button
                onClick={() => setError("")}
                className="text-xs font-bold text-red-500 hover:text-red-700"
              >
                ✕
              </button>
            </div>
          )}

          {/* Ask a Legal Question Card matching mockup Top-Left */}
          <div
            className={`rounded-2xl border shadow-sm transition-all overflow-hidden ${
              dm ? "bg-slate-800/90 border-slate-700/80" : "bg-white border-slate-200/90"
            }`}
          >
            {/* Card Header */}
            <div className="p-5 sm:p-6 pb-4 border-b border-slate-100 dark:border-slate-700/70 flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-blue-500/10 text-blue-600 dark:text-blue-400 flex items-center justify-center text-sm font-bold">
                💬
              </div>
              <div>
                <h2 className={`text-base sm:text-lg font-bold ${dm ? "text-white" : "text-slate-900"}`}>
                  Ask a Legal Question
                </h2>
                <p className={`text-xs ${dm ? "text-slate-400" : "text-slate-500"}`}>
                  Queries are matched against Supreme Court precedents with SerpAPI web fallback
                </p>
              </div>
            </div>

            {/* Input area */}
            <div className="p-5 sm:p-6 pt-4">
              <textarea
                value={question}
                onChange={(e) => {
                  setQuestion(e.target.value);
                  if (error) setError("");
                }}
                onKeyDown={handleKeyDown}
                disabled={loading}
                rows={4}
                placeholder="Type your legal question here... (e.g., What are the legal grounds for bail?)"
                className={`w-full p-4 rounded-xl border text-sm sm:text-base outline-none resize-none transition-all leading-relaxed ${
                  dm
                    ? "bg-slate-900/80 border-slate-700 text-white placeholder-slate-500 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                    : "bg-slate-50/60 border-slate-200 text-slate-900 placeholder-slate-400 focus:border-blue-500 focus:bg-white focus:ring-1 focus:ring-blue-500"
                }`}
              />

              {/* Optional Context Box */}
              {showContext && (
                <div className="mt-3">
                  <label className={`block text-xs font-semibold mb-1.5 ${dm ? "text-slate-300" : "text-slate-600"}`}>
                    Additional Factual Context (optional):
                  </label>
                  <textarea
                    value={context}
                    onChange={(e) => setContext(e.target.value)}
                    disabled={loading}
                    rows={2}
                    placeholder="Provide specific case facts, sections, or jurisdiction details..."
                    className={`w-full p-3 rounded-xl border text-xs outline-none resize-none ${
                      dm
                        ? "bg-slate-900/60 border-slate-700 text-slate-200 placeholder-slate-500"
                        : "bg-white border-slate-200 text-slate-800 placeholder-slate-400"
                    }`}
                  />
                </div>
              )}

              {/* Bottom Actions Row */}
              <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                <button
                  type="button"
                  onClick={() => setShowContext(!showContext)}
                  className={`inline-flex items-center gap-1.5 text-xs font-semibold transition-colors ${
                    showContext
                      ? "text-blue-600 dark:text-blue-400"
                      : dm
                      ? "text-slate-400 hover:text-slate-200"
                      : "text-slate-500 hover:text-slate-800"
                  }`}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                  </svg>
                  <span>{showContext ? "Hide Context" : "Add context (optional)"}</span>
                </button>

                <div className="flex items-center gap-3">
                  <span className={`text-[11px] hidden sm:inline ${dm ? "text-slate-500" : "text-slate-400"}`}>
                    Press Enter to submit · Shift+Enter for new line
                  </span>
                  <button
                    onClick={() => handleSubmit()}
                    disabled={loading || !question.trim()}
                    className={`inline-flex items-center gap-2 px-6 py-2.5 rounded-xl font-bold text-sm text-white transition-all shadow-md ${
                      loading || !question.trim()
                        ? "bg-slate-300 dark:bg-slate-700 text-slate-400 dark:text-slate-500 cursor-not-allowed shadow-none"
                        : "bg-blue-600 hover:bg-blue-700 active:scale-[0.99] shadow-blue-500/20"
                    }`}
                  >
                    {loading ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        <span>Analyzing...</span>
                      </>
                    ) : (
                      <>
                        <span>Ask Question</span>
                        <svg className="w-4 h-4 ml-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                        </svg>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Loading indicator card */}
          {loading && (
            <div
              className={`rounded-2xl border p-8 shadow-sm flex flex-col items-center justify-center text-center ${
                dm ? "bg-slate-800/80 border-slate-700" : "bg-white border-slate-200"
              }`}
            >
              <div className="w-12 h-12 rounded-full border-4 border-blue-500/20 border-t-blue-600 animate-spin mb-4" />
              <h3 className={`text-base font-bold ${dm ? "text-white" : "text-slate-900"}`}>
                Retrieving &amp; Reasoning Legal Context...
              </h3>
              <p className={`text-xs mt-1 max-w-md ${dm ? "text-slate-400" : "text-slate-500"}`}>
                Checking processed knowledge base for matching Supreme Court precedents, evaluating statutory citations, and synthesizing answer.
              </p>
            </div>
          )}

          {/* Quick suggestions section */}
          {!loading && (
            <div className="pt-2">
              <p className={`text-xs font-semibold uppercase tracking-wider mb-2.5 ${dm ? "text-slate-400" : "text-slate-500"}`}>
                Suggested Precedent Queries:
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {SUGGESTIONS.map((sugg) => (
                  <button
                    key={sugg}
                    onClick={() => {
                      setQuestion(sugg);
                      handleSubmit(sugg);
                    }}
                    className={`text-left p-3 rounded-xl border text-xs font-medium transition-all hover:border-blue-500 hover:shadow-sm ${
                      dm
                        ? "bg-slate-800/60 border-slate-700/80 text-slate-300 hover:text-white hover:bg-slate-800"
                        : "bg-white border-slate-200/90 text-slate-700 hover:text-slate-900 hover:bg-slate-50/80"
                    }`}
                  >
                    &ldquo;{sugg}&rdquo;
                  </button>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
