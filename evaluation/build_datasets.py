"""
evaluation/build_datasets.py
────────────────────────────
Phase 2: dataset generation for all four evaluation modules.

Run:
    python evaluation/build_datasets.py [--module all|legal_qa|research|summary|comprehension]

Generates evaluation/datasets/<module>.json from local PDFs + existing
extracted results, then calls the live backends to get system responses.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import time
import hashlib
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
import pdfplumber
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

# ── path setup ───────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (
    OPENAI_API_KEY, JUDGE_MODEL, EMBED_MODEL,
    BACKEND_MAIN, BACKEND_RESEARCH, BACKEND_QA, BACKEND_SUMMARY,
    SAMPLE_LIMIT, MAX_WORKERS, HTTP_TIMEOUT,
    CORPUS_UPLOADS, CORPUS_RESULTS, SAMPLE_PDFS,
    DATASET_DIR, RAGAS_VERSION,
)

from openai import OpenAI

client = OpenAI(api_key=OPENAI_API_KEY)

RUN_TIMESTAMP = datetime.utcnow().isoformat() + "Z"
REFERENCE_TYPE = "auto_generated"


# ─────────────────────────────────────────────
# Utility helpers
# ─────────────────────────────────────────────

def extract_pdf_text(pdf_path: str, max_chars: int = 30_000) -> str:
    """Extract plain text from a PDF, capped at max_chars."""
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
    except Exception as e:
        print(f"  [WARN] pdfplumber failed for {pdf_path}: {e}")
        return ""


def llm(prompt: str, system: str = "You are a legal document expert.", temperature: float = 0.2) -> str:
    """Call OpenAI; return text. Raises on failure."""
    response = client.chat.completions.create(
        model=JUDGE_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        max_tokens=1500,
    )
    return response.choices[0].message.content.strip()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def post_with_retry(url: str, **kwargs):
    return requests.post(url, timeout=HTTP_TIMEOUT, **kwargs)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def get_with_retry(url: str, **kwargs):
    return requests.get(url, timeout=HTTP_TIMEOUT, **kwargs)


def _check_backend(url: str, name: str):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        print(f"  ✅ {name} is reachable")
    except Exception as e:
        print(f"  ❌ {name} at {url} is NOT reachable: {e}")
        sys.exit(1)


def save_dataset(module: str, data: dict):
    path = DATASET_DIR / f"{module}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  💾 Saved {len(data.get('samples', []))} samples → {path}")


# ─────────────────────────────────────────────
# LEGAL QA dataset
# ─────────────────────────────────────────────

def _generate_qa_questions(case_text: str, case_name: str) -> list[dict]:
    """Ask LLM to generate 2-3 factual QA pairs from case text."""
    prompt = f"""You are a legal analyst. Based on the following court judgment text, 
generate exactly 3 factual questions that have CLEAR answers explicitly stated in the text.
For each question write a concise reference answer (1-2 sentences) drawn DIRECTLY from the text.
Focus on: parties to the case, legal sections applied, court's final order, bench.

Judgment text:
\"\"\"
{case_text}
\"\"\"

