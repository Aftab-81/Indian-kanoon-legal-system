"""
evaluation/scripts/seed_demo_results.py
────────────────────────────────────────
Injects realistic demo evaluation results into evaluation/results/
so the dashboard shows populated charts immediately — without
needing to run the full Ragas pipeline (which requires live backends
and OpenAI calls).

Run once from the project root:
    venv\\Scripts\\python.exe evaluation/scripts/seed_demo_results.py

The seed values are calibrated to reflect realistic performance levels
for a GPT-4o-mini-based Indian legal AI system. They are clearly
labelled as "demo" in the metadata.

Re-running the real evaluation (run_eval.py) overwrites these files.
"""

from __future__ import annotations
import json
import random
import hashlib
from datetime import datetime
from pathlib import Path

random.seed(42)

EVAL_DIR = Path(__file__).resolve().parent.parent
RESULT_DIR = EVAL_DIR / "results"
RESULT_DIR.mkdir(exist_ok=True)

RUN_TS = datetime.utcnow().isoformat() + "Z"
JUDGE  = "gpt-4o-mini (demo seed)"
RAGAS  = "0.2.15"

# ── Realistic score ranges per module ──────────────────────────────────────
# Calibrated based on published Ragas benchmarks for RAG legal QA systems.
# Faithfulness tends high (0.70–0.90) when source doc is provided.
# Context precision tends moderate (0.55–0.75) due to legal boilerplate.
# Factual correctness tends moderate-high (0.65–0.85).

MODULE_SPECS = {
    "legal_qa": {
        "metrics": {
            "faithfulness":                          (0.72, 0.90),
            "response_relevancy":                    (0.68, 0.84),
            "llm_context_precision_with_reference":  (0.58, 0.78),
            "context_recall":                        (0.60, 0.80),
            "factual_correctness":                   (0.65, 0.85),
            "cites_page_numbers":                    (0.20, 0.50),
        },
        "n_samples": 18,
        "notes": [
            "Demo seed data — replace by running: python evaluation/run_eval.py --module legal_qa",
            "Scores use auto-generated references and an LLM judge; treat as indicative, not ground truth.",
            "cites_page_numbers AspectCritic scores low for EXTERNAL mode answers (no page refs in source).",
        ],
        "pdf_names": [
            "1189512_U.P. State Sugar Corporation Ltd..._2005.pdf",
            "1608496_Cit vs S. Kamaljeet Singh_2005.pdf",
            "1687189_District And Sessions Judge vs Ratnesh_2005.pdf",
            "1822728_Saraya Industries Ltd. vs State Of U.P._2005.pdf",
            "1898332_Vijendra Sharma_2005.pdf",
            "1913281_Ex-Naik Upendra Kumar Tomar_2005.pdf",
        ],
        "questions": [
            "What was the main legal issue in this case?",
            "Which court delivered this judgment?",
            "What was the final order of the court?",
            "Who were the parties to the dispute?",
            "What sections of law were applied?",
            "What evidence did the court rely on?",
        ],
    },
    "research": {
        "metrics": {
            "llm_context_precision_with_reference":  (0.55, 0.72),
            "context_recall":                        (0.50, 0.70),
            "context_entity_recall":                 (0.48, 0.68),
        },
        "n_samples": 20,
        "notes": [
            "Demo seed data — replace by running: python evaluation/run_eval.py --module research",
            "Scores use auto-generated references; treat as indicative, not ground truth.",
            "Retrieved contexts are snippets from search results; quality depends on backend availability.",
        ],
        "questions": [
            "Section 302 IPC murder conviction evidence",
            "Article 21 Constitution right to life bail",
            "Section 498A IPC dowry harassment cruelty",
            "NDPS Act Section 37 bail narcotic drug",
            "Service law seniority promotion high court",
            "Income tax appeal reassessment escaped assessment",
            "Motor vehicle accident compensation negligence",
            "Anticipatory bail Section 438 CrPC conditions",
        ],
    },
    "summary": {
        "metrics": {
            "faithfulness":                          (0.74, 0.92),
            "response_relevancy":                    (0.70, 0.86),
            "covers_core_elements":                  (0.65, 0.90),
            "no_invented_details":                   (0.75, 0.95),
        },
        "n_samples": 10,
        "notes": [
            "Demo seed data — replace by running: python evaluation/run_eval.py --module summary",
            "Scores use auto-generated references; treat as indicative, not ground truth.",
            "SummarizationScore is not available in Ragas 0.2.15; substituted with Faithfulness + ResponseRelevancy.",
            "faithfulness used as SummarizationScore substitute (factual grounding).",
        ],
        "pdf_names": [
            "1189512_U.P. State Sugar Corporation Ltd..._2005.pdf",
            "1608496_Cit vs S. Kamaljeet Singh_2005.pdf",
            "103394330_Reserved On_2025.pdf",
            "185995005_Mohammed Siddique_2020.pdf",
            "187771162_Shilpa Mittal_2020.pdf",
        ],
    },
    "comprehension": {
        "metrics": {
            "faithfulness":                          (0.78, 0.94),
            "factual_correctness":                   (0.70, 0.90),
            "semantic_similarity":                   (0.82, 0.96),
            "field_is_complete":                     (0.62, 0.88),
        },
        "n_samples": 16,
        "notes": [
            "Demo seed data — replace by running: python evaluation/run_eval.py --module comprehension",
            "Scores use auto-generated references; treat as indicative, not ground truth.",
            "SemanticSimilarity uses OpenAI text-embedding-3-small (same as Research backend).",
            "Per-field and per-judgment aggregates computed from sample metadata.",
        ],
        "fields": [
            "Case Title & Citation",
            "Bench / Court",
            "Date",
            "Facts of the Case",
            "Issues Framed",
            "Arguments by Parties",
            "Court's Analysis / Reasoning",
            "Final Decision (Ratio Decidendi)",
        ],
    },
}

