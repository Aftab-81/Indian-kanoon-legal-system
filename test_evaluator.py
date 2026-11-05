import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path("d:/Multiple Projects/Legal_System-main/evaluation")))
from config import JUDGE_MODEL
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from ragas.dataset_schema import SingleTurnSample, EvaluationDataset
from ragas.metrics import Faithfulness, ResponseRelevancy, LLMContextPrecisionWithReference, ContextRecall
from ragas.llms import LangchainLLMWrapper
from ragas import evaluate

q = "What is the capital of France?"
ans = "The capital of France is Paris."
contexts = ["Paris is the capital and most populous city of France."]
reference = "Paris"

llm = ChatOpenAI(model=JUDGE_MODEL, temperature=0.0)

try:
    print("Testing LLM Invoke...")
    raw = llm.invoke([HumanMessage(content="Hello")]).content
    print("LLM generated:", raw)
except Exception as e:
    print("LLM Error:", e)

try:
    print("Testing Ragas...")
    sample = SingleTurnSample(
        user_input=q,
        response=ans,
        retrieved_contexts=contexts,
        reference=reference
    )
    dataset = EvaluationDataset(samples=[sample])
    metrics = [Faithfulness(), ResponseRelevancy(), LLMContextPrecisionWithReference(), ContextRecall()]
    wrapper = LangchainLLMWrapper(llm)
    res = evaluate(dataset, metrics=metrics, llm=wrapper, raise_exceptions=True)
    df = res.to_pandas()
    print("Ragas results:")
    for m in metrics:
        if m.name in df.columns:
            print(f"{m.name}: {df[m.name].mean():.4f}")
except Exception as e:
    print("Ragas Error:", e)
