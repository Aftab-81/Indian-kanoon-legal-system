import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../../components/dashboard/Header';
import Footer from '../components/dashboard/Footer';

function AboutPage() {
  const [darkMode, setDarkMode] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const toggleDarkMode = () => {
    const newDarkMode = !darkMode;
    setDarkMode(newDarkMode);
    localStorage.setItem('darkMode', newDarkMode ? 'true' : 'false');
  };

  useEffect(() => {
    const savedDarkMode = localStorage.getItem('darkMode');
    if (savedDarkMode !== null) {
      setDarkMode(savedDarkMode === 'true');
    } else {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      setDarkMode(prefersDark);
    }

    // Changed from localStorage to sessionStorage
    const loggedInStatus = sessionStorage.getItem('isLoggedIn');
    setIsLoggedIn(loggedInStatus === 'true');
  }, []);

  const handleLogin = (e) => {
    e.preventDefault();
    if (username === 'admin@123' && password === 'admin') {
      setIsLoggedIn(true);
      setError('');
      // Changed from localStorage to sessionStorage
      sessionStorage.setItem('isLoggedIn', 'true');
      navigate('/modules');
    } else {
      setError('Invalid credentials. Please try again.');
    }
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
    // Changed from localStorage to sessionStorage
    sessionStorage.removeItem('isLoggedIn');
  };

  const goToModules = () => navigate('/modules');

  return (
    <div className={`min-h-screen transition-colors duration-500 ${darkMode ? 'bg-gradient-to-b from-slate-900 to-slate-800' : 'bg-gradient-to-b from-gray-50 to-white'}`}>
      <Header darkMode={darkMode} toggleDarkMode={toggleDarkMode} />

      <main className="container mx-auto px-4 py-16 sm:px-6 lg:px-8 relative z-10">
        {/* Decorative Elements */}
        <div className="absolute top-0 right-0 w-1/3 h-1/3 bg-blue-500/5 rounded-full filter blur-3xl -z-10"></div>
        <div className="absolute bottom-0 left-0 w-1/4 h-1/4 bg-purple-500/5 rounded-full filter blur-3xl -z-10"></div>
        
        {/* Hero Section */}
        <div className={`mb-20 text-center relative ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          <div className="absolute inset-0 flex items-center justify-center -z-10">
            <div className="w-32 h-32 bg-blue-500/10 rounded-full filter blur-3xl"></div>
          </div>
          <h1 className="text-5xl font-bold mb-6 font-serif bg-gradient-to-r from-blue-600 via-indigo-500 to-purple-600 bg-clip-text text-transparent animate-gradient-x">
            Legal Document Analyzer
          </h1>
          <div className="h-1 w-24 bg-gradient-to-r from-blue-600 to-purple-600 mx-auto mb-8 rounded-full"></div>
          <p className="text-xl max-w-3xl mx-auto mb-8 leading-relaxed">
            Revolutionizing legal document analysis through AI-powered insights and advanced NLP techniques
          </p>
        </div>

        {/* Main Content Grid */}
        <div className="grid gap-12 lg:grid-cols-2 lg:gap-16 relative">
          {/* Features Section */}
          <div className={`p-10 rounded-3xl shadow-2xl backdrop-blur-sm transition-all duration-300 hover:shadow-blue-900/5 ${darkMode ? 'bg-slate-800/80 border border-slate-700/50' : 'bg-white/90 border border-gray-100'}`}>
            <div className="space-y-10">
              <div className="space-y-6">
                <h2 className="text-2xl font-bold mb-8 flex items-center">
                  <span className="mr-4 p-3 bg-blue-500/10 rounded-xl">
                    <svg className="w-6 h-6 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                  </span>
                  <span className={`${darkMode ? 'text-white' : 'text-gray-900'} relative`}>
                    Why Choose Our Platform?
                    <span className="absolute -bottom-2 left-0 w-12 h-1 bg-blue-500/30 rounded-full"></span>
                  </span>
                </h2>
                
                <div className={`space-y-8 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
                  <div className="flex items-start space-x-5 p-4 rounded-xl transition-all duration-300 hover:bg-blue-50/5">
                    <div className="mt-1 p-3 bg-green-500/10 rounded-xl shadow-sm">
                      <svg className="w-6 h-6 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                    <div>
                      <h3 className="font-semibold text-lg mb-2">AI-Powered Analysis</h3>
                      <p className="text-sm leading-relaxed">Advanced machine learning models extract key legal concepts and patterns</p>
                    </div>
                  </div>

                  <div className="flex items-start space-x-5 p-4 rounded-xl transition-all duration-300 hover:bg-purple-50/5">
                    <div className="mt-1 p-3 bg-purple-500/10 rounded-xl shadow-sm">
                      <svg className="w-6 h-6 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                      </svg>
                    </div>
                    <div>
                      <h3 className="font-semibold text-lg mb-2">Comprehensive Search</h3>
                      <p className="text-sm leading-relaxed">Cross-reference legal documents with integrated search capabilities</p>
                    </div>
                  </div>

                  <div className="flex items-start space-x-5 p-4 rounded-xl transition-all duration-300 hover:bg-orange-50/5">
                    <div className="mt-1 p-3 bg-orange-500/10 rounded-xl shadow-sm">
                      <svg className="w-6 h-6 text-orange-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                      </svg>
                    </div>
                    <div>
                      <h3 className="font-semibold text-lg mb-2">Military-Grade Security</h3>
                      <p className="text-sm leading-relaxed">Bank-level encryption and secure document handling protocols</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-12 pt-8 border-t border-gray-200/10">
                <h3 className={`text-lg font-semibold mb-6 relative inline-block ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                  Supported Document Types
                  <span className="absolute -bottom-2 left-0 w-10 h-1 bg-purple-500/30 rounded-full"></span>
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  {['PDF Documents', 'Word Files', 'Text Files', 'Scanned Images'].map((type, idx) => (
                    <div key={idx} className={`flex items-center space-x-3 p-4 rounded-xl transition-all duration-300 ${darkMode ? 'bg-slate-700/50 hover:bg-slate-700/80' : 'bg-gray-50 hover:bg-gray-100/80'}`}>
                      <svg className="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <span className={`text-sm font-medium ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>{type}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Auth Section */}
          <div className={`p-10 rounded-3xl shadow-2xl backdrop-blur-sm transition-all duration-300 hover:shadow-purple-900/5 ${darkMode ? 'bg-slate-800/80 border border-slate-700/50' : 'bg-white/90 border border-gray-100'} h-fit sticky top-8`}>
            {isLoggedIn ? (
              <div className="space-y-8">
                <div className="text-center">
                  <div className="inline-block p-5 bg-green-500/10 rounded-2xl mb-8 shadow-inner">
                    <svg className="w-14 h-14 text-green-500 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <h2 className="text-3xl font-bold mb-3">Welcome Back, Admin</h2>
                  <div className="h-1 w-16 bg-gradient-to-r from-green-400 to-green-600 mx-auto mb-6 rounded-full"></div>
                  <p className={`mb-8 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>Access your personalized dashboard</p>
                </div>
                
                <button
                  onClick={goToModules}
                  className="w-full flex items-center justify-center space-x-3 py-4 px-6 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-semibold rounded-xl transition-all duration-300 shadow-lg hover:shadow-blue-500/20 transform hover:-translate-y-1"
                >
                  <span>Continue to Dashboard</span>
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                  </svg>
                </button>
                
                <button
                  onClick={handleLogout}
                  className="w-full py-3 px-6 flex items-center justify-center space-x-2 text-red-500 hover:text-red-600 font-medium rounded-xl transition-colors border border-transparent hover:border-red-200/20 mt-4"
                >
                  <span>Sign Out</span>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                  </svg>
                </button>
              </div>
            ) : (
              <div className="space-y-8">
                <div className="text-center">
                  <div className="inline-block p-4 bg-blue-500/5 rounded-full mb-6">
                    <svg className="w-12 h-12 text-blue-500 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                    </svg>
                  </div>
                  <h2 className={`text-3xl font-bold mb-3 ${darkMode ? 'text-white' : 'text-gray-900'}`}>Admin Portal</h2>
                  <div className="h-1 w-16 bg-gradient-to-r from-blue-400 to-blue-600 mx-auto mb-6 rounded-full"></div>
                  <p className={`${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>Access requires authorized credentials</p>
                </div>

                <form onSubmit={handleLogin} className="space-y-6">
                  {error && (
                    <div className="p-4 bg-red-500/10 text-red-600 dark:text-red-400 rounded-xl flex items-center space-x-3 animate-pulse">
                      <svg className="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                      </svg>
                      <span>{error}</span>
                    </div>
                  )}

                  <div className="space-y-5">
                    <div>
                      <label className={`block text-sm font-medium mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                        Username
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                          <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                          </svg>
                        </div>
                        <input
                          type="text"
                          value={username}
                          onChange={(e) => setUsername(e.target.value)}
                          className={`w-full pl-10 pr-4 py-3 rounded-xl border ${darkMode ? 'bg-slate-700/70 border-slate-600 focus:border-blue-500 focus:ring-blue-500 text-white placeholder-gray-400' : 'bg-white border-gray-300 focus:border-blue-500 focus:ring-blue-500 text-gray-900 placeholder-gray-500'} transition-colors`}
                          placeholder="Enter admin username"
                        />
                      </div>
                    </div>

                    <div>
                      <label className={`block text-sm font-medium mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                        Password
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                          <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                          </svg>
                        </div>
                        <input
                          type="password"
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
                          className={`w-full pl-10 pr-4 py-3 rounded-xl border ${darkMode ? 'bg-slate-700/70 border-slate-600 focus:border-blue-500 focus:ring-blue-500 text-white placeholder-gray-400' : 'bg-white border-gray-300 focus:border-blue-500 focus:ring-blue-500 text-gray-900 placeholder-gray-500'} transition-colors`}
                          placeholder="Enter your password"
                        />
                      </div>
                    </div>
                  </div>

                  <button
                    type="submit"
                    className="w-full py-3 px-6 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-semibold rounded-xl transition-all duration-300 shadow-lg hover:shadow-blue-500/20 transform hover:-translate-y-1 mt-4"
                  >
                    Unlock Dashboard
                  </button>
                </form>
              </div>
            )}
          </div>
        </div>
      </main>

      <Footer darkMode={darkMode} />
    </div>
  );
}

export default AboutPage;