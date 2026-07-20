import { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import MainDashboard from './components/MainDashboard';
import IKSearchPage from './pages/IKSearchPage';
import GoogleSearchPage from './pages/GoogleSearchPage';
import UnifiedSearchPage from './pages/UnifiedSearchPage';
import ModuleSelectionPage from './pages/ModuleSelectionPage';
import ReferenceMainDashboard from './ReferenceModule/components/MainDashboard';
import ReferenceSearchPage from './ReferenceModule/pages/SearchPage';
import ReferenceAboutPage from './ReferenceModule/pages/AboutPage';
import LegalQAPage from './pages/LegalQAPage';
import SummaryExtractorPage from './pages/SummaryExtractorPage';
import { MAIN_API } from './config/api';

function App() {
  return (
    <Router>
      <Routes>
        {/* About Page as the main entry point */}
        <Route path="/" element={<ReferenceAboutPage />} />
        
        {/* Module Selection Page moved to its own route */}
        <Route path="/modules" element={<ModuleSelectionPage />} />
        
        {/* Core Summary Extraction Module Routes */}
        <Route path="/core" element={<MainDashboard />} />
        <Route path="/core/search" element={<UnifiedSearchPage />} />
        <Route path="/core/ik-search" element={<IKSearchPage />} />
        <Route path="/core/google-search" element={<GoogleSearchPage />} />
        
        {/* Legal QA System Module Route - NEW */}
        <Route path="/legal-qa" element={<LegalQAPage />} />

        {/* Summary Extractor Module Route - NEW */}
        <Route path="/summary-extractor" element={<SummaryExtractorPage />} />
        
        {/* Reference Module Routes */}
        <Route path="/reference" element={<ReferenceMainDashboard />} />
        <Route path="/reference/search" element={<ReferenceSearchPage />} />
        <Route path="/reference/about" element={<ReferenceAboutPage />} />
        
        {/* Redirect legacy routes to new structure */}
        <Route path="/search" element={<Navigate to="/core/search" replace />} />
        <Route path="/ik-search" element={<Navigate to="/core/ik-search" replace />} />
        <Route path="/google-search" element={<Navigate to="/core/google-search" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
