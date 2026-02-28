from types import SimpleNamespace
from pathlib import Path

import unity_docs_mcp.setup.bootstrap as bootstrap


def test_run_bootstrap_cpu_mode_installs_dev_deps(monkeypatch, tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True)
    venv_dir = tmp_path / ".venv"
    fake_python = tmp_path / "venv-python"
    fake_python.write_text("", encoding="utf-8")

    calls: list[list[str]] = []

    def fake_run(command, cwd=None, check=False):
        calls.append(list(command))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(bootstrap, "_venv_python", lambda _venv: fake_python)
    monkeypatch.setattr(bootstrap.subprocess, "run", fake_run)

    bootstrap.run_bootstrap(repo_root=repo_root, venv_dir=venv_dir, mode="cpu", cuda_channels=["cu128"])

    flat = [" ".join(cmd) for cmd in calls]
    assert any("-m venv" in cmd for cmd in flat)
    assert any("-m pip install -U pip" in cmd for cmd in flat)
    assert any("-m pip install -e .[dev]" in cmd for cmd in flat)
    assert not any("--force-reinstall torch" in cmd for cmd in flat)


def test_run_bootstrap_cuda_mode_falls_back_channels(monkeypatch, tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True)
    venv_dir = tmp_path / ".venv"
    venv_dir.mkdir(parents=True)
    fake_python = tmp_path / "venv-python"
    fake_python.write_text("", encoding="utf-8")

    install_attempts: list[str] = []
    verify_attempts = {"count": 0}

    def fake_run(command, cwd=None, check=False):
        cmd_text = " ".join(command)
        if "--index-url" in cmd_text:
            for channel in ("cu128", "cu121", "cu118"):
                if channel in cmd_text:
                    install_attempts.append(channel)
                    if channel == "cu128":
                        return SimpleNamespace(returncode=1)
                    return SimpleNamespace(returncode=0)
        if "-c" in command:
            verify_attempts["count"] += 1
            return SimpleNamespace(returncode=0 if verify_attempts["count"] == 2 else 1)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(bootstrap, "_venv_python", lambda _venv: fake_python)
    monkeypatch.setattr(bootstrap.subprocess, "run", fake_run)

    bootstrap.run_bootstrap(
        repo_root=repo_root,
        venv_dir=venv_dir,
        mode="cuda",
        cuda_channels=["cu128", "cu121", "cu118"],
    )

    assert install_attempts == ["cu128", "cu121", "cu118"]
    assert verify_attempts["count"] == 2
