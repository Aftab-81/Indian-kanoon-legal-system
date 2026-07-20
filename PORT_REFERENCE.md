# Port Reference Guide

Quick reference for all services in the Legal Case Analysis System.

## Backend Services

| Service | Port | Start Command | API Docs |
|---------|------|---------------|----------|
| **Main Backend** | 8000 | `python backend/api.py` | http://localhost:8000 |
| **Research Backend** | 8001 | `python rbackend/rbackend.py` | http://localhost:8001/docs |
| **Legal QA Backend** | 8002 | `python Legal_QA/legal-qa-system/backend/app.py` | http://localhost:8002 |
| **Summary Backend** | 8003 | `python Legal_Summary/backend/app.py` | http://localhost:8003/docs |

## Frontend Services

| Service | Port | Start Command | URL |
|---------|------|---------------|-----|
| **Main Frontend** | 5173 | `npm start` (in front-end folder) | http://localhost:5173 |
| **Summary Frontend** | 8501 | `streamlit run app.py` (in Legal_Summary/frontend) | http://localhost:8501 |

## API Endpoints by Service

### Main Backend (Port 8000)
- `/api/upload` - Upload PDF for processing
- `/api/cases` - Get all processed cases
- `/api/case/<case_file>` - Get specific case details
- `/api/google-search` - Search Google with SerpAPI
- `/api/ik-search` - Search Indian Kanoon

### Research Backend (Port 8001)
- `/api/analyze/legal` - Analyze legal document
- `/api/search/query` - Search legal information
- `/api/history` - Get document history
- `/api/document/<file_hash>` - Get document details
- `/api/remarks` - Save/get remarks

### Legal QA Backend (Port 8002)
- `/api/ask` - Ask legal question
- `/api/upload-pdf` - Upload case PDF
- `/api/history` - Get question history
- `/api/approve-answer` - Approve/reject answer
- `/api/stats` - Get system statistics

### Summary Backend (Port 8003)
- `/api/summarize` - Generate case summary
- `/api/summarize/detailed` - Generate detailed analysis
- `/api/history` - Get summary history
- `/api/history/<id>` - Get specific summary
- `/api/history/<id>` [DELETE] - Delete summary

## Starting All Services

### Option 1: Manual Start (Recommended for Development)

```bash
# Terminal 1 - Main Backend
cd d:\Backup\Jugement_fixed\backend
python api.py

# Terminal 2 - Research Backend
cd d:\Backup\Jugement_fixed\rbackend
python rbackend.py

# Terminal 3 - Legal QA Backend
cd d:\Backup\Jugement_fixed\Legal_QA\legal-qa-system\backend
python app.py

# Terminal 4 - Summary Backend
cd d:\Backup\Jugement_fixed\Legal_Summary\backend
python app.py

# Terminal 5 - Main Frontend
cd d:\Backup\Jugement_fixed\front-end
npm start
```

### Option 2: Batch Script (Windows)

Create `start_all.bat`:

```batch
start cmd /k "cd backend && python api.py"
start cmd /k "cd rbackend && python rbackend.py"
start cmd /k "cd Legal_QA\legal-qa-system\backend && python app.py"
start cmd /k "cd Legal_Summary\backend && python app.py"
timeout /t 5
start cmd /k "cd front-end && npm start"
```

## Troubleshooting

### Port Already in Use

If you get "port already in use" error:

**Windows:**
```bash
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

**Linux/Mac:**
```bash
lsof -ti:8000 | xargs kill -9
```

### API Connection Errors

1. Check if backend service is running on correct port
2. Verify CORS settings in backend
3. Check browser console for specific error messages
4. Ensure all environment variables are set (.env files)

## Common Connection Issues

### Frontend showing "Network Error" or "ERR_CONNECTION_REFUSED"

**Problem:** Frontend trying to connect to wrong port (often 5000 instead of 8000)

**Solution:**
1. Check the API base URL in the component that's failing
2. Verify backend is running: `http://localhost:8000/api/cases`
3. Update the API URL to correct port:
   - Main Backend: `http://localhost:8000/api`
   - Research: `http://localhost:8001/api`
   - Legal QA: `http://localhost:8002/api`
   - Summary: `http://localhost:8003/api`

**Quick Fix:**
```bash
# Search for wrong port references in frontend
cd front-end\src
findstr /s /i "localhost:5000" *.jsx *.js

# Should use 8000 for main backend instead
```

## Environment Variables

Each backend requires these environment variables:

```env
OPENAI_API_KEY=your_key_here
SERPAPI_KEY=your_key_here  # Optional, for Google search
```

Place `.env` file in each backend directory.

## Health Check

Test if all services are running:

```bash
# Main Backend
curl http://localhost:8000/api/cases

# Research Backend
curl http://localhost:8001/api/history

# Legal QA Backend
curl http://localhost:8002/api/stats

# Summary Backend
curl http://localhost:8003/api/history
```

All should return JSON responses without errors.
