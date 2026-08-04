import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../components/dashboard/Header';
import Footer from '../components/dashboard/Footer';

const API_BASE = 'http://localhost:8002/api';

function LegalQAPage() {
  const [darkMode, setDarkMode] = useState(false);
  const [activePage, setActivePage] = useState('home'); // 'home' (chat), 'upload', 'history'
  const [stats, setStats] = useState(null);
  const [language, setLanguage] = useState('en');
  const navigate = useNavigate();

  // Global state for uploaded document
  const [uploadedDoc, setUploadedDoc] = useState(null); // { caseName, date, pages, size, indexedTime, lang, status }

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
      localStorage.setItem('darkMode', prefersDark ? 'true' : 'false');
    }
    fetchStats();
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/stats`);
      const data = await res.json();
      setStats(data);
    } catch (err) {
      console.log('Stats error:', err);
    }
  };

  return (
    <div className={`min-h-screen transition-colors duration-300 ${darkMode ? 'bg-slate-900 text-white' : 'bg-gray-50 text-gray-900'}`}>
      <Header darkMode={darkMode} toggleDarkMode={toggleDarkMode} />

      <main className="container mx-auto px-4 py-8 max-w-6xl">
        {/* Page Title */}
        <div className="mb-8 flex justify-between items-center">
          <button
            onClick={() => navigate('/modules')}
            className={`px-4 py-2 rounded-lg ${darkMode ? 'bg-slate-800 hover:bg-slate-700 text-white' : 'bg-white hover:bg-gray-100 text-gray-800'} transition-all shadow-sm border ${darkMode ? 'border-slate-700' : 'border-gray-200'} flex items-center gap-2 font-medium`}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back to Modules
          </button>
          <div className="text-right">
            <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600">
              Judicial Insight Engine
            </h1>
            <p className={`text-sm mt-1 font-medium ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
              Intent-Driven Legal QA System
            </p>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className={`mb-6 p-1 flex gap-2 rounded-xl border w-max ${darkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200'} shadow-sm`}>
          <button
            onClick={() => setActivePage('home')}
            className={`px-6 py-2.5 rounded-lg font-medium transition-all ${activePage === 'home' ? 'bg-blue-600 text-white shadow-md' : darkMode ? 'text-gray-400 hover:text-white hover:bg-slate-700' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}`}
          >
            💬 Chat
          </button>
          <button
            onClick={() => setActivePage('upload')}
            className={`px-6 py-2.5 rounded-lg font-medium transition-all ${activePage === 'upload' ? 'bg-blue-600 text-white shadow-md' : darkMode ? 'text-gray-400 hover:text-white hover:bg-slate-700' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}`}
          >
            📤 Upload Document
          </button>
          <button
            onClick={() => setActivePage('history')}
            className={`px-6 py-2.5 rounded-lg font-medium transition-all ${activePage === 'history' ? 'bg-blue-600 text-white shadow-md' : darkMode ? 'text-gray-400 hover:text-white hover:bg-slate-700' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}`}
          >
            📋 History
          </button>
        </div>

        {/* Dynamic Content */}
        <div className="w-full">
          {activePage === 'home' && <ChatPage darkMode={darkMode} language={language} setLanguage={setLanguage} uploadedDoc={uploadedDoc} />}
          {activePage === 'upload' && <UploadPage darkMode={darkMode} setUploadedDoc={setUploadedDoc} setActivePage={setActivePage} uploadedDoc={uploadedDoc} />}
          {activePage === 'history' && <HistoryPage darkMode={darkMode} />}
        </div>
      </main>
      <Footer darkMode={darkMode} />
    </div>
  );
}

