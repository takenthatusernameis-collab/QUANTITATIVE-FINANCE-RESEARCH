#!/usr/bin/env python3
"""Merge-safe persistence for the frozen BTC difficulty-cut experiment."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HYPOTHESIS_ID = "QFR-2026-11-27-BTC-DIFFICULTY-CUT-DOWNSIDE-01"
PREREG_PATH = ROOT / "research" / "PREREGISTERED-QFR-2026-11-27-BTC-DIFFICULTY-CUT-DOWNSIDE-01.md"
REGISTRY_PATH = ROOT / "research" / "HYPOTHESIS-REGISTRY.md"
README_PATH = ROOT / "README.md"
README_START = "<!-- QFR:BTC-MINING-DIFFICULTY:START -->"
README_END = "<!-- QFR:BTC-MINING-DIFFICULTY:END -->"


def persist(manifest_path: Path, report_path: Path) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("hypothesis_id") != HYPOTHESIS_ID:
        raise ValueError("Manifest hypothesis ID does not match this persistence helper")
    expected_sha = os.environ.get("GITHUB_SHA")
    if expected_sha and manifest.get("source_commit_sha") != expected_sha:
        raise ValueError("Manifest source_commit_sha does not match the immutable admitted commit")
    actual_report_sha = hashlib.sha256(report_path.read_bytes()).hexdigest()
    if manifest.get("report_sha256") != actual_report_sha:
        raise ValueError("Report SHA-256 does not match the manifest")
    prereg = PREREG_PATH.read_text(encoding="utf-8")
    prereg_sha = hashlib.sha256(prereg.encode("utf-8")).hexdigest()
    if manifest.get("preregistration_sha256") != prereg_sha:
        raise ValueError("Preregistration changed after the admitted source commit")

    status = "BACKTESTED" if manifest.get("status") == "COMPLETE" else "INCONCLUSIVE/INFEASIBLE"
    decision = manifest.get("decision", "INCONCLUSIVE/INFEASIBLE")
    validation = manifest.get("validation") or {}
    test = manifest.get("test") or {}
    val_imp = validation.get("rmse_improvement_pct")
    test_imp = test.get("rmse_improvement_pct")
    paired = manifest.get("paired_test_loss_bootstrap")
    source = manifest.get("sources") or {}
    firsthand = source.get("difficulty_adjustments") or {}
    mempool = source.get("mempool_consistency_check") or {}
    price = source.get("binance_spot_prices") or {}
    coverage = price.get("coverage") or {}
    report_relative = "../" + report_path.relative_to(ROOT).as_posix()
    manifest_relative = "../" + manifest_path.relative_to(ROOT).as_posix()
    summary = (
        f"{manifest.get('status')}; decision={decision}; validation/test n="
        f"{validation.get('n', 0)}/{test.get('n', 0)}; RMSE improvement={val_imp}/{test_imp}; "
        f"paired test-loss bootstrap={paired}; error={manifest.get('error', 'none')}"
    )
    data_scope = (
        f"Firsthand Bitcoin difficulty-adjustment series; frozen {firsthand.get('frozen_first_date', 'unavailable')} "
        f"to {firsthand.get('frozen_last_date', 'unavailable')} ({firsthand.get('frozen_event_count', 0)} events); "
        f"Mempool 3y consistency check {mempool.get('matched_rows', 0)}/{mempool.get('mempool_rows', 0)}; "
        f"Binance BTCUSDT Spot 1d UTC {manifest.get('sample', {}).get('price_start')} to "
        f"{manifest.get('sample', {}).get('price_end')} ({coverage.get('observed_daily_rows', 0)} rows)"
    )
    mechanism = (
        "A strictly lagged downward Bitcoin difficulty retarget, proxied by max(-adjustment_pct, 0), "
        "may add information about next-five-session BTC downside semivariance beyond recent downside "
        "risk, realized variance and momentum."
    )
    row = (
        f"| {HYPOTHESIS_ID} | {status} | {mechanism} | {data_scope} | {summary} | "
        f"[session report]({report_relative}) / [manifest]({manifest_relative}) / "
        "[preregistration](PREREGISTERED-QFR-2026-11-27-BTC-DIFFICULTY-CUT-DOWNSIDE-01.md) |"
    )
    registry = REGISTRY_PATH.read_text(encoding="utf-8")
    lines = registry.splitlines()
    replaced = False
    for index, line in enumerate(lines):
        if line.startswith(f"| {HYPOTHESIS_ID} |"):
            lines[index] = row
            replaced = True
            break
    if not replaced:
        insert_at = next((i + 1 for i, line in enumerate(lines) if line.startswith("| ---")), len(lines))
        lines.insert(insert_at, row)
    REGISTRY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    prereg_lines = prereg.splitlines()
    status_line = (
        f"- **Status:** {status}; decision={decision}; workflow run {manifest.get('run_id')}; "
        f"validation/test forecasts {validation.get('n', 0)}/{test.get('n', 0)}."
    )
    for index, line in enumerate(prereg_lines):
        if line.startswith("- **Status:**"):
            prereg_lines[index] = status_line
            break
    execution = f"""## 8. Execution result

- Workflow run: https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/{manifest.get('run_id')}
- Triggering source commit: {manifest.get('source_commit_sha')}
- Status: {manifest.get('status')}
- Decision: {decision}
- Validation/test forecasts: {validation.get('n', 0)}/{test.get('n', 0)}
- Validation/test RMSE improvement: {val_imp}/{test_imp}
- Paired test-loss bootstrap: {json.dumps(paired, sort_keys=True)}
- Report: {report_relative}
- Manifest: {manifest_relative}

{manifest.get('decision_reason', manifest.get('error', ''))}
"""
    existing = "## 8. Execution result"
    text = "\n".join(prereg_lines).rstrip()
    if existing in text:
        text = text.split(existing, 1)[0].rstrip()
    PREREG_PATH.write_text(text + "\n\n" + execution, encoding="utf-8")

    readme = README_PATH.read_text(encoding="utf-8")
    section = f"""{README_START}
## Current admitted research workstream

- Hypothesis: `{HYPOTHESIS_ID}` — {status}; decision **{decision}**.
- Result: validation/test forecasts {validation.get('n', 0)}/{test.get('n', 0)}; RMSE improvement {val_imp}/{test_imp} percent.
- Evidence: [session report]({report_path.relative_to(ROOT).as_posix()}) · [preregistration](research/PREREGISTERED-QFR-2026-11-27-BTC-DIFFICULTY-CUT-DOWNSIDE-01.md) · [workflow run](https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/{manifest.get('run_id')}).
- Next: preserve the frozen result, red-team source timing and event construction, and select a materially distinct hypothesis only after reviewing the updated registry.
{README_END}"""
    if README_START in readme and README_END in readme:
        before, tail = readme.split(README_START, 1)
        _, after = tail.split(README_END, 1)
        readme = before.rstrip() + "\n\n" + section + after
    else:
        readme = readme.rstrip() + "\n\n" + section + "\n"
    README_PATH.write_text(readme, encoding="utf-8")

    print(json.dumps({
        "hypothesis_id": HYPOTHESIS_ID,
        "status": status,
        "decision": decision,
        "report": report_path.relative_to(ROOT).as_posix(),
        "manifest": manifest_path.relative_to(ROOT).as_posix(),
        "registry_updated": True,
        "preregistration_updated": True,
        "readme_updated": True,
    }, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: persist_btc_mining_difficulty_evidence.py MANIFEST REPORT")
    persist(Path(sys.argv[1]), Path(sys.argv[2]))
