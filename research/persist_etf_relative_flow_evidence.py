#!/usr/bin/env python3
"""Verify and merge ETF relative-flow evidence into the latest mainline documents."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import etf_relative_flow_ethbtc as model


def persist(manifest_path: Path, report_path: Path) -> dict:
    root = model.ROOT
    manifest_path = manifest_path.resolve()
    report_path = report_path.resolve()
    if not manifest_path.is_file() or not report_path.is_file():
        raise FileNotFoundError("Both the generated manifest and report must exist")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_report = (root / manifest["report_path"]).resolve()
    expected_manifest = (root / manifest["manifest_path"]).resolve()
    if report_path != expected_report or manifest_path != expected_manifest:
        raise ValueError("Evidence paths do not match the manifest's canonical paths")
    actual_sha = hashlib.sha256(report_path.read_bytes()).hexdigest()
    if not manifest.get("report_sha256") or actual_sha != manifest["report_sha256"]:
        raise ValueError("Research report SHA-256 does not match the generated manifest")

    if manifest.get("status") in {"COMPLETE", "INCONCLUSIVE/INFEASIBLE"}:
        model.update_documents(manifest, report_path, manifest_path)
    manifest["registry_sha256"] = hashlib.sha256(model.REGISTRY_PATH.read_bytes()).hexdigest()
    manifest["prereg_sha256"] = hashlib.sha256(model.PREREG_PATH.read_bytes()).hexdigest()
    manifest_path.write_text(
        json.dumps(model.base.json_safe(manifest), indent=2, sort_keys=True) + chr(10),
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
        raise SystemExit("usage: persist_etf_relative_flow_evidence.py MANIFEST REPORT")
    print(json.dumps(persist(Path(sys.argv[1]), Path(sys.argv[2])), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
