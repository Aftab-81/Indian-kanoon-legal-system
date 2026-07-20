import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Header from '../components/dashboard/Header';
import Footer from '../components/dashboard/Footer';

function ModuleSelectionPage() {
  const [darkMode, setDarkMode] = useState(false);

  const toggleDarkMode = () => {
    const newDarkMode = !darkMode;
    setDarkMode(newDarkMode);
    localStorage.setItem('darkMode', newDarkMode ? 'true' : 'false');
  };

  useEffect(() => {
    // Load dark mode preference from localStorage
    const savedDarkMode = localStorage.getItem('darkMode');
    if (savedDarkMode !== null) {
      setDarkMode(savedDarkMode === 'true');
    } else {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      setDarkMode(prefersDark);
      localStorage.setItem('darkMode', prefersDark ? 'true' : 'false');
    }
  }, []);

  return (
    <div className={`min-h-screen transition-colors duration-300 ${darkMode ? 'bg-slate-900 text-white' : 'bg-gradient-to-br from-gray-100 to-gray-200'}`}>
      <Header darkMode={darkMode} toggleDarkMode={toggleDarkMode} />

      <main className="container mx-auto px-6 py-12">
        <h1 className={`text-3xl font-serif text-center mb-12 ${darkMode ? 'text-white' : 'text-gray-800'}`}>
          Select a Module
        </h1>

        <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          {/* Core Summary Extraction Module */}
          <Link 
            to="/core"
            className={`${darkMode ? 'bg-slate-800 border-slate-700 hover:bg-slate-700' : 'bg-white border-gray-200 hover:bg-gray-50'} 
              border rounded-2xl shadow-lg overflow-hidden relative p-8 transition-all duration-300 transform hover:scale-105 hover:shadow-xl`}
          >
            <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-blue-500/10 to-purple-500/10 rounded-bl-full"></div>
            
            <div className="relative z-10">
              <div className="p-3 bg-indigo-100 text-indigo-700 rounded-xl w-fit mb-4">
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
              </div>
              
              <h2 className={`text-2xl font-medium mb-3 ${darkMode ? 'text-white' : 'text-gray-800'}`}>
                Core Summary Extraction
              </h2>
              
              <p className={`mb-6 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
                Analyze legal judgments to extract key information including case laws, statutes, and legal principles.
              </p>
              
              <div className={`inline-flex items-center gap-2 ${darkMode ? 'text-indigo-400' : 'text-indigo-600'}`}>
                <span>Open Module</span>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </div>
          </Link>

          {/* Legal QA System Module - NEW */}
          <Link 
            to="/legal-qa"
            className={`${darkMode ? 'bg-slate-800 border-slate-700 hover:bg-slate-700' : 'bg-white border-gray-200 hover:bg-gray-50'} 
              border rounded-2xl shadow-lg overflow-hidden relative p-8 transition-all duration-300 transform hover:scale-105 hover:shadow-xl`}
          >
            <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-purple-500/10 to-pink-500/10 rounded-bl-full"></div>
            
            <div className="relative z-10">
              <div className="p-3 bg-purple-100 text-purple-700 rounded-xl w-fit mb-4">
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              
              <h2 className={`text-2xl font-medium mb-3 ${darkMode ? 'text-white' : 'text-gray-800'}`}>
                Legal QA System
              </h2>
              
              <p className={`mb-6 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
                AI-powered legal question answering system with RAG, multilingual support, and judge-friendly analysis.
              </p>
              
              <div className={`inline-flex items-center gap-2 ${darkMode ? 'text-purple-400' : 'text-purple-600'}`}>
                <span>Open Module</span>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </div>
          </Link>

          {/* Summary Extractor Module - NEW */}
          <Link 
            to="/summary-extractor"
            className={`${darkMode ? 'bg-slate-800 border-slate-700 hover:bg-slate-700' : 'bg-white border-gray-200 hover:bg-gray-50'} 
              border rounded-2xl shadow-lg overflow-hidden relative p-8 transition-all duration-300 transform hover:scale-105 hover:shadow-xl`}
          >
            <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-orange-500/10 to-red-500/10 rounded-bl-full"></div>
            
            <div className="relative z-10">
              <div className="p-3 bg-orange-100 text-orange-700 rounded-xl w-fit mb-4">
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              
              <h2 className={`text-2xl font-medium mb-3 ${darkMode ? 'text-white' : 'text-gray-800'}`}>
                Summary Extractor
              </h2>
              
              <p className={`mb-6 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
                AI-powered legal document summarization with multilingual support and confidence scoring.
              </p>
              
              <div className={`inline-flex items-center gap-2 ${darkMode ? 'text-orange-400' : 'text-orange-600'}`}>
                <span>Open Module</span>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </div>
          </Link>

          {/* Reference Module */}
          <Link 
            to="/reference"
            className={`${darkMode ? 'bg-slate-800 border-slate-700 hover:bg-slate-700' : 'bg-white border-gray-200 hover:bg-gray-50'} 
              border rounded-2xl shadow-lg overflow-hidden relative p-8 transition-all duration-300 transform hover:scale-105 hover:shadow-xl`}
          >
            <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-green-500/10 to-blue-500/10 rounded-bl-full"></div>
            
            <div className="relative z-10">
              <div className="p-3 bg-blue-100 text-blue-700 rounded-xl w-fit mb-4">
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              
              <h2 className={`text-2xl font-medium mb-3 ${darkMode ? 'text-white' : 'text-gray-800'}`}>
                Document Reference System
              </h2>
              
              <p className={`mb-6 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
                Access and manage your document library with advanced search and organization features.
              </p>
              
              <div className={`inline-flex items-center gap-2 ${darkMode ? 'text-blue-400' : 'text-blue-600'}`}>
                <span>Open Module</span>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </div>
          </Link>
        </div>
      </main>

      <Footer darkMode={darkMode} />
    </div>
  );
}

export default ModuleSelectionPage;