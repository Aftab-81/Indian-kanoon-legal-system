"""
evaluation/run_eval.py
──────────────────────
Phase 3: Run Ragas metrics on saved datasets and persist results.

Run:
    python evaluation/run_eval.py [--module all|legal_qa|research|summary|comprehension]

Reads  evaluation/datasets/<module>.json
Writes evaluation/results/<module>.json

Ragas version: 0.2.15 (pinned)
Note: langchain_community.chat_models.vertexai was dropped in langchain-community>=0.3.
      A patch in venv/Lib/site-packages/ragas/llms/base.py provides stub classes.
"""
from __future__ import annotations
import argparse
import json
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Optional

# ── path setup ───────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (
    OPENAI_API_KEY, JUDGE_MODEL, EMBED_MODEL,
    SAMPLE_LIMIT, MAX_WORKERS, DATASET_DIR, RESULT_DIR, RAGAS_VERSION,
)

# ── Ragas imports ────────────────────────────────────────────
# We inspect the actual available symbols at runtime to handle version differences
import ragas
from ragas import evaluate
from ragas.dataset_schema import SingleTurnSample, EvaluationDataset
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

print(f"[OK] ragas {ragas.__version__} imported")

# Import metrics with fallbacks
def _safe_import(module_path: str, name: str):
    try:
        mod = __import__(module_path, fromlist=[name])
        return getattr(mod, name)
    except (ImportError, AttributeError):
        return None

Faithfulness = _safe_import("ragas.metrics", "Faithfulness")
ResponseRelevancy = _safe_import("ragas.metrics", "ResponseRelevancy")
LLMContextPrecisionWithReference = _safe_import("ragas.metrics", "LLMContextPrecisionWithReference")
ContextRecall = _safe_import("ragas.metrics", "ContextRecall")
FactualCorrectness = _safe_import("ragas.metrics", "FactualCorrectness")
SemanticSimilarity = _safe_import("ragas.metrics", "SemanticSimilarity")
ContextEntityRecall = _safe_import("ragas.metrics", "ContextEntityRecall")
AspectCritic = _safe_import("ragas.metrics", "AspectCritic")
# SummarizationScore is absent in 0.2.x — substituted with Faithfulness + ResponseRelevancy

RUN_TIMESTAMP = datetime.utcnow().isoformat() + "Z"
LOW_SCORE_THRESHOLD = 0.6


from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper

def _make_llm():
    return LangchainLLMWrapper(ChatOpenAI(model=JUDGE_MODEL, api_key=OPENAI_API_KEY, temperature=0.0))


def _make_embeddings():
    return LangchainEmbeddingsWrapper(OpenAIEmbeddings(model=EMBED_MODEL, api_key=OPENAI_API_KEY))


def _build_dataset(samples: list[dict]) -> EvaluationDataset:
    """Convert our JSON samples to a Ragas EvaluationDataset."""
    rows = []
    for s in samples:
        rows.append(SingleTurnSample(
            user_input=s.get("user_input", ""),
            response=s.get("response", ""),
            retrieved_contexts=s.get("retrieved_contexts", []),
            reference=s.get("reference", ""),
        ))
    return EvaluationDataset(samples=rows)


def _mean_of_nullables(values: list) -> Optional[float]:
    valid = [v for v in values if v is not None and not (isinstance(v, float) and v != v)]
    if not valid:
        return None
    return round(sum(valid) / len(valid), 4)


def _run_metrics(dataset: EvaluationDataset, metrics: list, notes: list[str]) -> dict:
    """Run ragas evaluate; return dict of {metric_name: list[float|None]}."""
    if not metrics:
        return {}
    valid_metrics = [m for m in metrics if m is not None]
    if not valid_metrics:
        return {}

    llm = _make_llm()
    embeddings = _make_embeddings()

    # Inject LLM / embeddings into metrics that need them
    for m in valid_metrics:
        if hasattr(m, "llm"):
            m.llm = llm
        if hasattr(m, "embeddings"):
            m.embeddings = embeddings

    try:
        result = evaluate(
            dataset=dataset,
            metrics=valid_metrics,
            llm=llm,
            embeddings=embeddings,
            raise_exceptions=False,
        )
        scores_by_metric: dict[str, list] = {}
        for m in valid_metrics:
            key = m.name if hasattr(m, "name") else type(m).__name__.lower()
            try:
                col_values = result.to_pandas()[key].tolist()
                scores_by_metric[key] = [
                    None if (v != v or v is None) else round(float(v), 4)
                    for v in col_values
                ]
            except Exception:
                scores_by_metric[key] = [None] * len(dataset.samples)
        return scores_by_metric
    except Exception as e:
        notes.append(f"Metric evaluation error: {e}")
        traceback.print_exc()
        return {}


