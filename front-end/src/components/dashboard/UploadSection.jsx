import React from 'react';

export const UploadSection = ({ 
  darkMode, 
  isProcessing, 
  uploadProgress, 
  error, 
  fileInputRef, 
  handleFileUpload, 
  handleSelectDocument 
}) => {
  return (
    <>
      <div className={`${darkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-t border-l border-white'} rounded-2xl shadow-lg overflow-hidden relative group transition-all duration-300 hover:shadow-xl`}>
        <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-blue-500/10 to-purple-500/10 rounded-bl-full"></div>
        <div className="absolute -bottom-10 -left-10 w-40 h-40 bg-gradient-to-br from-indigo-500/5 to-purple-500/5 rounded-full transform transition-transform duration-700 group-hover:translate-y-5"></div>
        <div className="absolute top-1/2 right-0 w-20 h-20 bg-gradient-to-br from-blue-500/5 to-indigo-500/5 rounded-full transform transition-transform duration-700 group-hover:translate-x-5"></div>
        
        <div className="p-8 relative z-10">
          <h2 className="text-xl font-serif text-gray-800 dark:text-white mb-6 flex items-center">
            <span className={`${darkMode ? 'bg-indigo-900/50 text-indigo-300' : 'bg-indigo-100 text-indigo-700'} p-1.5 rounded-lg mr-3`}>
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </span>
            Document Analysis
          </h2>
          <div className={`${darkMode ? 'border-indigo-800 hover:border-indigo-600 bg-gradient-to-br from-slate-800 to-indigo-900/30' : 'border-indigo-200 hover:border-indigo-400 bg-gradient-to-br from-white to-indigo-50/50'} border-2 border-dashed rounded-xl p-8 text-center transition-all duration-300`}>
            <div className={`inline-flex p-4 ${darkMode ? 'bg-indigo-900/50 text-indigo-300' : 'bg-indigo-100 text-indigo-700'} rounded-xl mb-4 shadow-sm`}>
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h3 className={`text-xl font-serif ${darkMode ? 'text-white' : 'text-gray-900'} mb-2`}>Upload Legal Document</h3>
            <p className={`${darkMode ? 'text-gray-400' : 'text-gray-600'} mb-6`}>Import PDF files of legal cases for comprehensive AI analysis</p>
            <input 
              type="file" 
              ref={fileInputRef} 
              onChange={handleFileUpload} 
              accept=".pdf" 
              className="hidden" 
            />
            <button 
              onClick={handleSelectDocument}
              className={`px-6 py-3 ${darkMode ? 'bg-gradient-to-r from-indigo-700 to-blue-800 hover:from-indigo-800 hover:to-blue-900' : 'bg-gradient-to-r from-indigo-600 to-blue-700 hover:from-indigo-700 hover:to-blue-800'} text-white rounded-lg font-medium transition-all duration-300 shadow-md transform hover:scale-105`}
            >
              Select Document
            </button>
            {error && (
              <div className="mt-4 text-red-500 text-sm">{error}</div>
            )}
          </div>
        </div>
      </div>

      {isProcessing && (
        <ProcessingStatus darkMode={darkMode} uploadProgress={uploadProgress} />
      )}
    </>
  );
};

const ProcessingStatus = ({ darkMode, uploadProgress }) => {
  return (
    <div className={`${darkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-t border-l border-white'} rounded-2xl shadow-lg p-6 relative overflow-hidden`}>
      <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-blue-500/10 to-purple-500/10 rounded-bl-full"></div>
      <div className="relative z-10">
        <div className="flex items-center gap-6">
          <div className="relative">
            <svg className="w-12 h-12 animate-spin text-indigo-600 dark:text-indigo-400" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          </div>
          <div>
            <h3 className={`text-lg font-serif ${darkMode ? 'text-white' : 'text-gray-900'}`}>Processing Document</h3>
            <p className={`${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Analyzing case contents with AI...</p>
          </div>
        </div>
        <div className="mt-6 space-y-2">
          <div className="flex justify-between text-sm">
            <span className={`${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Upload Progress</span>
            <span className={`${darkMode ? 'text-indigo-400' : 'text-indigo-600'} font-medium`}>{uploadProgress}%</span>
          </div>
          <div className={`h-2 ${darkMode ? 'bg-gray-700' : 'bg-gray-100'} rounded-full overflow-hidden`}>
            <div 
              className="h-full bg-gradient-to-r from-indigo-500 to-blue-500 rounded-full transition-all duration-500"
              style={{ width: `${uploadProgress}%` }}
            ></div>
          </div>
        </div>
      </div>
    </div>
  );
};