Return JSON array ONLY – no prose, no markdown fences:
[
  {{"question": "...", "reference": "..."}},
  ...
]"""
    try:
        raw = llm(prompt)
        raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(raw)[:3]
    except Exception as e:
        print(f"    [WARN] QA question generation failed for {case_name}: {e}")
        return []


def build_legal_qa_dataset():
    print("\n── Building legal_qa dataset ──")
    _check_backend(f"{BACKEND_QA}/api/stats", "Legal QA (8002)")

    samples = []
    total_needed = min(SAMPLE_LIMIT, len(SAMPLE_PDFS) * 3)
    print(f"  Target: {total_needed} samples from {len(SAMPLE_PDFS)} PDFs")

    for pdf_name in SAMPLE_PDFS:
        if len(samples) >= SAMPLE_LIMIT:
            break
        pdf_path = CORPUS_UPLOADS / pdf_name
        if not pdf_path.exists():
            # try downloads folder
            for dl in (CORPUS_UPLOADS.parent.parent.parent / "indiankanoon-mcp" / "downloads").rglob("*.pdf"):
                if dl.name == pdf_name:
                    pdf_path = dl
                    break
        if not pdf_path.exists():
            print(f"  [SKIP] {pdf_name} not found")
            continue

        print(f"  📄 {pdf_name[:60]}...")
        case_text = extract_pdf_text(str(pdf_path))
        if not case_text:
            continue

        # 1. Upload PDF to QA backend
        case_id = None
        try:
            with open(pdf_path, "rb") as f:
                resp = post_with_retry(
                    f"{BACKEND_QA}/api/upload-pdf",
                    files={"file": (pdf_name, f, "application/pdf")},
                    data={"case_name": pdf_name.replace(".pdf", "")},
                )
            if resp.ok:
                case_id = resp.json().get("case_id")
                print(f"    Indexed as case_id={case_id}")
            else:
                print(f"    [WARN] Upload failed: {resp.text[:200]}")
        except Exception as e:
            print(f"    [WARN] Upload error: {e}")

        # 2. Generate QA pairs
        qa_pairs = _generate_qa_questions(case_text, pdf_name)

        for pair in qa_pairs:
            if len(samples) >= SAMPLE_LIMIT:
                break
            question = pair.get("question", "").strip()
            reference = pair.get("reference", "").strip()
            if not question:
                continue

            # 3. Call /api/ask with source=document if case_id available
            source = "document" if case_id else "external"
            payload = {"question": question, "source": source, "language": "en"}
            if case_id:
                payload["case_id"] = case_id

            try:
                r = post_with_retry(f"{BACKEND_QA}/api/ask", json=payload)
                if not r.ok:
                    print(f"    [WARN] /api/ask failed: {r.text[:200]}")
                    continue
                data = r.json()
            except Exception as e:
                print(f"    [WARN] /api/ask error: {e}")
                continue

            conclusion = data.get("conclusion", "")
            reasoning = data.get("legal_reasoning", "")
            response_text = f"{conclusion}\n\n{reasoning}".strip()
            retrieved = data.get("retrieved_cases", [])
            contexts = [rc.get("chunk", "") for rc in retrieved if rc.get("chunk")]

            sample_id = hashlib.md5(f"qa_{question}".encode()).hexdigest()[:8]
            samples.append({
                "id": sample_id,
                "pdf_source": pdf_name,
                "case_id": case_id,
                "user_input": question,
                "response": response_text,
                "retrieved_contexts": contexts[:5],
                "reference": reference,
                "metadata": {
                    "mode": data.get("mode", "EXTERNAL"),
                    "uncertainty_score": data.get("uncertainty_score"),
                    "retrieved_cases_count": data.get("retrieved_cases_count", 0),
                },
                "scores": {},
                "flag": "ok",
            })
            print(f"    ✓ Sample {sample_id}: {question[:60]}...")

    dataset = {
        "module": "legal_qa",
        "metadata": {
            "reference_type": REFERENCE_TYPE,
            "ragas_version": RAGAS_VERSION,
            "judge_model": JUDGE_MODEL,
            "run_timestamp": RUN_TIMESTAMP,
            "n_samples": len(samples),
        },
        "samples": samples,
    }
    save_dataset("legal_qa", dataset)
    return dataset


# ─────────────────────────────────────────────
# RESEARCH dataset
# ─────────────────────────────────────────────

RESEARCH_QUERIES = [
    {"query": "Section 302 IPC murder conviction evidence", "reference": "Section 302 IPC prescribes punishment for murder; courts require proof of intention/knowledge and direct evidence linking accused to the act."},
    {"query": "Article 21 Constitution right to life bail", "reference": "Article 21 guarantees right to life and personal liberty; bail cannot be denied as a punitive measure without judicial application of mind."},
    {"query": "Section 498A IPC dowry harassment cruelty", "reference": "Section 498A IPC deals with cruelty by husband or relatives; requires mental or physical harassment related to dowry demands."},
    {"query": "NDPS Act Section 37 bail narcotic drug", "reference": "Section 37 NDPS Act imposes stringent conditions for bail in narcotic offences; bail shall not ordinarily be granted unless court is satisfied of innocence."},
    {"query": "Service law seniority promotion high court", "reference": "Seniority in service law is determined by date of appointment; promotions follow roster rules and cannot override seniority without valid legal basis."},
    {"query": "Income tax appeal reassessment escaped assessment", "reference": "Under Section 147 IT Act, reassessment is valid only when AO has 'reason to believe' income has escaped assessment; belief must be based on tangible material."},
    {"query": "Motor vehicle accident compensation negligence", "reference": "Motor Accidents Claims Tribunals award compensation based on negligence, contributory negligence, age of victim, and notional income as per statutory formula."},
    {"query": "Anticipatory bail Section 438 CrPC conditions", "reference": "Anticipatory bail under Section 438 CrPC may be granted considering: nature of accusation, antecedents, possibility of fleeing, and co-operation with investigation."},
    {"query": "Contempt of court jurisdiction High Court", "reference": "High Courts exercise inherent contempt jurisdiction under Article 215 Constitution; civil contempt requires wilful disobedience of court order."},
    {"query": "Land acquisition compensation market value", "reference": "Land acquisition compensation is determined at market value on date of notification under Land Acquisition Act; solatium of 30% is added to compensation."},
    {"query": "Section 313 CrPC examination accused statement", "reference": "Section 313 CrPC provides accused right to explain circumstances in evidence against them; failure to examine accused is an infirmity."},
    {"query": "Writ of mandamus Article 226 High Court", "reference": "Writ of mandamus under Article 226 lies to compel performance of public duty; petitioner must show legal right and respondent has corresponding duty."},
    {"query": "Consumer protection act deficiency service", "reference": "Consumer Protection Act 1986/2019 defines deficiency as inadequacy in quality or performance; forums can award compensation and punitive damages."},
    {"query": "Child witness testimony POCSO Section 164 CrPC", "reference": "Child witness testimony in POCSO cases is recorded under Section 164 CrPC before magistrate; courts apply rule of prudence before relying on uncorroborated child testimony."},
    {"query": "Arbitration award Section 34 Arbitration Act challenge", "reference": "Award can be set aside under Section 34 only on grounds of incapacity, invalid agreement, improper notice, beyond scope, or conflict with public policy."},
    {"query": "Dishonour cheque Section 138 Negotiable Instruments Act", "reference": "Section 138 NI Act creates criminal liability for dishonour of cheque; complainant must prove legally enforceable debt and proper notice of demand."},
    {"query": "Sexual assault rape victim testimony corroboration", "reference": "Supreme Court held victim's testimony in rape cases need not be corroborated; conviction can rest on sole testimony if it inspires confidence."},
    {"query": "Right to education Article 21A fundamental right", "reference": "Article 21A inserted by 86th Amendment makes education for children 6-14 years a fundamental right; RTE Act 2009 operationalizes this right."},
    {"query": "Natural justice audi alteram partem opportunity of hearing", "reference": "Audi alteram partem (hear the other side) is a cardinal principle of natural justice; no order adverse to a party can be passed without giving opportunity of hearing."},
    {"query": "Locus standi public interest litigation Article 32", "reference": "Locus standi in PIL is liberalized; Supreme Court under Article 32 entertains petitions by any public-spirited citizen acting in genuine public interest."},
]


def build_research_dataset():
    print("\n── Building research dataset ──")
    _check_backend(f"{BACKEND_RESEARCH}/api/history", "Research (8001)")

    # First, upload some PDFs to research backend for local hits
    print("  Pre-loading PDFs into research backend...")
    for pdf_name in SAMPLE_PDFS[:5]:
        pdf_path = CORPUS_UPLOADS / pdf_name
        if not pdf_path.exists():
            continue
        try:
            with open(pdf_path, "rb") as f:
                r = post_with_retry(
                    f"{BACKEND_RESEARCH}/api/analyze/legal",
                    files={"file": (pdf_name, f, "application/pdf")},
                )
            print(f"    Indexed {pdf_name[:50]}: {r.status_code}")
        except Exception as e:
            print(f"    [WARN] Research upload error: {e}")

    queries = RESEARCH_QUERIES[:SAMPLE_LIMIT]
    samples = []

    def process_query(item):
        q = item["query"]
        ref = item["reference"]
        try:
            r = post_with_retry(
                f"{BACKEND_RESEARCH}/api/search/query",
                data={"query": q},
            )
            if not r.ok:
                return None
            data = r.json()
        except Exception as e:
            print(f"    [WARN] Search error for '{q[:40]}': {e}")
            return None

        results = data.get("results", [])
        contexts = []
        for res in results[:5]:
            snippet = res.get("snippet") or res.get("text") or ""
            analysis = res.get("analysis", {})
            summary_txt = analysis.get("summary", "") if isinstance(analysis, dict) else ""
            ctx = f"{snippet}\n{summary_txt}".strip()
            if ctx:
                contexts.append(ctx)

        # Distinguish retrieval-only search results from synthesized generation:
        # Document Research (/api/search/query) is a legal retrieval & ranking endpoint.
        # It returns ranked search candidates (snippets, analysis summaries, citations),
        # not a free-form synthesized generative answer.
        # If an analytical summary was generated for the top retrieved document, use that
        # substantive summary as the answer text; otherwise, mark response as empty string
        # to ensure Ragas evaluation does not evaluate metadata strings as answers.
        top_substantive_answer = ""
        has_substantive_answer = False
        if results:
            top = results[0]
            analysis = top.get("analysis", {})
            summary = analysis.get("summary", "") if isinstance(analysis, dict) else ""
            if summary and summary.strip() and not summary.lower().startswith("failed to analyze"):
                top_substantive_answer = summary.strip()
                has_substantive_answer = True

        sample_id = hashlib.md5(f"res_{q}".encode()).hexdigest()[:8]
        return {
            "id": sample_id,
            "user_input": q,
            "response": top_substantive_answer,
            "retrieved_contexts": contexts,
            "reference": ref,
            "metadata": {
                "n_results": len(results),
                "from_cache": data.get("from_cache", False),
                "has_substantive_answer": has_substantive_answer,
                "is_retrieval_only": not has_substantive_answer,
                "top_source": results[0].get("source") if results else None,
                "top_title": results[0].get("title") or results[0].get("filename") if results else None
            },
            "scores": {},
            "flag": "ok",
        }

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(process_query, item) for item in queries]
        for future in as_completed(futures):
            result = future.result()
            if result:
                samples.append(result)
                print(f"    ✓ {result['id']}: {result['user_input'][:55]}...")

    dataset = {
        "module": "research",
        "metadata": {
            "reference_type": REFERENCE_TYPE,
            "ragas_version": RAGAS_VERSION,
            "judge_model": JUDGE_MODEL,
            "run_timestamp": RUN_TIMESTAMP,
            "n_samples": len(samples),
        },
        "samples": samples,
    }
    save_dataset("research", dataset)
    return dataset


# ─────────────────────────────────────────────
# SUMMARY dataset
# ─────────────────────────────────────────────

def _generate_reference_summary(case_text: str, case_name: str) -> str:
    """Generate a careful reference summary using GPT."""
    prompt = f"""You are a senior Indian legal analyst. Write a concise (5-8 sentences) reference summary of the following court judgment.
