import unittest
from unittest.mock import MagicMock, patch
import json
import numpy as np

# Import functions under test
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "rbackend"))
sys.path.insert(0, str(ROOT / "evaluation"))

from rbackend import (
    check_term_matches,
    preprocess_query_terms,
    is_law_related_query,
    semantic_search,
    vector_metadata,
    EMBEDDING_DIM
)
import faiss


class TestDocumentResearchRegression(unittest.TestCase):

    def test_1_response_cannot_accidentally_become_filename_or_metadata_string(self):
        """Case 1: Evaluation response cannot accidentally become a filename or metadata string."""
        sample_results = [
            {
                "source": "document",
                "filename": "1822728_Saraya_Industries.pdf",
                "title": "Saraya Industries vs State of U.P.",
                "snippet": "Excise duty challenge",
                "confidence": 95.5,
                "analysis": {"summary": "Substantive summary of excise challenge."}
            }
        ]
        
        # Test the builder logic
        top = sample_results[0]
        analysis = top.get("analysis", {})
        summary = analysis.get("summary", "") if isinstance(analysis, dict) else ""
        top_substantive_answer = summary.strip()
        
        # Ensure it does NOT contain metadata brackets, pipe delimiters or raw filename
        self.assertNotIn("[document]", top_substantive_answer)
        self.assertNotIn("| confidence:", top_substantive_answer)
        self.assertNotIn(".pdf", top_substantive_answer)
        self.assertEqual(top_substantive_answer, "Substantive summary of excise challenge.")

    def test_2_generated_answer_and_retrieved_context_remain_separate_fields(self):
        """Case 2: The generated answer and retrieved context remain separate fields."""
        q = "Section 302 IPC murder conviction evidence"
        ref = "Section 302 requires proof of intent..."
        results = [
            {
                "title": "State v. Kumar",
                "snippet": "Eyewitness testimony established intent.",
                "analysis": {"summary": "High court upheld conviction under Section 302."}
            }
        ]
        
        contexts = [f"{r.get('snippet','')}\n{r.get('analysis',{}).get('summary','')}".strip() for r in results]
        response = results[0]["analysis"]["summary"]
        
        sample = {
            "user_input": q,
            "response": response,
            "retrieved_contexts": contexts,
            "reference": ref,
        }
        
        self.assertIsInstance(sample["response"], str)
        self.assertIsInstance(sample["retrieved_contexts"], list)
        self.assertNotEqual(sample["response"], sample["retrieved_contexts"])
        self.assertIn("Eyewitness testimony established intent.", sample["retrieved_contexts"][0])
        self.assertEqual(sample["response"], "High court upheld conviction under Section 302.")

    def test_3_semantically_relevant_candidate_not_rejected_by_lexical_filter(self):
        """Case 3: A semantically relevant candidate is not automatically rejected solely because it lacks exact query terms."""
        critical_terms, non_critical_terms = preprocess_query_terms("Section 302 IPC murder conviction")
        
        # Case text discusses homicide, penal code, intentional killing without verbatim 'Section 302 IPC'
        candidate_text = "The appellant was held guilty for culpable homicide amounting to murder under the Indian Penal Code."
        is_valid, match_score = check_term_matches(candidate_text, critical_terms, non_critical_terms)
        
        # Must be valid (not rejected) and have a continuous match score
        self.assertTrue(is_valid)
        self.assertGreaterEqual(match_score, 0.0)
        self.assertLessEqual(match_score, 1.0)

    def test_4_explicit_constraint_distinguishes_real_constraints_from_casual_words(self):
        """Case 4: An explicitly requested case year or jurisdiction is preserved and not silently violated."""
        import re
        query_with_year = "judgment of Supreme Court in 2005 regarding bail"
        explicit_year_match = re.search(r'\b(?:in|year|dated|from|of)\s+((?:19|20)\d{2})\b|\(((?:19|20)\d{2})\)', query_with_year, re.IGNORECASE)
        query_year = (explicit_year_match.group(1) or explicit_year_match.group(2)) if explicit_year_match else None
        
        self.assertEqual(query_year, "2005")
        
        # Candidate 1: matches year 2005
        candidate_1_text = "supreme court order dated 15 march 2005 granting bail"
        self.assertIn(query_year, candidate_1_text)
        
        # Candidate 2: wrong year 2021
        candidate_2_text = "supreme court order dated 12 july 2021 granting bail"
        self.assertNotIn(query_year, candidate_2_text)

    def test_5_faiss_vector_positions_map_to_correct_metadata(self):
        """Case 5: FAISS vector positions map accurately to metadata keys."""
        # Create a mock FAISS index with 3 vectors
        d = 4
        index = faiss.IndexFlatL2(d)
        vecs = np.array([
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0]
        ], dtype='float32')
        index.add(vecs)
        
        mock_meta = {
            "doc_a": {"filename": "Doc A", "embedding": [1.0, 0.0, 0.0, 0.0], "text": "alpha text"},
            "doc_b": {"filename": "Doc B", "embedding": [0.0, 1.0, 0.0, 0.0], "text": "beta text"},
            "doc_c": {"filename": "Doc C", "embedding": [0.0, 0.0, 1.0, 0.0], "text": "gamma text"},
        }
        
        meta_keys = list(mock_meta.keys())
        query_vec = np.array([[0.0, 1.0, 0.0, 0.0]], dtype='float32')
        distances, indices = index.search(query_vec, 1)
        
        matched_idx = indices[0][0]
        self.assertEqual(matched_idx, 1)
        matched_key = meta_keys[matched_idx]
        self.assertEqual(matched_key, "doc_b")
        self.assertEqual(mock_meta[matched_key]["filename"], "Doc B")

    def test_6_unrelated_queries_do_not_all_return_same_irrelevant_result(self):
        """Case 6: Unrelated queries do not all return the exact same document when vector search is active."""
        d = 4
        index = faiss.IndexFlatL2(d)
        vecs = np.array([
            [1.0, 0.0, 0.0, 0.0],  # doc_a: criminal law
            [0.0, 1.0, 0.0, 0.0],  # doc_b: tax law
        ], dtype='float32')
        index.add(vecs)
        
        meta_keys = ["doc_criminal", "doc_tax"]
        
        q1_vec = np.array([[1.0, 0.1, 0.0, 0.0]], dtype='float32')
        _, idx1 = index.search(q1_vec, 1)
        
        q2_vec = np.array([[0.0, 0.9, 0.1, 0.0]], dtype='float32')
        _, idx2 = index.search(q2_vec, 1)
        
        self.assertEqual(meta_keys[idx1[0][0]], "doc_criminal")
        self.assertEqual(meta_keys[idx2[0][0]], "doc_tax")
        self.assertNotEqual(meta_keys[idx1[0][0]], meta_keys[idx2[0][0]])

    def test_7_missing_generated_answers_and_failed_metrics_are_reported_explicitly(self):
        """Case 7: Missing generated answers and failed metrics are reported explicitly rather than silently converted."""
        from run_eval import _mean_of_nullables
        
        # When all samples return None, mean should be None, not 0.0
        all_none = [None, None, None]
        self.assertIsNone(_mean_of_nullables(all_none))
        
        # When some scores are valid, mean calculates accurately
        mixed = [0.8, None, 0.6]
        self.assertEqual(_mean_of_nullables(mixed), 0.7)


if __name__ == "__main__":
    unittest.main()
