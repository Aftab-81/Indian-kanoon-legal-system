import React, { useEffect, useState } from 'react';

function Notification({ type, message, title, onDismiss, darkMode }) {
  const [isVisible, setIsVisible] = useState(true);
  
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsVisible(false);
      setTimeout(onDismiss, 300); // Allow fade-out animation to complete
    }, 5000);
    
    return () => clearTimeout(timer);
  }, [onDismiss]);
  
  // Get the appropriate icon based on notification type
  const getIcon = () => {
    switch(type) {
      case 'success':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        );
      case 'error':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        );
      case 'info':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      case 'warning':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        );
      default:
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
    }
  };
  
  // Get styles based on notification type and dark mode
  const getTypeStyles = () => {
    switch(type) {
      case 'success':
        return darkMode 
          ? 'bg-green-900/20 text-green-300 border-l-4 border-green-500' 
          : 'bg-green-50 text-green-800 border-l-4 border-green-500';
      case 'error':
        return darkMode 
          ? 'bg-red-900/20 text-red-300 border-l-4 border-red-500' 
          : 'bg-red-50 text-red-800 border-l-4 border-red-500';
      case 'info':
        return darkMode 
          ? 'bg-blue-900/20 text-blue-300 border-l-4 border-blue-500' 
          : 'bg-blue-50 text-blue-800 border-l-4 border-blue-500';
      case 'warning':
        return darkMode 
          ? 'bg-yellow-900/20 text-yellow-300 border-l-4 border-yellow-500' 
          : 'bg-yellow-50 text-yellow-800 border-l-4 border-yellow-500';
      default:
        return darkMode 
          ? 'bg-gray-800 text-gray-300 border-l-4 border-gray-600' 
          : 'bg-gray-100 text-gray-800 border-l-4 border-gray-400';
    }
  };
  
  return (
    <div className={`fixed top-4 right-4 z-50 transition-all duration-300 transform ${isVisible ? 'translate-x-0 opacity-100' : 'translate-x-4 opacity-0'}`}>
      <div className={`p-4 rounded-xl shadow-lg backdrop-blur-sm ${getTypeStyles()} animate-fadeIn`}>
        <div className="flex items-start gap-3">
          <div className={`p-1.5 rounded-lg ${darkMode ? 'bg-white/10' : 'bg-white/80'} flex-shrink-0`}>
            {getIcon()}
          </div>
          
          <div className="flex-1">
            {title && <h3 className="font-medium text-base mb-0.5">{title}</h3>}
            <p className={`${darkMode ? 'text-gray-300' : 'text-gray-600'} text-sm`}>{message}</p>
          </div>
          
          <button 
            onClick={() => {
              setIsVisible(false);
              setTimeout(onDismiss, 300);
            }}
            className={`${darkMode ? 'text-gray-400 hover:text-gray-200' : 'text-gray-500 hover:text-gray-700'} transition-colors p-1 rounded-full hover:bg-black/5`}
            aria-label="Dismiss notification"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}

export default Notification;