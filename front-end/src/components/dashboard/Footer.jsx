import React from 'react';

const Footer = ({ darkMode }) => {
  return (
    <footer className={`py-6 ${darkMode ? 'bg-slate-900 text-gray-400 border-t border-gray-800' : 'bg-white text-gray-500 border-t border-gray-100'}`}>
      <div className="container mx-auto px-6">
        <div className="flex flex-col md:flex-row justify-between items-center">
          <div className="mb-4 md:mb-0">
            <p className="text-sm">© 2023 Judicial Insight Engine. All rights reserved.</p>
          </div>
          <div className="flex items-center space-x-4">
            <a href="#" className={`text-sm ${darkMode ? 'hover:text-white' : 'hover:text-gray-700'} transition-colors`}>Privacy Policy</a>
            <a href="#" className={`text-sm ${darkMode ? 'hover:text-white' : 'hover:text-gray-700'} transition-colors`}>Terms of Service</a>
            <a href="#" className={`text-sm ${darkMode ? 'hover:text-white' : 'hover:text-gray-700'} transition-colors`}>Contact</a>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;