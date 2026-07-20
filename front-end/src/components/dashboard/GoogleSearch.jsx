import { useState } from 'react';

const API_BASE = 'http://localhost:8000/api';  // Changed from 5000 to 8000

export const GoogleSearch = ({ darkMode, onResultSelect }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState(null);
  const [selectedResult, setSelectedResult] = useState(null);
  const [modifiedQuery, setModifiedQuery] = useState(null);

  const handleSearch = async () => {
    if (!query.trim()) return;

    setIsSearching(true);
    setError(null);
    setResults([]);
    setModifiedQuery(null);

    try {
      console.log('Sending Google search request for:', query.trim());
      const response = await fetch(`${API_BASE}/google-search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: query.trim(),
          num_results: 10 // Number of results to return
        }),
      });

      const data = await response.json();
      console.log('Search response:', data);

      if (data.success) {
        if (Array.isArray(data.results)) {
          setResults(data.results);
          // Store the modified query if it was changed
          if (data.modified_query && data.original_query !== data.modified_query) {
            setModifiedQuery(data.modified_query);
          }
        } else {
          console.error('Unexpected results format:', data.results);
          setError('Received unexpected data format from server');
        }
      } else {
        console.error('Search error:', data.error);
        setError(data.error || 'Failed to search Google');
      }
    } catch (err) {
      console.error('Network error:', err);
      setError('Network error while searching Google');
    } finally {
      setIsSearching(false);
    }
  };

  const handleResultClick = (result) => {
    setSelectedResult(result);
    if (onResultSelect) {
      onResultSelect(result);
    }
    // Open the link in a new tab
    window.open(result.link, '_blank');
  };

  return (
    <div className={`${darkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-t border-l border-white'} rounded-2xl shadow-lg overflow-hidden`}>
      <div className="p-6">
        <h2 className={`text-xl font-serif ${darkMode ? 'text-white' : 'text-gray-800'} mb-4 flex items-center`}>
          <span className={`${darkMode ? 'bg-blue-900/50 text-blue-300' : 'bg-blue-100 text-blue-700'} p-1.5 rounded-lg mr-3`}>
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </span>
          Legal Google Search
        </h2>

        <div className="mb-4">
          <div className="flex">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search legal terms..."
              className={`flex-grow px-4 py-2 rounded-l-lg border ${darkMode ? 'bg-slate-700 border-slate-600 text-white' : 'bg-white border-gray-300'} focus:outline-none focus:ring-2 focus:ring-blue-500`}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            />
            <button
              onClick={handleSearch}
              disabled={isSearching}
              className={`px-4 py-2 rounded-r-lg ${darkMode ? 'bg-blue-700 hover:bg-blue-800' : 'bg-blue-600 hover:bg-blue-700'} text-white font-medium transition-colors`}
            >
              {isSearching ? (
                <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              ) : 'Search'}
            </button>
          </div>
          {error && <p className="mt-2 text-red-500 text-sm">{error}</p>}
          {modifiedQuery && (
            <p className={`mt-2 text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Showing legal results for: <span className="font-medium">{modifiedQuery}</span>
            </p>
          )}
        </div>

        {results.length > 0 && (
          <div className={`mt-4 ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>
            <h3 className="font-medium mb-2">Search Results</h3>
            <ul className={`divide-y ${darkMode ? 'divide-gray-700' : 'divide-gray-200'} max-h-96 overflow-y-auto`}>
              {results.map((result, index) => (
                <li key={index} className="py-3">
                  <button
                    onClick={() => handleResultClick(result)}
                    className={`text-left w-full px-3 py-2 rounded-lg transition-colors ${selectedResult === result ? (darkMode ? 'bg-blue-900/30 text-blue-300' : 'bg-blue-50 text-blue-700') : ''}`}
                  >
                    <div className="font-medium text-blue-600 dark:text-blue-400">{result.title}</div>
                    <div className="text-xs text-green-700 dark:text-green-400">{result.link}</div>
                    <div className="text-sm mt-1 opacity-80">{result.snippet}</div>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {isSearching && (
          <div className="flex justify-center items-center py-8">
            <div className="animate-pulse text-center">
              <div className={`${darkMode ? 'text-blue-400' : 'text-blue-600'} mb-2`}>Searching Google...</div>
              <div className={`${darkMode ? 'text-gray-400' : 'text-gray-500'} text-sm`}>This may take a moment</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};