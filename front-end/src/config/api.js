// Centralized API configuration for all backend services

export const API_ENDPOINTS = {
  // Main Backend - Case Processing (Port 8000)
  MAIN_BACKEND: import.meta.env.VITE_API_URL_MAIN || 'http://localhost:8000/api',
  
  // Research Backend - Document Analysis (Port 8001)
  RESEARCH_BACKEND: import.meta.env.VITE_API_URL_RESEARCH || 'http://localhost:8001/api',
  
  // Legal QA System (Port 8002)
  LEGAL_QA: import.meta.env.VITE_API_URL_QA || 'http://localhost:8002/api',
  
  // Summary Extractor (Port 8003)
  SUMMARY: import.meta.env.VITE_API_URL_SUMMARY || 'http://localhost:8003/api',
  
  // Evaluation Service (Port 8005)
  EVAL: import.meta.env.VITE_API_URL_EVAL || 'http://localhost:8005/api/eval',
  
  // Document Retrieval UI & API (Port 8004)
  DOCUMENT_RETRIEVAL: import.meta.env.VITE_API_URL_DOC_RETRIEVAL || 'http://localhost:8004',
};

// Export individual endpoints for convenience
export const MAIN_API = API_ENDPOINTS.MAIN_BACKEND;
export const RESEARCH_API = API_ENDPOINTS.RESEARCH_BACKEND;
export const QA_API = API_ENDPOINTS.LEGAL_QA;
export const SUMMARY_API = API_ENDPOINTS.SUMMARY;
export const EVAL_API = API_ENDPOINTS.EVAL;
export const DOC_RETRIEVAL_API = API_ENDPOINTS.DOCUMENT_RETRIEVAL;

// Default export
export default API_ENDPOINTS;