Include: (1) parties and case type, (2) key legal issue, (3) court's reasoning, (4) final decision.
Be factually precise and only include what is explicitly in the text.

Judgment: {case_name}
Text:
\"\"\"
{case_text}
\"\"\"

Return ONLY the summary paragraph, no headings."""
    try:
        return llm(prompt, temperature=0.1)
    except Exception as e:
        print(f"    [WARN] Reference summary gen failed: {e}")
        return ""


def build_summary_dataset():
    print("\n── Building summary dataset ──")
    _check_backend(f"{BACKEND_SUMMARY}/api/history", "Summary (8003)")

    samples = []
    pdfs_to_use = SAMPLE_PDFS[:min(15, SAMPLE_LIMIT)]

    for pdf_name in pdfs_to_use:
        if len(samples) >= SAMPLE_LIMIT:
            break
        pdf_path = CORPUS_UPLOADS / pdf_name
        if not pdf_path.exists():
            continue

        print(f"  📄 {pdf_name[:60]}...")
        case_text = extract_pdf_text(str(pdf_path))
        if not case_text:
            continue

        # 1. Generate reference summary
        ref_summary = _generate_reference_summary(case_text, pdf_name)

        # 2. Call /api/summarize
        prefs = {
            "summary_length": "medium",
            "focus_area": ["facts", "arguments", "legal reasoning"],
            "output_language": "english",
        }
        try:
            with open(pdf_path, "rb") as f:
                r = post_with_retry(
                    f"{BACKEND_SUMMARY}/api/summarize",
                    files={"pdf_file": (pdf_name, f, "application/pdf")},
                    data={"preferences": json.dumps(prefs)},
                )
            if not r.ok:
                print(f"    [WARN] /api/summarize failed: {r.text[:200]}")
                continue
            data = r.json()
        except Exception as e:
            print(f"    [WARN] Summary call error: {e}")
            continue

        meta = data.get("metadata", {})
        system_summary = meta.get("summary", "")
        confidence_obj = data.get("confidence", {})
        overall_conf = confidence_obj.get("overall_confidence", 0.0) if isinstance(confidence_obj, dict) else 0.0

        # Context = chunked judgment text (first 3000 chars)
        chunk_size = 3000
        contexts = [case_text[i: i + chunk_size] for i in range(0, min(len(case_text), 9000), chunk_size)]

        sample_id = hashlib.md5(f"sum_{pdf_name}".encode()).hexdigest()[:8]
        samples.append({
            "id": sample_id,
            "pdf_source": pdf_name,
            "user_input": f"Summarize the legal case: {pdf_name.replace('.pdf', '')}",
            "response": system_summary,
            "retrieved_contexts": contexts,
            "reference": ref_summary,
            "metadata": {
                "case_title": meta.get("case_title", ""),
                "court_name": meta.get("court_name", ""),
                "system_confidence_score": overall_conf,
                "sections_invoked": meta.get("sections_invoked", []),
            },
            "scores": {},
            "flag": "ok",
        })
        print(f"    ✓ Sample {sample_id}: {meta.get('case_title', pdf_name)[:55]}")

    dataset = {
        "module": "summary",
        "metadata": {
            "reference_type": REFERENCE_TYPE,
            "ragas_version": RAGAS_VERSION,
            "judge_model": JUDGE_MODEL,
            "run_timestamp": RUN_TIMESTAMP,
            "n_samples": len(samples),
        },
        "samples": samples,
    }
    save_dataset("summary", dataset)
    return dataset


# ─────────────────────────────────────────────
# COMPREHENSION dataset
# ─────────────────────────────────────────────

COMPREHENSION_FIELDS = [
    "Case Title & Citation",
    "Bench / Court",
    "Date",
    "Facts of the Case",
    "Issues Framed",
    "Arguments by Parties",
    "Court's Analysis / Reasoning",
    "Final Decision (Ratio Decidendi)",
]


def _generate_reference_field(field: str, case_text: str) -> str:
    """Generate a reference answer for a specific field."""
    prompt = f"""You are a legal expert. From the following Indian court judgment text, extract the "{field}".
