import { useState } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';
import DocumentDetails from './DocumentDetails';

function SearchComponent({ darkMode }) {
  const [query, setQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [selectedResult, setSelectedResult] = useState(null);
  const [documentDetails, setDocumentDetails] = useState(null);
  
  const API_BASE_URL = 'http://localhost:8001/api';  // CHANGED FROM 8000 TO 8001!

  const handleSearch = async () => {
    const trimmed = query.trim();
    if (!trimmed) return;

    setIsSearching(true);
    setError(null);
    setResults(null);
    setSelectedResult(null);
    setDocumentDetails(null);

    try {
      const formData = new FormData();
      formData.append('query', trimmed);
      const response = await axios.post(`${API_BASE_URL}/search/query`, formData);
      const data = response.data;
      if (data.status === 'invalid_query' || data.status === 'not_found') {
        setError(data.message);
      } else {
        setResults(data);
      }
    } catch (err) {
      const resp = err.response;
      if (resp) {
        if (resp.status === 404) setError('No results found for your query.');
        else if (resp.status === 400 && resp.data?.message) setError(resp.data.message);
        else setError(resp.data?.detail || 'An error occurred during search');
      } else {
        setError('Network error. Please try again.');
      }
      console.error('Search error:', err);
    } finally {
      setIsSearching(false);
    }
  };

  const handleViewDetails = async (fileHash) => {
    setError(null);
    try {
      const response = await axios.get(`${API_BASE_URL}/document/${fileHash}`);
      setDocumentDetails({ ...response.data, file_hash: fileHash });
      setSelectedResult(fileHash);
    } catch (err) {
      setError('Failed to fetch document details.');
      console.error('Error fetching document details:', err);
    }
  };

  const handleSaveRemark = async (fileHash, remark) => {
    setError(null);
    try {
      const resp = await axios.post(
        `${API_BASE_URL}/remarks`,
        { file_hash: fileHash, remark },
        { headers: { 'Content-Type': 'application/json' } }
      );
      if (resp.data.status === 'success') handleViewDetails(fileHash);
      else setError('Failed to save remark.');
    } catch (err) {
      setError('Failed to save remark.');
      console.error('Error saving remark:', err);
    }
  };

  const handleBackToResults = () => {
    setSelectedResult(null);
    setDocumentDetails(null);
  };

  return (
    <div className={`min-h-screen transition-colors duration-300 ${darkMode ? 'bg-slate-900 text-white' : 'bg-gradient-to-br from-gray-100 to-gray-200'}`}>
      <div className="container mx-auto px-6 py-8">
        {/* Back to Dashboard Link */}
        <div className="mb-8">
          <Link 
            to="/reference"
            className={`px-4 py-2 rounded-lg ${darkMode ? 'bg-indigo-800 hover:bg-indigo-700 text-white' : 'bg-indigo-100 hover:bg-indigo-200 text-indigo-700'} transition-colors flex items-center gap-2 shadow-sm w-fit`}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back to Dashboard
          </Link>
        </div>

        <div className={`${darkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-t border-l border-white'} rounded-2xl shadow-lg overflow-hidden relative p-6 mb-8`}>
          <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-blue-500/10 to-purple-500/10 rounded-bl-full"></div>
          
          <h2 className={`text-xl font-serif ${darkMode ? 'text-white' : 'text-gray-800'} mb-6 flex items-center relative z-10`}>
            <span className={`${darkMode ? 'bg-indigo-900/50 text-indigo-300' : 'bg-indigo-100 text-indigo-700'} p-1.5 rounded-lg mr-3`}>
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </span>
            Legal Search
          </h2>

          <div className="relative z-10">
            <p className={`mb-3 text-sm ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
              Enter your query (e.g., 'Maneka Gandhi v. Union of India', 'Section 377 IPC', 'IPC Section 402')
            </p>
            <div className="flex flex-col md:flex-row gap-4">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Enter your legal query"
                className={`flex-grow px-4 py-3 border rounded-lg ${
                  darkMode 
                    ? 'bg-slate-700 border-slate-600 text-white placeholder-slate-400' 
                    : 'bg-white border-gray-200 text-gray-800 placeholder-gray-400'
                } focus:outline-none focus:ring-2 ${
                  darkMode ? 'focus:ring-indigo-500' : 'focus:ring-indigo-400'
                } transition-all duration-300`}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              />
              <button
                onClick={handleSearch}
                disabled={isSearching}
                className={`px-6 py-3 rounded-lg transition-colors flex items-center justify-center gap-2 font-medium ${
                  darkMode
                    ? 'bg-indigo-600 hover:bg-indigo-700 text-white disabled:bg-indigo-800 disabled:text-indigo-300'
                    : 'bg-indigo-600 hover:bg-indigo-700 text-white disabled:bg-indigo-400'
                }`}
              >
                {isSearching ? (
                  <>
                    <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span>Searching...</span>
                  </>
                ) : (
                  <>
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                    <span>Search</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {error && (
          <div className={`p-4 mb-6 rounded-xl flex items-center ${
            darkMode 
              ? 'bg-red-900/20 text-red-300 border border-red-800/30' 
              : 'bg-red-50 text-red-700 border border-red-100'
          }`}>
            <svg className="w-5 h-5 mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p>{error}</p>
          </div>
        )}

        {results && !selectedResult && (
          <div className={`${darkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-t border-l border-white'} rounded-2xl shadow-lg overflow-hidden relative p-6`}>
            <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-blue-500/10 to-purple-500/10 rounded-bl-full"></div>
            
            <h2 className={`text-xl font-serif ${darkMode ? 'text-white' : 'text-gray-800'} mb-4 flex items-center relative z-10`}>
              <span className={`${darkMode ? 'bg-green-900/50 text-green-300' : 'bg-green-100 text-green-700'} p-1.5 rounded-lg mr-3`}>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
              </span>
              Search Results
              {results.from_cache && (
                <span className="ml-2 text-sm font-normal text-gray-500 dark:text-gray-400">
                  (Similar query: "{results.cached_query}")
                </span>
              )}
            </h2>

            <div className="relative z-10">
              {results.results.length > 0 ? (
                <div className="space-y-4">
                  {results.results.map((item, idx) => (
                    <div 
                      key={idx} 
                      className={`rounded-xl p-5 transition-all duration-300 ${
                        darkMode 
                          ? 'bg-slate-700/50 hover:bg-slate-700 border border-slate-600' 
                          : 'bg-white hover:bg-gray-50 border border-gray-200 shadow-sm hover:shadow'
                      }`}
                    >
                      {'filename' in item ? (
                        <>
                          <h4 className={`font-medium text-lg ${darkMode ? 'text-white' : 'text-gray-800'}`}>
                            {item.filename} 
                            <span className={`ml-2 text-sm font-normal ${darkMode ? 'text-indigo-300' : 'text-indigo-600'}`}>
                              ({item.source === 'webpage' ? 'Webpage' : 'Document'})
                            </span>
                          </h4>
                          <div className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium my-2 ${
                            darkMode ? 'bg-indigo-900/30 text-indigo-300' : 'bg-indigo-100 text-indigo-800'
                          }`}>
                            Confidence: {item.confidence.toFixed(1)}%
                          </div>
                          
                          {/* Display summary if available */}
                          {item.analysis?.summary && (
                            <div className={`my-3 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                              <h5 className={`text-sm font-medium mb-1 ${darkMode ? 'text-gray-200' : 'text-gray-600'}`}>Summary:</h5>
                              <p className="text-sm">{item.analysis.summary}</p>
                            </div>
                          )}
                          
                          {/* Display text snippet if no summary */}
                          {!item.analysis?.summary && (
                            <p className={`my-3 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                              {item.text}
                            </p>
                          )}
                          
                          {/* Always display URL if available */}
                          {item.url && (
                            <a
                              href={item.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className={`flex items-center ${darkMode ? 'text-blue-400 hover:text-blue-300' : 'text-blue-600 hover:text-blue-700'} mb-3`}
                            >
                              <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                              </svg>
                              View Source
                            </a>
                          )}
                        </>
                      ) : (
                        <>
                          <h4 className={`font-medium text-lg ${darkMode ? 'text-white' : 'text-gray-800'}`}>
                            {item.title}
                          </h4>
                          <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'} mb-1`}>
                            {item.citation} | {item.year} | {item.court}
                          </p>
                          <div className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium my-2 ${
                            darkMode ? 'bg-indigo-900/30 text-indigo-300' : 'bg-indigo-100 text-indigo-800'
                          }`}>
                            Confidence: {item.confidence.toFixed(1)}%
                          </div>
                          
                          {/* Display summary if available */}
                          {item.analysis?.summary && (
                            <div className={`my-3 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                              <h5 className={`text-sm font-medium mb-1 ${darkMode ? 'text-gray-200' : 'text-gray-600'}`}>Summary:</h5>
                              <p className="text-sm">{item.analysis.summary}</p>
                            </div>
                          )}
                          
                          {/* Display holding if no summary */}
                          {!item.analysis?.summary && (
                            <p className={`my-3 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                              {item.holding || 'No details available'}
                            </p>
                          )}
                          
                          {/* Display URL if available */}
                          {item.url && (
                            <a
                              href={item.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className={`flex items-center ${darkMode ? 'text-blue-400 hover:text-blue-300' : 'text-blue-600 hover:text-blue-700'} mb-3`}
                            >
                              <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                              </svg>
                              View Source
                            </a>
                          )}
                        </>
                      )}
                      <button
                        onClick={() => handleViewDetails(item.file_hash)}
                        className={`mt-2 flex items-center ${
                          darkMode 
                            ? 'text-indigo-400 hover:text-indigo-300' 
                            : 'text-indigo-600 hover:text-indigo-800'
                        } font-medium transition-colors duration-200`}
                      >
                        <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                        </svg>
                        View Full Details
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <div className={`p-8 text-center ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                  <svg className="w-12 h-12 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <p className="text-lg italic">No results available.</p>
                </div>
              )}
            </div>
          </div>
        )}

        {selectedResult && documentDetails && (
          <div className={`${darkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-t border-l border-white'} rounded-2xl shadow-lg overflow-hidden relative p-6`}>
            <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-blue-500/10 to-purple-500/10 rounded-bl-full"></div>
            
            <div className="mb-4 relative z-10">
              <button
                onClick={handleBackToResults}
                className={`flex items-center ${
                  darkMode 
                    ? 'text-indigo-400 hover:text-indigo-300' 
                    : 'text-indigo-600 hover:text-indigo-800'
                } font-medium transition-colors duration-200`}
              >
                <svg className="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                </svg>
                Back to results
              </button>
            </div>
            
            <div className="relative z-10">
              <DocumentDetails
                document={documentDetails}
                onSaveRemark={handleSaveRemark}
                darkMode={darkMode}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default SearchComponent;