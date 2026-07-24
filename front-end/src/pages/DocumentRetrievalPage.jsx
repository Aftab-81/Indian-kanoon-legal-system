import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../components/dashboard/Header';
import Footer from '../components/dashboard/Footer';

function DocumentRetrievalPage() {
  const [darkMode, setDarkMode] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const savedDarkMode = localStorage.getItem('darkMode');
    if (savedDarkMode !== null) {
      setDarkMode(savedDarkMode === 'true');
    } else {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      setDarkMode(prefersDark);
    }
  }, []);

  const toggleDarkMode = () => {
    const newDarkMode = !darkMode;
    setDarkMode(newDarkMode);
    localStorage.setItem('darkMode', newDarkMode ? 'true' : 'false');
  };

  return (
    <div className={`min-h-screen flex flex-col transition-colors duration-300 ${darkMode ? 'bg-slate-900 text-white' : 'bg-gray-50 text-gray-800'}`}>
      <Header darkMode={darkMode} toggleDarkMode={toggleDarkMode} />
      
      <main className="flex-grow w-full flex flex-col">
        <div className="container mx-auto px-6 pt-8 pb-4">
          <div className="flex justify-between items-center">
            <button
              onClick={() => navigate('/modules')}
              className={`px-4 py-2 rounded-lg ${darkMode ? 'bg-slate-700 hover:bg-slate-600 text-white' : 'bg-white hover:bg-gray-100 text-gray-800'} transition-colors shadow-sm flex items-center gap-2`}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              Back to Modules
            </button>
            <div className="text-right">
              <h1 className={`text-2xl font-serif ${darkMode ? 'text-white' : 'text-gray-800'}`}>
                Document Retrieval
              </h1>
            </div>
          </div>
        </div>
        
        <div className="flex-grow w-full">
          <iframe 
            src={`http://localhost:8004?theme=${darkMode ? 'dark' : 'light'}`}
            title="Document Retrieval System"
            className="w-full h-full min-h-[calc(100vh-140px)] border-0"
            allowFullScreen
          />
        </div>
      </main>

      <Footer darkMode={darkMode} />
    </div>
  );
}

export default DocumentRetrievalPage;
