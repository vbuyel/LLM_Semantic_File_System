"""
RAG evaluation script: LLM-as-judge scoring for groundedness and context relevance.

Why this matters for your CV claim ("79% context relevance"):
    A single aggregate number is not defensible on its own in an interview. What makes
    it credible is: (1) a fixed test set, (2) an explicit scoring rubric, (3) a named
    judge model, and (4) per-case results you can show if asked. This script produces
    all of that.

Usage:
    1. Fill in test_cases.json with your 50 (or however many) test cases:
       [
         {"query": "...", "retrieved_context": "..."},
         ...
       ]
    2. Set ANTHROPIC_API_KEY (or point OLLAMA_URL at your local Ollama instance).
    3. python rag_eval.py --input test_cases.json --output results.json --judge ollama
"""

import argparse
import json
import os
import re
import statistics
import urllib.request


GROUNDEDNESS_RUBRIC = """You are evaluating a RAG system's answer for GROUNDEDNESS.
Groundedness = every factual claim in the answer is directly supported by the
retrieved context (no hallucination, no unsupported claims).

Query: {query}
Retrieved context: {context}
Generated answer: {answer}

Score groundedness from 0 to 100, where:
- 100 = every claim is fully supported by the context
- 50 = some claims supported, some not
- 0 = answer is unsupported by or contradicts the context

Respond with ONLY a JSON object: {{"score": <int 0-100>, "reasoning": "<one sentence>"}}
"""

RELEVANCE_RUBRIC = """You are evaluating a RAG system's retrieved context for CONTEXT RELEVANCE.
Context relevance = how much of the retrieved context is actually relevant/useful
for answering the query (not noise or off-topic).

Query: {query}
Retrieved context: {context}

Score relevance from 0 to 100, where:
- 100 = all retrieved context is relevant to the query
- 50 = about half the context is relevant
- 0 = context is irrelevant to the query

Respond with ONLY a JSON object: {{"score": <int 0-100>, "reasoning": "<one sentence>"}}
"""


def call_ollama(prompt, model="gemma4:e4b", url=None):
    url = url or os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
    body = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    return data["response"]


def call_anthropic(prompt, model="claude-sonnet-4-6"):
    api_key = os.environ["ANTHROPIC_API_KEY"]
    body = json.dumps({
        "model": model,
        "max_tokens": 200,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    return data["content"][0]["text"]


def extract_json_score(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None, "could not parse judge response"
    try:
        obj = json.loads(match.group(0))
        return obj.get("score"), obj.get("reasoning", "")
    except json.JSONDecodeError:
        return None, "could not parse judge response"


def judge(prompt, backend, model):
    raw = call_ollama(prompt, model=model) if backend == "ollama" else call_anthropic(prompt, model=model)
    return extract_json_score(raw)


def evaluate(test_cases, backend, model):
    results = []
    for i, case in enumerate(test_cases):
        query = case.get("query", "")
        context = case.get("context") or case.get("retrieved_context", "")
        # Accept both legacy ("generated_answer"/"answer") and context-only datasets.
        answer = case.get("answer") or case.get("generated_answer") or context

        prompt_vars = {
            "query": query,
            "context": context,
            "answer": answer,
        }
        g_score, g_reason = judge(
            GROUNDEDNESS_RUBRIC.format(**prompt_vars), backend, model
        )
        r_score, r_reason = judge(
            RELEVANCE_RUBRIC.format(**prompt_vars), backend, model
        )
        results.append({
            "index": i,
            "query": query,
            "groundedness_score": g_score,
            "groundedness_reasoning": g_reason,
            "relevance_score": r_score,
            "relevance_reasoning": r_reason,
        })
        print(f"[{i+1}/{len(test_cases)}] groundedness={g_score} relevance={r_score}")
    return results


def summarize(results):
    g_scores = [r["groundedness_score"] for r in results if r["groundedness_score"] is not None]
    r_scores = [r["relevance_score"] for r in results if r["relevance_score"] is not None]
    return {
        "n_cases": len(results),
        "avg_groundedness": round(statistics.mean(g_scores), 1) if g_scores else None,
        "avg_context_relevance": round(statistics.mean(r_scores), 1) if r_scores else None,
    }


def main():
    parser = argparse.ArgumentParser(description="RAG LLM-as-judge evaluator")
    parser.add_argument("--input", required=True, help="Path to test_cases.json")
    parser.add_argument("--output", default="results.json", help="Path to write results")
    parser.add_argument("--judge", choices=["ollama", "anthropic"], default="ollama")
    parser.add_argument("--model", default="gemma4:e4b", help="Judge model name")
    args = parser.parse_args()

    with open(args.input) as f:
        test_cases = json.load(f)

    results = evaluate(test_cases, args.judge, args.model)
    summary = summarize(results)

    with open(args.output, "w") as f:
        json.dump({"summary": summary, "results": results}, f, indent=2)

    print("-" * 50)
    print(f"Judge model: {args.judge}/{args.model}")
    print(f"Test cases:  {summary['n_cases']}")
    print(f"Avg groundedness:      {summary['avg_groundedness']}%")
    print(f"Avg context relevance: {summary['avg_context_relevance']}%")
    print(f"Full results written to {args.output}")
    print("Keep results.json — it's your evidence if an interviewer asks how you got this number.")


if __name__ == "__main__":
    main()
