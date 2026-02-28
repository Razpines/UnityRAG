import json
from types import SimpleNamespace
from pathlib import Path

from unity_docs_mcp.bench import benchmark_cli


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_metric_helpers():
    assert benchmark_cli._recall_at_k(["a", "b"], ["b"]) == 1.0
    assert benchmark_cli._recall_at_k(["a", "b"], ["z"]) == 0.0
    assert benchmark_cli._mrr(["x", "y", "z"], ["y"]) == 0.5
    assert benchmark_cli._mrr(["x", "y", "z"], ["nope"]) == 0.0


def test_run_benchmark_warn_only_skip_when_artifacts_missing(monkeypatch, tmp_path: Path):
    _write(tmp_path / "config.yaml", "index:\n  vector: \"none\"\n")
    dataset = tmp_path / "dataset.jsonl"
    _write(
        dataset,
        '{"id":"q1","query":"job system","expected_doc_ids":["manual/job-system-parallel-for-jobs"]}\n',
    )
    output = tmp_path / "benchmark.json"
    monkeypatch.setenv("UNITY_DOCS_MCP_ROOT", str(tmp_path))
    monkeypatch.setenv("UNITY_DOCS_MCP_UNITY_VERSION", "6000.3")

    args = SimpleNamespace(
        dataset=str(dataset),
        k=5,
        output=str(output),
        unity_version="6000.3",
        config=None,
        vector_mode="config",
        require_artifacts=False,
    )
    code = benchmark_cli.run_benchmark(args)

    assert code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "skipped_missing_artifacts"
