import React from 'react';

function Footer({ darkMode }) {
  return (
    <footer className={`py-6 mt-8 text-center ${darkMode ? 'bg-slate-800 text-gray-300' : 'bg-gray-100 text-gray-600'}`}>
      <p className="text-sm">&copy; {new Date().getFullYear()} Legal Document Analyzer. All rights reserved.</p>
    </footer>
  );
}

export default Footer;