# ── Field-level expected accuracy (comprehension) ──────────────────────────
FIELD_ACCURACY = {
    "Case Title & Citation":          (0.90, 0.98),
    "Bench / Court":                   (0.88, 0.97),
    "Date":                            (0.92, 0.99),
    "Facts of the Case":               (0.70, 0.88),
    "Issues Framed":                   (0.65, 0.85),
    "Arguments by Parties":            (0.62, 0.82),
    "Court's Analysis / Reasoning":    (0.68, 0.87),
    "Final Decision (Ratio Decidendi)":(0.73, 0.91),
}


def rng(lo: float, hi: float) -> float:
    return round(random.uniform(lo, hi), 4)


def make_sample(sample_id: str, user_input: str, scores: dict[str, float], flag_threshold: float = 0.6) -> dict:
    mean = sum(scores.values()) / len(scores) if scores else 0.0
    return {
        "id": sample_id,
        "user_input": user_input,
        "response": "[Demo] System response for this question would appear here after a real evaluation run.",
        "retrieved_contexts": [
            "Context chunk 1: relevant legal text extracted from the judgment.",
            "Context chunk 2: additional precedents and reasoning from source document.",
        ],
        "reference": "[Demo] Reference answer generated by LLM from source document.",
        "metadata": {"demo": True},
        "scores": scores,
        "flag": "low" if mean < flag_threshold else "ok",
    }


def build_legal_qa_samples(spec: dict) -> list[dict]:
    samples = []
    qlist = spec["questions"]
    plist = spec["pdf_names"]
    for i in range(spec["n_samples"]):
        q = qlist[i % len(qlist)]
        p = plist[i % len(plist)]
        sid = hashlib.md5(f"demo_qa_{i}_{q}".encode()).hexdigest()[:8]
        scores = {k: rng(*v) for k, v in spec["metrics"].items()}
        s = make_sample(sid, f"[{p[:30]}] {q}", scores)
        s["pdf_source"] = p
        samples.append(s)
    return samples


def build_research_samples(spec: dict) -> list[dict]:
    samples = []
    qlist = spec["questions"]
    for i in range(spec["n_samples"]):
        q = qlist[i % len(qlist)]
        sid = hashlib.md5(f"demo_res_{i}_{q}".encode()).hexdigest()[:8]
        scores = {k: rng(*v) for k, v in spec["metrics"].items()}
        samples.append(make_sample(sid, q, scores))
    return samples


def build_summary_samples(spec: dict) -> list[dict]:
    samples = []
    plist = spec["pdf_names"]
    for i in range(spec["n_samples"]):
        p = plist[i % len(plist)]
        sid = hashlib.md5(f"demo_sum_{i}_{p}".encode()).hexdigest()[:8]
        scores = {k: rng(*v) for k, v in spec["metrics"].items()}
        s = make_sample(sid, f"Summarize the legal case: {p.replace('.pdf','')}", scores)
        s["pdf_source"] = p
        samples.append(s)
    return samples


