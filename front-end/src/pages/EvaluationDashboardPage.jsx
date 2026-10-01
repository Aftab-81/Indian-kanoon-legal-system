import { useState, useEffect, useCallback } from 'react';
import './EvaluationDashboardPage.css';
import { EVAL_API } from '../config/api';
import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from 'recharts';

// ─── Constants ─────────────────────────────────────────────────────────────

const MODULE_META = {
  legal_qa: {
    label: 'Legal QA',
    icon: '⚖️',
    description: 'Measures answer faithfulness, relevancy, context precision and factual correctness for legal Q&A.',
    color: '#6366f1',
    accent: '#4f46e5',
  },
  research: {
    label: 'Research',
    icon: '🔍',
    description: 'Measures context precision and recall for hybrid FAISS document search.',
    color: '#06b6d4',
    accent: '#0891b2',
  },
  summary: {
    label: 'Summary',
    icon: '📝',
    description: 'Measures summary faithfulness and completeness against reference summaries.',
    color: '#f59e0b',
    accent: '#d97706',
  },
  comprehension: {
    label: 'Comprehension',
    icon: '📖',
    description: 'Measures per-field extraction accuracy and semantic similarity of the 8 canonical judgment fields.',
    color: '#10b981',
    accent: '#059669',
  },
};

const METRIC_LABELS = {
  faithfulness: 'Faithfulness',
  response_relevancy: 'Response Relevancy',
  llm_context_precision_with_reference: 'Context Precision',
  context_recall: 'Context Recall',
  factual_correctness: 'Factual Correctness',
  semantic_similarity: 'Semantic Similarity',
  context_entity_recall: 'Entity Recall',
  cites_page_numbers: 'Cites Pages',
  covers_core_elements: 'Core Elements',
  no_invented_details: 'No Invented Details',
  field_is_complete: 'Field Completeness',
};

const SCORE_COLOR = (v) => {
  if (v === null || v === undefined) return '#94a3b8';
  if (v >= 0.8) return '#10b981';
  if (v >= 0.6) return '#f59e0b';
  return '#ef4444';
};

// ─── Helpers ───────────────────────────────────────────────────────────────

const pct = (v) => (v !== null && v !== undefined ? `${(v * 100).toFixed(1)}%` : '—');

const ScoreBadge = ({ value }) => {
  if (value === null || value === undefined) return <span className="score-badge score-na">N/A</span>;
  const pv = (value * 100).toFixed(1);
  const cls = value >= 0.8 ? 'score-high' : value >= 0.6 ? 'score-mid' : 'score-low';
  return <span className={`score-badge ${cls}`}>{pv}%</span>;
};

// ─── Sub-components ─────────────────────────────────────────────────────────

const ModuleCard = ({ module, data, selected, onClick }) => {
  const meta = MODULE_META[module];
  const agg = data?.aggregate || {};
  const scores = Object.values(agg).filter((v) => v !== null);
  const mean = scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : null;
  const nSamples = data?.metadata?.n_samples || '—';

  return (
    <button
      onClick={onClick}
      className={`module-card ${selected ? 'selected' : ''}`}
      style={{ '--accent': meta.color }}
    >
      <div className="module-card-icon">{meta.icon}</div>
      <h3 className="module-card-title">{meta.label}</h3>
      <p className="module-card-desc">{meta.description}</p>
      <div className="module-card-stats">
        <div className="stat">
          <span className="stat-label">Overall</span>
          <span className="stat-value" style={{ color: SCORE_COLOR(mean) }}>
            {pct(mean)}
          </span>
        </div>
        <div className="stat">
          <span className="stat-label">Samples</span>
          <span className="stat-value">{nSamples}</span>
        </div>
      </div>
      {data ? (
        <span className="module-status ready">Results ready ✓</span>
      ) : (
        <span className="module-status pending">No results yet</span>
      )}
    </button>
  );
};

const MetricBar = ({ name, value }) => {
  const label = METRIC_LABELS[name] || name;
  const pv = value !== null && value !== undefined ? value * 100 : null;
  return (
    <div className="metric-bar-row">
      <span className="metric-bar-label">{label}</span>
      <div className="metric-bar-track">
        <div
          className="metric-bar-fill"
          style={{ width: pv !== null ? `${pv}%` : '0%', background: SCORE_COLOR(value) }}
        />
      </div>
      <ScoreBadge value={value} />
    </div>
  );
};

