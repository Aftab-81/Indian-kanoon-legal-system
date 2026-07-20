import { useState } from 'react';

const API_BASE = 'http://localhost:8001/api';  // Changed to port 8001

function SearchModal({ darkMode, onClose, onSaveDocument }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSearch = async () => {
    if (!query.trim()) {
      setError('Please enter a search query');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const res = await fetch(`${API_BASE}/search/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      });

      const data = await res.json();

      if (res.status !== 200) {
        setError(data.error || data.message || 'Error occurred');
      } else {
        setResults(data.results || []);
      }
    } catch (err) {
      setError('Failed to connect: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveDocument = async (result) => {
    // ...existing code for saving document...
  };

  return (
    <div className={`fixed inset-0 z-50 flex items-center justify-center p-4 ${darkMode ? 'bg-black/80' : 'bg-white/80'}`}>
      <div className={`w-full max-w-3xl p-6 rounded-lg shadow-lg ${darkMode ? 'bg-slate-800 text-white' : 'bg-white text-gray-900'}`}>
        <div className="flex justify-between items-center mb-4">
          <h2 className={`text-2xl font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            🔍 Search Legal Information
          </h2>
          <button
            onClick={onClose}
            className={`p-2 rounded-full transition-all ${darkMode ? 'hover:bg-slate-700' : 'hover:bg-gray-100'}`}
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="mb-4">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter case number, party name, or legal topic"
            className={`w-full px-4 py-3 rounded-lg border transition-all focus:ring-2 focus:ring-indigo-500 focus:outline-none ${
              darkMode
                ? 'bg-slate-700 border-slate-600 text-white placeholder-gray-400'
                : 'bg-gray-50 border-gray-300 placeholder-gray-500'
            }`}
          />
        </div>

        {error && (
          <div className="p-4 mb-4 text-red-700 bg-red-50 rounded-lg">
            <p className="font-medium">❌ {error}</p>
          </div>
        )}

        <button
          onClick={handleSearch}
          disabled={loading}
          className="w-full px-6 py-4 mb-4 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 disabled:from-gray-400 disabled:to-gray-500 text-white font-semibold rounded-xl shadow-lg transition-all transform hover:scale-105 disabled:transform-none"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              Searching...
            </span>
          ) : (
            '🔍 Search'
          )}
        </button>

        {results.length > 0 && (
          <div className="space-y-4">
            {results.map((result) => (
              <div key={result.file_hash} className={`p-4 rounded-lg border ${darkMode ? 'bg-slate-700 border-slate-600' : 'bg-gray-50 border-gray-200'} shadow-md`}>
                <div className="flex justify-between items-center mb-2">
                  <h3 className={`text-lg font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                    {result.title}
                  </h3>
                  <span className={`px-3 py-1 rounded-full text-xs font-bold ${darkMode ? 'bg-indigo-500 text-white' : 'bg-indigo-100 text-indigo-700'}`}>
                    {result.source === 'document' ? 'Local Document' : 'Web Result'}
                  </span>
                </div>
                <p className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                  {result.snippet}
                </p>
                <div className="flex gap-2 mt-4">
                  <button
                    onClick={() => handleSaveDocument(result)}
                    className="px-4 py-2 bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600 text-white rounded-lg transition-all text-sm font-medium shadow-md transform hover:scale-105"
                  >
                    📥 Save Document
                  </button>
                  <a
                    href={result.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={`px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2 ${
                      darkMode
                        ? 'bg-slate-800 hover:bg-slate-700 text-gray-300'
                        : 'bg-white hover:bg-gray-50 text-gray-700'
                    }`}
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                    </svg>
                    View Full Result
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}

        {results.length === 0 && !loading && (
          <div className="py-12 text-center">
            <p className={`text-lg ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              No results found. Try refining your search query.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default SearchModal;