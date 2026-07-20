import { useState } from 'react';

const API_BASE = 'http://localhost:8000/api';  // Changed from 5000 to 8000

export const UnifiedSearch = ({ darkMode, onResultSelect }) => {
  // Common state
  const [query, setQuery] = useState('');
  const [searchType, setSearchType] = useState('both'); // 'google', 'indiankanoon', or 'both'
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState(null);
  
  // Google search state
  const [googleResults, setGoogleResults] = useState([]);
  const [selectedGoogleResult, setSelectedGoogleResult] = useState(null);
  const [modifiedQuery, setModifiedQuery] = useState(null);
  
  // Indian Kanoon search state
  const [ikResults, setIkResults] = useState([]);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [documentContent, setDocumentContent] = useState(null);
  const [isLoadingDocument, setIsLoadingDocument] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(null);

  const handleSearch = async () => {
    if (!query.trim()) return;

    setIsSearching(true);
    setError(null);
    setGoogleResults([]);
    setIkResults([]);
    setModifiedQuery(null);

    try {
      // Determine which searches to perform
      const performGoogleSearch = searchType === 'google' || searchType === 'both';
      const performIKSearch = searchType === 'indiankanoon' || searchType === 'both';
      
      const searchPromises = [];
      
      // Google Search
      if (performGoogleSearch) {
        const googlePromise = fetch(`${API_BASE}/google-search`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            query: query.trim(),
            num_results: 10
          }),
        }).then(res => res.json());
        
        searchPromises.push(googlePromise);
      }
      
      // Indian Kanoon Search
      if (performIKSearch) {
        const ikPromise = fetch(`${API_BASE}/ik-search`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            query: query.trim(),
            max_pages: 2
          }),
        }).then(res => res.json());
        
        searchPromises.push(ikPromise);
      }
      
      // Wait for all searches to complete
      const results = await Promise.all(searchPromises);
      
      // Process Google results
      if (performGoogleSearch) {
        const googleData = results[0];
        if (googleData.success) {
          if (Array.isArray(googleData.results)) {
            setGoogleResults(googleData.results);
            // Store the modified query if it was changed
            if (googleData.modified_query && googleData.original_query !== googleData.modified_query) {
              setModifiedQuery(googleData.modified_query);
            }
          } else {
            console.error('Unexpected Google results format:', googleData.results);
            setError('Received unexpected data format from Google search');
          }
        } else {
          console.error('Google search error:', googleData.error);
          setError(googleData.error || 'Failed to search Google');
        }
      }
      
      // Process Indian Kanoon results
      if (performIKSearch) {
        const ikData = performGoogleSearch ? results[1] : results[0];
        if (ikData.success) {
          // Check if results is an array or an object with a docs property
          if (Array.isArray(ikData.results)) {
            setIkResults(ikData.results);
          } else if (ikData.results && ikData.results.docs && Array.isArray(ikData.results.docs)) {
            setIkResults(ikData.results.docs);
          } else {
            console.error('Unexpected IK results format:', ikData.results);
            setError('Received unexpected data format from Indian Kanoon search');
          }
        } else {
          console.error('IK search error:', ikData.error);
          setError(ikData.error || 'Failed to search Indian Kanoon');
        }
      }
    } catch (err) {
      console.error('Network error:', err);
      setError('Network error while performing search');
    } finally {
      setIsSearching(false);
    }
  };

  const handleGoogleResultClick = (result) => {
    setSelectedGoogleResult(result);
    if (onResultSelect) {
      onResultSelect(result);
    }
    // Open the link in a new tab
    window.open(result.link, '_blank');
  };

  const fetchDocument = async (docId) => {
    // Add validation to prevent fetching with undefined ID
    if (!docId) {
      setError("Cannot fetch document: Missing document ID in search result");
      return;
    }
    
    setIsLoadingDocument(true);
    setError(null);
  
    try {
      console.log(`Fetching document with ID: ${docId}`);
      const response = await fetch(`http://localhost:5000/api/ik-document/${docId}`);
      const data = await response.json();
  
      if (data.success) {
        // Make sure content field exists and is not empty
        if (!data.document.content) {
          console.error('Document content is empty or missing');
          // If content is missing but text field exists, use that instead
          if (data.document.text) {
            data.document.content = data.document.text;
          }
        }
        
        setDocumentContent(data.document);
        setSelectedDocument(docId);
        if (onResultSelect) {
          onResultSelect(data.document);
        }
      } else {
        console.error('Failed to fetch document:', data.error);
        setError(data.error || 'Failed to fetch document');
      }
    } catch (err) {
      console.error('Error fetching document:', err);
      setError('Network error while fetching document');
    } finally {
      setIsLoadingDocument(false);
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
      const response = await fetch('http://localhost:5000/api/ik-save-document', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          document: documentContent
        }),
      });
      
      const data = await response.json();
      
      if (data.success) {
        setSaveSuccess({
          message: data.message,
          title: data.title,
          file: data.file
        });
      } else {
        setError(data.error || 'Failed to save document');
      }
    } catch (err) {
      console.error('Error saving document:', err);
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

        <div className="mb-4">
          <div className="flex flex-col space-y-2">
            <div className="flex">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search legal information..."
                className={`flex-grow px-4 py-2 rounded-l-lg border ${darkMode ? 'bg-slate-700 border-slate-600 text-white' : 'bg-white border-gray-300'} focus:outline-none focus:ring-2 focus:ring-purple-500`}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              />
              <button
                onClick={handleSearch}
                disabled={isSearching}
                className={`px-4 py-2 rounded-r-lg ${darkMode ? 'bg-purple-700 hover:bg-purple-800' : 'bg-purple-600 hover:bg-purple-700'} text-white font-medium transition-colors`}
              >
                {isSearching ? (
                  <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                ) : 'Search'}
              </button>
            </div>
            
            <div className="flex space-x-4">
              <label className={`inline-flex items-center ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                <input
                  type="radio"
                  className="form-radio h-4 w-4 text-purple-600"
                  name="searchType"
                  value="both"
                  checked={searchType === 'both'}
                  onChange={() => setSearchType('both')}
                />
                <span className="ml-2">Both</span>
              </label>
              <label className={`inline-flex items-center ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                <input
                  type="radio"
                  className="form-radio h-4 w-4 text-blue-600"
                  name="searchType"
                  value="google"
                  checked={searchType === 'google'}
                  onChange={() => setSearchType('google')}
                />
                <span className="ml-2">Google</span>
              </label>
              <label className={`inline-flex items-center ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                <input
                  type="radio"
                  className="form-radio h-4 w-4 text-indigo-600"
                  name="searchType"
                  value="indiankanoon"
                  checked={searchType === 'indiankanoon'}
                  onChange={() => setSearchType('indiankanoon')}
                />
                <span className="ml-2">Indian Kanoon</span>
              </label>
            </div>
          </div>
          
          {error && <p className="mt-2 text-red-500 text-sm">{error}</p>}
          {modifiedQuery && searchType !== 'indiankanoon' && (
            <p className={`mt-2 text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Showing legal results for: <span className="font-medium">{modifiedQuery}</span>
            </p>
          )}
        </div>

        {/* Document View (when a document is selected) */}
        {selectedDocument && documentContent ? (
          <div className={`mt-4 ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>
            <div className="flex justify-between items-center mb-4">
              <button
                onClick={handleBackToResults}
                className={`px-3 py-1 rounded ${darkMode ? 'bg-gray-700 hover:bg-gray-600' : 'bg-gray-200 hover:bg-gray-300'} flex items-center`}
              >
                <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                </svg>
                Back to Results
              </button>
              
              <button
                onClick={saveDocumentToAnalysis}
                disabled={isSaving}
                className={`px-3 py-1 rounded ${darkMode ? 'bg-green-700 hover:bg-green-600' : 'bg-green-600 hover:bg-green-700'} text-white flex items-center`}
              >
                {isSaving ? (
                  <svg className="animate-spin h-4 w-4 mr-1" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                ) : (
                  <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
                  </svg>
                )}
                Save for Analysis
              </button>
            </div>
            
            {saveSuccess && (
              <div className="mb-4 p-3 bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300 rounded">
                <p className="font-medium">{saveSuccess.message}</p>
                <p className="text-sm mt-1">Saved: {saveSuccess.title}</p>
              </div>
            )}
            
            <div className="border rounded-lg p-4 mb-4 overflow-auto max-h-96 whitespace-pre-wrap font-mono text-sm">
              {documentContent.content || documentContent.text || 'No content available'}
            </div>
          </div>
        ) : (
          <div className="mt-4">
            {/* Tabs for results */}
            {(googleResults.length > 0 || ikResults.length > 0) && (
              <div className="border-b mb-4">
                <nav className="-mb-px flex space-x-8">
                  {googleResults.length > 0 && (
                    <button
                      className={`py-2 px-1 border-b-2 font-medium text-sm ${darkMode ? 'text-blue-400 border-blue-500' : 'text-blue-600 border-blue-600'}`}
                      onClick={() => document.getElementById('google-results').scrollIntoView({ behavior: 'smooth' })}
                    >
                      Google Results ({googleResults.length})
                    </button>
                  )}
                  {ikResults.length > 0 && (
                    <button
                      className={`py-2 px-1 border-b-2 font-medium text-sm ${darkMode ? 'text-indigo-400 border-indigo-500' : 'text-indigo-600 border-indigo-600'}`}
                      onClick={() => document.getElementById('ik-results').scrollIntoView({ behavior: 'smooth' })}
                    >
                      Indian Kanoon Results ({ikResults.length})
                    </button>
                  )}
                </nav>
              </div>
            )}
            
            {/* Google Results */}
            {googleResults.length > 0 && (
              <div id="google-results" className={`mb-8 ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>
                <h3 className="font-medium mb-2 flex items-center">
                  <span className={`${darkMode ? 'text-blue-400' : 'text-blue-600'} mr-2`}>
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M12.545,10.239v3.821h5.445c-0.712,2.315-2.647,3.972-5.445,3.972c-3.332,0-6.033-2.701-6.033-6.032s2.701-6.032,6.033-6.032c1.498,0,2.866,0.549,3.921,1.453l2.814-2.814C17.503,2.988,15.139,2,12.545,2C7.021,2,2.543,6.477,2.543,12s4.478,10,10.002,10c8.396,0,10.249-7.85,9.426-11.748L12.545,10.239z"/>
                    </svg>
                  </span>
                  Google Search Results
                </h3>
                <ul className={`divide-y ${darkMode ? 'divide-gray-700' : 'divide-gray-200'} max-h-96 overflow-y-auto`}>
                  {googleResults.map((result, index) => (
                    <li key={index} className="py-3">
                      <button
                        onClick={() => handleGoogleResultClick(result)}
                        className={`text-left w-full px-3 py-2 rounded-lg transition-colors ${selectedGoogleResult === result ? (darkMode ? 'bg-blue-900/30 text-blue-300' : 'bg-blue-50 text-blue-700') : ''}`}
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
            
            {/* Indian Kanoon Results */}
            {ikResults.length > 0 && (
              <div id="ik-results" className={`${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>
                <h3 className="font-medium mb-2 flex items-center">
                  <span className={`${darkMode ? 'text-indigo-400' : 'text-indigo-600'} mr-2`}>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
                    </svg>
                  </span>
                  Indian Kanoon Results
                </h3>
                <ul className={`divide-y ${darkMode ? 'divide-gray-700' : 'divide-gray-200'} max-h-96 overflow-y-auto`}>
                  {ikResults.map((result, index) => (
                    <li key={index} className="py-3">
                      <button
                        onClick={() => fetchDocument(result.doc_id || result.docid)}
                        disabled={isLoadingDocument}
                        className={`text-left w-full px-3 py-2 rounded-lg transition-colors ${isLoadingDocument ? 'opacity-50 cursor-not-allowed' : ''}`}
                      >
                        <div className="font-medium text-indigo-600 dark:text-indigo-400">{result.title}</div>
                        <div className="text-xs text-gray-500 dark:text-gray-400">Document ID: {result.doc_id || result.docid}</div>
                        {result.snippet && <div className="text-sm mt-1 opacity-80">{result.snippet}</div>}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            
            {/* Loading State */}
            {isSearching && (
              <div className="flex justify-center items-center py-8">
                <div className="animate-pulse text-center">
                  <div className={`${darkMode ? 'text-purple-400' : 'text-purple-600'} mb-2`}>Searching...</div>
                  <div className={`${darkMode ? 'text-gray-400' : 'text-gray-500'} text-sm`}>This may take a moment</div>
                </div>
              </div>
            )}
            
            {/* No Results State */}
            {!isSearching && googleResults.length === 0 && ikResults.length === 0 && query.trim() !== '' && (
              <div className="text-center py-8">
                <div className={`${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>No results found</div>
                <div className={`${darkMode ? 'text-gray-500' : 'text-gray-400'} text-sm mt-1`}>Try a different search term</div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};