const SamplesTable = ({ samples = [] }) => (
  <div className="samples-table-wrap">
    <table className="samples-table">
      <thead>
        <tr>
          <th>#</th>
          <th>Question / Input</th>
          <th>Scores</th>
          <th>Flag</th>
        </tr>
      </thead>
      <tbody>
        {samples.map((s, i) => (
          <tr key={s.id} className={s.flag === 'low' ? 'row-low' : ''}>
            <td className="cell-idx">{i + 1}</td>
            <td className="cell-input">{s.user_input?.slice(0, 120)}{s.user_input?.length > 120 ? '…' : ''}</td>
            <td className="cell-scores">
              {Object.entries(s.scores || {}).map(([k, v]) => (
                <span key={k} className="score-chip" title={METRIC_LABELS[k] || k}>
                  {(METRIC_LABELS[k] || k).slice(0, 8)}: {pct(v)}
                </span>
              ))}
            </td>
            <td>
              <span className={`flag-badge ${s.flag}`}>{s.flag === 'low' ? '⚠ Low' : '✓ OK'}</span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

// ─── Main Page ──────────────────────────────────────────────────────────────

export default function EvaluationDashboardPage() {
  const [results, setResults] = useState({});
  const [status, setStatus] = useState({});
  const [glossary, setGlossary] = useState({});
  const [selectedModule, setSelectedModule] = useState(null);
  const [detailData, setDetailData] = useState(null);
  const [running, setRunning] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [showGlossary, setShowGlossary] = useState(false);

  const MODULES = ['legal_qa', 'research', 'summary', 'comprehension'];

  // ── fetch overview ─────────────────────────────────────────
  const fetchAll = useCallback(async () => {
    try {
      const [resR, statusR, glossR] = await Promise.all([
        fetch(`${EVAL_API}/results`),
        fetch(`${EVAL_API}/status`),
        fetch(`${EVAL_API}/glossary`),
      ]);
      if (resR.ok) setResults(await resR.json());
      if (statusR.ok) setStatus(await statusR.json());
      if (glossR.ok) setGlossary(await glossR.json());
    } catch (e) {
      setError('Evaluation API offline. Start it with: python -m uvicorn evaluation.api:app --port 8005');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, 10000);
    return () => clearInterval(interval);
  }, [fetchAll]);

  // ── fetch module detail ─────────────────────────────────────
  const fetchDetail = useCallback(async (mod) => {
    if (!mod) return;
    try {
      const r = await fetch(`${EVAL_API}/results/${mod}`);
      if (r.ok) setDetailData(await r.json());
      else setDetailData(null);
    } catch {
      setDetailData(null);
    }
  }, []);

  const handleSelectModule = (mod) => {
    setSelectedModule(mod);
    fetchDetail(mod);
    setActiveTab('overview');
  };

  // ── trigger evaluation ──────────────────────────────────────
  const triggerRun = async (mod) => {
    setRunning((p) => ({ ...p, [mod]: true }));
    try {
      const r = await fetch(`${EVAL_API}/run/${mod}`, { method: 'POST' });
      if (!r.ok) {
        const body = await r.json().catch(() => ({}));
        alert(body.detail || 'Failed to start evaluation');
      }
    } catch {
      alert('Could not reach evaluation API');
    } finally {
      setTimeout(() => setRunning((p) => ({ ...p, [mod]: false })), 3000);
    }
  };

  // ── radar chart data ────────────────────────────────────────
  const buildRadarData = () => {
    const allMetrics = new Set();
    MODULES.forEach((m) => {
      const agg = results[m]?.aggregate || {};
      Object.keys(agg).forEach((k) => allMetrics.add(k));
    });
    return [...allMetrics].map((metric) => {
      const row = { metric: METRIC_LABELS[metric] || metric };
      MODULES.forEach((m) => {
        const v = results[m]?.aggregate?.[metric];
        row[m] = v !== null && v !== undefined ? +(v * 100).toFixed(1) : 0;
      });
      return row;
    });
  };

  const buildBarData = (mod) => {
    const agg = results[mod]?.aggregate || {};
    return Object.entries(agg)
      .filter(([, v]) => v !== null)
      .map(([k, v]) => ({
        name: METRIC_LABELS[k] || k,
        value: +(v * 100).toFixed(1),
        fill: SCORE_COLOR(v),
      }));
  };

  const buildPerFieldData = (metadata) => {
    const pf = metadata?.per_field_aggregate || {};
    return Object.entries(pf)
      .filter(([, v]) => v !== null)
      .map(([k, v]) => ({ name: k.replace(/\(.+\)/, '').trim(), value: +(v * 100).toFixed(1), fill: SCORE_COLOR(v) }));
  };

  // ─────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="eval-page">
        <div className="eval-loading">
          <div className="spinner" />
          <p>Loading Evaluation Dashboard…</p>
        </div>
      </div>
    );
  }

  const radarData = buildRadarData();
  const selectedResult = results[selectedModule];
  const selectedStatus = status[selectedModule];
  const isRunning = selectedStatus?.job?.status === 'running' || running[selectedModule];
  const lowFlagSamples = detailData?.samples?.filter((s) => s.flag === 'low') || [];

  return (
    <div className="eval-page">
      {/* ── HEADER ── */}
      <header className="eval-header">
        <div className="eval-header-left">
          <span className="eval-badge">🧪 RAGAS</span>
          <h1>Evaluation Dashboard</h1>
          <span className="eval-subtitle">Automated quality metrics for the Judicial Insight Engine</span>
        </div>
        <div className="eval-header-right">
          <button className="btn-ghost" onClick={() => setShowGlossary(!showGlossary)}>
            {showGlossary ? 'Hide Glossary' : '📚 Glossary'}
          </button>
          <button className="btn-primary" onClick={() => triggerRun('all')} disabled={running['all']}>
            {running['all'] ? '⏳ Running…' : '▶ Run All'}
          </button>
          <button className="btn-ghost small" onClick={fetchAll}>↻ Refresh</button>
        </div>
      </header>

      {error && (
        <div className="eval-alert">
          <span>⚠️</span> {error}
        </div>
      )}

      {/* ── GLOSSARY PANEL ── */}
      {showGlossary && (
        <div className="glossary-panel">
          <h3>Metric Glossary</h3>
          <div className="glossary-grid">
            {Object.entries(glossary).map(([k, v]) => (
              <div key={k} className="glossary-item">
                <strong>{METRIC_LABELS[k] || k}</strong>
                <p>{v}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── MODULE CARDS ── */}
      <section className="eval-cards">
        {MODULES.map((mod) => (
          <ModuleCard
            key={mod}
            module={mod}
            data={results[mod]}
            selected={selectedModule === mod}
            onClick={() => handleSelectModule(mod)}
          />
        ))}
      </section>

      {/* ── OVERVIEW RADAR (only when ≥ 2 modules have results) ── */}
      {radarData.length > 0 && Object.values(results).filter(Boolean).length >= 2 && (
        <section className="eval-radar-section">
          <h2>Cross-Module Overview</h2>
          <ResponsiveContainer width="100%" height={350}>
            <RadarChart data={radarData} margin={{ top: 10, right: 30, bottom: 10, left: 30 }}>
              <PolarGrid stroke="#334155" />
              <PolarAngleAxis dataKey="metric" tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <PolarRadiusAxis domain={[0, 100]} tick={{ fill: '#64748b', fontSize: 10 }} />
              {MODULES.map((m) =>
                results[m] ? (
                  <Radar
                    key={m}
                    name={MODULE_META[m].label}
                    dataKey={m}
                    stroke={MODULE_META[m].color}
                    fill={MODULE_META[m].color}
                    fillOpacity={0.12}
                    strokeWidth={2}
                  />
                ) : null
              )}
              <Legend
                formatter={(v) => MODULE_META[v]?.label || v}
                wrapperStyle={{ color: '#94a3b8', fontSize: 12 }}
              />
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', color: '#f1f5f9' }}
                formatter={(v) => [`${v}%`]}
              />
            </RadarChart>
          </ResponsiveContainer>
        </section>
      )}

      {/* ── DETAIL PANEL ── */}
      {selectedModule && (
        <section className="eval-detail">
          <div className="eval-detail-header">
            <h2>
              {MODULE_META[selectedModule].icon} {MODULE_META[selectedModule].label} — Detail
            </h2>
            <div className="eval-detail-actions">
              {!isRunning ? (
                <button className="btn-primary small" onClick={() => triggerRun(selectedModule)}>
                  ▶ Re-run Evaluation
                </button>
              ) : (
                <span className="running-badge">⏳ Evaluating…</span>
              )}
            </div>
          </div>

          {selectedResult ? (
            <>
              {/* Tabs */}
              <div className="detail-tabs">
                {['overview', 'samples', 'notes'].map((tab) => (
                  <button
                    key={tab}
                    className={`detail-tab ${activeTab === tab ? 'active' : ''}`}
                    onClick={() => setActiveTab(tab)}
                  >
                    {tab.charAt(0).toUpperCase() + tab.slice(1)}
                    {tab === 'samples' && lowFlagSamples.length > 0 && (
                      <span className="tab-badge">{lowFlagSamples.length} ⚠</span>
                    )}
                  </button>
                ))}
              </div>

              {activeTab === 'overview' && (
                <div className="detail-overview">
                  {/* Metadata */}
                  <div className="meta-row">
                    {[
                      ['Samples', selectedResult.metadata?.n_samples],
                      ['Judge', selectedResult.metadata?.judge_model],
                      ['Ragas', selectedResult.metadata?.ragas_version],
                      ['Run at', selectedResult.metadata?.run_timestamp?.slice(0, 19).replace('T', ' ')],
                    ].map(([l, v]) => (
                      <div key={l} className="meta-item">
                        <span className="meta-label">{l}</span>
                        <span className="meta-value">{v ?? '—'}</span>
                      </div>
                    ))}
                  </div>

                  {/* Bar chart */}
                  <div className="detail-chart">
                    <h3>Metric Scores (% )</h3>
                    <ResponsiveContainer width="100%" height={220}>
                      <BarChart data={buildBarData(selectedModule)} margin={{ left: 0, right: 20 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                        <XAxis
                          dataKey="name"
                          tick={{ fill: '#94a3b8', fontSize: 10 }}
                          interval={0}
                          angle={-20}
                          textAnchor="end"
                          height={60}
                        />
                        <YAxis domain={[0, 100]} tick={{ fill: '#64748b', fontSize: 10 }} unit="%" />
                        <Tooltip
                          contentStyle={{ background: '#1e293b', border: '1px solid #334155', color: '#f1f5f9' }}
                          formatter={(v) => [`${v}%`]}
                        />
                        <Bar dataKey="value" maxBarSize={50}>
                          {buildBarData(selectedModule).map((entry, idx) => (
                            <Cell key={idx} fill={entry.fill} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>

                  {/* Per-field chart (comprehension only) */}
                  {selectedModule === 'comprehension' && selectedResult.metadata?.per_field_aggregate && (
                    <div className="detail-chart">
                      <h3>Per-Field Accuracy</h3>
                      <ResponsiveContainer width="100%" height={200}>
                        <BarChart data={buildPerFieldData(selectedResult.metadata)} margin={{ left: 0, right: 20 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                          <XAxis
                            dataKey="name"
                            tick={{ fill: '#94a3b8', fontSize: 10 }}
                            interval={0}
                            angle={-25}
                            textAnchor="end"
                            height={70}
                          />
                          <YAxis domain={[0, 100]} tick={{ fill: '#64748b', fontSize: 10 }} unit="%" />
                          <Tooltip
                            contentStyle={{ background: '#1e293b', border: '1px solid #334155', color: '#f1f5f9' }}
                            formatter={(v) => [`${v}%`]}
                          />
                          <Bar dataKey="value" maxBarSize={50}>
                            {buildPerFieldData(selectedResult.metadata).map((e, i) => (
                              <Cell key={i} fill={e.fill} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  )}

                  {/* Metric bars */}
                  <div className="metric-bars">
                    <h3>Score Breakdown</h3>
                    {Object.entries(selectedResult.aggregate || {}).map(([k, v]) => (
                      <MetricBar key={k} name={k} value={v} />
                    ))}
                  </div>
                </div>
              )}

              {activeTab === 'samples' && (
                <div className="detail-samples">
                  <div className="samples-header">
                    <span>
                      {detailData?.samples?.length ?? 0} samples&nbsp;
                      {lowFlagSamples.length > 0 && (
                        <span className="low-count">({lowFlagSamples.length} low-scoring)</span>
                      )}
                    </span>
                  </div>
                  <SamplesTable samples={detailData?.samples || []} />
                </div>
              )}

              {activeTab === 'notes' && (
                <div className="detail-notes">
                  <h3>Evaluation Notes</h3>
                  {(selectedResult.notes || []).length > 0 ? (
                    <ul>
                      {selectedResult.notes.map((n, i) => (
                        <li key={i}>{n}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="no-notes">No notes for this evaluation run.</p>
                  )}
                </div>
              )}
            </>
          ) : (
            <div className="no-result">
              <p>No results yet for <strong>{MODULE_META[selectedModule].label}</strong>.</p>
              <p>Click <strong>▶ Re-run Evaluation</strong> to start.</p>
              <p className="hint">This calls the live backends and uses GPT-4o-mini as judge. Estimated time: 3–8 min per module.</p>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
