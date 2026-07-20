import React from 'react';

// Helper function to safely render text content
const renderTextContent = (content) => {
  if (!content) return "";
  if (typeof content === 'string') return content;
  if (typeof content === 'object' && content.Value) {
    return content.Value;
  }
  if (typeof content === 'object') {
    return JSON.stringify(content);
  }
  return String(content);
};

const Notification = ({ notification, dismissNotification, darkMode }) => {
  if (!notification) return null;

  return (
    <div className={`mb-6 p-4 rounded-xl shadow-md flex justify-between items-center transform transition-all duration-500 animate-fadeIn ${
      notification.type === 'success' 
        ? darkMode 
          ? 'bg-green-900/20 text-green-300 border-l-4 border-green-500' 
          : 'bg-green-50 text-green-800 border-l-4 border-green-500'
        : notification.type === 'info' 
          ? darkMode
            ? 'bg-blue-900/20 text-blue-300 border-l-4 border-blue-500'
            : 'bg-blue-50 text-blue-800 border-l-4 border-blue-500'
          : darkMode
            ? 'bg-yellow-900/20 text-yellow-300 border-l-4 border-yellow-500'
            : 'bg-yellow-50 text-yellow-800 border-l-4 border-yellow-500'
    }`}>
      <div>
        <h3 className="font-medium">{renderTextContent(notification.title)}</h3>
        <p>{notification.message}</p>
      </div>
      <button 
        onClick={dismissNotification}
        className={`${darkMode ? 'text-gray-400 hover:text-gray-200' : 'text-gray-500 hover:text-gray-700'} transition-colors`}
      >
        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
          <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
        </svg>
      </button>
    </div>
  );
};

export default Notification;