def build_comprehension_samples(spec: dict) -> list[dict]:
    samples = []
    fields = spec["fields"]
    per_field: dict[str, list[float]] = {f: [] for f in fields}
    count = 0
    for field in fields:
        for j in range(spec["n_samples"] // len(fields)):
            sid = hashlib.md5(f"demo_comp_{field}_{j}".encode()).hexdigest()[:8]
            base_lo, base_hi = FIELD_ACCURACY.get(field, (0.65, 0.85))
            scores = {}
            for mk, (mlo, mhi) in spec["metrics"].items():
                # Blend with field accuracy
                v = rng(min(mlo, base_lo) * 0.5 + base_lo * 0.5,
                        min(mhi, base_hi) * 0.5 + base_hi * 0.5)
                scores[mk] = round(min(1.0, max(0.0, v)), 4)
            for v in scores.values():
                per_field[field].append(v)
            s = make_sample(sid, f"Extract the '{field}' from this Indian court judgment.", scores)
            s["field"] = field
            count += 1
            samples.append(s)
    return samples, {f: round(sum(v)/len(v), 4) for f, v in per_field.items() if v}


def aggregate(samples: list[dict]) -> dict:
    all_metrics: set[str] = set()
    for s in samples:
        all_metrics.update(s.get("scores", {}).keys())
    agg = {}
    for m in all_metrics:
        vals = [s["scores"].get(m) for s in samples if s["scores"].get(m) is not None]
        agg[m] = round(sum(vals) / len(vals), 4) if vals else None
    return agg


def save(module: str, metadata: dict, agg: dict, samples: list, notes: list):
    path = RESULT_DIR / f"{module}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "module": module,
            "metadata": metadata,
            "aggregate": agg,
            "samples": samples,
            "notes": notes,
        }, f, indent=2, ensure_ascii=False)
    mean = sum(v for v in agg.values() if v is not None) / max(1, sum(1 for v in agg.values() if v is not None))
    print(f"  [OK] {module}: {len(samples)} samples, mean={mean:.1%}, -> {path.name}")


def main():
    print("Seeding demo evaluation results...")

    # legal_qa
    spec = MODULE_SPECS["legal_qa"]
    samples = build_legal_qa_samples(spec)
    agg = aggregate(samples)
    save("legal_qa", {
        "reference_type": "demo_seed",
        "ragas_version": RAGAS, "judge_model": JUDGE,
        "run_timestamp": RUN_TS, "n_samples": len(samples),
        "metrics_used": list(spec["metrics"].keys()),
    }, agg, samples, spec["notes"])

    # research
    spec = MODULE_SPECS["research"]
    samples = build_research_samples(spec)
    agg = aggregate(samples)
    save("research", {
        "reference_type": "demo_seed",
        "ragas_version": RAGAS, "judge_model": JUDGE,
        "run_timestamp": RUN_TS, "n_samples": len(samples),
        "metrics_used": list(spec["metrics"].keys()),
    }, agg, samples, spec["notes"])

    # summary
    spec = MODULE_SPECS["summary"]
    samples = build_summary_samples(spec)
    agg = aggregate(samples)
    save("summary", {
        "reference_type": "demo_seed",
        "ragas_version": RAGAS, "judge_model": JUDGE,
        "run_timestamp": RUN_TS, "n_samples": len(samples),
        "metrics_used": list(spec["metrics"].keys()),
    }, agg, samples, spec["notes"])

    # comprehension
    spec = MODULE_SPECS["comprehension"]
    samples, per_field = build_comprehension_samples(spec)
    agg = aggregate(samples)
    save("comprehension", {
        "reference_type": "demo_seed",
        "ragas_version": RAGAS, "judge_model": JUDGE,
        "run_timestamp": RUN_TS, "n_samples": len(samples),
        "metrics_used": list(spec["metrics"].keys()),
        "per_field_aggregate": per_field,
    }, agg, samples, spec["notes"])

    print("\nDone! Dashboard at http://localhost:5173/evaluation")
    print("To replace with real results:")
    print("  venv\\Scripts\\python.exe evaluation/build_datasets.py --module all")
    print("  venv\\Scripts\\python.exe evaluation/run_eval.py --module all")


if __name__ == "__main__":
    main()
