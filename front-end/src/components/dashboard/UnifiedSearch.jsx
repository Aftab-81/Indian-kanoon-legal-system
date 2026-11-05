import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const API_BASE = 'http://localhost:8000/api';

const stripHtml = (html) => {
  if (!html) return '';
  const doc = new DOMParser().parseFromString(html, 'text/html');
  return doc.body.textContent || "";
};

export const UnifiedSearch = ({ darkMode, onResultSelect, searchType: initialSearchType = 'both' }) => {
  const navigate = useNavigate();

  // Common state
  const [query, setQuery] = useState('');
  const [searchType, setSearchType] = useState(initialSearchType); // 'google', 'indiankanoon', or 'both'
  const [isSearching, setIsSearching] = useState(false);
  
  // Independent error states
  const [googleError, setGoogleError] = useState(null);
  const [ikError, setIkError] = useState(null);
  const [generalError, setGeneralError] = useState(null);
  
  // Google search state
  const [googleResults, setGoogleResults] = useState([]);
  const [selectedGoogleResult, setSelectedGoogleResult] = useState(null);
  const [modifiedQuery, setModifiedQuery] = useState(null);
  
  // Indian Kanoon search state
  const [ikResults, setIkResults] = useState([]);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [documentContent, setDocumentContent] = useState(null);
  const [loadingDocId, setLoadingDocId] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(null);

  const fetchWithTimeout = async (url, options = {}, timeoutMs = 20000) => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      return response;
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name === 'AbortError') {
        throw new Error('Request timed out after 20 seconds');
      }
      throw err;
    }
  };

  const handleSearch = async (forcedSource = null) => {
    const activeSearchType = forcedSource || searchType;
    if (!query.trim()) return;

    setIsSearching(true);
    setGeneralError(null);

    const performGoogleSearch = activeSearchType === 'google' || activeSearchType === 'both';
    const performIKSearch = activeSearchType === 'indiankanoon' || activeSearchType === 'both';

    if (performGoogleSearch) {
      setGoogleResults([]);
      setGoogleError(null);
      setModifiedQuery(null);
    }
    if (performIKSearch) {
      setIkResults([]);
      setIkError(null);
    }

    const tasks = [];
    if (performGoogleSearch) {
      tasks.push(
        fetchWithTimeout(`${API_BASE}/google-search`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: query.trim(), num_results: 10 }),
        }, 20000)
          .then(async (res) => {
            const data = await res.json().catch(() => ({}));
            return { source: 'google', ok: res.ok, status: res.status, data };
          })
          .catch((err) => ({
            source: 'google',
            ok: false,
            error: err.message || 'Network error while contacting Google Search'
          }))
      );
    }

    if (performIKSearch) {
      tasks.push(
        fetchWithTimeout(`${API_BASE}/ik-search`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: query.trim(), max_pages: 2 }),
        }, 20000)
          .then(async (res) => {
            const data = await res.json().catch(() => ({}));
            return { source: 'indiankanoon', ok: res.ok, status: res.status, data };
          })
          .catch((err) => ({
            source: 'indiankanoon',
            ok: false,
            error: err.message || 'Network error while contacting Indian Kanoon'
          }))
      );
    }

    try {
      const settled = await Promise.allSettled(tasks);

      for (const outcome of settled) {
        if (outcome.status === 'fulfilled') {
          const item = outcome.value;
          if (item.source === 'google') {
            if (item.ok && item.data && item.data.success) {
              const resList = Array.isArray(item.data.results) ? item.data.results : [];
              setGoogleResults(resList);
              if (item.data.modified_query && item.data.original_query !== item.data.modified_query) {
                setModifiedQuery(item.data.modified_query);
              }
            } else {
              const errMsg = (item.data && (item.data.error || (item.data.errors && item.data.errors[0]))) || item.error || 'Google search failed';
              setGoogleError(errMsg);
            }
          } else if (item.source === 'indiankanoon') {
            if (item.ok && item.data && item.data.success) {
              let resList = [];
              if (Array.isArray(item.data.results)) {
                resList = item.data.results;
              } else if (item.data.results && item.data.results.docs && Array.isArray(item.data.results.docs)) {
                resList = item.data.results.docs;
              }
              setIkResults(resList);
            } else {
              const errMsg = (item.data && (item.data.error || (item.data.errors && item.data.errors[0]))) || item.error || 'Indian Kanoon search failed';
              setIkError(errMsg);
            }
          }
        }
      }
    } catch (err) {
      setGeneralError(err.message || 'An unexpected error occurred during search');
    } finally {
      setIsSearching(false);
    }
  };

  const fetchDocument = async (docId) => {
    if (!docId) {
      setError("Unable to load the judgment. The document reference could not be found.");
      return;
    }
    
    setLoadingDocId(docId);
    setError(null);
  
    try {
      const response = await fetch(`${API_BASE}/ik-document/${docId}`);
      const data = await response.json();
  
      if (data.success) {
        if (!data.document.content && data.document.text) {
          data.document.content = data.document.text;
        }
        setDocumentContent(data.document);
        setSelectedDocument(docId);
        if (onResultSelect) onResultSelect(data.document);
      } else {
        setError(data.error || 'Failed to fetch document');
      }
    } catch (err) {
      setError('Network error while fetching document');
    } finally {
      setLoadingDocId(null);
    }
  };

  const saveDocumentToAnalysis = async () => {
    if (!documentContent) {
      setError("No document to save");
      return;
    }
    
    setIsSaving(true);
    setSaveSuccess(null);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE}/ik-save-document`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ document: documentContent }),
      });
      
      const data = await response.json();
      
      if (data.success) {
        setSaveSuccess({
          message: data.message,
          title: data.title,
          file: data.file
        });
        setTimeout(() => {
          navigate('/core', { state: { selectedCaseFile: data.file } });
        }, 1500);
      } else {
        setError(data.error || 'Failed to save document');
      }
    } catch (err) {
      setError('Network error while saving document');
    } finally {
      setIsSaving(false);
    }
  };

  const handleBackToResults = () => {
    setSelectedDocument(null);
    setDocumentContent(null);
    setSaveSuccess(null);
  };

  return (
    <div className={`${darkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-t border-l border-white'} rounded-2xl shadow-lg overflow-hidden`}>
      <div className="p-6">
        <h2 className={`text-xl font-serif ${darkMode ? 'text-white' : 'text-gray-800'} mb-4 flex items-center`}>
          <span className={`${darkMode ? 'bg-purple-900/50 text-purple-300' : 'bg-purple-100 text-purple-700'} p-1.5 rounded-lg mr-3`}>
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </span>
          Unified Legal Search
        </h2>

        <div className="mb-6">
          <div className="flex flex-col space-y-4">
            <div className="flex">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search legal information..."
                className={`flex-grow px-4 py-3 rounded-l-lg border ${darkMode ? 'bg-slate-700 border-slate-600 text-white' : 'bg-white border-gray-300'} focus:outline-none focus:ring-2 focus:ring-purple-500`}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              />
              <button
                onClick={handleSearch}
                disabled={isSearching}
                className={`px-6 py-3 rounded-r-lg ${darkMode ? 'bg-purple-700 hover:bg-purple-800' : 'bg-purple-600 hover:bg-purple-700'} text-white font-medium transition-colors`}
              >
                {isSearching ? (
                  <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                ) : 'Search'}
              </button>
            </div>
            
            <div className="flex space-x-6">
              <label className={`inline-flex items-center cursor-pointer ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                <input
                  type="radio"
                  className="form-radio h-4 w-4 text-purple-600 focus:ring-purple-500"
                  name="searchType"
                  value="both"
                  checked={searchType === 'both'}
                  onChange={() => setSearchType('both')}
                />
                <span className="ml-2">Both</span>
              </label>
              <label className={`inline-flex items-center cursor-pointer ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                <input
                  type="radio"
                  className="form-radio h-4 w-4 text-blue-600 focus:ring-blue-500"
                  name="searchType"
                  value="google"
                  checked={searchType === 'google'}
                  onChange={() => setSearchType('google')}
                />
                <span className="ml-2">Google</span>
              </label>
              <label className={`inline-flex items-center cursor-pointer ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                <input
                  type="radio"
                  className="form-radio h-4 w-4 text-indigo-600 focus:ring-indigo-500"
                  name="searchType"
                  value="indiankanoon"
                  checked={searchType === 'indiankanoon'}
                  onChange={() => setSearchType('indiankanoon')}
                />
                <span className="ml-2">Indian Kanoon</span>
              </label>
            </div>
          </div>
          
          {generalError && (
            <div className="mt-4 p-3 bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300 rounded flex items-center justify-between">
              <div className="flex items-center">
                <svg className="w-5 h-5 mr-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                <span>Search failed: {generalError}</span>
              </div>
              <button 
                onClick={() => handleSearch()}
                className="ml-4 px-3 py-1 bg-red-200 dark:bg-red-800 hover:bg-red-300 dark:hover:bg-red-700 text-red-900 dark:text-red-100 rounded text-xs font-semibold uppercase tracking-wider"
              >
                Retry
              </button>
            </div>
          )}

          {googleError && (
            <div className="mt-4 p-3 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800/50 text-red-800 dark:text-red-300 rounded flex items-center justify-between">
              <div className="flex items-center">
                <span className="font-semibold mr-2">[Google Search failed]:</span>
                <span>{googleError}</span>
              </div>
              <button 
                onClick={() => handleSearch('google')}
                className="ml-4 px-3 py-1 bg-red-100 dark:bg-red-900/60 hover:bg-red-200 text-red-900 dark:text-red-200 rounded text-xs font-semibold uppercase tracking-wider"
              >
                Retry Google
              </button>
            </div>
          )}

          {ikError && (
            <div className="mt-4 p-3 bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800/50 text-amber-800 dark:text-amber-300 rounded flex items-center justify-between">
              <div className="flex items-center">
                <span className="font-semibold mr-2">[Indian Kanoon Search failed]:</span>
                <span>{ikError}</span>
              </div>
              <button 
                onClick={() => handleSearch('indiankanoon')}
                className="ml-4 px-3 py-1 bg-amber-100 dark:bg-amber-900/60 hover:bg-amber-200 text-amber-900 dark:text-amber-200 rounded text-xs font-semibold uppercase tracking-wider"
              >
                Retry Indian Kanoon
              </button>
            </div>
          )}

          {modifiedQuery && searchType !== 'indiankanoon' && (
            <p className={`mt-3 text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Showing legal results for: <span className="font-medium text-purple-600 dark:text-purple-400">{modifiedQuery}</span>
            </p>
          )}
        </div>

        {/* Document View Modal / Preview */}
        {selectedDocument && documentContent ? (
          <div className={`mt-6 border rounded-xl overflow-hidden ${darkMode ? 'border-slate-700' : 'border-gray-200'}`}>
            <div className={`p-4 flex justify-between items-center border-b ${darkMode ? 'bg-slate-750 border-slate-700' : 'bg-gray-50 border-gray-200'}`}>
              <button
                onClick={handleBackToResults}
                className={`px-4 py-2 rounded-lg font-medium ${darkMode ? 'bg-slate-700 hover:bg-slate-600 text-gray-200' : 'bg-white hover:bg-gray-100 text-gray-700 border border-gray-300'} flex items-center transition-colors`}
              >
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                </svg>
                Back to Results
              </button>
              
              <button
                onClick={saveDocumentToAnalysis}
                disabled={isSaving}
                className={`px-4 py-2 rounded-lg font-medium shadow-sm transition-colors flex items-center ${darkMode ? 'bg-green-700 hover:bg-green-600 text-white' : 'bg-green-600 hover:bg-green-700 text-white'}`}
              >
                {isSaving ? (
                  <svg className="animate-spin h-4 w-4 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                ) : (
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                )}
                Analyze in Case Comprehension
              </button>
            </div>
            
            <div className={`p-6 ${darkMode ? 'bg-slate-800' : 'bg-white'}`}>
              <div className="mb-6">
                <h3 className={`text-2xl font-bold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>{documentContent.title}</h3>
                <div className={`flex flex-wrap gap-4 text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  {documentContent.court && <span className="flex items-center"><svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/></svg>{documentContent.court}</span>}
                  {documentContent.date && <span className="flex items-center"><svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>{documentContent.date}</span>}
                  <span className="flex items-center">
                    <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                    Source: Indian Kanoon
                  </span>
                </div>
              </div>
              
              {saveSuccess && (
                <div className="mb-6 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 text-green-800 dark:text-green-300 rounded-lg flex flex-col justify-center items-center text-center">
                  <svg className="w-8 h-8 mb-2 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                  <p className="font-semibold text-lg">{saveSuccess.message}</p>
                  <p className="text-sm mt-1 opacity-90">Redirecting to Case Comprehension...</p>
                </div>
              )}
              
              <div 
                className={`prose max-w-none ${darkMode ? 'prose-invert' : ''} p-6 border rounded-xl overflow-auto max-h-[60vh] ${darkMode ? 'bg-slate-900 border-slate-700 text-gray-300' : 'bg-gray-50 border-gray-200 text-gray-700'}`}
                dangerouslySetInnerHTML={{ __html: documentContent.content || documentContent.text || 'No content available' }}
              />
            </div>
          </div>
        ) : (
          <div className="mt-6">
            {/* Tabs for results */}
            {(googleResults.length > 0 || ikResults.length > 0) && (
              <div className="border-b mb-6 dark:border-slate-700">
                <nav className="-mb-px flex space-x-8">
                  {ikResults.length > 0 && (
                    <button
                      className={`py-3 px-2 border-b-2 font-medium text-sm transition-colors ${darkMode ? 'text-indigo-400 border-indigo-500' : 'text-indigo-600 border-indigo-600'}`}
                      onClick={() => document.getElementById('ik-results').scrollIntoView({ behavior: 'smooth' })}
                    >
                      Indian Kanoon Results ({ikResults.length})
                    </button>
                  )}
                  {googleResults.length > 0 && (
                    <button
                      className={`py-3 px-2 border-b-2 font-medium text-sm transition-colors ${darkMode ? 'text-blue-400 border-blue-500' : 'text-blue-600 border-blue-600'}`}
                      onClick={() => document.getElementById('google-results').scrollIntoView({ behavior: 'smooth' })}
                    >
                      Google Results ({googleResults.length})
                    </button>
                  )}
                </nav>
              </div>
            )}
            
            <div className="space-y-8">
              {/* Indian Kanoon Results */}
              {ikResults.length > 0 && (
                <div id="ik-results">
                  <h3 className={`font-semibold text-lg mb-4 flex items-center ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>
                    <span className={`${darkMode ? 'bg-indigo-900/50 text-indigo-400' : 'bg-indigo-100 text-indigo-600'} p-1.5 rounded mr-2`}>
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
                      </svg>
                    </span>
                    Indian Kanoon Matches
                  </h3>
                  <div className="grid gap-4">
                    {ikResults.map((result, index) => (
                      <div key={index} className={`border rounded-xl p-5 transition-all duration-200 hover:shadow-md ${darkMode ? 'bg-slate-700/40 border-slate-600 hover:bg-slate-700' : 'bg-white border-gray-200 hover:border-indigo-300 hover:bg-indigo-50/30'}`}>
                        <h4 className="text-lg font-semibold text-indigo-600 dark:text-indigo-400 mb-2 leading-snug">{stripHtml(result.title)}</h4>
                        <div className="flex items-center text-xs text-gray-500 dark:text-gray-400 mb-3 space-x-3">
                          <span className="flex items-center">
                            <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" /></svg>
                            ID: {result.tid || result.doc_id || result.docid}
                          </span>
                        </div>
                        {result.snippet && <p className={`text-sm mb-4 line-clamp-2 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>{stripHtml(result.snippet)}</p>}
                        <button 
                          onClick={() => fetchDocument(result.tid || result.doc_id || result.docid)}
                          disabled={loadingDocId !== null}
                          className={`text-sm px-4 py-2 rounded-lg font-medium transition-colors flex items-center w-fit ${darkMode ? 'bg-indigo-900/50 text-indigo-300 hover:bg-indigo-800' : 'bg-indigo-50 text-indigo-700 hover:bg-indigo-100'} ${loadingDocId && loadingDocId !== (result.tid || result.doc_id || result.docid) ? 'opacity-50 cursor-not-allowed' : ''}`}
                        >
                          {loadingDocId === (result.tid || result.doc_id || result.docid) ? (
                            <>
                              <svg className="animate-spin h-4 w-4 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                              </svg>
                              Loading...
                            </>
                          ) : (
                            <>
                              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
                              View Judgment
                            </>
                          )}
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Google Results */}
              {googleResults.length > 0 && (
                <div id="google-results">
                  <h3 className={`font-semibold text-lg mb-4 flex items-center ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>
                    <span className={`${darkMode ? 'bg-blue-900/50 text-blue-400' : 'bg-blue-100 text-blue-600'} p-1.5 rounded mr-2`}>
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M12.545,10.239v3.821h5.445c-0.712,2.315-2.647,3.972-5.445,3.972c-3.332,0-6.033-2.701-6.033-6.032s2.701-6.032,6.033-6.032c1.498,0,2.866,0.549,3.921,1.453l2.814-2.814C17.503,2.988,15.139,2,12.545,2C7.021,2,2.543,6.477,2.543,12s4.478,10,10.002,10c8.396,0,10.249-7.85,9.426-11.748L12.545,10.239z"/>
                      </svg>
                    </span>
                    Google Search Results
                  </h3>
                  <div className="grid gap-4">
                    {googleResults.map((result, index) => (
                      <div key={index} className={`border rounded-xl p-5 transition-all duration-200 hover:shadow-md ${darkMode ? 'bg-slate-700/40 border-slate-600 hover:bg-slate-700' : 'bg-white border-gray-200 hover:border-blue-300 hover:bg-blue-50/30'}`}>
                        <h4 className="text-lg font-semibold text-blue-600 dark:text-blue-400 mb-1 leading-snug">{stripHtml(result.title)}</h4>
                        <div className="text-xs text-green-700 dark:text-green-400 mb-3 truncate max-w-full">{result.link}</div>
                        <p className={`text-sm mb-4 line-clamp-2 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>{stripHtml(result.snippet)}</p>
                        <button 
                          onClick={() => window.open(result.link, '_blank')}
                          className={`text-sm px-4 py-2 rounded-lg font-medium transition-colors flex items-center w-fit ${darkMode ? 'bg-blue-900/50 text-blue-300 hover:bg-blue-800' : 'bg-blue-50 text-blue-700 hover:bg-blue-100'}`}
                        >
                          <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
                          Visit External Link
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
            
            {/* Loading State */}
            {isSearching && (
              <div className="flex flex-col justify-center items-center py-16">
                <svg className="animate-spin h-10 w-10 text-purple-600 dark:text-purple-400 mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <div className={`text-lg font-medium ${darkMode ? 'text-purple-400' : 'text-purple-600'}`}>Searching Legal Databases...</div>
                <div className={`text-sm mt-2 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>Compiling results from Indian Kanoon and Google</div>
              </div>
            )}
            
            {/* No Results State (only shown when genuinely empty and without full failure) */}
            {!isSearching &&
              googleResults.length === 0 &&
              ikResults.length === 0 &&
              query.trim() !== '' &&
              !generalError &&
              !((searchType === 'google' && googleError) ||
                (searchType === 'indiankanoon' && ikError) ||
                (searchType === 'both' && googleError && ikError)) && (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <div className={`p-4 rounded-full mb-4 ${darkMode ? 'bg-slate-700' : 'bg-gray-100'}`}>
                  <svg className={`w-10 h-10 ${darkMode ? 'text-gray-400' : 'text-gray-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div className={`text-lg font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>No results found for "{query}"</div>
                <div className={`text-sm mt-2 ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>Try adjusting your keywords or using a different search type.</div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};