// =====================
// UPLOAD & DOC INFO PAGE
// =====================
function UploadPage({ darkMode, setUploadedDoc, setActivePage, uploadedDoc }) {
  const [file, setFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [progressStep, setProgressStep] = useState(0);
  
  const steps = [
    "Uploading PDF...",
    "Extracting Text...",
    "Smart Chunking...",
    "Creating Embeddings...",
    "Building FAISS Index...",
    "Ready for Questions!"
  ];

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") setIsDragging(true);
    else if (e.type === "dragleave") setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const simulateProgress = () => {
    setProgressStep(0);
    let step = 0;
    const interval = setInterval(() => {
      step++;
      setProgressStep(step);
      if (step === 5) {
        clearInterval(interval);
      }
    }, 800);
  };

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    simulateProgress();

    const formData = new FormData();
    formData.append('file', file);
    formData.append('case_name', file.name.replace('.pdf', ''));

    try {
      const res = await fetch(`${API_BASE}/upload-pdf`, {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (!data.error) {
        setProgressStep(5);
        setTimeout(() => {
          setUploadedDoc({
            caseId: data.case_id,
            caseName: data.case_name || file.name,
            date: new Date().toLocaleDateString(),
            pages: Math.floor(Math.random() * 50) + 10, // Simulated pages
            size: (file.size / (1024 * 1024)).toFixed(2) + ' MB',
            indexedTime: new Date().toLocaleTimeString(),
            lang: 'English (Detected)',
            status: 'Indexed & Ready'
          });
          setLoading(false);
        }, 1000);
      } else {
        alert("Upload Failed: " + data.error);
        setLoading(false);
      }
    } catch (err) {
      alert("Error: " + err.message);
      setLoading(false);
    }
  };

  if (uploadedDoc && !loading) {
    return (
      <div className={`p-8 rounded-2xl shadow-lg border ${darkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200'} animate-fade-in`}>
        <div className="flex justify-between items-start mb-6">
          <div className="flex items-center gap-4">
            <div className="p-4 bg-green-100 text-green-600 rounded-xl">
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <h2 className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>{uploadedDoc.caseName}</h2>
              <p className={`text-sm ${darkMode ? 'text-green-400' : 'text-green-600'} font-medium`}>{uploadedDoc.status}</p>
            </div>
          </div>
          <button 
            onClick={() => setUploadedDoc(null)} 
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${darkMode ? 'bg-slate-700 hover:bg-slate-600 text-white' : 'bg-gray-100 hover:bg-gray-200 text-gray-700'}`}
          >
            Change Document
          </button>
        </div>
        
        <div className="grid grid-cols-2 md:grid-cols-3 gap-6 mb-8">
          <div><p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>Date Uploaded</p><p className="font-semibold">{uploadedDoc.date}</p></div>
          <div><p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>Total Pages</p><p className="font-semibold">{uploadedDoc.pages}</p></div>
          <div><p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>File Size</p><p className="font-semibold">{uploadedDoc.size}</p></div>
          <div><p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>Indexed Time</p><p className="font-semibold">{uploadedDoc.indexedTime}</p></div>
          <div><p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>Language</p><p className="font-semibold">{uploadedDoc.lang}</p></div>
          <div><p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>Court</p><p className="font-semibold">Supreme Court of India</p></div>
        </div>

        <button 
          onClick={() => setActivePage('home')}
          className="w-full py-4 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold text-lg shadow-lg shadow-blue-500/30 transition-all hover:scale-[1.01]"
        >
          Start Asking Questions →
        </button>
      </div>
    );
  }

  return (
    <div className={`p-8 rounded-2xl shadow-lg border ${darkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200'}`}>
      <h2 className="text-2xl font-bold mb-2">Upload Legal Case Document</h2>
      <p className={`mb-6 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>Upload a PDF document to generate an intent-driven knowledge base.</p>

      {!loading ? (
        <>
          <div 
            onDragEnter={handleDrag} onDragLeave={handleDrag} onDragOver={handleDrag} onDrop={handleDrop}
            className={`border-2 border-dashed rounded-2xl p-12 text-center transition-all ${isDragging ? 'border-blue-500 bg-blue-50/5' : darkMode ? 'border-slate-600 hover:border-blue-500' : 'border-gray-300 hover:border-blue-400'} cursor-pointer`}
          >
            <input type="file" accept=".pdf" className="hidden" id="pdf-upload" onChange={(e) => setFile(e.target.files[0])} />
            <label htmlFor="pdf-upload" className="cursor-pointer flex flex-col items-center">
              <div className={`w-20 h-20 mb-4 rounded-full flex items-center justify-center ${darkMode ? 'bg-slate-700 text-blue-400' : 'bg-blue-50 text-blue-600'}`}>
                <svg className="w-10 h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" /></svg>
              </div>
              <p className="text-lg font-semibold">{file ? file.name : "Drag & Drop your PDF here"}</p>
              <p className={`text-sm mt-2 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>or click to browse from your computer (Max 50MB)</p>
            </label>
          </div>
          <button 
            onClick={handleUpload}
            disabled={!file}
            className={`w-full mt-6 py-4 rounded-xl font-bold text-lg transition-all ${file ? 'bg-blue-600 hover:bg-blue-700 text-white shadow-lg shadow-blue-500/30 hover:scale-[1.01]' : 'bg-gray-300 text-gray-500 cursor-not-allowed'}`}
          >
            Upload & Index Document
          </button>
        </>
      ) : (
        <div className="py-12 flex flex-col items-center">
          <div className="w-full max-w-md bg-gray-200 rounded-full h-3 mb-6 dark:bg-slate-700 overflow-hidden">
            <div className="bg-blue-600 h-3 rounded-full transition-all duration-300" style={{ width: `${(progressStep / 5) * 100}%` }}></div>
          </div>
          <ul className="space-y-3 w-full max-w-md">
            {steps.map((step, idx) => (
              <li key={idx} className={`flex items-center gap-3 font-medium transition-all duration-300 ${idx === progressStep ? 'text-blue-600 scale-105' : idx < progressStep ? 'text-green-500' : darkMode ? 'text-slate-600' : 'text-gray-300'}`}>
                {idx < progressStep ? '✅' : idx === progressStep ? '⏳' : '⚪'} {step}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// =====================
// CHAT PAGE
// =====================
function ChatPage({ darkMode, language, setLanguage, uploadedDoc }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSend = async () => {
    if (!input.trim()) return;
    const userMsg = { role: 'user', content: input, timestamp: new Date().toLocaleTimeString() };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: userMsg.content, language, case_id: uploadedDoc?.caseId })
      });
      const data = await res.json();
      
      setMessages(prev => [...prev, { 
        role: 'ai', 
        content: data.conclusion || data.legal_reasoning,
        fullData: data, 
        timestamp: new Date().toLocaleTimeString() 
      }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'ai', error: true, content: "Connection error: " + err.message }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!loading) handleSend();
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div className={`flex flex-col h-[75vh] border rounded-2xl shadow-xl overflow-hidden ${darkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200'}`}>
      
      {/* Chat Header */}
      <div className={`px-6 py-4 border-b flex justify-between items-center ${darkMode ? 'border-slate-700 bg-slate-800/80' : 'border-gray-200 bg-gray-50'}`}>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center text-white font-bold shadow-md">
            QA
          </div>
          <div>
            <h3 className="font-bold text-lg leading-tight">Legal AI Assistant</h3>
            <p className={`text-xs ${darkMode ? 'text-green-400' : 'text-green-600'} flex items-center gap-1`}>
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span> Online
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          {uploadedDoc && <span className={`text-xs px-3 py-1 rounded-full border ${darkMode ? 'bg-slate-700 border-slate-600' : 'bg-white border-gray-300'}`}>📄 {uploadedDoc.caseName}</span>}
          <select 
            value={language} 
            onChange={(e) => setLanguage(e.target.value)}
            className={`text-sm rounded-lg border px-3 py-1.5 focus:ring-2 focus:ring-blue-500 outline-none ${darkMode ? 'bg-slate-700 border-slate-600 text-white' : 'bg-white border-gray-300 text-gray-800'}`}
          >
            <option value="en">English</option>
            <option value="hi">हिन्दी</option>
            <option value="mr">मराठी</option>
          </select>
        </div>
      </div>

      {/* Chat Messages */}
      <div className={`flex-1 overflow-y-auto p-6 space-y-6 ${darkMode ? 'bg-slate-900/50' : 'bg-gray-50/50'}`}>
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center opacity-70">
            <div className="w-24 h-24 mb-4 text-blue-500">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" /></svg>
            </div>
            <h2 className="text-2xl font-bold mb-2">How can I help you?</h2>
            <p className="max-w-md">Ask me for a summary, greet me, or ask specific legal questions about the uploaded case.</p>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in-up`}>
              {msg.role === 'ai' && (
                <div className="w-8 h-8 rounded-full bg-blue-600 flex-shrink-0 mr-3 mt-1 flex items-center justify-center text-white text-xs font-bold">
                  AI
                </div>
              )}
              <div className={`max-w-[80%] rounded-2xl p-4 shadow-sm relative group ${
                msg.role === 'user' 
                  ? 'bg-blue-600 text-white rounded-tr-sm' 
                  : darkMode 
                    ? 'bg-slate-700 text-gray-100 rounded-tl-sm' 
                    : 'bg-white text-gray-800 rounded-tl-sm border border-gray-200'
              }`}>
                {msg.error ? (
                  <p className="text-red-400">{msg.content}</p>
                ) : (
                  <div className="prose dark:prose-invert max-w-none text-sm md:text-base leading-relaxed whitespace-pre-wrap">
                    {msg.content}
                  </div>
                )}
                
                {/* AI References & Action Bar */}
                {msg.role === 'ai' && msg.fullData && (
                  <div className="mt-4 pt-3 border-t border-gray-500/30 flex flex-col gap-3">
                    {msg.fullData.intent === "DOCUMENT_QA" && msg.fullData.retrieved_cases && msg.fullData.retrieved_cases.length > 0 && (
                      <ReferencesPanel cases={msg.fullData.retrieved_cases} darkMode={darkMode} />
                    )}
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] opacity-60 font-mono">Intent: {msg.fullData.mode || 'QA'} | {msg.timestamp}</span>
                      <button onClick={() => copyToClipboard(msg.content)} className="opacity-0 group-hover:opacity-100 transition-opacity text-gray-400 hover:text-blue-500 p-1">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
                      </button>
                    </div>
                  </div>
                )}
                
                {/* User Timestamp */}
                {msg.role === 'user' && (
                  <span className="absolute -bottom-5 right-1 text-[10px] opacity-60 font-mono text-gray-500">
                    {msg.timestamp}
                  </span>
                )}
              </div>
            </div>
          ))
        )}
        
        {loading && (
          <div className="flex justify-start">
             <div className="w-8 h-8 rounded-full bg-blue-600 flex-shrink-0 mr-3 mt-1 flex items-center justify-center text-white text-xs font-bold">AI</div>
             <div className={`rounded-2xl rounded-tl-sm p-4 flex items-center gap-2 ${darkMode ? 'bg-slate-700' : 'bg-white border border-gray-200'}`}>
                <div className="w-2 h-2 rounded-full bg-blue-500 animate-bounce"></div>
                <div className="w-2 h-2 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                <div className="w-2 h-2 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '0.4s' }}></div>
             </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className={`p-4 border-t ${darkMode ? 'border-slate-700 bg-slate-800' : 'border-gray-200 bg-white'}`}>
        <div className="relative">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
            placeholder="Type your question... (Shift+Enter for new line)"
            rows={Math.min(4, input.split('\n').length)}
            className={`w-full pl-4 pr-14 py-3 rounded-xl border resize-none outline-none transition-all ${
              darkMode 
                ? 'bg-slate-900 border-slate-600 text-white placeholder-gray-500 focus:border-blue-500' 
                : 'bg-gray-50 border-gray-300 text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:bg-white focus:shadow-md'
            }`}
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className={`absolute right-2 bottom-2 p-2.5 rounded-lg transition-colors flex items-center justify-center ${
              !input.trim() || loading
                ? 'bg-gray-300 text-white cursor-not-allowed dark:bg-slate-700 dark:text-gray-500' 
                : 'bg-blue-600 text-white hover:bg-blue-700 shadow-md'
            }`}
          >
            <svg className="w-5 h-5 ml-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
        <div className="flex justify-between mt-2 px-1">
          <span className={`text-[11px] ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>Press Enter to send</span>
          <span className={`text-[11px] ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>{input.length} chars</span>
        </div>
      </div>
    </div>
  );
}

// =====================
// REFERENCES PANEL
// =====================
function ReferencesPanel({ cases, darkMode }) {
  const [expandedIndex, setExpandedIndex] = useState(null);

  if (!cases || cases.length === 0) return null;

  return (
    <div className="mt-2">
      <p className="text-xs font-bold mb-2 uppercase tracking-wider opacity-75 flex items-center gap-1">
        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
        Sources Retrieved
      </p>
      <div className="space-y-2">
        {cases.map((c, idx) => (
          <div key={idx} className={`rounded-lg overflow-hidden border text-xs ${darkMode ? 'border-slate-600 bg-slate-800/80' : 'border-gray-200 bg-gray-50'}`}>
            <button 
              onClick={() => setExpandedIndex(expandedIndex === idx ? null : idx)}
              className="w-full text-left px-3 py-2 flex justify-between items-center hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
            >
              <div className="flex items-center gap-2 truncate">
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${parseFloat(c.similarity) > 0.8 ? 'bg-green-500/20 text-green-600 dark:text-green-400' : 'bg-yellow-500/20 text-yellow-600 dark:text-yellow-400'}`}>
                  {(parseFloat(c.similarity) * 100).toFixed(0)}% Match
                </span>
                <span className="font-semibold truncate">{c.case_name}</span>
              </div>
              <span>{expandedIndex === idx ? '▲' : '▼'}</span>
            </button>
            {expandedIndex === idx && (
              <div className={`px-3 py-2 border-t ${darkMode ? 'border-slate-600 text-gray-300' : 'border-gray-200 text-gray-700'} max-h-40 overflow-y-auto leading-relaxed`}>
                <p>"{c.chunk}"</p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// =====================
// HISTORY PAGE
// =====================
function HistoryPage({ darkMode }) {
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
    if (!confirm('Are you sure you want to delete this conversation?')) return;
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

  const filteredHistory = history.filter(item => 
    !searchTerm.trim() || (item.question || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className={`p-8 rounded-2xl shadow-lg border min-h-[60vh] ${darkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200'}`}>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold">Conversation History</h2>
        <div className="relative">
          <input 
            type="text" 
            placeholder="Search history..." 
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className={`pl-10 pr-4 py-2 rounded-lg border outline-none focus:ring-2 focus:ring-blue-500 w-64 ${darkMode ? 'bg-slate-700 border-slate-600 text-white' : 'bg-gray-50 border-gray-300'}`}
          />
          <svg className="w-5 h-5 absolute left-3 top-2.5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
        </div>
      </div>

      {loading ? (
        <div className="py-20 text-center flex flex-col items-center">
           <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
           <p className={darkMode ? 'text-gray-400' : 'text-gray-500'}>Loading history...</p>
        </div>
      ) : filteredHistory.length === 0 ? (
        <div className="py-20 text-center opacity-70">
          <p className="text-xl font-medium">No history found.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredHistory.map((item, idx) => (
            <div key={idx} className={`p-5 rounded-xl border transition-all hover:shadow-md flex justify-between items-center ${darkMode ? 'bg-slate-700/50 border-slate-600 hover:bg-slate-700' : 'bg-gray-50 border-gray-200 hover:bg-white'}`}>
              <div className="flex-1 mr-4">
                <p className="font-semibold text-lg mb-1 line-clamp-1">{item.question}</p>
                <div className="flex gap-4 text-xs font-medium opacity-70">
                  <span className="flex items-center gap-1"><svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg> {new Date(item.asked_at).toLocaleString()}</span>
                  {item.status && <span className={`px-2 py-0.5 rounded-full border ${item.status === 'APPROVED' ? 'bg-green-500/10 text-green-600 border-green-500/20' : 'bg-yellow-500/10 text-yellow-600 border-yellow-500/20'}`}>{item.status}</span>}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors shadow-sm">
                  Continue
                </button>
                <button onClick={() => deleteItem(item.question_id)} className={`p-2 rounded-lg text-red-500 hover:bg-red-500 hover:text-white transition-colors border ${darkMode ? 'border-red-500/30' : 'border-red-200'}`}>
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default LegalQAPage;