import { useState, useEffect } from 'react';
import Header from '../components/dashboard/Header';
import Footer from '../components/dashboard/Footer';

function DocumentRetrievalPage() {
  const [darkMode, setDarkMode] = useState(false);

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
      
      <main className="flex-grow w-full">
        <iframe 
          src="http://localhost:8004" 
          title="Document Retrieval System"
          className="w-full h-full min-h-[calc(100vh-140px)] border-0"
          allowFullScreen
        />
      </main>

      <Footer darkMode={darkMode} />
    </div>
  );
}

export default DocumentRetrievalPage;
