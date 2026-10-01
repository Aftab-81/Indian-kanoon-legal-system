// Centralized API configuration for all backend services

export const API_ENDPOINTS = {
  // Main Backend - Case Processing (Port 8000)
  MAIN_BACKEND: 'http://localhost:8000/api',
  
  // Research Backend - Document Analysis (Port 8001)
  RESEARCH_BACKEND: 'http://localhost:8001/api',
  
  // Legal QA System (Port 8002)
  LEGAL_QA: 'http://localhost:8002/api',
  
  // Summary Extractor (Port 8003)
  SUMMARY: 'http://localhost:8003/api',
  
  // Evaluation Service (Port 8005)
  EVAL: 'http://localhost:8005/api/eval',
};

// Export individual endpoints for convenience
export const MAIN_API = API_ENDPOINTS.MAIN_BACKEND;
export const RESEARCH_API = API_ENDPOINTS.RESEARCH_BACKEND;
export const QA_API = API_ENDPOINTS.LEGAL_QA;
export const SUMMARY_API = API_ENDPOINTS.SUMMARY;
export const EVAL_API = API_ENDPOINTS.EVAL;

// Default export
export default API_ENDPOINTS;
