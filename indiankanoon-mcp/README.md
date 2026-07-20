# Indian Kanoon Judgement Downloader 🏛️

A tool that searches and downloads court judgements from [indiankanoon.org](https://indiankanoon.org) by **year and month**, built using an **MCP (Model Context Protocol) server** for AI integration and a **beautiful web UI** for standalone use.

---

## 📐 Architecture

```
Browser UI (http://localhost:5000)
       │
       │  HTTP + Server-Sent Events
       ▼
  Flask App  ──── ui/app.py  (MCP Client)
       │
       │  imports & calls directly
       ▼
  MCP Server ──── mcp_server/server.py
       │
       │  HTTP requests + BeautifulSoup
       ▼
  indiankanoon.org
       │
       ▼
  📁 D:\indiankanoon-mcp\downloads\{year}\{month}\
```

### What is MCP?

**MCP (Model Context Protocol)** is an open standard by Anthropic that lets AI models (like Claude) call external tools in a structured, safe way.

The **MCP Server** in this project exposes 5 tools:

| Tool | Description |
|------|-------------|
| `list_courts` | Returns all available court types |
| `search_judgements` | Searches for judgements by year/month/court |
| `download_judgement_pdf` | Downloads a single judgement as PDF |
| `batch_download_month` | Downloads all judgements for a month |
| `get_judgement_text` | Returns full text of a judgement |

---

## 🚀 Quick Start

### Step 1 — Install wkhtmltopdf (for PDF output)

Download and install from: https://wkhtmltopdf.org/downloads.html

> Choose the **Windows 64-bit installer**. During installation, make sure it's added to your PATH.

This is optional — without it, judgements save as HTML files instead of PDFs.

---

### Step 2 — Run Setup

Double-click **`setup.bat`** or run in terminal:

```bat
cd D:\indiankanoon-mcp
setup.bat
```

This installs all Python packages:
- `fastmcp` — MCP server framework
- `flask` + `flask-cors` — Web UI backend
- `requests` + `beautifulsoup4` + `lxml` — Web scraping
- `pdfkit` — HTML to PDF conversion

---

### Step 3 — Start the App

Double-click **`run.bat`** or run:

```bat
cd D:\indiankanoon-mcp
run.bat
```

Then open your browser at: **http://localhost:5000**

---

## 🖥️ Using the UI

1. **Select Year** — e.g. 2025
2. **Select Month** — e.g. January
3. **Select Court** — e.g. Supreme Court (or All Courts)
4. **Set Max Judgements** — drag slider (default: 50, max: 500)
5. **Choose Format** — PDF (recommended) or HTML
6. Click **Start Download** and watch the live progress!

Downloaded files are saved to:
```
D:\indiankanoon-mcp\downloads\{year}\{month}\
```

Each file is named: `{doc_id}_{case_title}.pdf`

---

## 🤖 Using MCP with AI (Antigravity IDE)

To let the AI use the MCP tools directly in chat, register the server in your IDE config.

### Register the MCP server

Create or edit: `C:\Users\A\.gemini\config\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "indiankanoon": {
      "command": "python",
      "args": ["D:\\indiankanoon-mcp\\mcp_server\\server.py"]
    }
  }
}
```

Restart the IDE. Then you can ask in the AI chat:

> *"Download all Supreme Court judgements from January 2025 and save them to D:\indiankanoon-mcp\downloads"*

The AI will call the MCP tools automatically!

---

## 📁 Project Structure

```
D:\indiankanoon-mcp\
│
├── mcp_server\
│   ├── server.py           ← MCP Server (5 tools)
│   ├── scraper.py          ← Web scraping + PDF logic
│   └── requirements.txt
│
├── ui\
│   ├── app.py              ← Flask backend (MCP Client)
│   ├── templates\
│   │   └── index.html      ← Web UI
│   └── static\
│       ├── style.css       ← Dark glassmorphism theme
│       └── app.js          ← Real-time progress via SSE
│
├── downloads\              ← All PDFs saved here
│   └── 2025\
│       └── January\
│           ├── 117249167_Independent Sugar...pdf
│           └── ...
│
├── setup.bat               ← Install dependencies
├── run.bat                 ← Start web UI
├── run_mcp_server.bat      ← Start MCP server standalone
└── README.md
```

---

## ⚠️ Important Notes

### Rate Limiting
The scraper waits **1.2 seconds between requests** by default to avoid being blocked by the site. Reducing this is not recommended.

### Scale Warning
Some months have **100,000+ judgements** across all courts. Use the **Max Judgements** slider to limit downloads. Start with 50 to test.

### Legal / Ethical Usage
- Only download judgements for **personal research or legal work**
- Do not redistribute scraped content commercially
- Respect indiankanoon.org's [Terms of Service](https://indiankanoon.org/members/terms/)
- The site offers an **official API** at [api.indiankanoon.org](https://api.indiankanoon.org) for production use

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError` | Run `setup.bat` again |
| PDFs not generating | Install `wkhtmltopdf` and ensure it's in PATH |
| No results found | Try a different court or date range |
| Site blocked / CAPTCHA | Increase delay in `scraper.py` → `delay_seconds` |
| Port 5000 already in use | Edit `app.py` last line, change `port=5000` to `port=5001` |

---

## 📦 Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| fastmcp | ≥2.0 | MCP server framework |
| flask | ≥3.0 | Web UI server |
| flask-cors | ≥4.0 | Cross-origin support |
| requests | ≥2.31 | HTTP requests |
| beautifulsoup4 | ≥4.12 | HTML parsing |
| lxml | ≥4.9 | Fast XML/HTML parser |
| pdfkit | ≥1.0 | HTML → PDF via wkhtmltopdf |

---

*Built with ❤️ using FastMCP + Flask + Python*
