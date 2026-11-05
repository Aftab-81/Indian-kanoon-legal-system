"""
evaluation/store_reader.py
─────────────────────────
Cross-module reader for existing judicial data stores:
  1. Comprehension  : backend/Results/*_summary.json (11 cases, 8-field extractions + confidence)
  2. Legal QA       : Legal_QA/legal-qa-system/backend/qa_store.json (75 Q&A pairs + uncertainty scores)
  3. Legal Summary  : Legal_Summary/backend/history/*.json (15 case summaries)
  4. Research       : rbackend/vector_metadata.json (8 indexed judgments with principles & statutes)
  + Live Events     : evaluation/events/*.jsonl (real-time stream of incoming interactions)

Enables real-time, authentic Ragas evaluation on actual system data without
forcing the user to artificially generate dummy clicks or seed data.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from ragas.dataset_schema import SingleTurnSample

# Paths
EVAL_DIR = Path(__file__).resolve().parent
ROOT = EVAL_DIR.parent
sys.path.insert(0, str(EVAL_DIR))

from event_logger import read_events, event_counts
import pdfplumber

def extract_pdf_text_for_store(pdf_path: str, max_chars: int = 30000) -> str:
    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages = []
            total = 0
            for page in pdf.pages:
                t = page.extract_text() or ""
                pages.append(t)
                total += len(t)
                if total >= max_chars:
                    break
            return "\n".join(pages)[:max_chars]
    except Exception:
        return ""


def _clean_text(t: str | None) -> str:
    if not t:
        return ""
    # strip basic html tags if present
    cleaned = re.sub(r"<[^>]+>", "", str(t))
    return cleaned.strip()


def _fuzzy_match(title1: str, title2: str) -> bool:
    """Return True if title1 and title2 share significant case keywords."""
    w1 = set(re.findall(r"\b[a-zA-Z]{4,}\b", title1.lower()))
    w2 = set(re.findall(r"\b[a-zA-Z]{4,}\b", title2.lower()))
    stopwords = {"state", "union", "india", "court", "versus", "order", "january", "february", "march", "april", "special", "appeal", "equivalent", "citations", "alongwith", "civil"}
    w1 -= stopwords
    w2 -= stopwords
    if not w1 or not w2:
        return False
    overlap = w1.intersection(w2)
    return len(overlap) >= 2


class StoreReader:
    def __init__(self):
        self.comp_dir = ROOT / "backend" / "Results"
        self.qa_file = ROOT / "Legal_QA" / "legal-qa-system" / "backend" / "qa_store.json"
        self.sum_dir = ROOT / "Legal_Summary" / "backend" / "history"
        self.res_file = ROOT / "rbackend" / "query_cache.json"
        self.uploads_dir = ROOT / "Legal_QA" / "legal-qa-system" / "backend" / "uploads"

        # In-memory caches
        self._comprehensions: list[dict] = []
        self._qa_data: dict[str, Any] = {}
        self._summaries: list[dict] = []
        self._research_docs: dict[str, Any] = {}
        self._load_all()

    def _load_all(self):
        # 1. Comprehensions
        self._comprehensions = []
        if self.comp_dir.exists():
            for p in self.comp_dir.glob("*_summary.json"):
                try:
                    with open(p, encoding="utf-8") as f:
                        d = json.load(f)
                    d["_file"] = p.name
                    d["_title_clean"] = _clean_text(d.get("Case Title & Citation", ""))
                    self._comprehensions.append(d)
                except Exception as e:
                    print(f"[StoreReader] error loading {p.name}: {e}")

        # 2. Legal QA
        self._qa_data = {"questions": [], "answers": []}
        if self.qa_file.exists():
            try:
                with open(self.qa_file, encoding="utf-8") as f:
                    self._qa_data = json.load(f)
            except Exception as e:
                print(f"[StoreReader] error loading qa_store: {e}")

        # 3. Summaries
        self._summaries = []
        if self.sum_dir.exists():
            for p in self.sum_dir.glob("*.json"):
                try:
                    with open(p, encoding="utf-8") as f:
                        d = json.load(f)
                    d["_file"] = p.name
                    self._summaries.append(d)
                except Exception as e:
                    print(f"[StoreReader] error loading summary {p.name}: {e}")

        # 4. Research
        self._research_docs = {}
        if self.res_file.exists():
            try:
                with open(self.res_file, encoding="utf-8") as f:
                    self._research_docs = json.load(f)
            except Exception as e:
                print(f"[StoreReader] error loading research metadata: {e}")

    def get_stats(self) -> dict[str, Any]:
        """Return cross-module statistics and counts."""
        live_counts = event_counts()
        q_count = len(self._qa_data.get("questions", []))
        ans_count = len(self._qa_data.get("answers", []))
        comp_count = len(self._comprehensions)
        sum_count = len(self._summaries)
        res_count = len(self._research_docs)

        total_records = comp_count + ans_count + sum_count + res_count + sum(live_counts.values())

        return {
            "counts": {
                "comprehension": comp_count,
                "legal_qa": ans_count,
                "summary": sum_count,
                "research": res_count,
            },
            "live_events": live_counts,
            "total_records": total_records,
            "ready": total_records > 0,
        }

    # ── Sample builders for each module ──────────────────────────────────────────

    def get_comprehension_samples(self, max_samples: int = 15) -> list[SingleTurnSample]:
        """
        Build samples from backend/Results/*_summary.json.
        Evaluates extraction faithfulness and relevancy of core judgment fields:
          - Final Decision (Ratio Decidendi)
          - Court's Analysis / Reasoning
          - Facts of the Case & Issues
        """
        samples: list[SingleTurnSample] = []

        for comp in self._comprehensions:
            title = comp.get("_title_clean") or "Court Judgment"
            facts = _clean_text(comp.get("Facts of the Case"))
            issues = _clean_text(comp.get("Issues Framed"))
            arguments = _clean_text(comp.get("Arguments by Parties"))
            reasoning = _clean_text(comp.get("Court's Analysis / Reasoning"))
            decision = _clean_text(comp.get("Final Decision (Ratio Decidendi)"))
            confidence = comp.get("Confidence", {})

            retrieved_chunks_raw = comp.get("retrieved_chunks", [])
            context_chunks = []
            for c in retrieved_chunks_raw:
                if isinstance(c, dict) and c.get("text"):
                    text = c.get("text", "")
                    context_chunks.extend([text[i: i + 4000] for i in range(0, min(len(text), 16000), 4000)])

            if not context_chunks:
                context_chunks = [f"Precedent Case: {title} (Actual chunk text missing from historical logs)"]

            if decision and len(decision) > 30:
                samples.append(SingleTurnSample(
                    user_input=f"What is the final decision and ratio decidendi in {title}?",
                    response=decision,
                    retrieved_contexts=context_chunks,
                    reference_contexts=context_chunks,
                ))

            if reasoning and len(reasoning) > 40:
                samples.append(SingleTurnSample(
                    user_input=f"Analyze the court's reasoning and statutory interpretation for the issues framed in {title}.",
                    response=reasoning,
                    retrieved_contexts=context_chunks,
                    reference_contexts=context_chunks,
                ))

            if facts and issues and len(facts) > 40:
                samples.append(SingleTurnSample(
                    user_input=f"State the material facts and legal issues framed in {title}.",
                    response=f"Facts: {facts}\n\nIssues Framed: {issues}",
                    retrieved_contexts=context_chunks,
                    reference_contexts=context_chunks,
                ))

            if len(samples) >= max_samples:
                break

        # Also merge any live event samples if available
        live_events = read_events("comprehension", last_n=5)
        for ev in live_events:
            inp = ev.get("user_input", "").strip()
            resp = ev.get("response", "").strip()
            ctxs = [c for c in ev.get("contexts", []) if c.strip()]
            if inp and resp:
                samples.append(SingleTurnSample(
                    user_input=inp,
                    response=resp,
                    retrieved_contexts=ctxs or ["Comprehension case document."],
                    reference_contexts=ctxs or ["Comprehension case document."],
                ))

        return samples[:max_samples]

    def get_legal_qa_samples(self, max_samples: int = 15) -> list[SingleTurnSample]:
        """
        Build samples from Legal_QA/legal-qa-system/backend/qa_store.json.
        Pairs real user questions with answers and resolved cross-module judgment contexts.
        """
        samples: list[SingleTurnSample] = []
        q_map = {q["question_id"]: q["question_text"] for q in self._qa_data.get("questions", [])}
        
        uploads_by_stem = {}
        if self.uploads_dir.exists():
            for pdf in self.uploads_dir.glob("*.pdf"):
                uploads_by_stem[pdf.stem.lower()] = pdf

        for ans in self._qa_data.get("answers", []):
            qid = ans.get("question_id")
            q_text = q_map.get(qid, "").strip()
            conclusion = _clean_text(ans.get("conclusion", ""))
            reasoning = _clean_text(ans.get("legal_reasoning", ""))
            if not q_text or not conclusion:
                continue

            resp = conclusion
            if reasoning:
                resp += f"\n\nLegal Reasoning: {reasoning}"

            contexts = []
            chunks = ans.get("retrieved_chunks", [])
            for c in chunks:
                chunk_text = c.get("chunk", "")
                if chunk_text:
                    contexts.append(chunk_text)

            if not contexts:
                contexts.append("Actual chunk text missing from historical logs")

            samples.append(SingleTurnSample(
                user_input=q_text,
                response=resp,
                retrieved_contexts=contexts,
                reference_contexts=contexts,
            ))

            if len(samples) >= max_samples:
                break

        # Also merge live event samples
        live_events = read_events("legal_qa", last_n=5)
        for ev in live_events:
            inp = ev.get("user_input", "").strip()
            resp = ev.get("response", "").strip()
            ctxs = [c for c in ev.get("contexts", []) if c.strip()]
            if inp and resp:
                samples.append(SingleTurnSample(
                    user_input=inp,
                    response=resp,
                    retrieved_contexts=ctxs or ["Legal precedent repository."],
                    reference_contexts=ctxs or ["Legal precedent repository."],
                ))

        return samples[:max_samples]

    def get_summary_samples(self, max_samples: int = 15) -> list[SingleTurnSample]:
        """
        Build samples from Legal_Summary/backend/history/*.json.
        Evaluates summary faithfulness and relevancy against case metadata and cross-referenced judgments.
        """
        samples: list[SingleTurnSample] = []

        for s in self._summaries:
            meta = s.get("metadata", {})
            title = meta.get("case_title", "")
            court = meta.get("court_name", "")
            case_no = meta.get("case_number", "")
            summary = _clean_text(meta.get("summary", ""))
            sections = meta.get("sections_invoked", [])
            judges = meta.get("judge_names", [])

            if not title or not summary:
                continue

            retrieved_chunks_raw = s.get("retrieved_chunks", [])
            context_chunks = []
            for c in retrieved_chunks_raw:
                if isinstance(c, dict) and c.get("text"):
                    text = c.get("text", "")
                    context_chunks.extend([text[i: i + 4000] for i in range(0, min(len(text), 16000), 4000)])

            if not context_chunks:
                context_chunks = [f"Precedent Case: {title} (Actual chunk text missing from historical logs)"]

            samples.append(SingleTurnSample(
                user_input=f"Summarize the judicial ruling and ratio for {title} delivered by {court}.",
                response=summary,
                retrieved_contexts=context_chunks,
                reference_contexts=context_chunks,
            ))

            if len(samples) >= max_samples:
                break

        # Also merge live event samples
        live_events = read_events("summary", last_n=5)
        for ev in live_events:
            inp = ev.get("user_input", "").strip()
            resp = ev.get("response", "").strip()
            ctxs = [c for c in ev.get("contexts", []) if c.strip()]
            if inp and resp:
                samples.append(SingleTurnSample(
                    user_input=inp,
                    response=resp,
                    retrieved_contexts=ctxs or ["Judicial judgment summary context."],
                    reference_contexts=ctxs or ["Judicial judgment summary context."],
                ))

        return samples[:max_samples]

    def get_research_samples(self, max_samples: int = 15) -> list[SingleTurnSample]:
        """
        Build samples from rbackend/query_cache.json.
        Evaluates legal research retrieval for principles, case laws, and statutory provisions.
        """
        samples: list[SingleTurnSample] = []
        for query, cache_entry in self._research_docs.items():
            results_data = cache_entry.get("results", {})
            if isinstance(results_data, str):
                try:
                    results_data = json.loads(results_data)
                except:
                    results_data = {}
            
            # The actual results array
            results = results_data.get("results", [])
            
            if not results:
                continue

            # Ragas expects context chunks. We provide exactly what was retrieved.
            context_chunks = []
            for r in results:
                title = r.get("title", "")
                snippet = r.get("snippet", "")
                analysis = r.get("analysis", {})
                
                chunk = f"Title: {title}\nSnippet: {snippet}"
                if analysis:
                    chunk += f"\nAnalysis: {json.dumps(analysis)}"
                context_chunks.append(chunk)

            if not context_chunks:
                context_chunks = ["(Actual chunk text missing from historical logs)"]

            # Create a response summary based on the top results
            top_result = results[0]
            resp = f"Top Result: {top_result.get('title', '')}\n{top_result.get('snippet', '')}"

            samples.append(SingleTurnSample(
                user_input=query,
                response=resp,
                retrieved_contexts=context_chunks,
                reference_contexts=context_chunks,
            ))

            if len(samples) >= max_samples:
                break

        # Also merge live event samples
        live_events = read_events("research", last_n=5)
        for ev in live_events:
            inp = ev.get("user_input", "").strip()
            resp = ev.get("response", "").strip()
            ctxs = [c for c in ev.get("contexts", []) if c.strip()]
            if inp and resp:
                samples.append(SingleTurnSample(
                    user_input=inp,
                    response=resp,
                    retrieved_contexts=ctxs or ["Hybrid research search context."],
                    reference_contexts=ctxs or ["Hybrid research search context."],
                ))

        return samples[:max_samples]

    def get_samples_for_module(self, module: str, max_samples: int = 15) -> list[SingleTurnSample]:
        if module == "comprehension":
            return self.get_comprehension_samples(max_samples)
        elif module == "legal_qa":
            return self.get_legal_qa_samples(max_samples)
        elif module == "summary":
            return self.get_summary_samples(max_samples)
        elif module == "research":
            return self.get_research_samples(max_samples)
        return []


# Global singleton instance
reader = StoreReader()
