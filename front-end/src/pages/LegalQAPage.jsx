import React, { useState, useEffect, useCallback } from "react";
import LegalQAHeader from "../components/legal-qa/LegalQAHeader";
import StatsRow from "../components/legal-qa/StatsRow";
import AskQuestionTab from "../components/legal-qa/AskQuestionTab";
import UploadCaseTab from "../components/legal-qa/UploadCaseTab";
import HistoryTab from "../components/legal-qa/HistoryTab";
import { QA_API as API_BASE } from "../config/api";

export default function LegalQAPage() {
  const [darkMode, setDarkMode] = useState(false);
  const [activeTab, setActiveTab] = useState("ask"); // "ask" | "upload" | "history"
  const [language, setLanguage] = useState("en");
  const [stats, setStats] = useState(null);
  const [activeDoc, setActiveDoc] = useState(null);

  // Theme setup
  const toggleDarkMode = () => {
    const next = !darkMode;
    setDarkMode(next);
    localStorage.setItem("darkMode", next ? "true" : "false");
  };

  useEffect(() => {
    const saved = localStorage.getItem("darkMode");
    if (saved !== null) {
      setDarkMode(saved === "true");
    } else {
      const pref = window.matchMedia("(prefers-color-scheme: dark)").matches;
      setDarkMode(pref);
      localStorage.setItem("darkMode", pref ? "true" : "false");
    }
  }, []);

  // Fetch stats from backend
  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/stats`);
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  const tabs = [
    {
      id: "ask",
      label: "Ask Question",
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
        </svg>
      ),
    },
    {
      id: "upload",
      label: "Upload Case",
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
        </svg>
      ),
    },
    {
      id: "history",
      label: "History",
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
    },
  ];

  return (
    <div
      className={`min-h-screen transition-colors duration-200 font-sans ${
        darkMode ? "bg-slate-900 text-slate-100" : "bg-[#F8FAFC] text-slate-900"
      }`}
    >
      {/* Top Header */}
      <LegalQAHeader
        darkMode={darkMode}
        toggleDarkMode={toggleDarkMode}
        language={language}
        setLanguage={setLanguage}
      />

      {/* Main Container */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        {/* Navigation Tabs Bar matching mockup navigation */}
        <div className="mb-6 border-b border-slate-200 dark:border-slate-800">
          <nav className="flex space-x-6 sm:space-x-8" aria-label="Tabs">
            {tabs.map((tab) => {
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`inline-flex items-center gap-2 py-3 px-1 text-sm font-semibold border-b-2 transition-all cursor-pointer ${
                    isActive
                      ? "border-blue-600 text-blue-600 dark:text-blue-400 dark:border-blue-500 font-bold"
                      : "border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 hover:border-slate-300 dark:hover:border-slate-700"
                  }`}
                >
                  <span className={isActive ? "text-blue-600 dark:text-blue-400" : "text-slate-400"}>
                    {tab.icon}
                  </span>
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* Statistics Row - shown prominently across tabs, especially Ask Question */}
        <StatsRow stats={stats} darkMode={darkMode} />

        {/* Tab 1: Ask Question (General legal Q&A only, NO upload component) */}
        {activeTab === "ask" && (
          <AskQuestionTab
            language={language}
            setLanguage={setLanguage}
            darkMode={darkMode}
            onQuestionCompleted={fetchStats}
          />
        )}

        {/* Tab 2: Upload Case (PDF upload, FAISS indexing, and isolated document Q&A) */}
        {activeTab === "upload" && (
          <UploadCaseTab
            language={language}
            darkMode={darkMode}
            activeDoc={activeDoc}
            setActiveDoc={setActiveDoc}
            onDocIndexed={fetchStats}
          />
        )}

        {/* Tab 3: History (Questions, answers, review decisions, search & filters) */}
        {activeTab === "history" && (
          <HistoryTab
            darkMode={darkMode}
            onStatsChanged={fetchStats}
          />
        )}
      </main>
    </div>
  );
}
