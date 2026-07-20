import { useState } from 'react';

const API_BASE = 'http://localhost:8001/api';  // Changed to port 8001

function DocumentUpload({ darkMode, onDocumentAnalyzed }) {
  const [file, setFile] = useState(null);
  const [caseName, setCaseName] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const handleUpload = async () => {
    if (!file) {
      setMessage('❌ Please select a PDF file');
      return;
    }

    setLoading(true);
    setMessage('');

    const formData = new FormData();
    formData.append('file', file);
    formData.append('case_name', caseName || file.name);

    try {
      const res = await fetch(`${API_BASE}/upload-pdf`, {
        method: 'POST',
        body: formData
      });

      const data = await res.json();

      if (data.error) {
        setMessage('❌ ' + data.error);
      } else {
        setMessage('✅ ' + data.message);
        setFile(null);
        setCaseName('');
      }
    } catch (err) {
      setMessage('❌ Upload failed: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const cardClass = darkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200';

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className={`p-8 border-2 border-dashed rounded-xl ${darkMode ? 'border-slate-600 bg-slate-800/50' : 'border-gray-300 bg-gray-50'} shadow-lg transition-all hover:shadow-xl`}>
        <input
          type="file"
          accept=".pdf"
          onChange={(e) => setFile(e.target.files[0])}
          id="file-input"
          disabled={loading}
          className="hidden"
        />
        <label
          htmlFor="file-input"
          className={`block text-center cursor-pointer ${loading ? 'opacity-50 cursor-not-allowed' : 'hover:scale-105 transition-transform'}`}
        >
          <div className="text-6xl mb-4">📄</div>
          <p className={`text-xl font-semibold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            Click to select PDF
          </p>
          <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            Upload Supreme Court judgment documents
          </p>
        </label>
        {file && (
          <div className="mt-4 p-3 bg-green-500/10 border border-green-500 rounded-lg">
            <p className="text-center text-sm text-green-600 dark:text-green-400 font-semibold">
              ✓ Selected: {file.name}
            </p>
          </div>
        )}
      </div>

      <div className={`p-6 border rounded-xl ${cardClass} shadow-lg`}>
        <label className={`block text-sm font-semibold mb-3 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
          Case Name (Optional):
        </label>
        <input
          type="text"
          value={caseName}
          onChange={(e) => setCaseName(e.target.value)}
          placeholder="E.g., State of Goa v. XYZ (2025)"
          disabled={loading}
          className={`w-full px-4 py-3 rounded-lg border ${
            darkMode
              ? 'bg-slate-700 border-slate-600 text-white placeholder-gray-400'
              : 'bg-gray-50 border-gray-300 placeholder-gray-500'
          } focus:ring-2 focus:ring-indigo-500 focus:outline-none transition-all`}
        />
      </div>

      {message && (
        <div className={`p-4 rounded-lg border-l-4 ${
          message.includes('✅') 
            ? 'bg-green-50 border-green-500 dark:bg-green-900/20' 
            : 'bg-red-50 border-red-500 dark:bg-red-900/20'
        }`}>
          <p className={`font-medium ${
            message.includes('✅') 
              ? 'text-green-700 dark:text-green-400' 
              : 'text-red-700 dark:text-red-400'
          }`}>
            {message}
          </p>
        </div>
      )}

      <button
        onClick={handleUpload}
        disabled={loading || !file}
        className="w-full px-6 py-4 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 disabled:from-gray-400 disabled:to-gray-500 text-white font-semibold rounded-xl shadow-lg transition-all transform hover:scale-105 disabled:transform-none"
      >
        {loading ? (
          <span className="flex items-center justify-center gap-2">
            <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            Processing PDF...
          </span>
        ) : (
          '🚀 Upload & Index'
        )}
      </button>

      <div className={`p-6 rounded-xl border ${darkMode ? 'bg-blue-900/20 border-blue-700' : 'bg-blue-50 border-blue-200'} shadow-lg`}>
        <h4 className={`font-semibold mb-3 flex items-center gap-2 ${darkMode ? 'text-blue-300' : 'text-blue-800'}`}>
          <span className="text-xl">💡</span> Smart Indexing:
        </h4>
        <ul className={`space-y-2 text-sm ${darkMode ? 'text-blue-200' : 'text-blue-700'}`}>
          <li className="flex items-start gap-2">
            <span className="text-indigo-500 font-bold">•</span>
            <span>800-word chunks + 200 overlap</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-indigo-500 font-bold">•</span>
            <span>Keeps legal paragraph structure</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-indigo-500 font-bold">•</span>
            <span>Semantic search retrieves best parts</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-indigo-500 font-bold">•</span>
            <span>External fallback if no match found</span>
          </li>
        </ul>
      </div>
    </div>
  );
}

export default DocumentUpload;