#!/usr/bin/env python3
"""Merge research evidence into the latest main-branch registry without losing concurrent updates."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import taker_absorption_btc_downside as model


def persist(manifest_path: Path, report_path: Path) -> dict:
    root = model.ROOT
    manifest_path = manifest_path.resolve()
    report_path = report_path.resolve()
    if not manifest_path.is_file() or not report_path.is_file():
        raise FileNotFoundError("Both the generated manifest and report must exist")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_report_path = (root / manifest["report_path"]).resolve()
    expected_manifest_path = (root / manifest["manifest_path"]).resolve()
    if report_path != expected_report_path or manifest_path != expected_manifest_path:
        raise ValueError("Evidence paths do not match the manifest's canonical paths")
    expected_sha = manifest.get("report_sha256")
    actual_sha = hashlib.sha256(report_path.read_bytes()).hexdigest()
    if not expected_sha or actual_sha != expected_sha:
        raise ValueError("Research report SHA-256 does not match the generated manifest")

    model.update_documents(manifest, report_path, manifest_path)
    manifest["registry_sha256"] = hashlib.sha256(model.REGISTRY_PATH.read_bytes()).hexdigest()
    manifest["prereg_sha256"] = hashlib.sha256(model.PREREG_PATH.read_bytes()).hexdigest()
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, default=str) + chr(10),
        encoding="utf-8",
    )
    return {
        "report_path": manifest["report_path"],
        "manifest_path": manifest["manifest_path"],
        "report_sha256": actual_sha,
        "registry_sha256": manifest["registry_sha256"],
        "prereg_sha256": manifest["prereg_sha256"],
    }


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: persist_taker_absorption_evidence.py MANIFEST REPORT")
    result = persist(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