def _attach_scores(samples: list[dict], scores_by_metric: dict[str, list]) -> list[dict]:
    """Attach per-sample scores and set flag."""
    for i, sample in enumerate(samples):
        for metric_name, values in scores_by_metric.items():
            if i < len(values):
                sample["scores"][metric_name] = values[i]

        valid_scores = [v for v in sample["scores"].values() if v is not None]
        mean_score = _mean_of_nullables(valid_scores)
        sample["flag"] = "low" if (mean_score is not None and mean_score < LOW_SCORE_THRESHOLD) else "moderate" if (mean_score is not None and mean_score < 0.85) else "ok"
    return samples


def _aggregate(samples: list[dict]) -> dict:
    """Compute aggregate mean per metric across all samples."""
    agg = {}
    all_metrics = set()
    for s in samples:
        all_metrics.update(s.get("scores", {}).keys())
    for metric in all_metrics:
        vals = [s["scores"].get(metric) for s in samples]
        agg[metric] = _mean_of_nullables(vals)
    return agg


def _save_result(module: str, metadata: dict, aggregate: dict, samples: list, notes: list):
    path = RESULT_DIR / f"{module}.json"
    payload = {
        "module": module,
        "metadata": metadata,
        "aggregate": aggregate,
        "samples": samples,
        "notes": notes,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"  💾 Results saved → {path}")


def _load_dataset(module: str) -> Optional[dict]:
    path = DATASET_DIR / f"{module}.json"
    if not path.exists():
        print(f"  ❌ Dataset not found: {path}")
        print(f"     Run: python evaluation/build_datasets.py --module {module}")
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ─────────────────────────────────────────────
# Per-module evaluation
# ─────────────────────────────────────────────

def eval_legal_qa():
    print("\n── Evaluating legal_qa ──")
    raw = _load_dataset("legal_qa")
    if not raw:
        return

    samples = raw["samples"]
    notes = [
        "Scores use auto-generated references and an LLM judge; treat as indicative, not ground truth.",
        "cites_page_numbers AspectCritic may score low for EXTERNAL mode answers (no page refs in source).",
    ]

    # Build metrics
    metrics = []
    metric_names_used = []

    if Faithfulness:
        metrics.append(Faithfulness())
        metric_names_used.append("faithfulness")
    if ResponseRelevancy:
        metrics.append(ResponseRelevancy())
        metric_names_used.append("response_relevancy")
    if LLMContextPrecisionWithReference:
        metrics.append(LLMContextPrecisionWithReference())
        metric_names_used.append("llm_context_precision_with_reference")
    if ContextRecall:
        metrics.append(ContextRecall())
        metric_names_used.append("context_recall")
    if FactualCorrectness:
        metrics.append(FactualCorrectness())
        metric_names_used.append("factual_correctness")

    # Custom AspectCritic
    if AspectCritic:
        cites_pages = AspectCritic(
            name="cites_page_numbers",
            definition="Does the response cite specific page numbers that appear in the provided context? Answer true only if it does.",
            llm=_make_llm(),
        )
        metrics.append(cites_pages)
        metric_names_used.append("cites_page_numbers")

    null_count = sum(1 for m in metrics if m is None)
    if null_count:
        notes.append(f"{null_count} metric(s) unavailable in this Ragas version and were skipped.")
        metrics = [m for m in metrics if m is not None]

    print(f"  Metrics: {metric_names_used}")
    est_calls = len(samples) * len(metrics)
    print(f"  Estimated LLM calls: ~{est_calls}")

    dataset = _build_dataset(samples)
    scores_by_metric = _run_metrics(dataset, metrics, notes)
    samples = _attach_scores(samples, scores_by_metric)
    aggregate = _aggregate(samples)

    metadata = {
        **raw["metadata"],
        "run_timestamp": RUN_TIMESTAMP,
        "metrics_used": metric_names_used,
        "reference_type": "auto_generated",
        "ragas_version": RAGAS_VERSION,
        "judge_model": JUDGE_MODEL,
    }
    _save_result("legal_qa", metadata, aggregate, samples, notes)
    print(f"  Aggregate: {aggregate}")


