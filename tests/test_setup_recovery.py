from pathlib import Path

from unity_docs_mcp.config import Config, PathsConfig
import unity_docs_mcp.setup.ensure_artifacts as ensure_artifacts


def _config_for_tmp(tmp_path: Path) -> Config:
    cfg = Config()
    cfg.paths = PathsConfig(
        root=str(tmp_path),
        raw_zip=str(tmp_path / "raw" / "UnityDocumentation.zip"),
        raw_unzipped=str(tmp_path / "raw" / "UnityDocumentation"),
        baked_dir=str(tmp_path / "baked"),
        index_dir=str(tmp_path / "index"),
    )
    cfg.index.vector = "none"
    return cfg


def test_unzip_failure_redownloads_and_retries(monkeypatch, tmp_path: Path):
    cfg = _config_for_tmp(tmp_path)
    raw_zip = Path(cfg.paths.raw_zip)
    raw_unzipped = Path(cfg.paths.raw_unzipped)
    raw_zip.parent.mkdir(parents=True, exist_ok=True)
    raw_zip.write_bytes(b"corrupt")

    calls = {"download_overwrite": [], "unzip": 0}

    def fake_download(url: str, destination: Path, overwrite: bool = False, progress: bool = True) -> Path:
        calls["download_overwrite"].append(overwrite)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"fresh")
        return destination

    def fake_unzip(zip_path: Path, target_dir: Path) -> Path:
        calls["unzip"] += 1
        if calls["unzip"] == 1:
            target_dir.mkdir(parents=True, exist_ok=True)
            (target_dir / "partial.txt").write_text("partial", encoding="utf-8")
            raise RuntimeError("bad zip payload")
        (target_dir / "Documentation" / "en").mkdir(parents=True, exist_ok=True)
        return target_dir

    monkeypatch.setattr(ensure_artifacts, "download_zip", fake_download)
    monkeypatch.setattr(ensure_artifacts, "safe_unzip", fake_unzip)
    monkeypatch.setattr(ensure_artifacts, "bake", lambda _cfg: None)
    monkeypatch.setattr(ensure_artifacts, "index", lambda _cfg: None)

    ensure_artifacts.ensure(cfg)

    assert calls["unzip"] == 2
    assert calls["download_overwrite"] == [True]
    assert (raw_unzipped / "Documentation" / "en").is_dir()
    assert not (raw_unzipped / "partial.txt").exists()


def test_nonready_unzip_dir_is_cleared_before_unzip(monkeypatch, tmp_path: Path):
    cfg = _config_for_tmp(tmp_path)
    raw_zip = Path(cfg.paths.raw_zip)
    raw_unzipped = Path(cfg.paths.raw_unzipped)
    raw_zip.parent.mkdir(parents=True, exist_ok=True)
    raw_zip.write_bytes(b"zip-bytes")
    raw_unzipped.mkdir(parents=True, exist_ok=True)
    (raw_unzipped / "stale.tmp").write_text("stale", encoding="utf-8")

    calls = {"unzip": 0}

    def fake_unzip(zip_path: Path, target_dir: Path) -> Path:
        calls["unzip"] += 1
        assert not (target_dir / "stale.tmp").exists()
        (target_dir / "Documentation" / "en").mkdir(parents=True, exist_ok=True)
        return target_dir

    monkeypatch.setattr(ensure_artifacts, "safe_unzip", fake_unzip)
    monkeypatch.setattr(ensure_artifacts, "download_zip", lambda *args, **kwargs: raw_zip)
    monkeypatch.setattr(ensure_artifacts, "bake", lambda _cfg: None)
    monkeypatch.setattr(ensure_artifacts, "index", lambda _cfg: None)

    ensure_artifacts.ensure(cfg)

    assert calls["unzip"] == 1
    assert (raw_unzipped / "Documentation" / "en").is_dir()
