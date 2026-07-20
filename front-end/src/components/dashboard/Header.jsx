import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const Header = ({ darkMode, toggleDarkMode }) => {
  const navigate = useNavigate();
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    // Changed from localStorage to sessionStorage
    const loggedIn = sessionStorage.getItem('isLoggedIn') === 'true';
    setIsLoggedIn(loggedIn);
  }, []);

  const handleLogout = () => {
    // Changed from localStorage to sessionStorage
    sessionStorage.removeItem('isLoggedIn');
    setIsLoggedIn(false);
    navigate('/');
  };

  return (
    <header className={`${darkMode ? 'bg-gradient-to-r from-purple-900 via-indigo-900 to-blue-900' : 'bg-gradient-to-r from-indigo-600 to-blue-700'} shadow-xl relative overflow-hidden`}>
      <div className="absolute top-0 left-0 w-full h-full">
        <div className="absolute top-10 left-10 w-20 h-20 bg-white/10 rounded-full blur-xl"></div>
        <div className="absolute bottom-5 right-20 w-32 h-32 bg-blue-400/10 rounded-full blur-xl"></div>
        <div className="absolute top-1/2 left-1/3 w-40 h-10 bg-purple-400/10 rounded-full blur-xl transform -rotate-45"></div>
      </div>
      
      <div className="container mx-auto px-6 py-5 relative z-10">
        <div className="flex items-center justify-between">
          {/* Left Section - Branding */}
          <div className="flex items-center gap-4 flex-1">
            <div className="p-3 bg-white/10 backdrop-blur-md rounded-xl border border-white/20 shadow-lg">
              <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
            </div>
            <div>
              <h1 className="text-2xl font-serif text-white tracking-wide flex items-center">
                Judicial Insight Engine
                <span className="ml-2 text-xs bg-blue-500/30 px-2 py-1 rounded-full border border-blue-400/30">v1.0</span>
              </h1>
              <div className="flex items-center mt-1">
                <span className="h-2 w-2 rounded-full bg-green-400 mr-2 animate-pulse"></span>
                <p className="text-blue-200 text-sm">AI-Powered Case Analysis</p>
              </div>
            </div>
          </div>

          {/* Right Section - Controls */}
          <div className="flex items-center gap-4">
            {/* Logout Button */}
            {isLoggedIn && (
              <div className="flex items-center gap-4 border-r border-white/20 pr-4">
                <button
                  onClick={handleLogout}
                  className={`px-4 py-2 rounded-lg ${
                    darkMode 
                      ? 'bg-red-600 hover:bg-red-700 text-white' 
                      : 'bg-red-500 hover:bg-red-600 text-white'
                  } transition-colors flex items-center gap-2`}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                  </svg>
                  Logout
                </button>
              </div>
            )}

            {/* Dark Mode Toggle and User Icon */}
            <div className="flex items-center gap-3">
              <button 
                onClick={toggleDarkMode} 
                className="w-10 h-10 flex items-center justify-center rounded-full bg-white/10 backdrop-blur-md text-white hover:bg-white/20 transition-all"
                title={darkMode ? "Switch to light mode" : "Switch to dark mode"}
              >
                {darkMode ? (
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" fillRule="evenodd" clipRule="evenodd"></path>
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z"></path>
                  </svg>
                )}
              </button>
              <span className="w-10 h-10 flex items-center justify-center rounded-full bg-white/10 backdrop-blur-md text-white">SC</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;