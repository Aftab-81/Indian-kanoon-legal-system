import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { IKSearch } from '../components/dashboard/IKSearch';
import Header from '../components/dashboard/Header';
import Footer from '../components/dashboard/Footer';
import Notification from '../components/dashboard/Notification';

const IKSearchPage = () => {
  const [darkMode, setDarkMode] = useState(false);
  const [notification, setNotification] = useState(null);

  const toggleDarkMode = () => {
    const newDarkMode = !darkMode;
    setDarkMode(newDarkMode);
    localStorage.setItem('darkMode', newDarkMode ? 'true' : 'false');
  };

  const dismissNotification = () => {
    setNotification(null);
  };

  const handleIkResultSelect = (document) => {
    setNotification({
      type: 'info',
      message: `Viewing document from Indian Kanoon`,
      title: document.title
    });
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
      
      <main className="container mx-auto px-6 py-8">
        {notification && (
          <Notification 
            notification={notification} 
            dismissNotification={dismissNotification} 
            darkMode={darkMode} 
          />
        )}
        
        <div className="mb-6 flex items-center justify-between">
          <h1 className={`text-2xl font-serif ${darkMode ? 'text-white' : 'text-gray-800'}`}>Indian Kanoon Search</h1>
          <Link 
            to="/"
            className={`px-4 py-2 rounded-lg ${darkMode ? 'bg-slate-700 hover:bg-slate-600 text-white' : 'bg-white hover:bg-gray-100 text-gray-800'} transition-colors shadow-sm flex items-center gap-2`}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back to Dashboard
          </Link>
        </div>
        
        <IKSearch 
          darkMode={darkMode} 
          onResultSelect={handleIkResultSelect} 
        />
      </main>
      
      <Footer darkMode={darkMode} />
    </div>
  );
};

export default IKSearchPage;