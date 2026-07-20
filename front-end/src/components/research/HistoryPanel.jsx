import { useState, useEffect } from 'react';

const API_BASE = 'http://localhost:8001/api';  // Changed to port 8001

function HistoryPanel({ darkMode }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      const res = await fetch(`${API_BASE}/history`);
      const data = await res.json();
      setHistory(data.history || []);
    } catch (err) {
      console.error('History error:', err);
    } finally {
      setLoading(false);
    }
  };

  const deleteItem = async (questionId) => {
    if (!confirm('Are you sure you want to delete this question?')) return;
    
    try {
      await fetch(`${API_BASE}/delete-history`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question_id: questionId })
      });
      fetchHistory();
    } catch (err) {
      console.error('Delete error:', err);
    }
  };

  const getStatusColor = (status) => {
    if (status === 'APPROVED') return 'from-green-500 to-emerald-500';
    if (status === 'REJECTED') return 'from-red-500 to-rose-500';
    return 'from-yellow-500 to-orange-500';
  };

  const filteredHistory = history.filter((item) => {
    if (!searchTerm.trim()) return true;
    return (item.question || '').toLowerCase().includes(searchTerm.toLowerCase());
  });

  const cardClass = darkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200';

  if (loading) {
    return (
      <div className="text-center py-12">
        <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-indigo-500 border-t-transparent"></div>
        <p className={`mt-4 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Loading history...</p>
      </div>
    );
  }

  if (history.length === 0) {
    return (
      <div className={`text-center py-12 p-8 border rounded-xl ${cardClass} shadow-lg`}>
        <div className="text-6xl mb-4">📋</div>
        <p className={`text-xl ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
          No questions asked yet
        </p>
        <p className={`text-sm mt-2 ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
          Your past legal queries will appear here
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className={`p-6 border rounded-xl ${cardClass} shadow-lg`}>
        <label className={`block text-sm font-semibold mb-3 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
          Search in history:
        </label>
        <input
          type="text"
          placeholder="Filter previous questions..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className={`w-full px-4 py-3 rounded-lg border ${
            darkMode ? 'bg-slate-700 border-slate-600 text-white placeholder-gray-400' : 'bg-gray-50 border-gray-300 placeholder-gray-500'
          } focus:ring-2 focus:ring-indigo-500 focus:outline-none transition-all`}
        />
      </div>

      <div className="space-y-4">
        {filteredHistory.map((item, i) => (
          <div key={i} className={`p-6 border rounded-xl ${cardClass} shadow-lg hover:shadow-xl transition-shadow`}>
            <div className="flex justify-between items-start mb-4">
              <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                {item.asked_at ? new Date(item.asked_at).toLocaleString() : ''}
              </span>
              {item.status && (
                <span className={`px-3 py-1 rounded-full text-white text-xs font-bold bg-gradient-to-r ${getStatusColor(item.status)} shadow-md`}>
                  {item.status}
                </span>
              )}
            </div>

            <div className="mb-3">
              <strong className={`text-sm ${darkMode ? 'text-indigo-400' : 'text-indigo-600'}`}>Q:</strong>
              <p className={`mt-1 font-medium ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                {item.question}
              </p>
            </div>

            {item.conclusion && (
              <div className="mb-4">
                <strong className={`text-sm ${darkMode ? 'text-green-400' : 'text-green-600'}`}>A:</strong>
                <p className={`mt-1 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                  {item.conclusion.substring(0, 200)}
                  {item.conclusion.length > 200 && '...'}
                </p>
              </div>
            )}

            <button
              onClick={() => deleteItem(item.question_id)}
              className="px-4 py-2 bg-gradient-to-r from-red-500 to-rose-500 hover:from-red-600 hover:to-rose-600 text-white rounded-lg transition-all text-sm font-medium shadow-md transform hover:scale-105"
            >
              🗑️ Delete
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

export default HistoryPanel;