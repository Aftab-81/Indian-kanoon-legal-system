import React, { useState, useEffect } from 'react';

export const CaseDetails = ({ 
  darkMode, 
  selectedCase, 
  caseDetails, 
  cases,
  loadedCaseDetails,
  handleSelectCase,
  handleViewAllCases,
  handleDeleteCase  // Add this prop
}) => {
  const sections = [
    { key: "Facts of the Case", icon: "M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" },
    { key: "Issues Framed", icon: "M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" },
    { key: "Arguments by Parties", icon: "M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" },
    { key: "Court's Analysis / Reasoning", icon: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" },
    { key: "Final Decision (Ratio Decidendi)", icon: "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" },
    { key: "Obiter Dicta (if present)", icon: "M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" }
  ];

  return (
    <div className={`lg:col-span-3 ${darkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-t border-l border-white'} rounded-2xl shadow-lg overflow-hidden relative`}>
      <div className="absolute top-0 right-0 w-40 h-40 bg-gradient-to-br from-blue-500/10 to-purple-500/10 rounded-bl-full"></div>
      <div className="absolute bottom-0 left-0 w-full h-40 bg-gradient-to-t from-indigo-500/5 to-transparent"></div>
      <div className="absolute top-1/3 right-1/4 w-20 h-20 rounded-full bg-blue-500/5"></div>
      
      <div className="p-8 relative z-10">
        <div className="flex items-center justify-between mb-6">
          <h2 className={`text-xl font-serif ${darkMode ? 'text-white' : 'text-gray-800'} flex items-center`}>
            <span className={`${darkMode ? 'bg-indigo-900/50 text-indigo-300' : 'bg-indigo-100 text-indigo-700'} p-1.5 rounded-lg mr-3`}>
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            </span>
            {selectedCase ? 'Case Details' : 'Case Analysis'}
          </h2>
          <button 
            onClick={handleViewAllCases}
            className={`${darkMode ? 'text-indigo-400 hover:text-indigo-300' : 'text-indigo-600 hover:text-indigo-800'} font-medium flex items-center ${!selectedCase && 'invisible'}`}
          >
            <span>View All Cases</span>
            <svg className="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>

        {selectedCase && caseDetails ? (
          <CaseDetailView 
            darkMode={darkMode}
            selectedCase={selectedCase}
            caseDetails={caseDetails}
            loadedCaseDetails={loadedCaseDetails}
            sections={sections}
            handleDeleteCase={handleDeleteCase}  // Pass the prop here
          />
        ) : (
          <CaseListView 
            darkMode={darkMode}
            cases={cases}
            loadedCaseDetails={loadedCaseDetails}
            handleSelectCase={handleSelectCase}
            handleDeleteCase={handleDeleteCase}  // Pass the prop here
          />
        )}
      </div>
    </div>
  );
};

const CaseDetailView = ({ darkMode, selectedCase, caseDetails, loadedCaseDetails, sections, handleDeleteCase }) => {
  const [remarks, setRemarks] = useState("");
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // Update remarks when caseDetails changes
  useEffect(() => {
    if (caseDetails && caseDetails.Remarks) {
      setRemarks(caseDetails.Remarks);
    } else {
      setRemarks("");
    }
  }, [caseDetails]);

  const handleSaveRemarks = async () => {
    try {
      setIsSaving(true);
      const response = await fetch(`http://localhost:8000/api/case/${selectedCase.file}/remarks`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ remarks }),
      });

      const data = await response.json();
      if (data.success) {
        // Update the local state
        caseDetails.Remarks = remarks;
        setIsEditing(false);
      } else {
        console.error('Failed to save remarks:', data.error);
      }
    } catch (error) {
      console.error('Error saving remarks:', error);
    } finally {
      setIsSaving(false);
    }
  };

  // Helper function to safely render text content
  const renderTextContent = (content) => {
    // If content is null or undefined
    if (!content) return "Not specified in the document";
    
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

  return (
    <div className="space-y-6">
      <div className={`p-4 ${darkMode ? 'bg-indigo-900/20 border border-indigo-800/30' : 'bg-indigo-50 border border-indigo-100'} rounded-xl`}>
        <div className="flex justify-between items-center">
          <div>
            <h3 className={`text-lg font-medium ${darkMode ? 'text-white' : 'text-gray-900'} mb-1`}>
              {renderTextContent(caseDetails["Case Title & Citation"])}
            </h3>
            <p className={`text-sm ${darkMode ? 'text-indigo-300' : 'text-indigo-700'}`}>
              {renderTextContent(caseDetails["Bench / Court"])}
            </p>
          </div>
          
          <ConfidenceIndicator 
            darkMode={darkMode}
            confidence={loadedCaseDetails[selectedCase.file]?.averageConfidence}
            large
          />
        </div>
      </div>

      <div className="space-y-4">
        {sections.map((section) => {
          const sectionContent = renderTextContent(caseDetails[section.key]);
          
          return (
            <details 
              key={section.key} 
              className={`${darkMode ? 'bg-slate-700/50 hover:bg-slate-700' : 'bg-white hover:bg-gray-50'} rounded-xl shadow-sm overflow-hidden transition-all duration-300`}
            >
              <summary className={`flex items-center justify-between p-4 cursor-pointer ${darkMode ? 'text-white' : 'text-gray-800'}`}>
                <div className="flex items-center gap-3">
                  <span className={`p-1.5 ${darkMode ? 'bg-indigo-900/50 text-indigo-300' : 'bg-indigo-100 text-indigo-700'} rounded-lg`}>
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={section.icon} />
                    </svg>
                  </span>
                  <span className="font-medium">{section.key}</span>
                </div>
                <svg className="w-5 h-5 transform transition-transform duration-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </summary>
              <div className={`p-4 ${darkMode ? 'text-gray-300' : 'text-gray-600'} border-t ${darkMode ? 'border-gray-600' : 'border-gray-100'}`}>
                {/* Check if content contains HTML tags */}
                {sectionContent && sectionContent.includes('<') ? (
                  <div dangerouslySetInnerHTML={{ __html: sectionContent }} />
                ) : (
                  <p>{sectionContent}</p>
                )}
              </div>
            </details>
          );
        })}
      </div>

      {/* Custom Remarks Section */}
      <div className={`p-4 ${darkMode ? 'bg-slate-700/50 hover:bg-slate-700' : 'bg-white hover:bg-gray-50'} rounded-xl shadow-sm overflow-hidden transition-all duration-300 mt-6`}>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <span className={`p-1.5 ${darkMode ? 'bg-indigo-900/50 text-indigo-300' : 'bg-indigo-100 text-indigo-700'} rounded-lg`}>
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
            </span>
            <span className="font-medium">Human Evaluation</span>
          </div>
          {!isEditing ? (
            <button
              onClick={() => setIsEditing(true)}
              className={`px-3 py-1 ${darkMode ? 'bg-indigo-900/30 text-indigo-300 hover:bg-indigo-900/50' : 'bg-indigo-50 text-indigo-700 hover:bg-indigo-100'} rounded-lg transition-colors flex items-center text-sm`}
            >
              <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
              </svg>
              Edit
            </button>
          ) : (
            <div className="flex gap-2">
              <button
                onClick={() => setIsEditing(false)}
                className={`px-3 py-1 ${darkMode ? 'bg-gray-700 text-gray-300 hover:bg-gray-600' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'} rounded-lg transition-colors flex items-center text-sm`}
                disabled={isSaving}
              >
                Cancel
              </button>
              <button
                onClick={handleSaveRemarks}
                className={`px-3 py-1 ${darkMode ? 'bg-green-900/30 text-green-300 hover:bg-green-900/50' : 'bg-green-50 text-green-700 hover:bg-green-100'} rounded-lg transition-colors flex items-center text-sm`}
                disabled={isSaving}
              >
                {isSaving ? 'Saving...' : 'Save'}
              </button>
            </div>
          )}
        </div>
        {isEditing ? (
          <textarea
            value={remarks}
            onChange={(e) => setRemarks(e.target.value)}
            className={`w-full p-3 min-h-[100px] ${darkMode ? 'bg-slate-800 text-white border-gray-700' : 'bg-gray-50 text-gray-900 border-gray-200'} border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent`}
            placeholder="Add your remarks about this case here..."
          />
        ) : (
          <div className={`p-3 ${darkMode ? 'text-gray-300' : 'text-gray-600'} min-h-[50px]`}>
            {remarks ? (
              <p style={{ whiteSpace: 'pre-wrap' }}>{remarks}</p>
            ) : (
              <p className={`italic ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>No remarks added yet.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

const CaseListView = ({ darkMode, cases, loadedCaseDetails, handleSelectCase, handleDeleteCase }) => {
  const [searchTerm, setSearchTerm] = useState('');

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
      return renderTextContent(details.Date);
    }
    
    // Convert title to string if it's not already (handles React elements or objects)
    const titleStr = renderTextContent(caseItem.title);
    
    // If no specific date is found, extract from title string
    const datePattern = /on (\d{1,2} [A-Za-z]+,? \d{4})|(\[\d{4}\])|(\d{4} INSC)/;
    const match = titleStr.match(datePattern);
    
    if (match) {
      if (match[1]) return match[1].replace(',', ''); // Full date
      if (match[2]) return match[2].replace('[', '').replace(']', ''); // Year in brackets
      if (match[3]) return match[3]; // INSC year
    }
    
    return caseItem.date || 'Date not specified';
  };

  // Convert title to string for filtering
  const getTitleString = (title) => {
    return renderTextContent(title);
  };

  const filteredCases = cases.filter(caseItem => {
    const titleStr = getTitleString(caseItem.title);
    return titleStr.toLowerCase().includes(searchTerm.toLowerCase());
  });

  if (cases.length === 0) {
    return (
      <div className={`text-center py-8 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
        No cases have been analyzed yet. Upload a document to get started.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className={`${darkMode ? 'bg-slate-700/50' : 'bg-white'} rounded-xl p-3`}>
        <div className="relative">
          <input
            type="text"
            placeholder="Search cases..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className={`w-full pl-10 pr-4 py-2 ${
              darkMode 
                ? 'bg-slate-800 text-white placeholder-gray-400 border-gray-700' 
                : 'bg-gray-50 text-gray-900 placeholder-gray-500 border-gray-200'
            } border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent`}
          />
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <svg className={`w-5 h-5 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
        </div>
      </div>

      {filteredCases.length === 0 ? (
        <div className={`text-center py-8 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
          No cases found matching your search.
        </div>
      ) : (
        filteredCases.map((caseItem) => {
          const titleText = renderTextContent(caseItem.title);
          
          return (
            <div 
              key={caseItem.id}
              className={`p-6 rounded-xl ${darkMode ? 'bg-gradient-to-br from-slate-800 to-indigo-900/20 border border-indigo-800/30' : 'bg-gradient-to-br from-white to-indigo-50/50 border border-indigo-100'} shadow-sm hover:shadow-md transition-all duration-300`}
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className={`text-lg font-medium ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                  {titleText.includes('<') ? (
                    <span dangerouslySetInnerHTML={{ __html: titleText }} />
                  ) : (
                    titleText
                  )}
                </h3>
                <div className="flex items-center gap-3">
                  <ConfidenceIndicator 
                    darkMode={darkMode}
                    confidence={loadedCaseDetails[caseItem.file]?.averageConfidence}
                  />
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteCase(caseItem.file);
                    }}
                    className={`p-2 ${darkMode ? 'text-gray-500 hover:text-red-400' : 'text-gray-400 hover:text-red-500'} transition-colors rounded-lg hover:bg-red-500/10`}
                    title="Delete case"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <button 
                  onClick={() => handleSelectCase(caseItem)}
                  className={`px-4 py-2 ${darkMode ? 'text-indigo-300 bg-indigo-900/30 hover:bg-indigo-900/50' : 'text-indigo-700 bg-indigo-50 hover:bg-indigo-100'} rounded-lg transition-colors flex items-center`}
                >
                  <span>View Details</span>
                  <svg className="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                  </svg>
                </button>
                <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                  {formatDate(caseItem)}
                </span>
              </div>
            </div>
          );
        })
      )}
    </div>
  );
};

const ConfidenceIndicator = ({ darkMode, confidence, large = false }) => {
  if (!confidence) return null;

  return (
    <div className="flex flex-col items-end">
      {large && (
        <span className={`text-sm font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'} mb-1`}>
          Overall Confidence
        </span>
      )}
      <div className="flex items-center">
        <div className={`${large ? 'w-24 h-2.5' : 'w-16 h-2'} rounded-full ${
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
        <span className={`ml-2 ${large ? 'font-medium' : 'text-xs'} ${
          confidence > 80 
            ? darkMode ? 'text-green-400' : 'text-green-600' 
            : confidence > 60 
              ? darkMode ? 'text-yellow-400' : 'text-yellow-600'
              : darkMode ? 'text-red-400' : 'text-red-600'
        }`}>
          {confidence}%
        </span>
      </div>
    </div>
  );
};