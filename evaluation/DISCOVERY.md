# Phase 0 – Discovery Notes

_Generated autonomously on 2026-10-01 by feature/ragas-evaluation_

---

## 1. Repo Map

| Layer | Entry File | Port | Framework |
|---|---|---|---|
| Frontend | `front-end/src/App.jsx` | 5173 | React 19 + Vite + Tailwind v4 |
| Main Backend | `backend/api.py` | 8000 | Flask |
| Research Backend | `rbackend/rbackend.py` | 8001 | FastAPI |
| Legal QA Backend | `Legal_QA/legal-qa-system/backend/app.py` | 8002 | Flask |
| Summary Backend | `Legal_Summary/backend/app.py` | 8003 | FastAPI |
| Kanoon Downloader | `indiankanoon-mcp/ui/app.py` | 8004 | Flask (MCP client) |
| Evaluation API | `evaluation/api.py` | **8005** | FastAPI (NEW) |

### Config / Key loading

All backends use `python-dotenv` (`load_dotenv()`) to read `.env` files.  
Keys used:
- `OPENAI_API_KEY` – all LLM-calling backends
- `SERPAPI_KEY` / `SERPAPI_API_KEY` – 8000, 8001, 8002
- `INDIA_KANNON_API_KEY` – 8000

### Embedding models
- **8002 Legal QA**: `sentence-transformers/all-mpnet-base-v2` (768-dim, local)
- **8001 Research**: `text-embedding-3-small` via OpenAI API (1536-dim)

---

## 2. Endpoints Used by Evaluation

### 8000 – Main Backend (Case Comprehension)
| Route | Method | Body | Response shape |
|---|---|---|---|
| `/api/upload` | POST | multipart `file=<pdf>` | `{success, cases:[{title,file,status}]}` |
| `/api/case/<file>` | GET | – | Full JSON with 8 fields + Confidence map |
| `/api/cases` | GET | – | `[{id,title,file}]` |

### 8001 – Research Backend
| Route | Method | Body | Response |
|---|---|---|---|
| `/api/analyze/legal` | POST | multipart `file=<pdf\|docx>` | `{status,analysis:{case_laws,statutes,...},file_hash}` |
| `/api/search/query` | POST | form `query=<str>` | `{status,results:[{source,title,snippet,url,confidence,analysis}]}` |
| `/api/history` | GET | – | `{history:[...]}` |
| `/api/document/<hash>` | GET | – | full doc record |

### 8002 – Legal QA Backend
| Route | Method | Body | Response |
|---|---|---|---|
| `/api/upload-pdf` | POST | multipart `file=<pdf>`, form `case_name=<str>` | `{status,case_id,chunks_created}` |
| `/api/ask` | POST | JSON `{question,source,case_id?,language}` | `{conclusion,legal_reasoning,retrieved_cases,uncertainty_score,...}` |
| `/api/stats` | GET | – | `{total_questions,total_answers,...}` |
| `/api/history` | GET | – | list of past Q&A |

**Note on `/api/ask` response**: `retrieved_cases` is an array of `{chunk,case_id,case_name,similarity}` — these become `retrieved_contexts` in Ragas.  `conclusion + legal_reasoning` become `response`.

### 8003 – Summary Backend
| Route | Method | Body | Response |
|---|---|---|---|
| `/api/summarize` | POST | multipart `pdf_file`, form `preferences=<JSON>` | `{metadata:{case_title,court_name,...,summary,sections_invoked},confidence:{...},detailed_available}` |
| `/api/summarize/detailed` | POST | multipart `pdf_file`, form `output_language`, `focus_areas=<JSON>` | full forensic object |
| `/api/history` | GET | – | `{history:[{id,case_title,...}]}` |

---

## 3. Locally Available Judgments

### In `backend/Results/` (11 processed JSON summaries)
These have the 8 canonical fields already extracted — ideal for comprehension evaluation.

### In `Legal_QA/legal-qa-system/backend/uploads/` (25 PDFs)
Full PDF text available; suitable for QA and summary evaluation.

### In `indiankanoon-mcp/downloads/` (25+ PDFs)
Downloaded from Indian Kanoon; supplementary corpus.

**Total unique PDFs available: 25 in uploads** – well above the minimum 8 required.
Chosen 10 representative PDFs for the evaluation corpus (mix of criminal, civil, labour, income tax):

1. `1189512_U.P. State Sugar Corporation Ltd...` (labour law)
2. `1608496_Cit vs S. Kamaljeet Singh...` (income tax)
3. `1687189_District And Sessions Judge vs Ratnesh Kumar...` (service law)
4. `1822728_Saraya Industries Ltd. vs State Of U.P...` (commercial)
5. `1898332_Vijendra Sharma...vs State Of U.P...` (criminal)
6. `1913281_Ex-Naik Upendra Kumar Tomar vs Union Of India...` (armed forces)
7. `103394330_Reserved On_...vs State Of H.P...` (criminal)
8. `185995005_Mohammed Siddique vs National Insurance...` (motor accidents)
9. `187771162_Shilpa Mittal vs State Of NCT Of Delhi...` (criminal juvenile)
10. `92625542_Directorate Of Revenue Intelligence vs Raj Kumar Arora...` (NDPS)

---

## 4. Frontend Chart Library

**Not present.** `package.json` has no chart library. Will install `recharts` during Phase 4.

---

## 5. Ragas Version Decision

Installing `ragas==0.2.6` (latest stable as of evaluation). API uses:
- `ragas.metrics` classes directly
- `EvaluationDataset` + `evaluate()` function

Metric mapping (0.2.x):
| Spec name | Actual class (0.2.x) |
|---|---|
| Faithfulness | `ragas.metrics.Faithfulness` |
| ResponseRelevancy | `ragas.metrics.ResponseRelevancy` |
| LLMContextPrecisionWithReference | `ragas.metrics.LLMContextPrecisionWithReference` |
| ContextRecall | `ragas.metrics.ContextRecall` |
| FactualCorrectness | `ragas.metrics.FactualCorrectness` |
| AspectCritic | `ragas.metrics.AspectCritic` |
| SummarizationScore | No direct equivalent in 0.2.x → **substituted with Faithfulness + ResponseRelevancy** (recorded in notes) |
| SemanticSimilarity | `ragas.metrics.SemanticSimilarity` |
| ContextEntityRecall | `ragas.metrics.ContextEntityRecall` |

---

## 6. Judge Model

`gpt-4o-mini` — the same model already used by 8002 Legal QA backend. Budget guard: 20 samples/module, max_workers=4.

---

## 7. Decisions Made

1. **recharts** added to frontend (no chart lib existed).
2. **SummarizationScore** does not exist in Ragas 0.2.6 → replaced with `Faithfulness + ResponseRelevancy` pair. Noted in results JSON `notes` field.
3. **Port 8005** used for Evaluation API (no conflict with existing services).
4. Evaluation results are static JSON files — the UI only reads them; no LLM call happens during a page load.
5. **Dataset generation** uses existing extracted JSON from `backend/Results/` and PDFs from uploads to avoid re-running heavy extraction where possible.
