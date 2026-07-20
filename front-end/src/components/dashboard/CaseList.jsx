import React from 'react';

export const CaseList = ({ darkMode, cases, selectedCase, loadedCaseDetails, handleSelectCase, handleDeleteCase }) => {
  // Helper function to safely render text content
  const renderTextContent = (content) => {
    // If content is null or undefined
    if (!content) return "Not specified";
    
    // If it's a string, return as is
    if (typeof content === 'string') return content;
    
    // If it's an object with Value property (from confidence scoring)
    if (typeof content === 'object' && content.Value) {
      return content.Value;
    }
    
    // If it's any other object, try to stringify it
    if (typeof content === 'object') {
      return JSON.stringify(content);
    }
    
    // Default fallback
    return String(content);
  };

  const formatDate = (caseItem) => {
    // First try to get the date from loadedCaseDetails
    const details = loadedCaseDetails[caseItem.file];
    if (details?.Date) {
      return renderTextContent(details.Date);  // Apply renderTextContent here
    }
    
    // Convert title to string if it's not already
    const titleStr = renderTextContent(caseItem.title);
    
    // If no specific date is found, extract from title string
    const datePattern = /on (\d{1,2} [A-Za-z]+,? \d{4})|(\[\d{4}\])|(\d{4} INSC)/;
    const match = titleStr.match(datePattern);
    
    if (match) {
      if (match[1]) return match[1].replace(',', ''); // Full date
      if (match[2]) return match[2].replace('[', '').replace(']', ''); // Year in brackets
      if (match[3]) return match[3]; // INSC year
    }
    
    return renderTextContent(caseItem.date) || 'Date not specified';  // Apply renderTextContent here too
  };

  return (
    <div className={`${darkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-t border-l border-white'} rounded-2xl shadow-lg overflow-hidden`}>
      <div className="p-6">
        <h2 className={`text-xl font-serif ${darkMode ? 'text-white' : 'text-gray-800'} mb-4 flex items-center`}>
          <span className={`${darkMode ? 'bg-indigo-900/50 text-indigo-300' : 'bg-indigo-100 text-indigo-700'} p-1.5 rounded-lg mr-3`}>
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
          </span>
          Analyzed Cases
        </h2>
        
        {cases.length === 0 ? (
          <div className={`text-center py-8 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
            No cases have been analyzed yet. Upload a document to get started.
          </div>
        ) : (
          <ul className={`divide-y ${darkMode ? 'divide-gray-700' : 'divide-gray-100'}`}>
            {cases.map((caseItem) => {
              const titleText = renderTextContent(caseItem.title);
              
              return (
                <li key={caseItem.file} className="py-3">
                  <div className="flex justify-between items-center">
                    <button
                      onClick={() => handleSelectCase(caseItem)}
                      className={`text-left flex-grow py-2 px-3 rounded-lg transition-colors ${
                        selectedCase && selectedCase.file === caseItem.file 
                          ? (darkMode ? 'bg-indigo-900/30 text-indigo-300' : 'bg-indigo-50 text-indigo-700') 
                          : (darkMode ? 'hover:bg-slate-700' : 'hover:bg-indigo-50')
                      }`}
                    >
                      <div className={`font-medium ${darkMode ? 'text-white' : ''}`}>
                        {titleText.includes('<') ? (
                          <span dangerouslySetInnerHTML={{ __html: titleText }} />
                        ) : (
                          titleText
                        )}
                      </div>
                      <div className="flex items-center justify-between">
                        <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                          {formatDate(caseItem)}
                        </div>
                        <ConfidenceIndicator 
                          darkMode={darkMode}
                          confidence={loadedCaseDetails[caseItem.file]?.averageConfidence}
                        />
                      </div>
                    </button>
                    
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteCase(caseItem.file);
                      }}
                      className={`p-2 ${darkMode ? 'text-gray-500 hover:text-red-400' : 'text-gray-400 hover:text-red-500'} transition-colors`}
                      title="Delete case"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
};

const ConfidenceIndicator = ({ darkMode, confidence }) => {
  if (!confidence) return null;

  return (
    <div className="flex items-center mt-1">
      <div className={`w-12 h-1.5 rounded-full ${
        confidence > 80 
          ? darkMode ? 'bg-green-700' : 'bg-green-500' 
          : confidence > 60 
            ? darkMode ? 'bg-yellow-700' : 'bg-yellow-500'
            : darkMode ? 'bg-red-700' : 'bg-red-500'
      }`}>
        <div 
          className={`h-full rounded-full ${
            confidence > 80 
              ? darkMode ? 'bg-green-400' : 'bg-green-300' 
              : confidence > 60 
                ? darkMode ? 'bg-yellow-400' : 'bg-yellow-300'
                : darkMode ? 'bg-red-400' : 'bg-red-300'
          }`}
          style={{ width: `${confidence}%` }}
        ></div>
      </div>
      <span className={`ml-1 text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
        {confidence}%
      </span>
    </div>
  );
};