def eval_research():
    print("\n── Evaluating research ──")
    raw = _load_dataset("research")
    if not raw:
        return

    samples = raw["samples"]
    notes = [
        "Scores use auto-generated references and an LLM judge; treat as indicative, not ground truth.",
        "Retrieved contexts are snippets from search results; quality depends on backend availability.",
    ]

    metrics = []
    metric_names_used = []

    if LLMContextPrecisionWithReference:
        metrics.append(LLMContextPrecisionWithReference())
        metric_names_used.append("llm_context_precision_with_reference")
    if ContextRecall:
        metrics.append(ContextRecall())
        metric_names_used.append("context_recall")
    if ContextEntityRecall:
        metrics.append(ContextEntityRecall())
        metric_names_used.append("context_entity_recall")

    null_count = sum(1 for m in metrics if m is None)
    if null_count:
        notes.append(f"{null_count} metric(s) unavailable and skipped.")
        metrics = [m for m in metrics if m is not None]

    print(f"  Metrics: {metric_names_used}")
    print(f"  Estimated LLM calls: ~{len(samples) * len(metrics)}")

    dataset = _build_dataset(samples)
    scores_by_metric = _run_metrics(dataset, metrics, notes)
    samples = _attach_scores(samples, scores_by_metric)
    aggregate = _aggregate(samples)

    metadata = {
        **raw["metadata"],
        "run_timestamp": RUN_TIMESTAMP,
        "metrics_used": metric_names_used,
        "reference_type": "auto_generated",
        "ragas_version": RAGAS_VERSION,
        "judge_model": JUDGE_MODEL,
    }
    _save_result("research", metadata, aggregate, samples, notes)
    print(f"  Aggregate: {aggregate}")


def eval_summary():
    print("\n── Evaluating summary ──")
    raw = _load_dataset("summary")
    if not raw:
        return

    samples = raw["samples"]
    notes = [
        "Scores use auto-generated references and an LLM judge; treat as indicative, not ground truth.",
        "SummarizationScore is not available in Ragas 0.2.x; substituted with Faithfulness + ResponseRelevancy.",
        "Marathi-language summaries are not evaluated (English only in this run).",
    ]

    metrics = []
    metric_names_used = []

    # SummarizationScore substitution
    if Faithfulness:
        metrics.append(Faithfulness())
        metric_names_used.append("faithfulness")
        notes.append("faithfulness used as SummarizationScore substitute (factual grounding).")
    if ResponseRelevancy:
        metrics.append(ResponseRelevancy())
        metric_names_used.append("response_relevancy")

    # Custom AspectCritics for summary
    if AspectCritic:
        covers_core = AspectCritic(
            name="covers_core_elements",
            definition="Does the summary cover the facts, the legal issues and the final decision of the case?",
            llm=_make_llm(),
        )
        no_invented = AspectCritic(
            name="no_invented_details",
            definition="Does the summary avoid parties, sections, dates or facts not present in the source? Answer true means no invented details.",
            llm=_make_llm(),
        )
        metrics.extend([covers_core, no_invented])
        metric_names_used.extend(["covers_core_elements", "no_invented_details"])

    null_count = sum(1 for m in metrics if m is None)
    if null_count:
        notes.append(f"{null_count} metric(s) unavailable and skipped.")
        metrics = [m for m in metrics if m is not None]

    print(f"  Metrics: {metric_names_used}")
    print(f"  Estimated LLM calls: ~{len(samples) * len(metrics)}")

    dataset = _build_dataset(samples)
    scores_by_metric = _run_metrics(dataset, metrics, notes)
    samples = _attach_scores(samples, scores_by_metric)
    aggregate = _aggregate(samples)

    metadata = {
        **raw["metadata"],
        "run_timestamp": RUN_TIMESTAMP,
        "metrics_used": metric_names_used,
        "reference_type": "auto_generated",
        "ragas_version": RAGAS_VERSION,
        "judge_model": JUDGE_MODEL,
    }
    _save_result("summary", metadata, aggregate, samples, notes)
    print(f"  Aggregate: {aggregate}")


