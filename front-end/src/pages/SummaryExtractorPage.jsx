import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../components/dashboard/Header';
import Footer from '../components/dashboard/Footer';

const API_BASE = 'http://localhost:8003/api'; // Changed to port 8003

function SummaryExtractorPage() {
  const [darkMode, setDarkMode] = useState(false);
  const [activePage, setActivePage] = useState('home');
  const [uploadedFile, setUploadedFile] = useState(null);
  const [summaryLength, setSummaryLength] = useState('medium');
  const [language, setLanguage] = useState('english');
  const [focusAreas, setFocusAreas] = useState({
    facts: true,
    arguments: true,
    evidence: true,
    legal_reasoning: true,
    precedents: false
  });
  const [loading, setLoading] = useState(false);
  const [summaryResult, setSummaryResult] = useState(null);
  const [detailedResult, setDetailedResult] = useState(null);
  const [showDetailed, setShowDetailed] = useState(false);
  const [error, setError] = useState('');
  const fileInputRef = useRef(null);
  const navigate = useNavigate();

  const toggleDarkMode = () => {
    const newDarkMode = !darkMode;
    setDarkMode(newDarkMode);
    localStorage.setItem('darkMode', newDarkMode ? 'true' : 'false');
  };

  useEffect(() => {
    const savedDarkMode = localStorage.getItem('darkMode');
    if (savedDarkMode !== null) {
      setDarkMode(savedDarkMode === 'true');
    } else {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      setDarkMode(prefersDark);
      localStorage.setItem('darkMode', prefersDark ? 'true' : 'false');
    }
  }, []);

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file && file.type === 'application/pdf') {
      setUploadedFile(file);
      setError('');
      setSummaryResult(null);
      setDetailedResult(null);
      setShowDetailed(false);
    } else {
      setError('Please select a valid PDF file');
      setUploadedFile(null);
    }
  };

  const handleGenerateSummary = async () => {
    if (!uploadedFile) {
      setError('Please upload a PDF file first');
      return;
    }

    setLoading(true);
    setError('');

    const formData = new FormData();
    formData.append('pdf_file', uploadedFile);
    
    const selectedFocusAreas = Object.entries(focusAreas)
      .filter(([_, checked]) => checked)
      .map(([key, _]) => key.replace('_', ' '));
    
    const preferences = {
      summary_length: summaryLength,
      focus_area: selectedFocusAreas,
      output_language: language
    };
    
    formData.append('preferences', JSON.stringify(preferences));

    try {
      const response = await fetch(`${API_BASE}/summarize`, {
        method: 'POST',
        body: formData
      });

      if (response.ok) {
        const data = await response.json();
        setSummaryResult(data);
        setShowDetailed(false);
        setActivePage('home'); // Switch to results view
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to generate summary');
      }
    } catch (err) {
      setError('Failed to connect to server: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateDetailed = async () => {
    if (!uploadedFile) {
      setError('Please upload a PDF file first');
      return;
    }

    setLoading(true);
    setError('');

    const formData = new FormData();
    formData.append('pdf_file', uploadedFile);
    formData.append('output_language', language);
    
    const selectedFocusAreas = Object.entries(focusAreas)
      .filter(([_, checked]) => checked)
      .map(([key, _]) => key.replace('_', ' '));
    
    formData.append('focus_areas', JSON.stringify(selectedFocusAreas));

    try {
      const response = await fetch(`${API_BASE}/summarize/detailed`, {
        method: 'POST',
        body: formData
      });

      if (response.ok) {
        const data = await response.json();
        setDetailedResult(data);
        setShowDetailed(true);
        setSummaryResult(null);
        setActivePage('home'); // Switch to results view
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to generate detailed analysis');
      }
    } catch (err) {
      setError('Failed to connect to server: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const cardClass = darkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200';

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
              Summary Extractor
            </h1>
            <div className="w-40"></div>
          </div>
          <p className={`text-lg ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            AI-Powered Legal Case Summarization with Multilingual Support
          </p>
        </div>

        {/* Tab Navigation */}
        <div className={`mb-8 border-b ${darkMode ? 'border-slate-700' : 'border-gray-300'}`}>
          <div className="flex gap-1">
            <button
              onClick={() => {
                setActivePage('home');
                setSummaryResult(null);
                setDetailedResult(null);
                setShowDetailed(false);
              }}
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
              📄 Generate Summary
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

        {/* Main Content */}
        {activePage === 'home' && (
          <div className="grid lg:grid-cols-3 gap-8">
            {/* Left Panel - Upload & Preferences */}
            <div className="lg:col-span-1 space-y-6">
              {/* File Upload */}
              <div className={`p-6 border rounded-xl ${cardClass} shadow-lg`}>
                <h2 className={`text-xl font-serif font-bold mb-4 flex items-center gap-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                  <span>📄</span> Upload Document
                </h2>
                
                <input
                  type="file"
                  accept=".pdf"
                  onChange={handleFileSelect}
                  ref={fileInputRef}
                  className="hidden"
                />
                
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className={`w-full p-8 border-2 border-dashed rounded-xl ${
                    darkMode ? 'border-slate-600 hover:border-slate-500' : 'border-gray-300 hover:border-gray-400'
                  } transition-colors cursor-pointer`}
                >
                  <div className="text-center">
                    <div className="text-5xl mb-3">📤</div>
                    <p className={`font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                      Click to upload PDF
                    </p>
                    <p className={`text-sm mt-1 ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
                      Supports: English, Hindi, Marathi
                    </p>
                  </div>
                </button>

                {uploadedFile && (
                  <div className="mt-4 p-3 bg-green-500/10 border border-green-500 rounded-lg">
                    <div className="flex items-center gap-2">
                      <span className="flex-shrink-0">✓</span>
                      <p className="text-sm text-green-600 dark:text-green-400 font-semibold break-all overflow-wrap-anywhere flex-1">
                        {uploadedFile.name}
                      </p>
                    </div>
                    <p className="text-xs text-center mt-1 text-gray-500">
                      {(uploadedFile.size / 1024).toFixed(2)} KB
                    </p>
                  </div>
                )}
              </div>

              {/* Preferences */}
              <div className={`p-6 border rounded-xl ${cardClass} shadow-lg`}>
                <h2 className={`text-xl font-serif font-bold mb-4 flex items-center gap-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                  <span>⚙️</span> Preferences
                </h2>

                {/* Summary Length */}
                <div className="mb-4">
                  <label className={`block text-sm font-semibold mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                    Summary Length
                  </label>
                  <select
                    value={summaryLength}
                    onChange={(e) => setSummaryLength(e.target.value)}
                    className={`w-full px-4 py-2 rounded-lg border ${
                      darkMode ? 'bg-slate-700 border-slate-600 text-white' : 'bg-gray-50 border-gray-300'
                    } focus:ring-2 focus:ring-indigo-500 focus:outline-none`}
                  >
                    <option value="short">Short</option>
                    <option value="medium">Medium</option>
                    <option value="detailed">Detailed</option>
                  </select>
                </div>

                {/* Output Language */}
                <div className="mb-4">
                  <label className={`block text-sm font-semibold mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                    Output Language
                  </label>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setLanguage('english')}
                      className={`flex-1 px-4 py-2 rounded-lg font-medium transition-all ${
                        language === 'english'
                          ? 'bg-indigo-600 text-white shadow-lg'
                          : darkMode ? 'bg-slate-700 text-gray-300 hover:bg-slate-600' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      English
                    </button>
                    <button
                      onClick={() => setLanguage('marathi')}
                      className={`flex-1 px-4 py-2 rounded-lg font-medium transition-all ${
                        language === 'marathi'
                          ? 'bg-indigo-600 text-white shadow-lg'
                          : darkMode ? 'bg-slate-700 text-gray-300 hover:bg-slate-600' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      मराठी
                    </button>
                  </div>
                </div>

                {/* Focus Areas */}
                <div>
                  <label className={`block text-sm font-semibold mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                    Focus Areas
                  </label>
                  <div className="space-y-2">
                    {Object.entries(focusAreas).map(([key, checked]) => (
                      <label key={key} className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={(e) => setFocusAreas({ ...focusAreas, [key]: e.target.checked })}
                          className="w-4 h-4 text-indigo-600 rounded focus:ring-2 focus:ring-indigo-500"
                        />
                        <span className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                          {key.charAt(0).toUpperCase() + key.slice(1).replace('_', ' ')}
                        </span>
                      </label>
                    ))}
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="space-y-3">
                <button
                  onClick={handleGenerateSummary}
                  disabled={!uploadedFile || loading}
                  className="w-full px-6 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 disabled:from-gray-400 disabled:to-gray-500 text-white font-semibold rounded-xl shadow-lg transition-all transform hover:scale-105 disabled:transform-none"
                >
                  {loading && !showDetailed ? '⏳ Processing...' : '🔍 Generate Summary'}
                </button>

                <button
                  onClick={handleGenerateDetailed}
                  disabled={!uploadedFile || loading}
                  className="w-full px-6 py-3 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 disabled:from-gray-400 disabled:to-gray-500 text-white font-semibold rounded-xl shadow-lg transition-all transform hover:scale-105 disabled:transform-none"
                >
                  {loading && showDetailed ? '⏳ Processing...' : '📊 Detailed Analysis'}
                </button>
              </div>
            </div>

            {/* Right Panel - Results */}
            <div className="lg:col-span-2">
              {error && (
                <div className="mb-6 p-4 bg-red-50 border-l-4 border-red-500 rounded-r-lg">
                  <p className="text-red-700 font-medium">❌ {error}</p>
                </div>
              )}

              {!summaryResult && !detailedResult && !error && (
                <div className={`p-12 border rounded-xl ${cardClass} shadow-lg text-center`}>
                  <div className="text-6xl mb-4">⚖️</div>
                  <h3 className={`text-2xl font-serif mb-3 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                    Ready to Extract Summary
                  </h3>
                  <p className={darkMode ? 'text-gray-400' : 'text-gray-600'}>
                    Upload a legal case PDF and configure your preferences to begin
                  </p>
                </div>
              )}

              {summaryResult && !showDetailed && (
                <SummaryView result={summaryResult} darkMode={darkMode} />
              )}

              {detailedResult && showDetailed && (
                <DetailedView 
                  result={detailedResult} 
                  focusAreas={Object.entries(focusAreas)
                    .filter(([_, checked]) => checked)
                    .map(([key, _]) => key.replace('_', ' '))} 
                  darkMode={darkMode} 
                />
              )}
            </div>
          </div>
        )}

        {activePage === 'history' && <HistoryPage darkMode={darkMode} />}
      </main>

      <Footer darkMode={darkMode} />
    </div>
  );
}

// =====================
// SUMMARY VIEW
// =====================
function SummaryView({ result, darkMode }) {
  const metadata = result.metadata || {};
  const confidence = result.confidence_score || {};
  const cardClass = darkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200';

  const getConfidenceColor = (level) => {
    if (level === 'high') return '#10b981';
    if (level === 'medium') return '#f59e0b';
    return '#ef4444';
  };

  return (
    <div className="space-y-6">
      {/* Confidence Score */}
      {confidence && confidence.overall_confidence && (
        <div className={`p-6 border rounded-xl ${cardClass} shadow-lg`}>
          <div className="flex justify-between items-center mb-4">
            <h3 className={`text-xl font-serif font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              Confidence Score
            </h3>
            <div
              className="px-4 py-2 rounded-full text-sm font-bold"
              style={{
                backgroundColor: `${getConfidenceColor(confidence.confidence_level)}20`,
                color: getConfidenceColor(confidence.confidence_level),
                border: `2px solid ${getConfidenceColor(confidence.confidence_level)}`
              }}
            >
              {confidence.confidence_level?.toUpperCase()} - {confidence.overall_confidence}/100
            </div>
          </div>
          <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            {confidence.reliability_assessment}
          </p>
        </div>
      )}

      {/* Case Metadata */}
      <div className={`p-6 border rounded-xl ${cardClass} shadow-lg`}>
        <h3 className={`text-xl font-serif font-bold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          Case Information
        </h3>
        <div className="grid md:grid-cols-2 gap-4">
          <MetadataField label="Case Title" value={metadata.case_title} darkMode={darkMode} />
          <MetadataField label="Court" value={metadata.court_name} darkMode={darkMode} />
          <MetadataField label="Case Number" value={metadata.case_number} darkMode={darkMode} />
          <MetadataField label="Judgment Date" value={metadata.date_of_judgement} darkMode={darkMode} />
          <MetadataField label="Judges" value={metadata.judge_names?.join(', ')} darkMode={darkMode} />
          <MetadataField label="Jurisdiction" value={metadata.jurisdiction} darkMode={darkMode} />
        </div>
      </div>

      {/* Sections Invoked */}
      {metadata.sections_invoked && metadata.sections_invoked.length > 0 && (
        <div className={`p-6 border rounded-xl ${cardClass} shadow-lg`}>
          <h3 className={`text-xl font-serif font-bold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            Sections Invoked
          </h3>
          <div className="flex flex-wrap gap-2">
            {metadata.sections_invoked.map((section, i) => (
              <span
                key={i}
                className={`px-3 py-1 rounded-full text-sm font-medium ${
                  darkMode ? 'bg-indigo-900/30 text-indigo-300' : 'bg-indigo-100 text-indigo-700'
                }`}
              >
                {section}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Summary */}
      <div className={`p-6 border rounded-xl ${cardClass} shadow-lg`}>
        <h3 className={`text-xl font-serif font-bold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          Summary
        </h3>
        <p className={`leading-relaxed ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
          {metadata.summary}
        </p>
      </div>
    </div>
  );
}

// Helper component for metadata fields
function MetadataField({ label, value, darkMode }) {
  return (
    <div>
      <label className={`block text-sm font-semibold mb-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
        {label}
      </label>
      <p className={`${darkMode ? 'text-white' : 'text-gray-900'}`}>
        {value || 'N/A'}
      </p>
    </div>
  );
}

// =====================
// DETAILED VIEW
// =====================
function DetailedView({ result, focusAreas, darkMode }) {
  const cardClass = darkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200';
  const [expandedSection, setExpandedSection] = useState(null);

  const shouldShow = (area) => focusAreas.length === 0 || focusAreas.includes(area);

  return (
    <div className="space-y-6">
      {/* Case Title */}
      <div className={`p-6 border rounded-xl ${cardClass} shadow-lg`}>
        <h2 className={`text-2xl font-serif font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          {result.case_title || 'Case Summary'}
        </h2>
      </div>

      {/* Important Dates */}
      {shouldShow('facts') && result.important_dates && (
        <div className={`p-6 border rounded-xl ${cardClass} shadow-lg`}>
          <h3 className={`text-xl font-serif font-bold mb-4 flex items-center gap-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            <span>📅</span> Important Dates
          </h3>
          <div className="grid md:grid-cols-3 gap-4">
            <DateField label="Incident Date" value={result.important_dates.incident_date} darkMode={darkMode} />
            <DateField label="FIR Date" value={result.important_dates.fir_date} darkMode={darkMode} />
            <DateField label="Judgment Date" value={result.important_dates.judgement_date} darkMode={darkMode} />
          </div>
        </div>
      )}

      {/* Court & Judges */}
      <div className={`p-6 border rounded-xl ${cardClass} shadow-lg`}>
        <h3 className={`text-xl font-serif font-bold mb-4 flex items-center gap-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          <span>🏛️</span> Court & Judges
        </h3>
        <div className="space-y-2">
          <p><strong>Court:</strong> {result.court_and_judge?.court_name || 'N/A'}</p>
          <p><strong>Judges:</strong> {result.court_and_judge?.judge_names?.join(', ') || 'N/A'}</p>
        </div>
      </div>

      {/* Charges & Sections */}
      {shouldShow('evidence') && result.charges_and_sections && result.charges_and_sections.length > 0 && (
        <div className={`p-6 border rounded-xl ${cardClass} shadow-lg`}>
          <h3 className={`text-xl font-serif font-bold mb-4 flex items-center gap-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            <span>⚖️</span> Charges & Sections
          </h3>
          <div className="space-y-3">
            {result.charges_and_sections.map((charge, i) => (
              <div key={i} className={`p-3 rounded-lg ${darkMode ? 'bg-slate-700/50' : 'bg-gray-50'}`}>
                <p className="font-semibold">{charge.section}</p>
                <p className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>{charge.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Brief Facts */}
      {shouldShow('facts') && result.brief_facts && (
        <div className={`p-6 border rounded-xl ${cardClass} shadow-lg`}>
          <h3 className={`text-xl font-serif font-bold mb-4 flex items-center gap-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            <span>📝</span> Brief Facts
          </h3>
          <p className={`leading-relaxed ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
            {result.brief_facts}
          </p>
        </div>
      )}

      {/* Key Issues */}
      {shouldShow('arguments') && result.key_issues && result.key_issues.length > 0 && (
        <div className={`p-6 border rounded-xl ${cardClass} shadow-lg`}>
          <h3 className={`text-xl font-serif font-bold mb-4 flex items-center gap-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            <span>❓</span> Key Issues
          </h3>
          <ul className="space-y-2">
            {result.key_issues.map((issue, i) => (
              <li key={i} className={`pl-4 border-l-4 ${darkMode ? 'border-indigo-500 text-gray-300' : 'border-indigo-600 text-gray-700'}`}>
                {issue}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Arguments */}
      {shouldShow('arguments') && result.arguments && (
        <div className={`p-6 border rounded-xl ${cardClass} shadow-lg`}>
          <h3 className={`text-xl font-serif font-bold mb-4 flex items-center gap-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            <span>💬</span> Arguments
          </h3>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <h4 className="font-semibold mb-2">Prosecution:</h4>
              <p className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                {result.arguments.prosecution}
              </p>
            </div>
            <div>
              <h4 className="font-semibold mb-2">Defense:</h4>
              <p className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                {result.arguments.defense}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Evidence Summary */}
      {shouldShow('evidence') && result.evidence_summary && (
        <div className={`p-6 border rounded-xl ${cardClass} shadow-lg`}>
          <h3 className={`text-xl font-serif font-bold mb-4 flex items-center gap-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            <span>🔍</span> Evidence Summary
          </h3>
          {result.evidence_summary.witnesses && result.evidence_summary.witnesses.length > 0 && (
            <div className="mb-4">
              <h4 className="font-semibold mb-2">Witnesses:</h4>
              <div className="space-y-2">
                {result.evidence_summary.witnesses.map((witness, i) => (
                  <div key={i} className={`p-2 rounded ${darkMode ? 'bg-slate-700/50' : 'bg-gray-50'}`}>
                    <span className="font-medium">{witness.name}</span> - {witness.role}
                    <span className={`ml-2 text-xs px-2 py-1 rounded ${
                      witness.reliability === 'High' ? 'bg-green-500/20 text-green-600' :
                      witness.reliability === 'Medium' ? 'bg-yellow-500/20 text-yellow-600' :
                      'bg-red-500/20 text-red-600'
                    }`}>
                      {witness.reliability}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {result.evidence_summary.material_evidence && result.evidence_summary.material_evidence.length > 0 && (
            <div>
              <h4 className="font-semibold mb-2">Material Evidence:</h4>
              <ul className="list-disc list-inside space-y-1">
                {result.evidence_summary.material_evidence.map((item, i) => (
                  <li key={i} className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>{item}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Legal Analysis */}
      {shouldShow('legal_reasoning') && result.legal_analysis && (
        <div className={`p-6 border rounded-xl ${cardClass} shadow-lg`}>
          <h3 className={`text-xl font-serif font-bold mb-4 flex items-center gap-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            <span>📖</span> Legal Analysis
          </h3>
          <p className={`leading-relaxed ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
            {result.legal_analysis}
          </p>
        </div>
      )}

      {/* Precedents Cited */}
      {shouldShow('precedents') && result.precedents_cited && result.precedents_cited.length > 0 && (
        <div className={`p-6 border rounded-xl ${cardClass} shadow-lg`}>
          <h3 className={`text-xl font-serif font-bold mb-4 flex items-center gap-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            <span>📚</span> Precedents Cited
          </h3>
          <div className="space-y-3">
            {result.precedents_cited.map((prec, i) => (
              <div key={i} className={`p-3 rounded-lg ${darkMode ? 'bg-slate-700/50' : 'bg-gray-50'}`}>
                <p className="font-semibold">{prec.case}</p>
                <p className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>{prec.principle}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Decision Summary */}
      {shouldShow('legal_reasoning') && result.decision_summary && (
        <div className={`p-6 border rounded-xl ${cardClass} shadow-lg`}>
          <h3 className={`text-xl font-serif font-bold mb-4 flex items-center gap-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            <span>⚖️</span> Decision Summary
          </h3>
          <div className="space-y-3">
            <div>
              <strong>Final Order:</strong>
              <p className={darkMode ? 'text-gray-300' : 'text-gray-700'}>{result.decision_summary.final_order}</p>
            </div>
            <div>
              <strong>Sentence:</strong>
              <p className={darkMode ? 'text-gray-300' : 'text-gray-700'}>{result.decision_summary.sentence}</p>
            </div>
            <div>
              <strong>Important Observations:</strong>
              <p className={darkMode ? 'text-gray-300' : 'text-gray-700'}>{result.decision_summary.important_observations}</p>
            </div>
          </div>
        </div>
      )}

      {/* One-Page Summary */}
      <div className={`p-6 border-2 rounded-xl ${darkMode ? 'bg-indigo-900/20 border-indigo-700' : 'bg-indigo-50 border-indigo-200'} shadow-lg`}>
        <h3 className={`text-xl font-serif font-bold mb-4 flex items-center gap-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          <span>📄</span> One-Page Summary for Judges
        </h3>
        <p className={`leading-relaxed ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>
          {result.one_page_summary_for_judges}
        </p>
      </div>

      {/* Risk Flags */}
      <div className={`p-6 border rounded-xl ${cardClass} shadow-lg`}>
        <h3 className={`text-xl font-serif font-bold mb-4 flex items-center gap-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          <span>⚠️</span> Risk Flags
        </h3>
        {result.risk_flags?.missing_evidence && result.risk_flags.missing_evidence.length > 0 && (
          <div className="mb-3">
            <h4 className="text-red-600 font-semibold mb-1">Missing Evidence:</h4>
            <ul className="list-disc list-inside space-y-1">
              {result.risk_flags.missing_evidence.map((item, i) => (
                <li key={i} className="text-sm">{item}</li>
              ))}
            </ul>
          </div>
        )}
        {result.risk_flags?.contradictions && result.risk_flags.contradictions.length > 0 && (
          <div className="mb-3">
            <h4 className="text-yellow-600 font-semibold mb-1">Contradictions:</h4>
            <ul className="list-disc list-inside space-y-1">
              {result.risk_flags.contradictions.map((item, i) => (
                <li key={i} className="text-sm">{item}</li>
              ))}
            </ul>
          </div>
        )}
        {result.risk_flags?.procedural_lapses && result.risk_flags.procedural_lapses.length > 0 && (
          <div>
            <h4 className="text-orange-600 font-semibold mb-1">Procedural Lapses:</h4>
            <ul className="list-disc list-inside space-y-1">
              {result.risk_flags.procedural_lapses.map((item, i) => (
                <li key={i} className="text-sm">{item}</li>
              ))}
            </ul>
          </div>
        )}
        {(!result.risk_flags || 
          (!result.risk_flags.missing_evidence?.length && 
           !result.risk_flags.contradictions?.length && 
           !result.risk_flags.procedural_lapses?.length)) && (
          <p className="text-green-600 font-medium">✓ No risk flags identified</p>
        )}
      </div>

      {/* Extracted Entities */}
      {shouldShow('facts') && result.extracted_entities && (
        <div className={`p-6 border rounded-xl ${cardClass} shadow-lg`}>
          <h3 className={`text-xl font-serif font-bold mb-4 flex items-center gap-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            <span>👥</span> Extracted Entities
          </h3>
          <div className="grid md:grid-cols-2 gap-4">
            <EntityField label="Accused" value={result.extracted_entities.accused} darkMode={darkMode} />
            <EntityField label="Victim" value={result.extracted_entities.victim} darkMode={darkMode} />
            <EntityField label="Witnesses" value={result.extracted_entities.witnesses} darkMode={darkMode} />
            <EntityField label="Locations" value={result.extracted_entities.locations} darkMode={darkMode} />
          </div>
        </div>
      )}
    </div>
  );
}

function DateField({ label, value, darkMode }) {
  return (
    <div className={`p-3 rounded-lg ${darkMode ? 'bg-slate-700/50' : 'bg-gray-50'}`}>
      <p className="text-sm text-gray-400 mb-1">{label}</p>
      <p className={`font-medium ${darkMode ? 'text-white' : 'text-gray-900'}`}>{value || 'N/A'}</p>
    </div>
  );
}

function EntityField({ label, value, darkMode }) {
  return (
    <div>
      <p className="text-sm font-semibold text-gray-400 mb-1">{label}</p>
      <p className={darkMode ? 'text-gray-300' : 'text-gray-700'}>
        {Array.isArray(value) && value.length > 0 ? value.join(', ') : 'N/A'}
      </p>
    </div>
  );
}

// =====================
// HISTORY PAGE COMPONENT - NEW
// =====================
function HistoryPage({ darkMode }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSummary, setSelectedSummary] = useState(null);

  const cardClass = darkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200';

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      const response = await fetch(`${API_BASE}/history`);
      if (response.ok) {
        const data = await response.json();
        setHistory(data.history || []);
      } else {
        console.error('Failed to fetch history');
      }
    } catch (err) {
      console.error('History fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (summaryId) => {
    if (!confirm('Are you sure you want to delete this summary?')) return;

    try {
      const response = await fetch(`${API_BASE}/history/${summaryId}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        setHistory(history.filter(item => item.id !== summaryId));
        if (selectedSummary && selectedSummary.id === summaryId) {
          setSelectedSummary(null);
        }
      } else {
        alert('Failed to delete summary');
      }
    } catch (err) {
      console.error('Delete error:', err);
      alert('Failed to delete summary');
    }
  };

  const handleViewSummary = async (summaryId) => {
    try {
      const response = await fetch(`${API_BASE}/history/${summaryId}`);
      if (response.ok) {
        const data = await response.json();
        setSelectedSummary(data);
      } else {
        alert('Failed to load summary details');
      }
    } catch (err) {
      console.error('View summary error:', err);
      alert('Failed to load summary');
    }
  };

  const filteredHistory = history.filter(item => {
    if (!searchTerm.trim()) return true;
    const searchLower = searchTerm.toLowerCase();
    return (
      item.case_title?.toLowerCase().includes(searchLower) ||
      item.case_number?.toLowerCase().includes(searchLower) ||
      item.created_at?.toLowerCase().includes(searchLower)
    );
  });

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
          No summaries generated yet
        </p>
        <p className={`text-sm mt-2 ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
          Your past case summaries will appear here
        </p>
      </div>
    );
  }

  return (
    <div className="grid lg:grid-cols-3 gap-6">
      {/* History List */}
      <div className="lg:col-span-1 space-y-6">
        <div className={`p-6 border rounded-xl ${cardClass} shadow-lg`}>
          <h2 className={`text-xl font-serif font-bold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            Summary History
          </h2>
          
          {/* Search */}
          <input
            type="text"
            placeholder="Search by case title or number..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className={`w-full px-4 py-2 rounded-lg border mb-4 ${
              darkMode ? 'bg-slate-700 border-slate-600 text-white placeholder-gray-400' : 'bg-gray-50 border-gray-300 placeholder-gray-500'
            } focus:ring-2 focus:ring-indigo-500 focus:outline-none`}
          />

          {/* History Items */}
          <div className="space-y-3 max-h-[600px] overflow-y-auto">
            {filteredHistory.map((item) => (
              <div
                key={item.id}
                className={`p-4 rounded-lg border cursor-pointer transition-all ${
                  selectedSummary && selectedSummary.id === item.id
                    ? darkMode ? 'bg-indigo-900/30 border-indigo-600' : 'bg-indigo-50 border-indigo-500'
                    : darkMode ? 'bg-slate-700/50 border-slate-600 hover:bg-slate-700' : 'bg-gray-50 border-gray-200 hover:bg-gray-100'
                }`}
                onClick={() => handleViewSummary(item.id)}
              >
                <h3 className={`font-semibold mb-1 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                  {item.case_title || 'Untitled Case'}
                </h3>
                <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  {new Date(item.created_at).toLocaleDateString()} {new Date(item.created_at).toLocaleTimeString()}
                </p>
                {item.summary_type && (
                  <span className={`inline-block mt-2 px-2 py-1 rounded text-xs ${
                    darkMode ? 'bg-indigo-900/50 text-indigo-300' : 'bg-indigo-100 text-indigo-700'
                  }`}>
                    {item.summary_type}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Summary Detail View */}
      <div className="lg:col-span-2">
        {!selectedSummary ? (
          <div className={`p-12 border rounded-xl ${cardClass} shadow-lg text-center`}>
            <div className="text-6xl mb-4">👈</div>
            <p className={`text-xl ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Select a summary to view details
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Header with Delete Button */}
            <div className={`p-6 border rounded-xl ${cardClass} shadow-lg flex justify-between items-start`}>
              <div className="flex-1">
                <h2 className={`text-2xl font-serif font-bold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                  {selectedSummary.metadata?.case_title || selectedSummary.case_title || 'Case Summary'}
                </h2>
                <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  Generated on {new Date(selectedSummary.created_at).toLocaleString()}
                </p>
              </div>
              <button
                onClick={() => handleDelete(selectedSummary.id)}
                className="px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors font-medium"
              >
                🗑️ Delete
              </button>
            </div>

            {/* Display summary based on type */}
            {selectedSummary.summary_type === 'detailed' ? (
              <DetailedView 
                result={selectedSummary} 
                focusAreas={[]} 
                darkMode={darkMode} 
              />
            ) : (
              <SummaryView 
                result={selectedSummary} 
                darkMode={darkMode} 
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default SummaryExtractorPage;
