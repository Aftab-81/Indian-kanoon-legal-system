import React, { useState } from 'react';

function DocumentDetails({ document, onSaveRemark, darkMode }) {
  const [remark, setRemark] = useState(document?.remark || '');
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  
  // Add useEffect to handle remark updates
  React.useEffect(() => {
    setRemark(document?.remark || '');
  }, [document]);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await onSaveRemark(document.file_hash, remark);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2000);
      setIsEditing(false);
    } catch (error) {
      console.error('Failed to save remark:', error);
    } finally {
      setIsSaving(false);
    }
  };
  
  if (!document) return null;
  
  // Extract all analysis data from the analysis object
  const caseLaws = document.analysis?.case_laws || [];
  const statutes = document.analysis?.statutes || [];
  const constitutionalProvisions = document.analysis?.constitutional_provisions || [];
  const internationalLaws = document.analysis?.international_laws || [];
  const legalPrinciples = document.analysis?.legal_principles || [];
  
  // Define sections with icons for consistent styling
  const sections = [
    { 
      key: "caseLaws", 
      title: "Case Laws", 
      icon: "M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z",
      content: caseLaws,
      type: "caseLaw"
    },
    { 
      key: "statutes", 
      title: "Statutes", 
      icon: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2",
      content: statutes,
      type: "statute"
    },
    { 
      key: "constitutionalProvisions", 
      title: "Constitutional Provisions", 
      icon: "M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3",
      content: constitutionalProvisions,
      type: "provision"
    },
    { 
      key: "internationalLaws", 
      title: "International Laws", 
      icon: "M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
      content: internationalLaws,
      type: "law"
    },
    { 
      key: "legalPrinciples", 
      title: "Legal Principles", 
      icon: "M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z",
      content: legalPrinciples,
      type: "principles"
    }
  ];
  
  return (
    <div className={`${darkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-t border-l border-white'} rounded-2xl shadow-lg overflow-hidden relative`}>
      {/* Decorative elements */}
      <div className="absolute top-0 right-0 w-40 h-40 bg-gradient-to-br from-blue-500/10 to-purple-500/10 rounded-bl-full"></div>
      <div className="absolute bottom-0 left-0 w-full h-40 bg-gradient-to-t from-indigo-500/5 to-transparent"></div>
      <div className="absolute top-1/3 right-1/4 w-20 h-20 rounded-full bg-blue-500/5"></div>
      
      <div className="p-8 relative z-10">
        {/* Document header */}
        <div className={`p-4 ${darkMode ? 'bg-indigo-900/20 border border-indigo-800/30' : 'bg-indigo-50 border border-indigo-100'} rounded-xl mb-6`}>
          <div className="flex justify-between items-center">
            <div>
              <h2 className={`text-xl font-medium ${darkMode ? 'text-white' : 'text-gray-900'} mb-1`}>
                {document.filename}
              </h2>
              <p className={`text-sm ${darkMode ? 'text-indigo-300' : 'text-indigo-700'}`}>
                Uploaded on {new Date(document.timestamp).toLocaleString()}
              </p>
              
              {/* Add URL link if available */}
              {document.url && (
                <a
                  href={document.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={`flex items-center mt-2 ${
                    darkMode ? 'text-blue-400 hover:text-blue-300' : 'text-blue-600 hover:text-blue-700'
                  }`}
                >
                  <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002 2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                  View Source
                </a>
              )}
            </div>
          </div>
        </div>

        {/* Document content sections */}
        <div className="space-y-4">
          {sections.map((section, index) => {
            const isEmpty = Array.isArray(section.content) 
              ? section.content.length === 0 
              : !section.content;
              
            return (
              <details 
                key={section.key} 
                className={`${darkMode ? 'bg-slate-700/50 hover:bg-slate-700' : 'bg-white hover:bg-gray-50'} rounded-xl shadow-sm overflow-hidden transition-all duration-300`}
                open={index === 0} // Keep first section open by default
              >
                <summary className={`flex items-center justify-between p-4 cursor-pointer ${darkMode ? 'text-white' : 'text-gray-800'}`}>
                  <div className="flex items-center gap-3">
                    <span className={`p-1.5 ${darkMode ? 'bg-indigo-900/50 text-indigo-300' : 'bg-indigo-100 text-indigo-700'} rounded-lg`}>
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={section.icon} />
                      </svg>
                    </span>
                    <span className="font-medium">{section.title}</span>
                  </div>
                  <svg className="w-5 h-5 transform transition-transform duration-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </summary>
                
                <div className={`p-4 ${darkMode ? 'text-gray-300 border-t border-gray-600' : 'text-gray-600 border-t border-gray-100'}`}>
                  {isEmpty ? (
                    <p className={`${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                      No {section.title.toLowerCase()} available
                    </p>
                  ) : section.type === 'text' ? (
                    <p>{section.content}</p>
                  ) : section.type === 'principles' ? (
                    <ul className="list-disc pl-5 space-y-1">
                      {section.content.map((principle, index) => (
                        <li key={index}>{principle}</li>
                      ))}
                    </ul>
                  ) : (
                    <div className="space-y-4">
                      {section.content.map((item, index) => {
                        let title, details;
                        
                        if (section.type === 'caseLaw') {
                          title = item.case_name;
                          
                          const determineCaseType = (caseItem) => {
                            if (caseItem.case_type) return caseItem.case_type;
                            
                            const text = `${caseItem.case_name || ''} ${caseItem.context || ''}`.toLowerCase();
                            if (text.includes('criminal') || text.includes('murder') || text.includes('bail') || text.includes('accused') || text.includes('conviction') || text.includes('ipc') || text.includes('cr.p.c')) return 'Criminal';
                            if (text.includes('family') || text.includes('divorce') || text.includes('marriage') || text.includes('maintenance') || text.includes('custody')) return 'Family';
                            if (text.includes('tax') || text.includes('income tax') || text.includes('gst') || text.includes('assessment')) return 'Tax';
                            if (text.includes('consumer') || text.includes('deficiency')) return 'Consumer';
                            if (text.includes('labour') || text.includes('workman') || text.includes('industrial') || text.includes('wages')) return 'Labour';
                            if (text.includes('constitution') || text.includes('writ') || text.includes('fundamental right')) return 'Constitutional';
                            if (text.includes('environment') || text.includes('pollution') || text.includes('forest') || text.includes('ngt')) return 'Environmental';
                            if (text.includes('commercial') || text.includes('arbitration') || text.includes('contract') || text.includes('company')) return 'Commercial';
                            if (text.includes('service') || text.includes('promotion') || text.includes('pension') || text.includes('dismissal')) return 'Service';
                            if (text.includes('civil') || text.includes('property') || text.includes('suit') || text.includes('tenant') || text.includes('eviction')) return 'Civil';
                            
                            return 'Not Available';
                          };

                          const formatContext = (text) => {
                            if (!text) return 'No context provided';
                            
                            const words = text.split(/\s+/);
                            if (words.length <= 75) return text.trim();
                            
                            const sentences = text.match(/[^.!?]+[.!?]+(?:\s+|$)/g);
                            if (!sentences) {
                              return words.slice(0, 60).join(' ') + '.';
                            }
                            
                            let summary = '';
                            let wordCount = 0;
                            
                            for (let sentence of sentences) {
                              const sentenceWords = sentence.trim().split(/\s+/).length;
                              if (wordCount + sentenceWords > 75 && wordCount > 0) {
                                break;
                              }
                              summary += sentence;
                              wordCount += sentenceWords;
                              if (wordCount >= 50) {
                                break;
                              }
                            }
                            
                            return summary.trim() || sentences[0].trim();
                          };

                          details = [
                            { label: 'Case Type', value: determineCaseType(item) },
                            { label: 'Year', value: item.year },
                            { label: 'Court', value: item.court },
                            { label: 'Context', value: `"${formatContext(item.context)}"`, isContext: true }
                          ];
                        } else if (section.type === 'statute') {
                          title = item.statute_name;
                          details = [
                            { label: 'Section', value: item.section },
                            { label: 'Reference', value: item.full_reference },
                            { label: 'Context', value: `"${item.context}"`, isContext: true }
                          ];
                        } else if (section.type === 'provision') {
                          title = item.article;
                          details = [
                            { label: 'Subject', value: item.subject },
                            { label: 'Reference', value: item.full_reference },
                            { label: 'Context', value: `"${item.context}"`, isContext: true }
                          ];
                        } else if (section.type === 'law') {
                          title = item.name;
                          details = [
                            { label: 'Article', value: item.article },
                            { label: 'Reference', value: item.full_reference },
                            { label: 'Context', value: `"${item.context}"`, isContext: true }
                          ];
                        }
                        
                        return (
                          <div 
                            key={index} 
                            className={`${index !== section.content.length - 1 ? 'pb-4 border-b ' + (darkMode ? 'border-gray-600' : 'border-gray-200') : ''}`}
                          >
                            <h4 className={`font-medium ${darkMode ? 'text-white' : 'text-gray-800'} mb-2`}>{title}</h4>
                            <div className="space-y-1">
                              {details.map((detail, i) => (
                                <p 
                                  key={i} 
                                  className={`text-sm ${detail.isContext ? 'mt-2' : ''} ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}
                                >
                                  <span className="font-medium">{detail.label}:</span> {detail.value}
                                </p>
                              ))}
                            </div>
                          </div>
                        );
                      })}
                    </div>
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
                  onClick={handleSave}
                  className={`px-3 py-1 ${darkMode ? 'bg-green-900/30 text-green-300 hover:bg-green-900/50' : 'bg-green-50 text-green-700 hover:bg-green-100'} rounded-lg transition-colors flex items-center text-sm`}
                  disabled={isSaving}
                >
                  {isSaving ? 'Saving...' : 'Save'}
                  {saveSuccess && (
                    <svg className="w-4 h-4 ml-1 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  )}
                </button>
              </div>
            )}
          </div>
          {isEditing ? (
            <textarea
              value={remark}
              onChange={(e) => setRemark(e.target.value)}
              className={`w-full p-3 min-h-[100px] ${darkMode ? 'bg-slate-800 text-white border-gray-700' : 'bg-gray-50 text-gray-900 border-gray-200'} border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent`}
              placeholder="Add your remarks about this document here..."
            />
          ) : (
            <div className={`p-3 ${darkMode ? 'text-gray-300' : 'text-gray-600'} min-h-[50px]`}>
              {remark ? (
                <p style={{ whiteSpace: 'pre-wrap' }}>{remark}</p>
              ) : (
                <p className={`italic ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>No remarks added yet.</p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default DocumentDetails;