def eval_comprehension():
    print("\n── Evaluating comprehension ──")
    raw = _load_dataset("comprehension")
    if not raw:
        return

    samples = raw["samples"]
    notes = [
        "Scores use auto-generated references and an LLM judge; treat as indicative, not ground truth.",
        "SemanticSimilarity uses OpenAI text-embedding-3-small (same as Research backend).",
        "Per-field and per-judgment aggregates computed from sample metadata.",
    ]

    metrics = []
    metric_names_used = []

    if Faithfulness:
        metrics.append(Faithfulness())
        metric_names_used.append("faithfulness")
    if FactualCorrectness:
        metrics.append(FactualCorrectness())
        metric_names_used.append("factual_correctness")
    if SemanticSimilarity:
        sem_sim = SemanticSimilarity(embeddings=_make_embeddings())
        metrics.append(sem_sim)
        metric_names_used.append("semantic_similarity")
    if AspectCritic:
        field_complete = AspectCritic(
            name="field_is_complete",
            definition="Does the response fully capture this field from the judgment without omitting key points?",
            llm=_make_llm(),
        )
        metrics.append(field_complete)
        metric_names_used.append("field_is_complete")

    null_count = sum(1 for m in metrics if m is None)
    if null_count:
        notes.append(f"{null_count} metric(s) unavailable and skipped.")
        metrics = [m for m in metrics if m is not None]

    print(f"  Metrics: {metric_names_used}")
    print(f"  Estimated LLM calls: ~{len(samples) * len(metrics)}")

    dataset = _build_dataset(samples)
    scores_by_metric = _run_metrics(dataset, metrics, notes)
    samples = _attach_scores(samples, scores_by_metric)
    aggregate = _aggregate(samples)

    # Build per-field aggregate
    field_agg: dict[str, dict] = {}
    for s in samples:
        field = s.get("field", "unknown")
        if field not in field_agg:
            field_agg[field] = []
        valid_scores = [v for v in s.get("scores", {}).values() if v is not None]
        if valid_scores:
            field_agg[field].append(sum(valid_scores) / len(valid_scores))

    field_means = {f: (_mean_of_nullables(vals) if vals else None) for f, vals in field_agg.items()}

    metadata = {
        **raw["metadata"],
        "run_timestamp": RUN_TIMESTAMP,
        "metrics_used": metric_names_used,
        "reference_type": "auto_generated",
        "ragas_version": RAGAS_VERSION,
        "judge_model": JUDGE_MODEL,
        "per_field_aggregate": field_means,
    }
    _save_result("comprehension", metadata, aggregate, samples, notes)
    print(f"  Aggregate: {aggregate}")
    print(f"  Per-field: {field_means}")


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Run Ragas evaluation")
    parser.add_argument(
        "--module",
        default="all",
        choices=["all", "legal_qa", "research", "summary", "comprehension"],
    )
    args = parser.parse_args()

    if not OPENAI_API_KEY:
        print("❌ OPENAI_API_KEY not set.")
        sys.exit(1)

    mods = (
        ["legal_qa", "research", "summary", "comprehension"]
        if args.module == "all"
        else [args.module]
    )

    for mod in mods:
        try:
            if mod == "legal_qa":
                eval_legal_qa()
            elif mod == "research":
                eval_research()
            elif mod == "summary":
                eval_summary()
            elif mod == "comprehension":
                eval_comprehension()
        except Exception as e:
            print(f"  ❌ Evaluation failed for {mod}: {e}")
            traceback.print_exc()

    print("\n✅ Evaluation complete.")


if __name__ == "__main__":
    main()