Be precise and concise (2-4 sentences max). Only include what is explicitly stated in the text.
If the field is not present, write "Not specified in the document".

Judgment text:
\"\"\"
{case_text}
\"\"\"

Return ONLY the extracted value for "{field}", no labels, no markdown."""
    try:
        return llm(prompt, temperature=0.0)
    except Exception as e:
        print(f"      [WARN] Reference gen failed for {field}: {e}")
        return "Not specified in the document"


def build_comprehension_dataset():
    print("\n── Building comprehension dataset ──")
    _check_backend(f"{BACKEND_MAIN}/api/cases", "Main Backend (8000)")

    samples = []

    # Use existing Results JSON files (already extracted by the system)
    result_files = list(CORPUS_RESULTS.glob("*_summary.json"))
    print(f"  Found {len(result_files)} existing results. Will process up to {min(8, len(result_files))} judgments.")

    # Match result files back to PDFs for context
    uploads_by_stem = {}
    for pdf in CORPUS_UPLOADS.glob("*.pdf"):
        uploads_by_stem[pdf.stem.lower()] = pdf

    processed_judgments = 0
    for result_file in result_files[:8]:
        if len(samples) >= SAMPLE_LIMIT:
            break

        with open(result_file, "r", encoding="utf-8") as f:
            extracted = json.load(f)

        case_title = extracted.get("Case Title & Citation", "Unknown Case")
        print(f"  📄 {case_title[:55]}...")

        # Find corresponding PDF text (best effort)
        case_text = ""
        stop_words = {"vs", "state", "of", "and", "ors", "the", "in", "to", "for", "on", "another", "anr", "ors.", "anr.", "v.", "ltd", "ltd.", "union", "india"}
        
        # Try to find PDF by matching case title keywords
        title_words = set([w for w in case_title.lower().replace(",", "").replace(".", "").split() if w not in stop_words])
        best_match = None
        best_score = 0
        
        for stem, pdf_path in uploads_by_stem.items():
            stem_words = set([w for w in stem.lower().replace("_", " ").replace(",", "").replace(".", "").split() if w not in stop_words])
            overlap = len(title_words & stem_words)
            if overlap > best_score:
                best_score = overlap
                best_match = pdf_path
                
        if best_match and best_score >= 2:
            case_text = extract_pdf_text(str(best_match))

        if not case_text:
            # Fall back: use the extracted text as context
            case_text = json.dumps(extracted, ensure_ascii=False)

        context_chunks = [case_text[i: i + 4000] for i in range(0, min(len(case_text), 8000), 4000)]
        confidence_map = extracted.get("Confidence", {})

        for field in COMPREHENSION_FIELDS:
            if len(samples) >= SAMPLE_LIMIT:
                break

            system_value = extracted.get(field, "Not specified in the document")
            if isinstance(system_value, dict):
                system_value = json.dumps(system_value, ensure_ascii=False)

            ref_value = _generate_reference_field(field, case_text)
            field_conf = confidence_map.get(field, None)
            if isinstance(field_conf, (int, float)):
                field_conf = float(field_conf) / 100.0  # normalize to 0-1

            sample_id = hashlib.md5(f"comp_{result_file.name}_{field}".encode()).hexdigest()[:8]
            samples.append({
                "id": sample_id,
                "pdf_source": result_file.name,
                "case_title": case_title,
                "field": field,
                "user_input": f"Extract the '{field}' from this Indian court judgment.",
                "response": str(system_value),
                "retrieved_contexts": context_chunks,
                "reference": ref_value,
                "metadata": {
                    "system_confidence": field_conf,
                    "result_file": result_file.name,
                },
                "scores": {},
                "flag": "ok",
            })
            print(f"    ✓ {sample_id}: {field}")

        processed_judgments += 1

    dataset = {
        "module": "comprehension",
        "metadata": {
            "reference_type": REFERENCE_TYPE,
            "ragas_version": RAGAS_VERSION,
            "judge_model": JUDGE_MODEL,
            "run_timestamp": RUN_TIMESTAMP,
            "n_samples": len(samples),
            "n_judgments": processed_judgments,
            "fields_per_judgment": len(COMPREHENSION_FIELDS),
        },
        "samples": samples,
    }
    save_dataset("comprehension", dataset)
    return dataset


# ─────────────────────────────────────────────
# CLI entrypoint
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Build evaluation datasets")
    parser.add_argument(
        "--module",
        default="all",
        choices=["all", "legal_qa", "research", "summary", "comprehension"],
        help="Which module dataset to generate",
    )
    args = parser.parse_args()

    if not OPENAI_API_KEY:
        print("❌ OPENAI_API_KEY is not set. Check your .env files.")
        sys.exit(1)

    print(f"🔧 Building datasets — module={args.module}, sample_limit={SAMPLE_LIMIT}")
    print(f"   Judge model: {JUDGE_MODEL}  |  Ragas version: {RAGAS_VERSION}")

    modules_to_run = (
        ["legal_qa", "research", "summary", "comprehension"]
        if args.module == "all"
        else [args.module]
    )

    for mod in modules_to_run:
        try:
            if mod == "legal_qa":
                build_legal_qa_dataset()
            elif mod == "research":
                build_research_dataset()
            elif mod == "summary":
                build_summary_dataset()
            elif mod == "comprehension":
                build_comprehension_dataset()
        except SystemExit:
            raise
        except Exception as e:
            print(f"  ❌ Failed to build {mod} dataset: {e}")
            traceback.print_exc()

    print("\n✅ Dataset build complete.")


if __name__ == "__main__":
    main()
