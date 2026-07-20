# Legal Case Analysis System

Comprehensive legal case processing and analysis system with multiple AI-powered modules.

## Quick Start

### 1. Initial Setup

Run the setup script to initialize the environment:

```batch
setup.bat
```

This will:
- Create Python virtual environment
- Install all backend dependencies
- Install frontend dependencies
- Create .env template files

### 2. Configure API Keys

Update the following .env files with your OpenAI API keys:

- `backend\.env`
- `rbackend\.env`
- `Legal_QA\legal-qa-system\backend\.env`
- `Legal_Summary\backend\.env`

### 3. Start All Services

```batch
start_all.bat
```

This starts:
- Main Backend (Port 8000)
- Research Backend (Port 8001)
- Legal QA Backend (Port 8002)
- Summary Backend (Port 8003)
- Document Retrieval Backend (Port 8004)
- Frontend (Port 5173)

Access the application at: http://localhost:5173

### 4. Stop All Services

```batch
stop_all.bat
```

## Utility Scripts

### Check Port Status

```batch
check_ports.bat
```

Shows which ports are currently in use and their process IDs.

## Manual Start (for development)

If you prefer to start services individually:

### Backend Services

```batch
# Activate virtual environment first
venv\Scripts\activate

# Terminal 1 - Main Backend
cd backend
python api.py

# Terminal 2 - Research Backend
cd rbackend
python rbackend.py

# Terminal 3 - Legal QA Backend
cd Legal_QA\legal-qa-system\backend
python app.py

# Terminal 4 - Summary Backend
cd Legal_Summary\backend
python app.py

# Terminal 5 - Document Retrieval Backend
cd indiankanoon-mcp\ui
python app.py
```

### Frontend

```batch
# Terminal 6 - Frontend
cd front-end
npm run dev
```

## Port Reference

| Service | Port | URL |
|---------|------|-----|
| Main Backend | 8000 | http://localhost:8000 |
| Research Backend | 8001 | http://localhost:8001 |
| Legal QA Backend | 8002 | http://localhost:8002 |
| Summary Backend | 8003 | http://localhost:8003 |
| Document Retrieval Backend | 8004 | http://localhost:8004 |
| Frontend | 5173 | http://localhost:5173 |

## Project Structure

