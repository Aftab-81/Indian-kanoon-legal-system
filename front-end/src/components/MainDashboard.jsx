import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { CaseList } from './dashboard/CaseList';
import { CaseDetails } from './dashboard/CaseDetails';
import { UploadSection } from './dashboard/UploadSection';
import Header from './dashboard/Header';
import Footer from './dashboard/Footer';
import Notification from './dashboard/Notification';

function MainDashboard() {
  const [isProcessing, setIsProcessing] = useState(false);
  const [cases, setCases] = useState([]);
  const [selectedCase, setSelectedCase] = useState(null);
  const [caseDetails, setCaseDetails] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState(null);
  const [notification, setNotification] = useState(null);
  const [darkMode, setDarkMode] = useState(false);
  const [loadedCaseDetails, setLoadedCaseDetails] = useState({});
  const [ikApiToken, setIkApiToken] = useState('');
  const fileInputRef = useRef(null);
  
  const API_BASE = 'http://localhost:8000/api';  // Changed from 5000 to 8000

  const dismissNotification = () => {
    setNotification(null);
  };

  const toggleDarkMode = () => {
    const newDarkMode = !darkMode;
    setDarkMode(newDarkMode);
    localStorage.setItem('darkMode', newDarkMode ? 'true' : 'false');
  };
  
  const saveApiToken = () => {
    if (ikApiToken) {
      localStorage.setItem('ikApiToken', ikApiToken);
      setNotification({
        type: 'success',
        message: 'API token saved successfully',
        title: 'Token Saved'
      });
    }
  };

  const fetchCases = async () => {
    try {
      setError(null);
      const response = await axios.get(`${API_BASE}/cases`);
      if (response.data && Array.isArray(response.data)) {
        setCases(response.data);
      } else {
        console.error('Unexpected response format:', response.data);
        setError('Received invalid data format from server');
      }
    } catch (err) {
      setError('Failed to fetch cases. Please try again later.');
      console.error('Error fetching cases:', err);
    }
  };

  const fetchCaseDetails = async (caseFile) => {
    try {
      const response = await axios.get(`${API_BASE}/case/${caseFile}`);
      setCaseDetails(response.data);
      
      if (response.data.Confidence) {
        const confidenceValues = Object.values(response.data.Confidence);
        const averageConfidence = Math.round(
          confidenceValues.reduce((sum, value) => sum + value, 0) / confidenceValues.length
        );
        
        setLoadedCaseDetails(prev => ({
          ...prev,
          [caseFile]: {
            ...response.data,
            averageConfidence
          }
        }));
      }
    } catch (err) {
      setError('Failed to fetch case details. Please try again later.');
      console.error('Error fetching case details:', err);
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setIsProcessing(true);
    setError(null);
    setUploadProgress(0);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API_BASE}/upload`, formData, {
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadProgress(percentCompleted);
        },
      });

      if (response.data.success) {
        const alreadyAnalyzedCases = response.data.cases.filter(c => c.status === "already analyzed");
        
        if (alreadyAnalyzedCases.length > 0) {
          setNotification({
            type: 'info',
            message: `This judgment has already been analyzed previously.`,
            title: alreadyAnalyzedCases[0].title
          });
        } else {
          setNotification({
            type: 'success',
            message: 'Judgment successfully analyzed!',
            title: response.data.cases[0]?.title || 'New Judgment'
          });
        }
        
        fetchCases();
      } else {
        setError(response.data.error || 'An error occurred during processing');
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to upload file');
      console.error('Upload error:', err);
    } finally {
      setIsProcessing(false);
      setUploadProgress(0);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleSelectDocument = () => {
    fileInputRef.current.click();
  };

  const handleViewAllCases = () => {
    setSelectedCase(null);
    setCaseDetails(null);
  };

  const handleSelectCase = (caseItem) => {
    setSelectedCase(caseItem);
  };

  const handleDeleteCase = async (caseFile) => {
    if (window.confirm("Are you sure you want to delete this case? This action cannot be undone.")) {
      try {
        setError(null);
        const response = await axios.delete(`${API_BASE}/case/${caseFile}`);
        
        if (response.data.success) {
          setNotification({
            type: 'success',
            message: 'Case deleted successfully',
            title: 'Delete Successful'
          });
          
          if (selectedCase && selectedCase.file === caseFile) {
            setSelectedCase(null);
            setCaseDetails(null);
          }
          
          fetchCases();
        } else {
          setError(response.data.error || 'An error occurred during deletion');
        }
      } catch (err) {
        setError(err.response?.data?.error || 'Failed to delete case');
        console.error('Delete error:', err);
      }
    }
  };

  useEffect(() => {
    fetchCases();
    
    // Load dark mode preference from localStorage
    const savedDarkMode = localStorage.getItem('darkMode');
    if (savedDarkMode !== null) {
      setDarkMode(savedDarkMode === 'true');
    } else {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      setDarkMode(prefersDark);
      localStorage.setItem('darkMode', prefersDark ? 'true' : 'false');
    }
    
    // Load saved API token if available
    const savedToken = localStorage.getItem('ikApiToken');
    if (savedToken) {
      setIkApiToken(savedToken);
    }
  }, []);

  useEffect(() => {
    if (cases.length > 0) {
      const visibleCases = cases.slice(0, 5);
      visibleCases.forEach(caseItem => {
        fetchCaseDetails(caseItem.file);
      });
      
      if (cases.length > 5) {
        const remainingCases = cases.slice(5);
        setTimeout(() => {
          remainingCases.forEach((caseItem, index) => {
            setTimeout(() => {
              fetchCaseDetails(caseItem.file);
            }, index * 300);
          });
        }, 2000);
      }
    }
  }, [cases]);

  useEffect(() => {
    if (selectedCase) {
      fetchCaseDetails(selectedCase.file);
    }
  }, [selectedCase]);

  return (
    <div className={`min-h-screen transition-colors duration-300 ${darkMode ? 'bg-slate-900 text-white' : 'bg-gradient-to-br from-gray-100 to-gray-200'}`}>
      <Header darkMode={darkMode} toggleDarkMode={toggleDarkMode} />

      <main className="container mx-auto px-6 py-8">
        {notification && (
          <Notification 
            notification={notification} 
            dismissNotification={dismissNotification} 
            darkMode={darkMode} 
          />
        )}
        
        <div className="mb-8 flex justify-between items-center">
          <Link 
            to="/modules"
            className={`px-4 py-2 rounded-lg ${darkMode ? 'bg-slate-700 hover:bg-slate-600 text-white' : 'bg-white hover:bg-gray-100 text-gray-800'} transition-colors shadow-sm flex items-center gap-2`}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back to Module Selection
          </Link>
          <h1 className={`text-2xl font-serif ${darkMode ? 'text-white' : 'text-gray-800'}`}>Core Summary Extraction</h1>
        </div>

        {/* Unified Search Link */}
        <div className="mb-8 flex flex-wrap gap-4">
          <Link 
            to="/search"
            className={`px-4 py-2 rounded-lg ${darkMode ? 'bg-purple-800 hover:bg-purple-700 text-white' : 'bg-purple-100 hover:bg-purple-200 text-purple-700'} transition-colors flex items-center gap-2 shadow-sm`}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            Legal Search
          </Link>
        </div>

        <div className="grid lg:grid-cols-5 gap-8">
          <div className="lg:col-span-2 space-y-6">
            <UploadSection 
              darkMode={darkMode}
              isProcessing={isProcessing}
              uploadProgress={uploadProgress}
              error={error}
              fileInputRef={fileInputRef}
              handleFileUpload={handleFileUpload}
              handleSelectDocument={handleSelectDocument}
            />

            <CaseList 
              darkMode={darkMode}
              cases={cases}
              selectedCase={selectedCase}
              loadedCaseDetails={loadedCaseDetails}
              handleSelectCase={handleSelectCase}
              handleDeleteCase={handleDeleteCase}
            />
          </div>

          <CaseDetails 
            darkMode={darkMode}
            selectedCase={selectedCase}
            caseDetails={caseDetails}
            cases={cases}
            loadedCaseDetails={loadedCaseDetails}
            handleSelectCase={handleSelectCase}
            handleViewAllCases={() => setSelectedCase(null)}
            handleDeleteCase={handleDeleteCase}
          />
        </div>
      </main>

      <Footer darkMode={darkMode} />
    </div>
  );
}

export default MainDashboard;

