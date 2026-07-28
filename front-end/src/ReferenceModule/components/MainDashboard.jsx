import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import Header from '../../components/dashboard/Header'; // Changed from ../../../../components
import Footer from './dashboard/Footer';
import Notification from './dashboard/Notification';
import DocumentList from './dashboard/DocumentList';
import DocumentDetails from './dashboard/DocumentDetails';
import UploadSection from './dashboard/UploadSection';

function MainDashboard() {
  const [isProcessing, setIsProcessing] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [documentDetails, setDocumentDetails] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState(null);
  const [notification, setNotification] = useState(null);
  const [darkMode, setDarkMode] = useState(false);
  const fileInputRef = useRef(null);
  
  const API_BASE_URL = 'http://localhost:8001/api';  // CHANGED FROM 8000 TO 8001!

  const dismissNotification = () => setNotification(null);

  const toggleDarkMode = () => {
    const newDark = !darkMode;
    setDarkMode(newDark);
    localStorage.setItem('darkMode', newDark ? 'true' : 'false');
  };

  const fetchDocuments = async () => {
    try {
      setError(null);
      const { data } = await axios.get(`${API_BASE_URL}/history`);
      setDocuments(data.history || []);
    } catch (err) {
      setError('Failed to fetch documents.');
      console.error(err);
    }
  };

  const handleDeleteDocument = async (fileHash) => {
    try {
      setError(null);
      const response = await axios.delete(`${API_BASE_URL}/document/${fileHash}`);
      
      if (response.data.status === 'success') {
        // If the deleted document was selected, clear the selection
        if (selectedDocument && selectedDocument.file_hash === fileHash) {
          setSelectedDocument(null);
          setDocumentDetails(null);
        }
        
        // Update the documents list
        setDocuments(documents.filter(doc => doc.file_hash !== fileHash));
        
        // Show success notification
        setNotification({
          type: 'success',
          message: 'Document deleted successfully',
          title: 'Document Deleted'
        });
      } else {
        setError(response.data.error || 'An error occurred while deleting the document');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete document');
      console.error('Document deletion error:', err);
    }
  };

  const fetchDocumentDetails = async (fileHash) => {
    try {
      const { data } = await axios.get(`${API_BASE_URL}/document/${fileHash}`);
      // Merge file_hash so DocumentDetails can save
      setDocumentDetails({ ...data, file_hash: fileHash });
    } catch (err) {
      setError('Failed to fetch document details.');
      console.error(err);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0]; if (!file) return;
    setIsProcessing(true); setError(null); setUploadProgress(0);
    const formData = new FormData(); formData.append('file', file);
    
    // Add file size check
    if (file.size > 10 * 1024 * 1024) { // 10MB
      setError('File size exceeds 10MB limit');
      setIsProcessing(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }
    
    try {
      // Show initial progress immediately for better UX
      setUploadProgress(10);
      
      // Simulate progress during processing to provide feedback
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 5;
        });
      }, 1000);
      
      const res = await axios.post(`${API_BASE_URL}/analyze/legal`, formData, {
        onUploadProgress: (event) => {
          // Only update for actual upload progress, not processing time
          const uploadPercentage = Math.round((event.loaded * 30) / event.total);
          setUploadProgress(Math.min(30, uploadPercentage)); // Cap at 30% for upload phase
        }
      });
      
      // Clear the interval when response is received
      clearInterval(progressInterval);
      setUploadProgress(100);
      
      const { status, filename, original_filename } = res.data;
      if (status === 'success' || status === 'already_exists') {
        setNotification({
          type: status === 'success' ? 'success' : 'info',
          title: status === 'success' ? filename : original_filename,
          message: status === 'success' ? 'Document analyzed.' : 'Document already processed.'
        });
        fetchDocuments();
      } else {
        setError(res.data.error || 'Processing error');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed');
      console.error(err);
    } finally {
      setIsProcessing(false);
      setUploadProgress(0);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleSelectDocument = (doc) => {
    setSelectedDocument(doc);
    fetchDocumentDetails(doc.file_hash);
  };

  const handleViewAll = () => {
    setSelectedDocument(null);
    setDocumentDetails(null);
  };

  const handleSaveRemark = async (fileHash, remark) => {
    try {
      await axios.post(`${API_BASE_URL}/remarks`, { file_hash: fileHash, remark }, {
        headers: { 'Content-Type': 'application/json' }
      });
      // update history list
      setDocuments((prev) => prev.map(d => d.file_hash === fileHash ? { ...d, remark } : d));
      // update detail view
      setDocumentDetails((prev) => prev ? { ...prev, remark } : prev);
    } catch (err) {
      setError('Failed to save remark.');
      console.error(err);
      throw err;
    }
  };

  useEffect(() => {
    fetchDocuments();
    const saved = localStorage.getItem('darkMode');
    if (saved != null) setDarkMode(saved === 'true');
    else toggleDarkMode();
  }, []);

  return (
    <div className={`min-h-screen transition-colors duration-300 ${darkMode ? 'bg-slate-900 text-white' : 'bg-gradient-to-br from-gray-100 to-gray-200'}`}>      
      <Header darkMode={darkMode} toggleDarkMode={toggleDarkMode} />
      {notification && <Notification {...notification} onDismiss={dismissNotification} darkMode={darkMode} />}
      


      <main className="container mx-auto px-6 py-8">
      <div className="mb-8 flex justify-between items-center">
  <Link 
    to="/modules"
    className={`px-4 py-2 rounded-lg ${darkMode ? 'bg-slate-700 hover:bg-slate-600 text-white' : 'bg-white hover:bg-gray-100 text-gray-800'} transition-colors shadow-sm flex items-center gap-2`}
  >
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
    </svg>
    Back to Modules
  </Link>
  <div className="text-right">
    <h1 className={`text-2xl font-serif ${darkMode ? 'text-white' : 'text-gray-800'}`}>Document Reference System</h1>
    <p className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
      AI-Powered Legal Reference Discovery Across Cases, Statutes, and Precedents
    </p>
  </div>
</div>
        {/* Unified Search Link */}
        {/* <div className="mb-8 flex flex-wrap gap-4">
          <Link 
            to="/search"
            className={`px-4 py-2 rounded-lg ${darkMode ? 'bg-purple-800 hover:bg-purple-700 text-white' : 'bg-purple-100 hover:bg-purple-200 text-purple-700'} transition-colors flex items-center gap-2 shadow-sm`}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            Legal Search
          </Link>
        </div> */}
        
        <div className="grid lg:grid-cols-5 gap-8">
          <div className="lg:col-span-2 space-y-6">
            {/* Upload Section */}
            <div className={`${darkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-t border-l border-white'} rounded-2xl shadow-lg overflow-hidden relative p-6`}>
              <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-blue-500/10 to-purple-500/10 rounded-bl-full"></div>
              
              <h2 className={`text-xl font-serif ${darkMode ? 'text-white' : 'text-gray-800'} mb-4 flex items-center relative z-10`}>
                <span className={`${darkMode ? 'bg-indigo-900/50 text-indigo-300' : 'bg-indigo-100 text-indigo-700'} p-1.5 rounded-lg mr-3`}>
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                </span>
                Upload Document
              </h2>
              
              <div className="relative z-10">
                <UploadSection
                  onSelectDocument={() => fileInputRef.current.click()}
                  fileInputRef={fileInputRef}
                  handleFileUpload={handleFileUpload}
                  isProcessing={isProcessing}
                  uploadProgress={uploadProgress}
                  darkMode={darkMode}
                />
              </div>
            </div>
            
            {/* Document List */}
            <DocumentList
              documents={documents}
              selectedDocument={selectedDocument}
              onSelectDocument={handleSelectDocument}
              onViewAll={handleViewAll}
              onDeleteDocument={handleDeleteDocument}
              darkMode={darkMode}
            />
          </div>
          
          <div className="lg:col-span-3">
            {error && (
              <div className={`p-4 ${darkMode ? 'bg-red-900/20 text-red-300 border border-red-800/30' : 'bg-red-50 text-red-700 border border-red-100'} rounded-xl mb-4`}>
                <div className="flex items-center">
                  <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <p>{error}</p>
                </div>
              </div>
            )}
            
            {selectedDocument && documentDetails ? (
              <DocumentDetails
                document={documentDetails}
                onSaveRemark={handleSaveRemark}
                darkMode={darkMode}
              />
            ) : (
              <div className={`${darkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-t border-l border-white'} rounded-2xl shadow-lg overflow-hidden relative`}>
                <div className="absolute top-0 right-0 w-40 h-40 bg-gradient-to-br from-blue-500/10 to-purple-500/10 rounded-bl-full"></div>
                <div className="absolute bottom-0 left-0 w-full h-40 bg-gradient-to-t from-indigo-500/5 to-transparent"></div>
                
                <div className="p-8 relative z-10">
                  <h2 className={`text-xl font-serif ${darkMode ? 'text-white' : 'text-gray-800'} flex items-center mb-6`}>
                    <span className={`${darkMode ? 'bg-indigo-900/50 text-indigo-300' : 'bg-indigo-100 text-indigo-700'} p-1.5 rounded-lg mr-3`}>
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                      </svg>
                    </span>
                    Legal Document Analyzer
                  </h2>
                  
                  <p className={`mb-6 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
                    Upload a legal document (PDF or DOCX) to analyze its content or search for legal information.
                  </p>
                  
                  <div className="flex flex-wrap gap-4">
                    <button 
                      onClick={() => fileInputRef.current.click()} 
                      className={`px-4 py-2 ${darkMode ? 'bg-indigo-600 hover:bg-indigo-700' : 'bg-indigo-600 hover:bg-indigo-700'} text-white rounded-lg flex items-center gap-2 transition-colors`}
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                      </svg>
                      Upload Document
                    </button>
                    
                    <Link 
                      to="/reference/search" 
                      className={`px-4 py-2 ${darkMode ? 'bg-purple-700 hover:bg-purple-800' : 'bg-purple-600 hover:bg-purple-700'} text-white rounded-lg flex items-center gap-2 transition-colors`}
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                      </svg>
                      Search Legal Information
                    </Link>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
      
      <Footer darkMode={darkMode} />
    </div>
  );
}

export default MainDashboard;

// Add this near the top of the component return statement, inside the container div
