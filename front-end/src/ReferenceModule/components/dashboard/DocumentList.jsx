import React from 'react';

function DocumentList({ documents, selectedDocument, onSelectDocument, onViewAll, onDeleteDocument, darkMode }) {
  // Helper function to format date safely
  const formatDate = (dateString) => {
    try {
      if (!dateString) return "No date available";
      const date = new Date(dateString);
      return date instanceof Date && !isNaN(date) 
        ? date.toLocaleString() 
        : "Date format error";
    } catch (error) {
      console.error("Date parsing error:", error);
      return "Date error";
    }
  };

  if (!documents || documents.length === 0) {
    return (
      <div className={`text-center py-8 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
        <p>No documents found. Upload a document to get started.</p>
      </div>
    );
  }

  return (
    <div className={`${darkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-t border-l border-white'} rounded-2xl shadow-lg overflow-hidden relative`}>
      <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-blue-500/10 to-purple-500/10 rounded-bl-full"></div>
      <div className="absolute bottom-0 left-0 w-full h-20 bg-gradient-to-t from-indigo-500/5 to-transparent"></div>
      
      <div className="p-6 relative z-10">
        <h2 className={`text-xl font-serif ${darkMode ? 'text-white' : 'text-gray-800'} mb-4 flex items-center`}>
          <span className={`${darkMode ? 'bg-indigo-900/50 text-indigo-300' : 'bg-indigo-100 text-indigo-700'} p-1.5 rounded-lg mr-3`}>
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
          </span>
          Document History
        </h2>
        
        <div className="space-y-3 max-h-[600px] overflow-y-auto">
          {documents.map((doc) => (
            <div
              key={doc.file_hash}
              className={`p-4 rounded-lg border transition-all ${
                selectedDocument && selectedDocument.file_hash === doc.file_hash
                  ? darkMode ? 'bg-indigo-900/30 border-indigo-600' : 'bg-indigo-50 border-indigo-500'
                  : darkMode ? 'bg-slate-700/50 border-slate-600 hover:bg-slate-700' : 'bg-gray-50 border-gray-200 hover:bg-gray-100'
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div 
                  className="flex-1 min-w-0 cursor-pointer"
                  onClick={() => onSelectDocument(doc)}
                >
                  <h3 
                    className={`font-semibold mb-1 break-words ${darkMode ? 'text-white' : 'text-gray-900'}`}
                    style={{ wordBreak: 'break-word', overflowWrap: 'anywhere' }}
                    title={doc.filename}
                  >
                    {doc.filename || 'Untitled'}
                  </h3>
                  <p className={`text-sm mb-2 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                    {new Date(doc.timestamp || doc.analyzed_at).toLocaleDateString()} {new Date(doc.timestamp || doc.analyzed_at).toLocaleTimeString()}
                  </p>
                  {doc.remark && (
                    <p className={`text-xs italic ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
                      📝 {doc.remark.substring(0, 50)}{doc.remark.length > 50 ? '...' : ''}
                    </p>
                  )}
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteDocument(doc.file_hash);
                  }}
                  className="flex-shrink-0 p-2 rounded-lg hover:bg-red-500 hover:text-white transition-colors group"
                  title="Delete document"
                >
                  <svg className="w-5 h-5 text-red-500 group-hover:text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            </div>
          ))}
        </div>
        
        {selectedDocument && (
          <button
            onClick={onViewAll}
            className={`mt-4 w-full py-2 px-3 text-sm rounded-lg transition-colors ${darkMode 
              ? 'bg-slate-700 text-white hover:bg-slate-600' 
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'} flex items-center justify-center gap-2`}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to All Documents
          </button>
        )}
      </div>
    </div>
  );
}

export default DocumentList;