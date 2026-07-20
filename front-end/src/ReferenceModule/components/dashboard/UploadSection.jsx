import React from 'react';

function UploadSection({ onSelectDocument, fileInputRef, handleFileUpload, isProcessing, uploadProgress, darkMode }) {
  return (
    <div className="upload-section">
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileUpload}
        className="hidden"
        accept=".pdf,.docx,.doc"
      />
      
      <div 
        className={`border-2 border-dashed rounded-xl p-6 mb-4 text-center transition-colors ${
          darkMode 
            ? 'border-slate-600 hover:border-indigo-500/70 bg-slate-700/30' 
            : 'border-gray-300 hover:border-indigo-400/70 bg-gray-50'
        }`}
      >
        <div className="flex flex-col items-center justify-center">
          <svg 
            className={`w-10 h-10 mb-3 ${
              darkMode ? 'text-indigo-400' : 'text-indigo-500'
            }`} 
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
          >
            <path 
              strokeLinecap="round" 
              strokeLinejoin="round" 
              strokeWidth={1.5} 
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
            />
          </svg>
          <p className={`mb-2 text-sm ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
            <span className="font-medium">Click to upload</span> or drag and drop
          </p>
          <p className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
            PDF, DOCX files (up to 10MB)
          </p>
        </div>
      </div>
      
      <button
        onClick={onSelectDocument}
        disabled={isProcessing}
        className={`w-full py-3 px-4 rounded-lg font-medium transition-all duration-300 flex items-center justify-center gap-2 ${
          isProcessing 
          ? darkMode
              ? 'bg-gray-700 text-gray-400 cursor-not-allowed' 
              : 'bg-gray-300 text-gray-600 cursor-not-allowed'
          : darkMode 
              ? 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm hover:shadow' 
              : 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm hover:shadow-md'
        }`}
      >
        {isProcessing ? (
          <>
            <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span>Processing...</span>
          </>
        ) : (
          <>
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <span>Select Document</span>
          </>
        )}
      </button>
      
      {isProcessing && (
        <div className="mt-4">
          <div className={`relative pt-1 ${darkMode ? 'text-indigo-300' : 'text-indigo-600'}`}>
            <div className="flex mb-2 items-center justify-between">
              <div>
                <span className={`text-xs font-semibold inline-block ${darkMode ? 'text-indigo-300' : 'text-indigo-600'}`}>
                  Processing Document
                </span>
              </div>
              <div className="text-right">
                <span className={`text-xs font-semibold inline-block ${darkMode ? 'text-indigo-300' : 'text-indigo-600'}`}>
                  {uploadProgress}%
                </span>
              </div>
            </div>
            <div className={`overflow-hidden h-2 mb-4 text-xs flex rounded-full ${darkMode ? 'bg-slate-600' : 'bg-gray-200'}`}>
              <div 
                style={{ width: `${uploadProgress}%` }} 
                className={`shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center ${
                  darkMode ? 'bg-indigo-500' : 'bg-indigo-600'
                } transition-all duration-300 ease-out`}
              ></div>
            </div>
          </div>
        </div>
      )}
      
      <div className={`mt-4 text-sm ${darkMode ? 'text-gray-400' : 'text-gray-500'} flex items-center justify-center gap-2`}>
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <p>Supported formats: PDF, DOCX</p>
      </div>
    </div>
  );
}

export default UploadSection;