import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import Header from '../components/dashboard/Header';
import Footer from '../components/dashboard/Footer';

// THIS IS THE FIX - Change from 8000 to 8001!
const API_BASE = 'http://localhost:8001/api';  // Research backend on port 8001 (NOT 8000!)

function CaseResearchPage() {
  const [darkMode, setDarkMode] = useState(false);
  const [activePage, setActivePage] = useState('home');
  const [stats, setStats] = useState(null);
  const [language, setLanguage] = useState('en');
  const [documents, setDocuments] = useState([]);
  const [history, setHistory] = useState([]);
  const navigate = useNavigate();

  const toggleDarkMode = () => {
    const newDarkMode = !darkMode;
    setDarkMode(newDarkMode);
    localStorage.setItem('darkMode', newDarkMode ? 'true' : 'false');
  };

  useEffect(() => {
    // Load dark mode preference
    const savedDarkMode = localStorage.getItem('darkMode');
    if (savedDarkMode !== null) {
      setDarkMode(savedDarkMode === 'true');
    } else {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      setDarkMode(prefersDark);
      localStorage.setItem('darkMode', prefersDark ? 'true' : 'false');
    }

    fetchStats();
    fetchDocuments();
    fetchHistory();
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/stats`);
      const data = await res.json();
      setStats(data);
    } catch (err) {
      console.log('Stats error:', err);
    }
  };

  const fetchDocuments = async () => {
    try {
      const response = await axios.get(`${API_BASE}/documents`);
      if (response.data.success) {
        setDocuments(response.data.documents || []);
      }
    } catch (err) {
      console.error('Error fetching documents:', err);
      setDocuments([]);
    }
  };

  const fetchHistory = async () => {
    try {
      const response = await axios.get(`${API_BASE}/history`);
      if (response.data.success) {
        setHistory(response.data.history || []);
      }
    } catch (err) {
      console.error('Error fetching history:', err);
      setHistory([]);
    }
  };

  return (
    <div className={`min-h-screen transition-colors duration-300 ${darkMode ? 'bg-slate-900 text-white' : 'bg-gradient-to-br from-gray-100 to-gray-200'}`}>
      <Header darkMode={darkMode} toggleDarkMode={toggleDarkMode} />

      <main className="container mx-auto px-6 py-8">
        {/* Page Title with Back Button */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-4 mb-3">
            <button
              onClick={() => navigate('/modules')}
              className={`px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2 ${
                darkMode
                  ? 'bg-slate-800 hover:bg-slate-700 text-gray-300 border border-slate-700'
                  : 'bg-white hover:bg-gray-50 text-gray-700 border border-gray-300 shadow-sm'
              }`}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              Back to Modules
            </button>
            <h1 className={`text-4xl font-serif ${darkMode ? 'text-white' : 'text-gray-800'}`}>
              Legal QA System
            </h1>
            <div className="w-40"></div> {/* Spacer for centering */}
          </div>
          <p className={`text-lg ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            AI-Powered Legal Question Answering with Supreme Court Precedents
          </p>
        </div>

        {/* Tab Navigation */}
        <div className={`mb-8 border-b ${darkMode ? 'border-slate-700' : 'border-gray-300'}`}>
          <div className="flex gap-1">
            <button
              onClick={() => setActivePage('home')}
              className={`px-6 py-3 font-medium transition-colors border-b-2 ${
                activePage === 'home'
                  ? darkMode
                    ? 'border-indigo-500 text-indigo-400'
                    : 'border-indigo-600 text-indigo-600'
                  : darkMode
                  ? 'border-transparent text-gray-400 hover:text-gray-300'
                  : 'border-transparent text-gray-600 hover:text-gray-800'
              }`}
            >
              🏠 Ask Question
            </button>
            <button
              onClick={() => setActivePage('upload')}
              className={`px-6 py-3 font-medium transition-colors border-b-2 ${
                activePage === 'upload'
                  ? darkMode
                    ? 'border-indigo-500 text-indigo-400'
                    : 'border-indigo-600 text-indigo-600'
                  : darkMode
                  ? 'border-transparent text-gray-400 hover:text-gray-300'
                  : 'border-transparent text-gray-600 hover:text-gray-800'
              }`}
            >
              📤 Upload Case
            </button>
            <button
              onClick={() => setActivePage('history')}
              className={`px-6 py-3 font-medium transition-colors border-b-2 ${
                activePage === 'history'
                  ? darkMode
                    ? 'border-indigo-500 text-indigo-400'
                    : 'border-indigo-600 text-indigo-600'
                  : darkMode
                  ? 'border-transparent text-gray-400 hover:text-gray-300'
                  : 'border-transparent text-gray-600 hover:text-gray-800'
              }`}
            >
              📋 History
            </button>
          </div>
        </div>

        {/* Stats Bar */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className={`p-4 rounded-xl ${darkMode ? 'bg-slate-800 border border-slate-700' : 'bg-white border border-gray-200'} shadow-lg`}>
            <div className="text-sm text-gray-400 mb-1">Cases Uploaded</div>
            <div className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              {stats?.total_cases_uploaded || 0}
            </div>
          </div>
          <div className={`p-4 rounded-xl ${darkMode ? 'bg-slate-800 border border-slate-700' : 'bg-white border border-gray-200'} shadow-lg`}>
            <div className="text-sm text-gray-400 mb-1">Questions Asked</div>
            <div className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              {stats?.total_questions_asked || 0}
            </div>
          </div>
          <div className={`p-4 rounded-xl ${darkMode ? 'bg-slate-800 border border-slate-700' : 'bg-white border border-gray-200'} shadow-lg`}>
            <div className="text-sm text-gray-400 mb-1">Approved Answers</div>
            <div className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              {stats?.approved_answers || 0}
            </div>
          </div>
          <div className={`p-4 rounded-xl ${darkMode ? 'bg-slate-800 border border-slate-700' : 'bg-white border border-gray-200'} shadow-lg`}>
            <div className="text-sm text-gray-400 mb-1">Cached Queries</div>
            <div className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              {stats?.cached_queries || 0}
            </div>
          </div>
        </div>

        {/* Language Selector */}
        <div className={`mb-6 p-4 rounded-xl ${darkMode ? 'bg-slate-800 border border-slate-700' : 'bg-white border border-gray-200'} shadow-lg`}>
          <label className={`block text-sm font-semibold mb-3 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
            🌐 Answer Language
          </label>
          <div className="flex gap-3">
            <button
              onClick={() => setLanguage('en')}
              className={`px-6 py-2 rounded-lg font-medium transition-all ${
                language === 'en'
                  ? 'bg-indigo-600 text-white shadow-lg transform scale-105'
                  : darkMode
                  ? 'bg-slate-700 text-gray-300 hover:bg-slate-600'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              English
            </button>
            <button
              onClick={() => setLanguage('mr')}
              className={`px-6 py-2 rounded-lg font-medium transition-all ${
                language === 'mr'
                  ? 'bg-indigo-600 text-white shadow-lg transform scale-105'
                  : darkMode
                  ? 'bg-slate-700 text-gray-300 hover:bg-slate-600'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              मराठी
            </button>
          </div>
        </div>

        {/* Main Content */}
        {activePage === 'home' && <HomePage language={language} darkMode={darkMode} />}
        {activePage === 'upload' && <UploadPage darkMode={darkMode} />}
        {activePage === 'history' && <HistoryPage darkMode={darkMode} />}
      </main>

      <Footer darkMode={darkMode} />
    </div>
  );
}

// =====================
// HOME PAGE
// =====================
function HomePage({ language, darkMode }) {
  const [question, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [answer, setAnswer] = useState(null);
  const [error, setError] = useState('');

  const handleAsk = async () => {
    if (!question.trim()) {
      setError('Please enter a question');
      return;
    }

    setLoading(true);
    setError('');
    setAnswer(null);

    try {
      const res = await fetch(`${API_BASE}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, language })
      });

      const data = await res.json();

      if (res.status !== 200) {
        setError(data.error || data.message || 'Error occurred');
      } else {
        setAnswer(data);
      }
    } catch (err) {
      setError('Failed to connect: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (approve, comment) => {
    if (!answer) return;

    try {
      await fetch(`${API_BASE}/approve-answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          answer_id: answer.answer_id,
          approved: approve,
          comment: comment || ''
        })
      });

      setAnswer({
        ...answer,
        status: approve ? 'APPROVED' : 'REJECTED',
        review_comment: comment || ''
      });
    } catch (err) {
      console.error(err);
    }
  };

  const cardClass = darkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200';

  return (
    <div>
      {!answer ? (
        <div className="space-y-6">
          <div className={`p-6 rounded-xl border ${cardClass} shadow-lg`}>
            <label className={`block text-sm font-semibold mb-3 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              Your Legal Question:
            </label>
            <textarea
              value={question}
              onChange={(e) => setText(e.target.value)}
              placeholder="E.g., Under NDPS, can bail be granted if only named in disclosure and no recovery?"
              rows={6}
              disabled={loading}
              className={`w-full px-4 py-3 rounded-lg border ${
                darkMode
                  ? 'bg-slate-700 border-slate-600 text-white placeholder-gray-400'
                  : 'bg-gray-50 border-gray-300 text-gray-900'
              } focus:ring-2 focus:ring-indigo-500 focus:outline-none transition-all`}
            />
          </div>

          {error && (
            <div className="p-4 bg-red-50 border-l-4 border-red-500 rounded-r-lg">
              <p className="text-red-700 font-medium">❌ {error}</p>
            </div>
          )}

          <button
            onClick={handleAsk}
            disabled={loading}
            className="w-full px-6 py-4 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 disabled:from-gray-400 disabled:to-gray-500 text-white font-semibold rounded-xl shadow-lg transition-all transform hover:scale-105 disabled:transform-none"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Analyzing...
              </span>
            ) : (
              '🔍 Ask Question'
            )}
          </button>

          <div className={`p-6 rounded-xl border ${darkMode ? 'bg-blue-900/20 border-blue-700' : 'bg-blue-50 border-blue-200'} shadow-lg`}>
            <h4 className={`font-semibold mb-3 flex items-center gap-2 ${darkMode ? 'text-blue-300' : 'text-blue-800'}`}>
              <span className="text-xl">💡</span> How it works:
            </h4>
            <ul className={`space-y-2 text-sm ${darkMode ? 'text-blue-200' : 'text-blue-700'}`}>
              <li className="flex items-start gap-2">
                <span className="text-indigo-500 font-bold">•</span>
                <span>Searches uploaded Supreme Court judgments (RAG mode)</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-indigo-500 font-bold">•</span>
                <span>If not found, uses external legal reasoning + SerpAPI fallback</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-indigo-500 font-bold">•</span>
                <span>Structured judge-friendly answer with reasoning</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-indigo-500 font-bold">•</span>
                <span>Caching for duplicate question speed</span>
              </li>
            </ul>
          </div>
        </div>
      ) : (
        <AnswerPanel
          answer={answer}
          onApprove={handleApprove}
          onNew={() => {
            setAnswer(null);
            setText('');
          }}
          darkMode={darkMode}
        />
      )}
    </div>
  );
}

