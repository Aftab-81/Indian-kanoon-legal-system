import { useState } from 'react';

const API_BASE = 'http://localhost:8000/api';  // Changed from 5000 to 8000

export const IKSearch = ({ darkMode, onResultSelect }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState(null);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [documentContent, setDocumentContent] = useState(null);
  const [isLoadingDocument, setIsLoadingDocument] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(null);

  const handleSearch = async () => {
    if (!query.trim()) return;

    setIsSearching(true);
    setError(null);
    setResults([]);

    try {
      console.log('Sending search request for:', query.trim());
      const response = await fetch(`${API_BASE}/ik-search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: query.trim(),
          max_pages: 2 // Limit to 2 pages for faster results
        }),
      });

      const data = await response.json();
      console.log('Search response:', data);

      if (data.success) {
        // Check if results is an array or an object with a docs property
        if (Array.isArray(data.results)) {
          // Log the structure of the first result to debug
          if (data.results.length > 0) {
            console.log('First result structure:', JSON.stringify(data.results[0]));
          }
          console.log('Search results structure:', data.results.map(r => ({ 
            tid: r.tid, 
            docid: r.docid, 
            id: r.id, 
            doc_id: r.doc_id, 
            title: r.title 
          })));
          setResults(data.results);
        } else if (data.results && data.results.docs && Array.isArray(data.results.docs)) {
          console.log('Search results docs structure:', data.results.docs.map(r => ({ 
            tid: r.tid, 
            docid: r.docid, 
            id: r.id, 
            doc_id: r.doc_id, 
            title: r.title 
          })));
          setResults(data.results.docs);
        } else {
          console.error('Unexpected results format:', data.results);
          setError('Received unexpected data format from server');
        }
      } else {
        console.error('Search error:', data.error);
        setError(data.error || 'Failed to search Indian Kanoon');
      }
    } catch (err) {
      console.error('Network error:', err);
      setError('Network error while searching Indian Kanoon');
    } finally {
      setIsSearching(false);
    }
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
      const response = await fetch(`${API_BASE}/ik-document/${docId}`);
      const data = await response.json();
  
      console.log('Full document response:', data);
  
      if (data.success) {
        // Log the document content for debugging
        console.log('Document content received:', data.document);
        console.log('Document keys:', Object.keys(data.document));
        console.log('Content field exists:', Boolean(data.document.content));
        console.log('Content field type:', typeof data.document.content);
        console.log('Content field length:', data.document.content ? data.document.content.length : 0);
        
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
      const response = await fetch(`${API_BASE}/ik-save-document`, {
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
          <span className={`${darkMode ? 'bg-indigo-900/50 text-indigo-300' : 'bg-indigo-100 text-indigo-700'} p-1.5 rounded-lg mr-3`}>
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </span>
          Indian Kanoon Search
        </h2>

        <div className="mb-4">
          <div className="flex">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search Indian Kanoon..."
              className={`flex-grow px-4 py-2 rounded-l-lg border ${darkMode ? 'bg-slate-700 border-slate-600 text-white' : 'bg-white border-gray-300'} focus:outline-none focus:ring-2 focus:ring-indigo-500`}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            />
            <button
              onClick={handleSearch}
              disabled={isSearching}
              className={`px-4 py-2 rounded-r-lg ${darkMode ? 'bg-indigo-700 hover:bg-indigo-800' : 'bg-indigo-600 hover:bg-indigo-700'} text-white font-medium transition-colors`}
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
        </div>

        {/* Document View */}
        {selectedDocument && documentContent ? (
          <div className={`mt-4 ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>
            <div className="flex justify-between items-center mb-4">
              <button
                onClick={handleBackToResults}
                className={`${darkMode ? 'text-indigo-400 hover:text-indigo-300' : 'text-indigo-600 hover:text-indigo-800'} font-medium flex items-center`}
              >
                <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
                <span>Back to Results</span>
              </button>
              
              <button
                onClick={saveDocumentToAnalysis}
                disabled={isSaving}
                className={`px-4 py-2 rounded-lg ${darkMode ? 'bg-green-700 hover:bg-green-800' : 'bg-green-600 hover:bg-green-700'} text-white font-medium transition-colors flex items-center`}
              >
                {isSaving ? (
                  <svg className="animate-spin h-5 w-5 text-white mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                ) : (
                  <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
                  </svg>
                )}
                Save to Analysis
              </button>
            </div>
            
            {saveSuccess && (
              <div className={`mb-4 p-4 rounded-lg ${darkMode ? 'bg-green-900/20 text-green-300 border border-green-800' : 'bg-green-50 text-green-800 border border-green-200'}`}>
                <h4 className="font-medium">{saveSuccess.title}</h4>
                <p>{saveSuccess.message}</p>
              </div>
            )}
            
            <div className={`p-4 ${darkMode ? 'bg-slate-700/50 border border-slate-600' : 'bg-white border border-gray-200'} rounded-xl shadow-sm`}>
              <h3 
                className="text-xl font-medium mb-2"
                dangerouslySetInnerHTML={{ __html: documentContent.title }}
              />
              <div className="flex flex-wrap gap-2 mb-4">
                <span className={`text-sm px-2 py-1 rounded ${darkMode ? 'bg-slate-600 text-slate-300' : 'bg-gray-100 text-gray-700'}`}>
                  {documentContent.court || 'Court not specified'}
                </span>
                <span className={`text-sm px-2 py-1 rounded ${darkMode ? 'bg-slate-600 text-slate-300' : 'bg-gray-100 text-gray-700'}`}>
                  {documentContent.date || 'Date not specified'}
                </span>
              </div>
              
              {/* Document Sections */}
              {documentContent.sections && Object.keys(documentContent.sections).length > 0 ? (
                <div className="space-y-4 mb-4">
                  {Object.entries(documentContent.sections).map(([key, value]) => (
                    <details key={key} className={`${darkMode ? 'bg-slate-700/50 hover:bg-slate-700' : 'bg-white hover:bg-gray-50'} rounded-xl shadow-sm overflow-hidden transition-all duration-300`}>
                      <summary className={`flex items-center justify-between p-4 cursor-pointer ${darkMode ? 'text-white' : 'text-gray-800'}`}>
                        <span className="font-medium">{key}</span>
                        <svg className="w-5 h-5 transform transition-transform duration-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                      </summary>
                      <div 
                        className={`p-4 ${darkMode ? 'text-gray-300' : 'text-gray-600'} border-t ${darkMode ? 'border-gray-600' : 'border-gray-100'}`}
                        dangerouslySetInnerHTML={{ __html: value }}
                      />
                    </details>
                  ))}
                </div>
              ) : (
                <div className="mb-4">
                  <h4 className="font-medium mb-2">Full Document Content</h4>
                  <div 
                    className={`p-4 ${darkMode ? 'bg-slate-800 text-gray-300' : 'bg-gray-50 text-gray-700'} rounded-lg max-h-96 overflow-y-auto`}
                    dangerouslySetInnerHTML={{ __html: documentContent.content }}
                  />
                </div>
              )}
            </div>
          </div>
        ) : (
          <>
            {/* Search Results */}
            {results.length > 0 && (
              <div className={`mt-4 ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>
                <h3 className="font-medium mb-2">Search Results</h3>
                <ul className={`divide-y ${darkMode ? 'divide-gray-700' : 'divide-gray-200'} max-h-96 overflow-y-auto`}>
                  {results.map((result, index) => (
                    <li key={index} className="py-3">
                      <button
                        onClick={() => fetchDocument(result.tid)}
                        className={`text-left w-full px-3 py-2 rounded-lg transition-colors hover:${darkMode ? 'bg-indigo-900/30' : 'bg-indigo-50'}`}
                      >
                        <div 
                          className={`font-medium ${darkMode ? 'text-indigo-400' : 'text-indigo-600'}`}
                          dangerouslySetInnerHTML={{ __html: result.title }}
                        />
                        <div className="flex flex-wrap gap-2 mt-1">
                          <span className={`text-xs px-2 py-0.5 rounded ${darkMode ? 'bg-slate-700 text-slate-300' : 'bg-gray-100 text-gray-700'}`}>
                            {result.docsource || 'Source not specified'}
                          </span>
                          <span className={`text-xs px-2 py-0.5 rounded ${darkMode ? 'bg-slate-700 text-slate-300' : 'bg-gray-100 text-gray-700'}`}>
                            {result.publishdate || 'Date not specified'}
                          </span>
                        </div>
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
                  <div className={`${darkMode ? 'text-indigo-400' : 'text-indigo-600'} mb-2`}>Searching Indian Kanoon...</div>
                  <div className={`${darkMode ? 'text-gray-400' : 'text-gray-500'} text-sm`}>This may take a moment</div>
                </div>
              </div>
            )}
            
            {/* Document Loading State */}
            {isLoadingDocument && (
              <div className="flex justify-center items-center py-8">
                <div className="animate-pulse text-center">
                  <div className={`${darkMode ? 'text-indigo-400' : 'text-indigo-600'} mb-2`}>Loading document...</div>
                  <div className={`${darkMode ? 'text-gray-400' : 'text-gray-500'} text-sm`}>Retrieving content from Indian Kanoon</div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};