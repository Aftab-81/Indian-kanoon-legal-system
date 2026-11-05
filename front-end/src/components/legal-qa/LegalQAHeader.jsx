import React from "react";
import { useNavigate } from "react-router-dom";

export default function LegalQAHeader({
  darkMode,
  toggleDarkMode,
  language,
  setLanguage,
}) {
  const navigate = useNavigate();

  return (
    <header className="bg-[#0B1528] text-white border-b border-slate-800 shadow-lg sticky top-0 z-50 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 sm:h-20">
          {/* Left: Scales of Justice + Title + Subtitle */}
          <div className="flex items-center gap-3 sm:gap-4 min-w-0">
            {/* Scales of Justice Icon */}
            <div className="w-10 h-10 sm:w-11 sm:h-11 rounded-xl bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400 shadow-inner flex-shrink-0">
              <svg
                className="w-6 h-6 sm:w-7 sm:h-7"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth={1.75}
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z" />
                <path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z" />
                <path d="M7 21h10" />
                <path d="M12 3v18" />
                <path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2" />
              </svg>
            </div>

            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h1 className="text-lg sm:text-xl font-bold tracking-tight text-white truncate">
                  Legal QA System
                </h1>
                <span className="hidden md:inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-500/20 text-blue-300 border border-blue-500/30">
                  Judicial Intelligence
                </span>
              </div>
              <p className="text-xs sm:text-sm text-slate-400 truncate font-normal">
                AI-Powered Legal Question Answering with Supreme Court Precedents
              </p>
            </div>
          </div>

          {/* Right: Back to Modules + Language Selector + Theme Toggle + User Avatar */}
          <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0">
            {/* Back to Modules */}
            <button
              onClick={() => navigate("/modules")}
              className="hidden lg:flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-300 hover:text-white bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 transition-all shadow-sm"
              title="Return to Module Selection"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              <span>Modules</span>
            </button>

            {/* Language dropdown */}
            <div className="relative flex items-center">
              <span className="absolute left-2.5 text-slate-400 pointer-events-none text-xs">🌐</span>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="pl-7 pr-7 py-1.5 rounded-lg text-xs font-medium bg-slate-800/90 text-slate-200 border border-slate-700 hover:border-slate-600 focus:outline-none focus:ring-1 focus:ring-blue-500 transition-colors cursor-pointer appearance-none"
                title="Select Answer Language"
              >
                <option value="en">English</option>
                <option value="mr">मराठी (Marathi)</option>
                <option value="hi">हिन्दी (Hindi)</option>
              </select>
              <span className="absolute right-2 text-slate-400 pointer-events-none text-[10px]">▼</span>
            </div>

            {/* Light / Dark Mode Toggle */}
            <button
              onClick={toggleDarkMode}
              className="w-9 h-9 rounded-lg bg-slate-800/90 hover:bg-slate-700 border border-slate-700 flex items-center justify-center text-slate-300 hover:text-white transition-colors"
              title={darkMode ? "Switch to light mode" : "Switch to dark mode"}
              aria-label="Toggle theme"
            >
              {darkMode ? (
                /* Sun Icon */
                <svg className="w-4 h-4 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                </svg>
              ) : (
                /* Moon Icon */
                <svg className="w-4 h-4 text-blue-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                </svg>
              )}
            </button>

            {/* User Profile Avatar */}
            <div
              className="w-9 h-9 rounded-full bg-blue-600 border border-blue-400/40 text-white font-bold text-xs flex items-center justify-center shadow-md select-none"
              title="User Account"
            >
              U
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
