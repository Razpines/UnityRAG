from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


class BootstrapError(RuntimeError):
    pass


def _venv_python(venv_dir: Path) -> Path:
    if sys.platform.startswith("win"):
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _run(command: list[str], cwd: Path) -> None:
    result = subprocess.run(command, cwd=str(cwd), check=False)
    if result.returncode != 0:
        raise BootstrapError(f"Command failed ({result.returncode}): {' '.join(command)}")


def _verify_cuda(python_exe: Path, cwd: Path) -> bool:
    cmd = [
        str(python_exe),
        "-c",
        (
            "import torch,sys; "
            "print('[bootstrap] torch=' + str(torch.__version__) + "
            "' cuda=' + str(torch.version.cuda) + "
            "' available=' + str(torch.cuda.is_available())); "
            "raise SystemExit(0 if (torch.cuda.is_available() and torch.version.cuda is not None) else 1)"
        ),
    ]
    result = subprocess.run(cmd, cwd=str(cwd), check=False)
    return result.returncode == 0


def run_bootstrap(repo_root: Path, venv_dir: Path, mode: str, cuda_channels: list[str]) -> None:
    mode_norm = (mode or "").strip().lower()
    if mode_norm not in {"cuda", "cpu"}:
        raise BootstrapError(f"Unsupported mode: {mode}. Use 'cuda' or 'cpu'.")

    if not venv_dir.exists():
        print(f"[bootstrap] Creating venv at {venv_dir}...")
        _run([sys.executable, "-m", "venv", str(venv_dir)], cwd=repo_root)
    else:
        print(f"[bootstrap] Reusing existing venv at {venv_dir}.")

    python_exe = _venv_python(venv_dir)
    if not python_exe.exists():
        raise BootstrapError(f"Venv python not found at {python_exe}")

    print("[bootstrap] Upgrading pip...")
    _run([str(python_exe), "-m", "pip", "install", "-U", "pip"], cwd=repo_root)

    extras = ".[dev,vector]" if mode_norm == "cuda" else ".[dev]"
    print(f"[bootstrap] Installing project dependencies: {extras}")
    _run([str(python_exe), "-m", "pip", "install", "-e", extras], cwd=repo_root)

    if mode_norm == "cpu":
        print("[bootstrap] CPU-only mode selected (FTS-only retrieval).")
        return

    if not cuda_channels:
        raise BootstrapError("No CUDA channels configured for CUDA mode.")
    print(f"[bootstrap] Installing CUDA torch build ({' -> '.join(cuda_channels)})...")
    for channel in cuda_channels:
        print(f"[bootstrap] Trying torch channel: {channel}")
        install_cmd = [
            str(python_exe),
            "-m",
            "pip",
            "install",
            "--force-reinstall",
            "torch",
            "--index-url",
            f"https://download.pytorch.org/whl/{channel}",
        ]
        result = subprocess.run(install_cmd, cwd=str(repo_root), check=False)
        if result.returncode != 0:
            print(f"[bootstrap] {channel} install failed.")
            continue
        if _verify_cuda(python_exe, cwd=repo_root):
            print(f"[bootstrap] Installed CUDA-capable torch from {channel}.")
            return
        print(f"[bootstrap] {channel} installed but CUDA runtime verification failed.")

    raise BootstrapError("Failed to install a CUDA-capable torch build.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create/reuse venv and install UnityRAG dependencies.")
    parser.add_argument("--repo-root", required=True, help="Repository root path.")
    parser.add_argument("--venv", required=True, help="Virtual environment path.")
    parser.add_argument("--mode", choices=["cuda", "cpu"], required=True, help="Setup mode.")
    parser.add_argument(
        "--cuda-channels",
        default="cu128,cu121,cu118",
        help="Comma-separated torch CUDA channels to try in order.",
    )
    args = parser.parse_args()

    channels = [c.strip() for c in args.cuda_channels.split(",") if c.strip()]
    try:
        run_bootstrap(
            repo_root=Path(args.repo_root).resolve(),
            venv_dir=Path(args.venv).resolve(),
            mode=args.mode,
            cuda_channels=channels,
        )
    except BootstrapError as exc:
        print(f"[bootstrap] ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - defensive last resort
        print(f"[bootstrap] ERROR: unexpected failure: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
