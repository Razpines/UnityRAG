from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from unity_docs_mcp.config import UNITY_VERSION_ENV, load_config
from unity_docs_mcp.paths import make_paths
from unity_docs_mcp.tools.ops import DocStore


@dataclass
class EvalCase:
    case_id: str
    query: str
    expected_doc_ids: list[str]
    source_types: list[str] | None = None


def _load_dataset(path: Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    with path.open("r", encoding="utf-8") as handle:
        for idx, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            case_id = str(row.get("id") or f"case-{idx}")
            query = str(row["query"]).strip()
            expected = [str(item) for item in row.get("expected_doc_ids", []) if str(item).strip()]
            if not query or not expected:
                raise ValueError(f"Invalid dataset row at line {idx}: query and expected_doc_ids are required.")
            source_types = row.get("source_types")
            source_list = [str(s) for s in source_types] if isinstance(source_types, list) else None
            cases.append(EvalCase(case_id=case_id, query=query, expected_doc_ids=expected, source_types=source_list))
    return cases


def _recall_at_k(found_doc_ids: list[str], expected_doc_ids: list[str]) -> float:
    expected = set(expected_doc_ids)
    return 1.0 if any(doc_id in expected for doc_id in found_doc_ids) else 0.0


def _mrr(found_doc_ids: list[str], expected_doc_ids: list[str]) -> float:
    expected = set(expected_doc_ids)
    for rank, doc_id in enumerate(found_doc_ids, start=1):
        if doc_id in expected:
            return 1.0 / rank
    return 0.0


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_benchmark(args: argparse.Namespace) -> int:
    os.environ.setdefault(UNITY_VERSION_ENV, args.unity_version)
    cfg = load_config(args.config)
    if args.vector_mode == "none":
        cfg.index.vector = "none"

    paths = make_paths(cfg)
    required = [paths.baked_dir / "corpus.jsonl", paths.baked_dir / "link_graph.jsonl", paths.index_dir / "fts.sqlite"]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        result = {
            "status": "skipped_missing_artifacts",
            "message": "Benchmark skipped because required artifacts are missing.",
            "missing_paths": missing,
            "dataset": str(Path(args.dataset).resolve()),
            "unity_version": cfg.unity_version,
            "k": args.k,
        }
        _write_json(Path(args.output), result)
        print("[benchmark] Skipped: required artifacts are missing.")
        for path in missing:
            print(f"[benchmark] missing: {path}")
        if args.require_artifacts:
            return 1
        return 0

    dataset_path = Path(args.dataset).resolve()
    cases = _load_dataset(dataset_path)
    store = DocStore(cfg)

    recall_scores: list[float] = []
    mrr_scores: list[float] = []
    case_results: list[dict[str, Any]] = []
    for case in cases:
        results = store.search(query=case.query, k=args.k, source_types=case.source_types)
        found_doc_ids = [result.doc_id for result in results]
        recall = _recall_at_k(found_doc_ids, case.expected_doc_ids)
        mrr_score = _mrr(found_doc_ids, case.expected_doc_ids)
        recall_scores.append(recall)
        mrr_scores.append(mrr_score)
        case_results.append(
            {
                **asdict(case),
                "found_doc_ids": found_doc_ids,
                "recall_at_k": recall,
                "mrr": mrr_score,
            }
        )

    summary = {
        "status": "ok",
        "unity_version": cfg.unity_version,
        "dataset": str(dataset_path),
        "k": args.k,
        "cases": len(cases),
        "recall_at_k": _mean(recall_scores),
        "mrr": _mean(mrr_scores),
    }
    payload = {
        "summary": summary,
        "results": case_results,
    }
    _write_json(Path(args.output), payload)
    print(f"[benchmark] cases={summary['cases']} recall@{args.k}={summary['recall_at_k']:.3f} mrr={summary['mrr']:.3f}")
    print(f"[benchmark] wrote {Path(args.output).resolve()}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Unity docs retrieval benchmark.")
    parser.add_argument(
        "--dataset",
        default="benchmarks/eval/unity_queries_v1.jsonl",
        help="Path to JSONL eval dataset.",
    )
    parser.add_argument("--k", type=int, default=5, help="Top-k retrieval depth.")
    parser.add_argument(
        "--output",
        default="benchmarks/results/latest.json",
        help="Output JSON path for benchmark metrics.",
    )
    parser.add_argument(
        "--unity-version",
        default="6000.3",
        help=f"Unity docs version for config resolution (used if {UNITY_VERSION_ENV} is unset).",
    )
    parser.add_argument("--config", default=None, help="Optional config file override path.")
    parser.add_argument(
        "--vector-mode",
        choices=["config", "none"],
        default="config",
        help="Use configured vector mode or force FTS-only benchmark reads.",
    )
    parser.add_argument(
        "--require-artifacts",
        action="store_true",
        help="Fail when baked/index artifacts are missing instead of warn-only skip.",
    )
    args = parser.parse_args()
    try:
        return run_benchmark(args)
    except Exception as exc:
        payload = {
            "status": "error",
            "message": str(exc),
            "dataset": str(Path(args.dataset).resolve()),
            "k": args.k,
        }
        _write_json(Path(args.output), payload)
        print(f"[benchmark] ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