// =====================
// ANSWER PANEL
// =====================
function AnswerPanel({ answer, onApprove, onNew, darkMode }) {
  const [expandedCase, setExpandedCase] = useState(null);
  const [reviewComment, setReviewComment] = useState('');

  const getScoreColor = (score) => {
    if (score >= 0.75) return '#10b981';
    if (score >= 0.5) return '#f59e0b';
    return '#ef4444';
  };

  const getScoreLabel = (score) => {
    if (score >= 0.75) return 'HIGH CONFIDENCE';
    if (score >= 0.5) return 'MEDIUM CONFIDENCE';
    return 'LOW - NEEDS REVIEW';
  };

  const validator = answer.validator_result || {};
  const renderPrecedentText = (prec) => {
    if (typeof prec === 'string') return prec;
    if (prec && typeof prec === 'object') {
      const parts = [];
      if (prec.case_name) parts.push(prec.case_name);
      if (prec.citation) parts.push(prec.citation);
      if (prec.summary) parts.push(prec.summary);
      return parts.join(' — ');
    }
    return '';
  };

  const cardClass = darkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200';

  return (
    <div className="space-y-6">
      {/* Cache/Mode Banners */}
      {answer.from_cache && (
        <div className="px-6 py-3 bg-gradient-to-r from-green-500 to-emerald-500 text-white rounded-xl font-semibold shadow-lg flex items-center gap-3">
          <span className="text-2xl">⚡</span>
          <span>Instant Answer (Retrieved from cache)</span>
        </div>
      )}

      {answer.mode && (
        <div className={`px-6 py-3 ${answer.mode === 'EXTERNAL' ? 'bg-gradient-to-r from-blue-600 to-blue-700' : 'bg-gradient-to-r from-green-600 to-emerald-600'} text-white rounded-xl font-semibold shadow-lg flex items-center gap-3`}>
          <span className="text-2xl">{answer.mode === 'EXTERNAL' ? '🌐' : '📄'}</span>
          <span>{answer.mode === 'EXTERNAL' ? 'External Legal Reasoning' : 'RAG: Uploaded Judgments Used'}</span>
        </div>
      )}

      {/* Conclusion Card */}
      <div className={`p-6 border rounded-xl ${cardClass} shadow-lg`}>
        <div className="flex justify-between items-start mb-4">
          <h3 className={`text-2xl font-serif font-bold flex items-center gap-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            <span>📌</span> CONCLUSION
          </h3>
          <div
            className="px-4 py-2 rounded-full text-sm font-bold shadow-md"
            style={{ 
              backgroundColor: `${getScoreColor(answer.uncertainty_score)}20`,
              color: getScoreColor(answer.uncertainty_score),
              border: `2px solid ${getScoreColor(answer.uncertainty_score)}`
            }}
          >
            {getScoreLabel(answer.uncertainty_score)}
          </div>
        </div>

        <p className={`text-lg leading-relaxed mb-4 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
          {answer.conclusion}
        </p>

        <div className="relative w-full h-4 bg-gray-200 rounded-full overflow-hidden shadow-inner">
          <div
            className="h-full transition-all duration-500 rounded-full"
            style={{
              width: `${(answer.uncertainty_score || 0) * 100}%`,
              background: `linear-gradient(to right, ${getScoreColor(answer.uncertainty_score)}, ${getScoreColor(answer.uncertainty_score)}dd)`
            }}
          />
        </div>
        <p className={`text-sm mt-2 font-medium ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
          Confidence: {((answer.uncertainty_score || 0) * 100).toFixed(0)}%
        </p>
      </div>

      {/* Legal Reasoning */}
      <div className={`p-6 border rounded-xl ${cardClass} shadow-lg`}>
        <h3 className={`text-xl font-serif font-bold mb-4 flex items-center gap-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          <span>⚖️</span> LEGAL REASONING
        </h3>
        <div className={`prose max-w-none ${darkMode ? 'prose-invert' : ''}`}>
          <p className={`leading-relaxed ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
            {answer.legal_reasoning}
          </p>
        </div>
      </div>

      {/* Suggested Decision */}
      {answer.suggested_decision?.trim() && (
        <div className={`p-6 border rounded-xl ${cardClass} shadow-lg`}>
          <h3 className={`text-xl font-serif font-bold mb-4 flex items-center gap-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            <span>🧾</span> Suggested Judicial Approach
          </h3>
          <p className={`leading-relaxed ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
            {answer.suggested_decision}
          </p>
        </div>
      )}

      {/* Recommended Next Steps */}
      {Array.isArray(answer.recommended_next_steps) && answer.recommended_next_steps.length > 0 && (
        <div className={`p-6 border rounded-xl ${cardClass} shadow-lg`}>
          <h3 className={`text-xl font-serif font-bold mb-4 flex items-center gap-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            <span>🧭</span> Recommended Next Steps
          </h3>
          <ul className="space-y-3">
            {answer.recommended_next_steps.map((s, i) => (
              <li key={i} className={`pl-6 border-l-4 py-2 ${darkMode ? 'border-indigo-500 text-gray-300' : 'border-indigo-600 text-gray-700'}`}>
                {s}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Precedents */}
      {Array.isArray(answer.precedents) && answer.precedents.length > 0 && (
        <div className={`p-6 border rounded-xl ${cardClass} shadow-lg`}>
          <h3 className={`text-xl font-serif font-bold mb-4 flex items-center gap-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            <span>📖</span> Precedents Cited
          </h3>
          <div className="space-y-3">
            {answer.precedents.map((prec, i) => (
              <div key={i} className={`flex gap-3 p-4 rounded-lg ${darkMode ? 'bg-slate-700/50' : 'bg-gray-50'} border ${darkMode ? 'border-slate-600' : 'border-gray-200'}`}>
                <span className="flex-shrink-0 w-8 h-8 bg-gradient-to-br from-indigo-600 to-purple-600 text-white rounded-full flex items-center justify-center font-bold shadow-lg">
                  {i + 1}
                </span>
                <span className={`flex-1 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                  {renderPrecedentText(prec)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Retrieved Cases */}
      {Array.isArray(answer.retrieved_cases) && answer.retrieved_cases.length > 0 && (
        <div className={`p-6 border rounded-xl ${cardClass} shadow-lg`}>
          <h3 className={`text-xl font-serif font-bold mb-4 flex items-center gap-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            <span>🔗</span> Retrieved Case Chunks
          </h3>
          <div className="space-y-3">
            {answer.retrieved_cases.map((caseItem, i) => (
              <div key={i} className={`border rounded-lg overflow-hidden ${darkMode ? 'border-slate-600 bg-slate-700/30' : 'border-gray-300 bg-gray-50'}`}>
                <button
                  onClick={() => setExpandedCase(expandedCase === i ? null : i)}
                  className={`w-full px-4 py-3 flex justify-between items-center ${darkMode ? 'hover:bg-slate-700/50' : 'hover:bg-gray-100'} transition-colors`}
                >
                  <strong className={darkMode ? 'text-white' : 'text-gray-900'}>
                    {caseItem.case_name}
                  </strong>
                  <span className="text-xl">{expandedCase === i ? '▼' : '▶'}</span>
                </button>
                {expandedCase === i && (
                  <div className={`px-4 py-3 border-t ${darkMode ? 'border-slate-600 text-gray-300 bg-slate-800/50' : 'border-gray-300 text-gray-700 bg-white'}`}>
                    <p className="leading-relaxed">{caseItem.chunk}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Validation */}
      {validator && (
        <div className={`p-6 border rounded-xl ${cardClass} shadow-lg`}>
          <h3 className={`text-xl font-serif font-bold mb-4 flex items-center gap-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            <span>🔍</span> Validation Report
          </h3>
          <div className="grid grid-cols-3 gap-4">
            <div className={`p-4 rounded-lg ${darkMode ? 'bg-slate-700/50' : 'bg-gray-50'}`}>
              <div className="text-sm text-gray-400 mb-1">Valid Answer</div>
              <div className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                {validator.is_valid ? '✅ Yes' : '⚠️ Issues'}
              </div>
            </div>
            <div className={`p-4 rounded-lg ${darkMode ? 'bg-slate-700/50' : 'bg-gray-50'}`}>
              <div className="text-sm text-gray-400 mb-1">Hallucinations</div>
              <div className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                {validator.hallucinations_found || 0}
              </div>
            </div>
            <div className={`p-4 rounded-lg ${darkMode ? 'bg-slate-700/50' : 'bg-gray-50'}`}>
              <div className="text-sm text-gray-400 mb-1">Validation Score</div>
              <div className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                {((validator.confidence_score || 0) * 100).toFixed(0)}%
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Review Comment */}
      <div className={`p-6 border rounded-xl ${cardClass} shadow-lg`}>
        <h3 className={`text-xl font-serif font-bold mb-4 flex items-center gap-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          <span>🧑‍⚖️</span> Human Review (Judge Comment)
        </h3>
        <textarea
          placeholder="Add your comment before approving or rejecting..."
          rows={3}
          value={reviewComment}
          onChange={(e) => setReviewComment(e.target.value)}
          className={`w-full px-4 py-3 rounded-lg border ${
            darkMode ? 'bg-slate-700 border-slate-600 text-white placeholder-gray-400' : 'bg-gray-50 border-gray-300 placeholder-gray-500'
          } focus:ring-2 focus:ring-indigo-500 focus:outline-none transition-all`}
        />
      </div>

      {/* Action Buttons */}
      <div className="grid grid-cols-3 gap-4">
        <button
          onClick={() => onApprove(true, reviewComment)}
          className="px-6 py-3 bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600 text-white font-semibold rounded-xl shadow-lg transition-all transform hover:scale-105"
        >
          ✅ Approve
        </button>
        <button
          onClick={() => onApprove(false, reviewComment)}
          className="px-6 py-3 bg-gradient-to-r from-red-500 to-rose-500 hover:from-red-600 hover:to-rose-600 text-white font-semibold rounded-xl shadow-lg transition-all transform hover:scale-105"
        >
          ❌ Reject
        </button>
        <button
          onClick={onNew}
          className="px-6 py-3 bg-gradient-to-r from-gray-600 to-gray-700 hover:from-gray-700 hover:to-gray-800 text-white font-semibold rounded-xl shadow-lg transition-all transform hover:scale-105"
        >
          📝 Ask Another
        </button>
      </div>

      {/* Status Banner */}
      {answer.status && (
        <div className={`px-6 py-3 rounded-xl font-semibold shadow-lg ${
          answer.status === 'APPROVED' 
            ? 'bg-gradient-to-r from-green-500 to-emerald-500' 
            : answer.status === 'REJECTED' 
            ? 'bg-gradient-to-r from-red-500 to-rose-500' 
            : 'bg-gradient-to-r from-yellow-500 to-orange-500'
        } text-white`}>
          Status: {answer.status}
          {answer.review_comment && (
            <span className="ml-2 italic opacity-90">({answer.review_comment})</span>
          )}
        </div>
      )}
    </div>
  );
}

// =====================
// UPLOAD PAGE
// =====================
function UploadPage({ darkMode }) {
  const [file, setFile] = useState(null);
  const [caseName, setCaseName] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const handleUpload = async () => {
    if (!file) {
      setMessage('❌ Please select a PDF file');
      return;
    }

    setLoading(true);
    setMessage('');

    const formData = new FormData();
    formData.append('file', file);
    formData.append('case_name', caseName || file.name);

    try {
      const res = await fetch(`${API_BASE}/upload-pdf`, {
        method: 'POST',
        body: formData
      });

      const data = await res.json();

      if (data.error) {
        setMessage('❌ ' + data.error);
      } else {
        setMessage('✅ ' + data.message);
        setFile(null);
        setCaseName('');
      }
    } catch (err) {
      setMessage('❌ Upload failed: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const cardClass = darkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200';

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className={`p-8 border-2 border-dashed rounded-xl ${darkMode ? 'border-slate-600 bg-slate-800/50' : 'border-gray-300 bg-gray-50'} shadow-lg transition-all hover:shadow-xl`}>
        <input
          type="file"
          accept=".pdf"
          onChange={(e) => setFile(e.target.files[0])}
          id="file-input"
          disabled={loading}
          className="hidden"
        />
        <label
          htmlFor="file-input"
          className={`block text-center cursor-pointer ${loading ? 'opacity-50 cursor-not-allowed' : 'hover:scale-105 transition-transform'}`}
        >
          <div className="text-6xl mb-4">📄</div>
          <p className={`text-xl font-semibold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            Click to select PDF
          </p>
          <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            Upload Supreme Court judgment documents
          </p>
        </label>
        {file && (
          <div className="mt-4 p-3 bg-green-500/10 border border-green-500 rounded-lg">
            <p className="text-center text-sm text-green-600 dark:text-green-400 font-semibold">
              ✓ Selected: {file.name}
            </p>
          </div>
        )}
      </div>

      <div className={`p-6 border rounded-xl ${cardClass} shadow-lg`}>
        <label className={`block text-sm font-semibold mb-3 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
          Case Name (Optional):
        </label>
        <input
          type="text"
          value={caseName}
          onChange={(e) => setCaseName(e.target.value)}
          placeholder="E.g., State of Goa v. XYZ (2025)"
          disabled={loading}
          className={`w-full px-4 py-3 rounded-lg border ${
            darkMode
              ? 'bg-slate-700 border-slate-600 text-white placeholder-gray-400'
              : 'bg-gray-50 border-gray-300 placeholder-gray-500'
          } focus:ring-2 focus:ring-indigo-500 focus:outline-none transition-all`}
        />
      </div>

      {message && (
        <div className={`p-4 rounded-lg border-l-4 ${
          message.includes('✅') 
            ? 'bg-green-50 border-green-500 dark:bg-green-900/20' 
            : 'bg-red-50 border-red-500 dark:bg-red-900/20'
        }`}>
          <p className={`font-medium ${
            message.includes('✅') 
              ? 'text-green-700 dark:text-green-400' 
              : 'text-red-700 dark:text-red-400'
          }`}>
            {message}
          </p>
        </div>
      )}

      <button
        onClick={handleUpload}
        disabled={loading || !file}
        className="w-full px-6 py-4 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 disabled:from-gray-400 disabled:to-gray-500 text-white font-semibold rounded-xl shadow-lg transition-all transform hover:scale-105 disabled:transform-none"
      >
        {loading ? (
          <span className="flex items-center justify-center gap-2">
            <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            Processing PDF...
          </span>
        ) : (
          '🚀 Upload & Index'
        )}
      </button>

      <div className={`p-6 rounded-xl border ${darkMode ? 'bg-blue-900/20 border-blue-700' : 'bg-blue-50 border-blue-200'} shadow-lg`}>
        <h4 className={`font-semibold mb-3 flex items-center gap-2 ${darkMode ? 'text-blue-300' : 'text-blue-800'}`}>
          <span className="text-xl">💡</span> Smart Indexing:
        </h4>
        <ul className={`space-y-2 text-sm ${darkMode ? 'text-blue-200' : 'text-blue-700'}`}>
          <li className="flex items-start gap-2">
            <span className="text-indigo-500 font-bold">•</span>
            <span>800-word chunks + 200 overlap</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-indigo-500 font-bold">•</span>
            <span>Keeps legal paragraph structure</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-indigo-500 font-bold">•</span>
            <span>Semantic search retrieves best parts</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-indigo-500 font-bold">•</span>
            <span>External fallback if no match found</span>
          </li>
        </ul>
      </div>
    </div>
  );
}

// =====================
// HISTORY PAGE
// =====================
function HistoryPage({ darkMode }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      const response = await axios.get(`${API_BASE}/history`);
      if (response.data.success) {
        setHistory(response.data.history || []);
      }
    } catch (err) {
      console.error('Error fetching history:', err);
    } finally {
      setLoading(false);
    }
  };

  const deleteItem = async (questionId) => {
    if (!confirm('Are you sure you want to delete this question?')) return;
    
    try {
      await fetch(`${API_BASE}/delete-history`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question_id: questionId })
      });
      fetchHistory();
    } catch (err) {
      console.error('Delete error:', err);
    }
  };

  const getStatusColor = (status) => {
    if (status === 'APPROVED') return 'from-green-500 to-emerald-500';
    if (status === 'REJECTED') return 'from-red-500 to-rose-500';
    return 'from-yellow-500 to-orange-500';
  };

  const filteredHistory = history.filter((item) => {
    if (!searchTerm.trim()) return true;
    return (item.question || '').toLowerCase().includes(searchTerm.toLowerCase());
  });

  const cardClass = darkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200';

  if (loading) {
    return (
      <div className="text-center py-12">
        <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-indigo-500 border-t-transparent"></div>
        <p className={`mt-4 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Loading history...</p>
      </div>
    );
  }

  if (history.length === 0) {
    return (
      <div className={`text-center py-12 p-8 border rounded-xl ${cardClass} shadow-lg`}>
        <div className="text-6xl mb-4">📋</div>
        <p className={`text-xl ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
          No questions asked yet
        </p>
        <p className={`text-sm mt-2 ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
          Your past legal queries will appear here
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className={`p-6 border rounded-xl ${cardClass} shadow-lg`}>
        <label className={`block text-sm font-semibold mb-3 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
          Search in history:
        </label>
        <input
          type="text"
          placeholder="Filter previous questions..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className={`w-full px-4 py-3 rounded-lg border ${
            darkMode ? 'bg-slate-700 border-slate-600 text-white placeholder-gray-400' : 'bg-gray-50 border-gray-300 placeholder-gray-500'
          } focus:ring-2 focus:ring-indigo-500 focus:outline-none transition-all`}
        />
      </div>

      <div className="space-y-4">
        {filteredHistory.map((item, i) => (
          <div key={i} className={`p-6 border rounded-xl ${cardClass} shadow-lg hover:shadow-xl transition-shadow`}>
            <div className="flex justify-between items-start mb-4">
              <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                {item.asked_at ? new Date(item.asked_at).toLocaleString() : ''}
              </span>
              {item.status && (
                <span className={`px-3 py-1 rounded-full text-white text-xs font-bold bg-gradient-to-r ${getStatusColor(item.status)} shadow-md`}>
                  {item.status}
                </span>
              )}
            </div>

            <div className="mb-3">
              <strong className={`text-sm ${darkMode ? 'text-indigo-400' : 'text-indigo-600'}`}>Q:</strong>
              <p className={`mt-1 font-medium ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                {item.question}
              </p>
            </div>

            {item.conclusion && (
              <div className="mb-4">
                <strong className={`text-sm ${darkMode ? 'text-green-400' : 'text-green-600'}`}>A:</strong>
                <p className={`mt-1 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                  {item.conclusion.substring(0, 200)}
                  {item.conclusion.length > 200 && '...'}
                </p>
              </div>
            )}

            <button
              onClick={() => deleteItem(item.question_id)}
              className="px-4 py-2 bg-gradient-to-r from-red-500 to-rose-500 hover:from-red-600 hover:to-rose-600 text-white rounded-lg transition-all text-sm font-medium shadow-md transform hover:scale-105"
            >
              🗑️ Delete
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

export default CaseResearchPage;