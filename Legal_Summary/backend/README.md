# Case Summarization Backend

AI-powered legal case summarization system using OpenAI GPT.

## Features

- PDF upload and text extraction
- Configurable summary length (short/medium/detailed)
- Focus area selection (facts, arguments, evidence, legal reasoning, precedents)
- Comprehensive detailed analysis with:
  - Case metadata extraction
  - Timeline and important dates
  - Charges and legal sections
  - Evidence and witness analysis
  - Risk flags and contradictions
  - Entity extraction (accused, victims, witnesses, locations)
  - One-page judge summary

## Setup

### 1. Install Dependencies

```bash
cd d:\Projects\Judge_Project\Backend
pip install -r requirements.txt
```

### 2. Configure OpenAI API

Create `.env` file:

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:

```
OPENAI_API_KEY=sk-your-actual-api-key-here
OPENAI_MODEL=gpt-4-turbo-preview
```

### 3. Start Server

```bash
python app.py
```

Server runs at: `http://localhost:8003`

API docs: `http://localhost:8003/docs`

## Testing

### Run Demo Script

```bash
# Place a legal case PDF as sample_case.pdf in Backend folder
python test_demo.py
```

### Manual API Testing

**Short Summary:**
```bash
curl -X POST http://localhost:8003/api/summarize \
  -F "pdf_file=@case.pdf" \
  -F 'preferences={"summary_length":"short","focus_area":["facts"]}'
```

**Medium Summary with Focus:**
```bash
curl -X POST http://localhost:8003/api/summarize \
  -F "pdf_file=@case.pdf" \
  -F 'preferences={"summary_length":"medium","focus_area":["arguments","legal reasoning"]}'
```

**Comprehensive Detailed Analysis:**
```bash
curl -X POST http://localhost:8003/api/summarize/detailed \
  -F "pdf_file=@case.pdf"
```

## Response Examples

### Summary Response (`/summarize`)

```json
{
  "metadata": {
    "case_title": "State of Maharashtra vs Accused X",
    "court_name": "High Court of Bombay",
    "case_number": "Criminal Appeal No. 122/2023",
    "judge_names": ["Justice A", "Justice B"],
    "date_of_judgement": "2024-02-12",
    "jurisdiction": "India",
    "summary": "Brief summary based on length preference...",
    "sections_invoked": ["IPC 302", "CrPC 161"]
  },
  "detailed_available": true
}
```

### Detailed Response (`/summarize/detailed`)

Full structured analysis including facts, arguments, evidence, legal reasoning, risk flags, and entity extraction.

## Project Structure

```
Backend/
├── app.py                 # FastAPI application entry
├── config.py              # Configuration and environment variables
├── schemas.py             # Pydantic models
├── services.py            # Core business logic and OpenAI integration
├── test_demo.py           # Demo testing script
├── requirements.txt       # Python dependencies
├── .env.example           # Environment template
├── routes/
│   ├── __init__.py
│   └── cases.py          # API endpoints
└── utils/
    ├── __init__.py
    └── pdf_extractor.py  # PDF text extraction
```

## Notes

- PDF text extraction works best with text-based PDFs (not scanned images)
- OpenAI API costs apply based on token usage
- GPT-4 Turbo recommended for better legal document analysis
- Context window limited to 10K-15K characters per request
