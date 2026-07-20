# Legal Case Analysis Frontend

React-based frontend for the Legal Case Analysis System.

## Features

- **Case Processing Module** (Port 8000)
  - Upload and process legal case PDFs
  - Extract case details and summaries
  - View and manage processed cases

- **Case Research Module** (Port 8001)
  - Search legal documents and webpages
  - Indian Kanoon and Google search integration
  - Analyze legal content with AI

- **Legal QA System** (Port 8002)
  - Ask legal questions
  - RAG-based answers from uploaded cases
  - External legal reasoning fallback

- **Summary Extractor** (Port 8003)
  - Generate case summaries
  - Detailed legal analysis
  - History of generated summaries

## Backend Services

| Service | Port | Purpose |
|---------|------|---------|
| Case Processing | 8000 | PDF upload and case extraction |
| Research Backend | 8001 | Document analysis and web search |
| Legal QA | 8002 | Question answering system |
| Summary Extractor | 8003 | Case summarization |

## Setup

### Install Dependencies

```bash
npm install
```

### Configure Backend URLs

All API endpoints are configured to use the correct ports:
- Case Processing: `http://localhost:8000/api`
- Research Backend: `http://localhost:8001/api`
- Legal QA: `http://localhost:8002/api`
- Summary Extractor: `http://localhost:8003/api`

### Run Development Server

```bash
npm start
```

The frontend will run on `http://localhost:5173`

## Usage

1. Start all backend services first (ports 8000-8003)
2. Start the frontend (`npm start`)
3. Access the application at `http://localhost:5173`
4. Navigate between modules using the dashboard
