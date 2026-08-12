"""Run a small DeepEval experiment on saved OrbitTech benchmark artifacts.

This script is optional bonus work for Exercise 3.4. It does not replace the
required evaluator in template.py.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from deepeval.metrics import (
    AnswerRelevancyMetric,
    ContextualPrecisionMetric,
    ContextualRecallMetric,
    FaithfulnessMetric,
)
from deepeval.models import DeepEvalBaseLLM
from deepeval.test_case import LLMTestCase


class GroqDeepEvalModel(DeepEvalBaseLLM):
    def __init__(self, model: str, api_keys: list[str]) -> None:
        self.model_name = model
        self.api_keys = api_keys
        self.next_key_index = 0
        super().__init__(model=model)

    def load_model(self) -> "GroqDeepEvalModel":
        return self

    def _call(self, prompt: str, json_mode: bool = False) -> str:
        errors: list[str] = []
        for attempt in range(len(self.api_keys)):
            index = (self.next_key_index + attempt) % len(self.api_keys)
            client = OpenAI(
                api_key=self.api_keys[index],
                base_url="https://api.groq.com/openai/v1",
            )
            try:
                kwargs: dict[str, Any] = {
                    "model": self.model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0,
                    "max_tokens": 1200,
                }
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}
                response = client.chat.completions.create(
                    **kwargs,
                )
                self.next_key_index = (index + 1) % len(self.api_keys)
                return (response.choices[0].message.content or "").strip()
            except Exception as exc:  # DeepEval should continue with next key.
                errors.append(f"key #{index + 1}: {exc}")
        raise RuntimeError("All Groq keys failed: " + " | ".join(errors))

    def generate(self, prompt: str, *args: Any, **kwargs: Any) -> str:
        return self._call(prompt, json_mode=kwargs.get("schema") is not None)

    async def a_generate(self, prompt: str, *args: Any, **kwargs: Any) -> str:
        return await asyncio.to_thread(
            self._call,
            prompt,
            kwargs.get("schema") is not None,
        )

    def get_model_name(self) -> str:
        return f"groq/{self.model_name}"

    def supports_json_mode(self) -> bool:
        return True

    def supports_structured_outputs(self) -> bool:
        return True


def _groq_keys() -> list[str]:
    keys: list[str] = []
    for index in range(1, 5):
        value = os.getenv(f"GROQ_API_KEY_{index}", "").strip()
        if value and not value.startswith("gsk_your_"):
            keys.append(value)
    keys.extend(
        value.strip()
        for value in os.getenv("GROQ_API_KEYS", "").split(",")
        if value.strip() and not value.strip().startswith("gsk_your_")
    )
    if not keys:
        raise RuntimeError("No real GROQ_API_KEY_1..4 found in .env")
    return keys


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _selected_records(
    golden_path: Path,
    actual_path: Path,
    ids: set[str],
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    golden = _read_json(golden_path)
    actual = _read_json(actual_path)
    golden_by_id = {record["id"]: record for record in golden["qa_pairs"]}
    selected: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for answer in actual["answers"]:
        if answer["id"] in ids:
            selected.append((golden_by_id[answer["id"]], answer))
    return selected


def _measure(metric: Any, test_case: LLMTestCase) -> dict[str, Any]:
    try:
        metric.measure(test_case)
        return {
            "score": float(metric.score) if metric.score is not None else None,
            "reason": metric.reason,
            "success": metric.is_successful(),
            "error": None,
        }
    except Exception as exc:
        return {
            "score": None,
            "reason": None,
            "success": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--golden", type=Path, default=Path("golden_dataset.json"))
    parser.add_argument("--actual", type=Path, default=Path("artifacts/actual_answers.json"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/deepeval_results.json"))
    parser.add_argument("--ids", default="")
    parser.add_argument("--include-reason", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_dotenv(Path(__file__).resolve().with_name(".env"))
    ids = {item.strip() for item in args.ids.split(",") if item.strip()}
    if not ids:
        ids = {
            record["id"]
            for record in _read_json(args.golden)["qa_pairs"]
        }
    model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
    judge = GroqDeepEvalModel(model_name, _groq_keys())

    selected_records = _selected_records(args.golden, args.actual, ids)
    results: list[dict[str, Any]] = []
    for golden, answer in _selected_records(args.golden, args.actual, ids):
        test_case = LLMTestCase(
            input=golden["question"],
            actual_output=answer["actual_answer"],
            expected_output=golden["expected_answer"],
            retrieval_context=[
                context["text"] for context in answer["retrieved_contexts"]
            ],
        )
        faithfulness = FaithfulnessMetric(
            threshold=0.7,
            model=judge,
            include_reason=args.include_reason,
            async_mode=False,
        )
        answer_relevancy = AnswerRelevancyMetric(
            threshold=0.7,
            model=judge,
            include_reason=args.include_reason,
            async_mode=False,
        )
        contextual_recall = ContextualRecallMetric(
            threshold=0.7,
            model=judge,
            include_reason=args.include_reason,
            async_mode=False,
        )
        contextual_precision = ContextualPrecisionMetric(
            threshold=0.7,
            model=judge,
            include_reason=args.include_reason,
            async_mode=False,
        )
        results.append(
            {
                "id": golden["id"],
                "question": golden["question"],
                "actual_answer": answer["actual_answer"],
                "expected_answer": golden["expected_answer"],
                "faithfulness": _measure(faithfulness, test_case),
                "answer_relevancy": _measure(answer_relevancy, test_case),
                "contextual_recall": _measure(contextual_recall, test_case),
                "contextual_precision": _measure(contextual_precision, test_case),
            }
        )
        partial_summary = _summarize(results)
        partial_artifact = {
            "provider": "groq",
            "model": model_name,
            "framework": "deepeval",
            "completed": len(results),
            "total": len(selected_records),
            "summary": partial_summary,
            "results": results,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(partial_artifact, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    summary = _summarize(results)
    artifact = {
        "provider": "groq",
        "model": model_name,
        "framework": "deepeval",
        "completed": len(results),
        "total": len(selected_records),
        "summary": summary,
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"summary": summary, "output": str(args.output)}, ensure_ascii=False, indent=2))
    return 0


def _summarize(results: list[dict[str, Any]]) -> dict[str, float | None]:
    metric_names = (
        "faithfulness",
        "answer_relevancy",
        "contextual_recall",
        "contextual_precision",
    )
    summary: dict[str, float | None] = {}
    for metric in metric_names:
        values = [
            item[metric]["score"]
            for item in results
            if item.get(metric, {}).get("score") is not None
        ]
        summary[metric] = sum(values) / len(values) if values else None
    return summary


if __name__ == "__main__":
    raise SystemExit(main())
