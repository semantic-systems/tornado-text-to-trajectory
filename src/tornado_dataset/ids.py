"""Deterministic identifiers and run manifests.

UIDs are derived from the *source* identifiers rather than from row order, so
that re-running a stage — or running it on a different machine — produces the
same keys and downstream links stay valid.

The manifest is the reproducibility record of a run: what was built, from which
window, with which code, and what the outputs hash to.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from . import config
from .http import utcnow_iso


def uid(namespace: str, *parts: Any) -> str:
    """Stable short id, e.g. ``uid("hazard", "{GUID-1}", "{GUID-2}")``.

    Parts are sorted before hashing so that a hazard assembled from the same
    members gets the same id regardless of the order they were discovered in.
    """
    payload = "|".join(sorted(str(p) for p in parts))
    digest = hashlib.sha1(f"{namespace}:{payload}".encode("utf-8")).hexdigest()[:16]
    return f"{namespace}_{digest}"


def git_sha() -> str | None:
    """Current commit, suffixed ``-dirty`` when the tree has uncommitted changes.

    The suffix matters: without it a manifest can claim a run came from a commit
    whose code differs from what actually ran.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(config.REPO_ROOT), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10, check=True)
        sha = result.stdout.strip()
        status = subprocess.run(
            ["git", "-C", str(config.REPO_ROOT), "status", "--porcelain"],
            capture_output=True, text=True, timeout=15, check=True)
        return f"{sha}-dirty" if status.stdout.strip() else sha
    except Exception:
        return None


def file_checksum(path: Path) -> str:
    """SHA-256 of a file, streamed so large GeoJSON stays out of memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_manifest(path: Path, stage: str, *, counts: dict[str, Any],
                   outputs: list[Path], extra: dict[str, Any] | None = None) -> None:
    """Write the reproducibility record for one pipeline stage."""
    manifest = {
        "stage": stage,
        "written_at": utcnow_iso(),
        "git_sha": git_sha(),
        "window": {"start": config.WINDOW_START.isoformat(),
                   "end": config.WINDOW_END.isoformat()},
        "counts": counts,
        "outputs": {
            p.name: {"bytes": p.stat().st_size, "sha256": file_checksum(p)}
            for p in outputs if p.exists()
        },
    }
    if extra:
        manifest.update(extra)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
