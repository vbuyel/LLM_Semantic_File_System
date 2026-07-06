#!/usr/bin/env python3
"""
LLM quality benchmarks for Semantic FS.

Metrics:
  - ttft              Time to First Token (streaming generation latency)
  - context_relevance Retrieved document relevance to the user query
  - groundedness      Faithfulness — answer supported by retrieved context
  - answer_relevance  Final answer usefulness for the user query
  - all               Run every metric
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

# Allow imports from the LLM microservice package.
LLM_ROOT = Path(__file__).resolve().parents[2] / "src" / "llm"
sys.path.insert(0, str(LLM_ROOT))
load_dotenv(dotenv_path=LLM_ROOT / ".env")

from adapters.rag_search import RAGSearch  # noqa: E402
from adapters.kafka import Kafka  # noqa: E402

BENCHMARK_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = BENCHMARK_ROOT / "llm" / "dataset_50.json"
DEFAULT_RESULTS_DIR = BENCHMARK_ROOT / "results"

SYSTEM_PROMPT = (
    "You are a research assistant with access to the user's personal files.\n"
    "Answer using ONLY the provided document context. "
    "If the context does not contain the answer, say so clearly. "
    "Reply in the same language as the user's question."
)


@dataclass
class CaseResult:
    case_id: str
    query: str
    ttft_ms: float | None = None
    total_generation_ms: float | None = None
    context_relevance: float | None = None
    groundedness: float | None = None
    answer_relevance: float | None = None
    answer_preview: str = ""
    context_preview: str = ""
    error: str | None = None


def _client() -> OpenAI:
    return OpenAI(
        base_url=os.getenv("BASE_MODEL_URL"),
        api_key=os.getenv("OPENAI_API_KEY", "ollama"),
    )


def _model() -> str:
    model = os.getenv("MODEL")
    if not model:
        raise RuntimeError("MODEL is not set in src/llm/.env")
    return model


def _parse_score(text: str) -> float | None:
    text = text.strip()
    if not text:
        return None

    try:
        payload = json.loads(text)
        if isinstance(payload, dict) and "score" in payload:
            return max(0.0, min(1.0, float(payload["score"])))
    except json.JSONDecodeError:
        pass

    for pattern in (
        r'"score"\s*:\s*(0(?:\.\d+)?|1(?:\.0+)?)',
        r"(?:score|rating|relevance|groundedness)\s*[:=]\s*(0(?:\.\d+)?|1(?:\.0+)?)",
        r"\b(0(?:\.\d+)?|1(?:\.0+)?)\b",
    ):
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        if matches:
            return max(0.0, min(1.0, float(matches[-1])))

    return None


def _message_text(message: Any) -> str:
    parts: list[str] = []
    content = getattr(message, "content", None)
    if content:
        parts.append(str(content))

    reasoning = getattr(message, "reasoning", None)
    if reasoning:
        parts.append(str(reasoning))

    if hasattr(message, "model_dump"):
        dump = message.model_dump()
        if dump.get("reasoning"):
            parts.append(str(dump["reasoning"]))

    return "\n".join(parts)


def _heuristic_context_relevance(query: str, context: str) -> float:
    lowered = context.lower()
    if "no relevant files found" in lowered:
        return 0.0

    query_tokens = {token for token in re.findall(r"[a-z0-9]{4,}", query.lower())}
    context_tokens = set(re.findall(r"[a-z0-9]{4,}", lowered))
    if not query_tokens:
        return 0.0
    overlap = len(query_tokens & context_tokens) / len(query_tokens)
    return round(min(1.0, 0.35 + overlap * 0.65), 2)


def _heuristic_groundedness(context: str, answer: str) -> float:
    if "no relevant files found" in context.lower():
        return 1.0 if "not contain" in answer.lower() or "cannot" in answer.lower() else 0.2

    answer_tokens = set(re.findall(r"[a-z0-9]{5,}", answer.lower()))
    context_tokens = set(re.findall(r"[a-z0-9]{5,}", context.lower()))
    if not answer_tokens:
        return 0.0
    supported = len(answer_tokens & context_tokens) / len(answer_tokens)
    return round(min(1.0, supported), 2)


def _heuristic_answer_relevance(query: str, answer: str, reference_answer: str | None) -> float:
    if "no relevant files" in answer.lower() or "does not contain" in answer.lower():
        return 0.1

    query_tokens = set(re.findall(r"[a-z0-9]{4,}", query.lower()))
    answer_tokens = set(re.findall(r"[a-z0-9]{4,}", answer.lower()))
    if not query_tokens:
        return 0.0

    overlap = len(query_tokens & answer_tokens) / len(query_tokens)
    score = min(1.0, 0.25 + overlap * 0.75)

    if reference_answer:
        ref_tokens = set(re.findall(r"[a-z0-9]{4,}", reference_answer.lower()))
        if ref_tokens:
            ref_overlap = len(ref_tokens & answer_tokens) / len(ref_tokens)
            score = max(score, min(1.0, ref_overlap))

    return round(score, 2)


def _judge(client: OpenAI, prompt: str, heuristic_score: float) -> float:
    response = client.chat.completions.create(
        model=_model(),
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an evaluation judge. "
                    "Respond with one line only: {\"score\": 0.0} to {\"score\": 1.0}."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=512,
    )
    text = _message_text(response.choices[0].message)
    parsed = _parse_score(text)
    if parsed is not None:
        return parsed
    return heuristic_score


def _stream_generation(
    client: OpenAI,
    query: str,
    context: str,
) -> tuple[str, float | None, float]:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Question:\n{query}\n\n"
                f"Document context:\n{context}\n\n"
                "Answer the question using the context above."
            ),
        },
    ]

    start = time.perf_counter()
    ttft_ms: float | None = None
    parts: list[str] = []

    stream = client.chat.completions.create(
        model=_model(),
        messages=messages,
        temperature=0.3,
        max_tokens=1024,
        stream=True,
    )

    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            if ttft_ms is None:
                ttft_ms = (time.perf_counter() - start) * 1000
            parts.append(delta)

    total_ms = (time.perf_counter() - start) * 1000
    return "".join(parts).strip(), ttft_ms, total_ms


def _score_context_relevance(client: OpenAI, query: str, context: str) -> float:
    heuristic = _heuristic_context_relevance(query, context)
    prompt = (
        "Rate how relevant the retrieved documents are to the user query.\n"
        "1.0 = perfectly relevant documents; 0.0 = completely irrelevant or empty.\n\n"
        f"User query:\n{query}\n\n"
        f"Retrieved context:\n{context[:6000]}\n\n"
        "Return JSON: {\"score\": <float>}"
    )
    return _judge(client, prompt, heuristic)


def _score_groundedness(client: OpenAI, context: str, answer: str) -> float:
    heuristic = _heuristic_groundedness(context, answer)
    prompt = (
        "Rate whether the answer is fully grounded in the provided context "
        "(no hallucinations or unsupported claims).\n"
        "1.0 = every claim is supported by context; 0.0 = mostly hallucinated.\n\n"
        f"Context:\n{context[:6000]}\n\n"
        f"Answer:\n{answer[:3000]}\n\n"
        "Return JSON: {\"score\": <float>}"
    )
    return _judge(client, prompt, heuristic)


def _score_answer_relevance(
    client: OpenAI,
    query: str,
    answer: str,
    reference_answer: str | None = None,
) -> float:
    heuristic = _heuristic_answer_relevance(query, answer, reference_answer)
    reference_block = ""
    if reference_answer:
        reference_block = f"\nReference answer (optional):\n{reference_answer}\n"

    prompt = (
        "Rate how well the answer addresses the user's question and solves their problem.\n"
        "1.0 = directly answers the question; 0.0 = off-topic or useless.\n\n"
        f"User query:\n{query}\n"
        f"{reference_block}\n"
        f"Model answer:\n{answer[:3000]}\n\n"
        "Return JSON: {\"score\": <float>}"
    )
    return _judge(client, prompt, heuristic)


async def _retrieve_context(rag: RAGSearch, query: str, owner: str) -> str:
    correlation_id = str(uuid.uuid4())
    response = await rag.do_search(query, owner, correlation_id)
    return response.text.strip()


async def _evaluate_case(
    rag: RAGSearch,
    client: OpenAI,
    case: dict[str, Any],
    owner: str,
    metrics: set[str],
) -> CaseResult:
    case_id = case["id"]
    query = case["query"]
    reference_answer = case.get("reference_answer")
    result = CaseResult(case_id=case_id, query=query)

    try:
        context = await _retrieve_context(rag, query, owner)
        result.context_preview = context[:240].replace("\n", " ")

        answer = ""
        ttft_ms: float | None = None
        total_ms: float | None = None
        needs_generation = bool(
            metrics & {"ttft", "groundedness", "answer_relevance", "all"}
        )

        if needs_generation:
            answer, ttft_ms, total_ms = _stream_generation(client, query, context)
            result.answer_preview = answer[:240].replace("\n", " ")
            if "ttft" in metrics or "all" in metrics:
                result.ttft_ms = ttft_ms
                result.total_generation_ms = total_ms

        if "context_relevance" in metrics or "all" in metrics:
            result.context_relevance = _score_context_relevance(client, query, context)

        if ("groundedness" in metrics or "all" in metrics) and answer:
            result.groundedness = _score_groundedness(client, context, answer)

        if ("answer_relevance" in metrics or "all" in metrics) and answer:
            result.answer_relevance = _score_answer_relevance(
                client, query, answer, reference_answer
            )
    except Exception as exc:
        result.error = str(exc)

    return result


def _avg(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = int(pct * len(ordered))
    if index < 0:
        index = 0
    if index >= len(ordered):
        index = len(ordered) - 1
    return ordered[index]


def _summarize(results: list[CaseResult], metric: str) -> dict[str, Any]:
    summary: dict[str, Any] = {"metric": metric, "cases": len(results)}

    def collect(field: str) -> list[float]:
        out: list[float] = []
        for item in results:
            value = getattr(item, field)
            if value is not None and item.error is None:
                out.append(float(value))
        return out

    for field in (
        "ttft_ms",
        "total_generation_ms",
        "context_relevance",
        "groundedness",
        "answer_relevance",
    ):
        values = collect(field)
        if values:
            avg = _avg(values) or 0.0
            summary[f"avg_{field}"] = round(avg, 2)
            summary[f"min_{field}"] = round(min(values), 2)
            summary[f"max_{field}"] = round(max(values), 2)
            summary[f"p50_{field}"] = round(_percentile(values, 0.50), 2)
            summary[f"p95_{field}"] = round(_percentile(values, 0.95), 2)
            if len(values) > 1:
                variance = sum((value - avg) ** 2 for value in values) / len(values)
                summary[f"std_{field}"] = round(variance ** 0.5, 2)

    summary["errors"] = sum(1 for item in results if item.error)
    summary["successful_cases"] = len(results) - summary["errors"]
    return summary


async def _close_kafka() -> None:
    kafka = Kafka()
    if kafka._consumer is not None:
        await kafka._consumer.stop()
        kafka._consumer = None
    if kafka._producer is not None:
        await kafka._producer.stop()
        kafka._producer = None


async def _run(args: argparse.Namespace) -> int:
    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print(f"ERROR: dataset not found: {dataset_path}", file=sys.stderr)
        return 1

    with dataset_path.open(encoding="utf-8") as handle:
        dataset = json.load(handle)

    owner = args.owner or dataset.get("owner", "benchmark@local.test")
    cases = dataset.get("cases", [])
    if not cases:
        print("ERROR: dataset contains no cases", file=sys.stderr)
        return 1

    if args.limit is not None:
        cases = cases[: args.limit]

    min_cases = args.min_cases
    if len(cases) < min_cases:
        print(
            f"ERROR: dataset has {len(cases)} cases but --min-cases={min_cases}",
            file=sys.stderr,
        )
        return 1

    metrics = {args.metric}
    if args.metric == "all":
        metrics = {"all"}

    print(f"Running {len(cases)} evaluation case(s)...")
    rag = RAGSearch()
    client = _client()
    results: list[CaseResult] = []

    try:
        for index, case in enumerate(cases, start=1):
            case_id = case["id"]
            print(f"[{index}/{len(cases)}] Evaluating case: {case_id} ...", flush=True)
            case_started = time.perf_counter()
            result = await _evaluate_case(rag, client, case, owner, metrics)
            results.append(result)
            case_elapsed = time.perf_counter() - case_started

            if result.error:
                print(f"  ERROR ({case_id}): {result.error}", flush=True)
                continue

            if args.verbose:
                if result.ttft_ms is not None:
                    print(
                        f"  ttft_ms={result.ttft_ms:.2f} "
                        f"total_generation_ms={result.total_generation_ms:.2f}",
                        flush=True,
                    )
                if result.context_relevance is not None:
                    print(f"  context_relevance={result.context_relevance:.2f}", flush=True)
                if result.groundedness is not None:
                    print(f"  groundedness={result.groundedness:.2f}", flush=True)
                if result.answer_relevance is not None:
                    print(f"  answer_relevance={result.answer_relevance:.2f}", flush=True)
            else:
                parts = [f"done in {case_elapsed:.1f}s"]
                if result.ttft_ms is not None:
                    parts.append(f"ttft={result.ttft_ms:.0f}ms")
                if result.context_relevance is not None:
                    parts.append(f"ctx={result.context_relevance:.2f}")
                if result.groundedness is not None:
                    parts.append(f"ground={result.groundedness:.2f}")
                if result.answer_relevance is not None:
                    parts.append(f"answer={result.answer_relevance:.2f}")
                print(f"  {' | '.join(parts)}", flush=True)

            if index % args.progress_every == 0 or index == len(cases):
                errors = sum(1 for item in results if item.error)
                print(
                    f"  progress: {index}/{len(cases)} complete (errors={errors})",
                    flush=True,
                )
    finally:
        await _close_kafka()

    summary = _summarize(results, args.metric)
    print("")
    print("Summary:")
    for key, value in summary.items():
        print(f"  {key}={value}")

    args.results_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.results_dir / f"llm_{args.metric}_{time.strftime('%Y%m%d_%H%M%S')}.json"
    payload = {
        "summary": summary,
        "results": [asdict(item) for item in results],
    }
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved: {output_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Semantic FS LLM quality benchmarks")
    parser.add_argument(
        "--metric",
        required=True,
        choices=[
            "ttft",
            "context_relevance",
            "groundedness",
            "answer_relevance",
            "all",
        ],
    )
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--owner", default=None)
    parser.add_argument("--results-dir", default=str(DEFAULT_RESULTS_DIR))
    parser.add_argument("--limit", type=int, default=None, help="Max number of cases to run")
    parser.add_argument("--min-cases", type=int, default=1, help="Fail if dataset has fewer cases")
    parser.add_argument("--verbose", action="store_true", help="Print per-case metrics")
    parser.add_argument(
        "--progress-every",
        type=int,
        default=10,
        help="Print progress every N cases (non-verbose mode)",
    )
    args = parser.parse_args()
    args.results_dir = Path(args.results_dir)
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
