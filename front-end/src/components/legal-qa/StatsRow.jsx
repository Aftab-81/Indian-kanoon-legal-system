import React from "react";

export default function StatsRow({ stats, darkMode: dm }) {
  if (!stats) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className={`rounded-2xl p-4 sm:p-5 border animate-pulse ${
              dm ? "bg-slate-800/60 border-slate-700/60" : "bg-white border-slate-200"
            }`}
          >
            <div className="w-9 h-9 rounded-xl bg-slate-200 dark:bg-slate-700 mb-3" />
            <div className="h-3 w-20 bg-slate-200 dark:bg-slate-700 rounded mb-2" />
            <div className="h-6 w-12 bg-slate-200 dark:bg-slate-700 rounded" />
          </div>
        ))}
      </div>
    );
  }

  const approvalRate =
    stats.approval_rate != null
      ? `${stats.approval_rate}% approval rate`
      : stats.total_questions_asked > 0 && stats.approved_answers != null
      ? `${((stats.approved_answers / stats.total_questions_asked) * 100).toFixed(1)}% approval rate`
      : "No reviews yet";

  const cards = [
    {
      title: "Total Cases",
      value: stats.total_cases_uploaded != null ? stats.total_cases_uploaded : 0,
      subtext: "Uploaded to knowledge base",
      iconBg: dm ? "bg-blue-500/15 text-blue-400 border border-blue-500/20" : "bg-blue-50 text-blue-600 border border-blue-100",
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      ),
    },
    {
      title: "Total Questions",
      value: stats.total_questions_asked != null ? stats.total_questions_asked : 0,
      subtext: "Asked across all sources",
      iconBg: dm ? "bg-indigo-500/15 text-indigo-400 border border-indigo-500/20" : "bg-indigo-50 text-indigo-600 border border-indigo-100",
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
        </svg>
      ),
    },
    {
      title: "Approved Answers",
      value: stats.approved_answers != null ? stats.approved_answers : 0,
      subtext: approvalRate,
      iconBg: dm ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/20" : "bg-emerald-50 text-emerald-600 border border-emerald-100",
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
        </svg>
      ),
    },
    {
      title: "Pending Review",
      value: stats.pending_review != null ? stats.pending_review : 0,
      subtext: "Awaiting user approval",
      iconBg: dm ? "bg-amber-500/15 text-amber-400 border border-amber-500/20" : "bg-amber-50 text-amber-600 border border-amber-100",
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {cards.map((c) => (
        <div
          key={c.title}
          className={`rounded-2xl p-4 sm:p-5 border shadow-sm transition-all hover:shadow-md ${
            dm ? "bg-slate-800/80 border-slate-700/80" : "bg-white border-slate-200/90"
          }`}
        >
          <div className="flex items-start justify-between">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${c.iconBg}`}>
              {c.icon}
            </div>
          </div>
          <div className="mt-3">
            <p className={`text-xs font-semibold uppercase tracking-wider ${dm ? "text-slate-400" : "text-slate-500"}`}>
              {c.title}
            </p>
            <p className={`text-2xl sm:text-3xl font-extrabold mt-0.5 tracking-tight ${dm ? "text-white" : "text-slate-900"}`}>
              {c.value}
            </p>
            <p className={`text-xs mt-1 font-medium ${dm ? "text-slate-400" : "text-slate-500"}`}>
              {c.subtext}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}
