#!/usr/bin/env python3
"""Read-only PIT-vintage and cross-source concordance audit for the ETH queue IDEA."""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import statistics
import urllib.parse
from pathlib import Path

import eth_validator_queue_source_preflight as source

CANDIDATE_ID = source.CANDIDATE_ID
VALIDATORQUEUE_RAW_URL = "https://raw.githubusercontent.com/etheralpha/validatorqueue-com/main/historical_data.json"
VALIDATORQUEUE_COMMITS_URL = "https://api.github.com/repos/etheralpha/validatorqueue-com/commits"
PECTRA_BUG_START = dt.date(2025, 5, 7)
PECTRA_BUG_END = dt.date(2025, 5, 21)
GITHUB_PAGE_SIZE = 100
GITHUB_MAX_PAGES = 20

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = os.environ.get("GITHUB_RUN_ID", "local")
ATTEMPT = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
SOURCE_SHA = os.environ.get("GITHUB_SHA", "local")
NOW = dt.datetime.now(dt.timezone.utc)
OUTPUT_DIR = ROOT / "reports" / "generated" / "eth-validator-queue-pit-concordance" / f"{RUN_ID}-attempt-{ATTEMPT}"
SESSION_DIR = ROOT / "reports" / "sessions" / NOW.strftime("%Y-%m-%d")


class AuditError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def parse_history(raw: bytes) -> dict:
    payload = source.parse_json(raw, "ValidatorQueue historical_data.json")
    require(isinstance(payload, list) and payload, "ValidatorQueue history is not a non-empty array")
    rows = []
    previous = None
    for index, item in enumerate(payload):
        require(isinstance(item, dict), f"ValidatorQueue row {index} is not an object")
        try:
            day = dt.date.fromisoformat(str(item["date"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise AuditError(f"ValidatorQueue row {index} has an invalid date") from exc
        require(previous is None or day > previous, f"ValidatorQueue dates are not strictly increasing at {day}")
        entry = source.parse_number(item.get("entry_wait"), f"ValidatorQueue entry_wait {day}")
        exit_ = source.parse_number(item.get("exit_wait"), f"ValidatorQueue exit_wait {day}")
        rows.append({"date": day, "entry_wait": entry, "exit_wait": exit_})
        previous = day
    dates = [item["date"] for item in rows]
    expected_days = (dates[-1] - dates[0]).days + 1
    gaps = [
        {"after": left.isoformat(), "before": right.isoformat(), "missing_days": (right - left).days - 1}
        for left, right in zip(dates, dates[1:])
        if (right - left).days > 1
    ]
    return {
        "rows": rows,
        "raw_sha256": source.sha256(raw),
        "row_count": len(rows),
        "first_date": dates[0],
        "last_date": dates[-1],
        "expected_days": expected_days,
        "missing_days": expected_days - len(rows),
        "gap_count": len(gaps),
        "gaps": gaps,
    }


def parse_commit_timestamp(item: dict) -> dict:
    commit = item.get("commit", {})
    raw_date = commit.get("committer", {}).get("date")
    require(isinstance(raw_date, str), "GitHub commit history item is missing committer.date")
    try:
        timestamp = dt.datetime.fromisoformat(raw_date.replace("Z", "+00:00")).astimezone(dt.timezone.utc)
    except ValueError as exc:
        raise AuditError(f"Invalid GitHub commit timestamp: {raw_date!r}") from exc
    return {
        "sha": str(item.get("sha", "")),
        "timestamp": timestamp,
        "message": str(commit.get("message", "")).splitlines()[0],
    }


def fetch_commit_history() -> dict:
    commits = []
    remaining_headers = []
    for page in range(1, GITHUB_MAX_PAGES + 1):
        query = urllib.parse.urlencode({"path": "historical_data.json", "per_page": GITHUB_PAGE_SIZE, "page": page})
        raw, headers = source.fetch_bytes(
            f"{VALIDATORQUEUE_COMMITS_URL}?{query}",
            accept="application/vnd.github+json",
        )
        payload = source.parse_json(raw, f"ValidatorQueue GitHub commit history page {page}")
        require(isinstance(payload, list), f"GitHub commit history page {page} is not an array")
        remaining_headers.append(headers.get("x-ratelimit-remaining"))
        if not payload:
            break
        commits.extend(parse_commit_timestamp(item) for item in payload)
        if len(payload) < GITHUB_PAGE_SIZE:
            break
    else:
        raise AuditError(f"GitHub commit history exceeded the {GITHUB_MAX_PAGES}-page safety bound")
    require(commits, "GitHub returned no commits for historical_data.json")
    commits.sort(key=lambda item: (item["timestamp"], item["sha"]))
    canonical = "".join(
        f"{item['sha']},{item['timestamp'].isoformat()},{item['message']}\n" for item in commits
    )
    return {
        "commits": commits,
        "count": len(commits),
        "sha256": source.sha256(canonical.encode("utf-8")),
        "rate_limit_remaining_min": min(
            (int(value) for value in remaining_headers if value is not None),
            default=None,
        ),
    }


def average_ranks(values: list[float]) -> list[float]:
    ordered = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and ordered[end][1] == ordered[index][1]:
            end += 1
        average_rank = ((index + 1) + end) / 2.0
        for position in range(index, end):
            ranks[ordered[position][0]] = average_rank
        index = end
    return ranks


def correlation(left: list[float], right: list[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    left_mean = statistics.fmean(left)
    right_mean = statistics.fmean(right)
    left_ss = sum((value - left_mean) ** 2 for value in left)
    right_ss = sum((value - right_mean) ** 2 for value in right)
    if left_ss <= 0 or right_ss <= 0:
        return None
    covariance = sum((x - left_mean) * (y - right_mean) for x, y in zip(left, right))
    return covariance / math.sqrt(left_ss * right_ss)


def comparison_summary(reference: list[float], observed: list[float]) -> dict:
    require(len(reference) == len(observed), "Cross-source comparison arrays have different lengths")
    require(reference, "Cross-source comparison has no paired observations")
    errors = [right - left for left, right in zip(reference, observed)]
    absolute = sorted(abs(value) for value in errors)
    percentile_index = max(0, math.ceil(0.95 * len(absolute)) - 1)
    return {
        "n": len(reference),
        "pearson_r": correlation(reference, observed),
        "spearman_r": correlation(average_ranks(reference), average_ranks(observed)),
        "mean_bias_observed_minus_reference": statistics.fmean(errors),
        "mae": statistics.fmean(absolute),
        "median_absolute_error": statistics.median(absolute),
        "p95_absolute_error": absolute[percentile_index],
        "rmse": math.sqrt(statistics.fmean(value * value for value in errors)),
    }


def build_commit_vintages(history: dict, commit_history: dict) -> dict:
    rows = history["rows"]
    commits = commit_history["commits"]
    if len(rows) != len(commits):
        return {
            "mapping_complete": False,
            "row_count": len(rows),
            "commit_count": len(commits),
            "error": "Commit count does not equal append-only history row count; row-to-commit mapping is not assumed.",
            "commit_times": {},
        }
    commit_times = {}
    date_offsets = []
    same_day_count = 0
    expected_message_count = 0
    availability_offsets = []
    for row, commit in zip(rows, commits):
        day = row["date"]
        timestamp = commit["timestamp"]
        offset_days = (timestamp.date() - day).days
        date_offsets.append(offset_days)
        same_day_count += int(offset_days == 0)
        expected_message_count += int(
            commit["message"].startswith("Update index.html with latest validator queue data")
        )
        require(
            timestamp >= dt.datetime.combine(day, dt.time.min, tzinfo=dt.timezone.utc),
            f"Git commit predates its mapped ValidatorQueue row: {day}",
        )
        commit_times[day] = timestamp
        availability_offsets.append(
            (timestamp - dt.datetime.combine(day, dt.time.min, tzinfo=dt.timezone.utc)).total_seconds() / 3600.0
        )
    ordered_offsets = sorted(availability_offsets)
    p95_index = max(0, math.ceil(0.95 * len(ordered_offsets)) - 1)
    return {
        "mapping_complete": True,
        "row_count": len(rows),
        "commit_count": len(commits),
        "same_utc_date_commit_count": same_day_count,
        "same_utc_date_commit_fraction": same_day_count / len(rows),
        "expected_daily_update_message_count": expected_message_count,
        "commit_date_offset_days_min": min(date_offsets),
        "commit_date_offset_days_max": max(date_offsets),
        "commit_lag_from_utc_day_start_hours_max": max(availability_offsets),
        "commit_lag_from_utc_day_start_hours_p95": ordered_offsets[p95_index],
        "commit_history_sha256": commit_history["sha256"],
        "github_rate_limit_remaining_min": commit_history["rate_limit_remaining_min"],
        "commit_times": commit_times,
    }


def is_bug_date(day: dt.date) -> bool:
    return PECTRA_BUG_START <= day <= PECTRA_BUG_END


def cross_source_concordance(history: dict, queue: dict) -> dict:
    rows_by_date = {item["date"]: item for item in history["rows"]}
    entry_values = queue["entry_values"]
    exit_values = queue["exit_values"]
    common = sorted(set(rows_by_date) & set(entry_values) & set(exit_values))
    clean = [day for day in common if not is_bug_date(day)]
    regimes = {
        "all_clean_overlap": clean,
        "pre_pectra": [day for day in clean if day < PECTRA_BUG_START],
        "post_pectra": [day for day in clean if day > PECTRA_BUG_END],
    }
    result = {
        "common_dates_before_known_bug_exclusion": len(common),
        "known_pectra_bug_dates_excluded": sum(int(is_bug_date(day)) for day in common),
        "clean_common_dates": len(clean),
        "clean_first_date": clean[0].isoformat() if clean else None,
        "clean_last_date": clean[-1].isoformat() if clean else None,
        "regimes": {},
    }
    for regime, days in regimes.items():
        vq_entry = [rows_by_date[day]["entry_wait"] for day in days]
        vq_exit = [rows_by_date[day]["exit_wait"] for day in days]
        ckh_entry = [entry_values[day] for day in days]
        ckh_exit = [exit_values[day] for day in days]
        vq_asymmetry = [math.log1p(entry) - math.log1p(exit_) for entry, exit_ in zip(vq_entry, vq_exit)]
        ckh_asymmetry = [math.log1p(entry) - math.log1p(exit_) for entry, exit_ in zip(ckh_entry, ckh_exit)]
        result["regimes"][regime] = {
            "n": len(days),
            "start": days[0].isoformat() if days else None,
            "end": days[-1].isoformat() if days else None,
            "entry_wait_days": comparison_summary(ckh_entry, vq_entry) if days else None,
            "exit_wait_days": comparison_summary(ckh_exit, vq_exit) if days else None,
            "log1p_entry_minus_exit": comparison_summary(ckh_asymmetry, vq_asymmetry) if days else None,
        }
    return result


def make_origin_dates(step_days: int) -> tuple[list[dt.date], list[dt.date]]:
    warmup = []
    day = source.ORIGIN_GRID_START
    while day < source.VALIDATION_START:
        warmup.append(day)
        day += dt.timedelta(days=step_days)
    schedule = []
    day = source.ORIGIN_GRID_START
    while day <= source.SAMPLE_END:
        if day >= source.VALIDATION_START:
            schedule.append(day)
        day += dt.timedelta(days=step_days)
    return warmup, schedule


def schedule_feasibility(
    history: dict,
    commit_times: dict | None,
    *,
    step_days: int = source.ORIGIN_STEP_DAYS,
    min_train_events: int = source.MIN_TRAIN_EVENTS,
) -> dict:
    rows_by_date = {item["date"]: item for item in history["rows"]}
    warmup, schedule = make_origin_dates(step_days)
    valid = []
    missing_feature = 0
    known_bug_feature = 0
    unavailable_at_origin = 0
    for origin in warmup + schedule:
        feature_day = origin - dt.timedelta(days=2)
        if feature_day not in rows_by_date:
            missing_feature += 1
            continue
        if is_bug_date(feature_day):
            known_bug_feature += 1
            continue
        if commit_times is not None:
            commit_time = commit_times.get(feature_day)
            if commit_time is None or commit_time > dt.datetime.combine(origin, dt.time.min, tzinfo=dt.timezone.utc):
                unavailable_at_origin += 1
                continue
        valid.append(origin)
    accepted = []
    training_counts = []
    previous_valid = []
    for origin in valid:
        if origin >= source.VALIDATION_START:
            matured = [
                prior for prior in previous_valid
                if prior + dt.timedelta(days=source.TARGET_HORIZON_DAYS) < origin
            ]
            if len(matured) >= min_train_events:
                accepted.append(origin)
                training_counts.append(min(source.MAX_TRAIN_EVENTS, len(matured)))
        previous_valid.append(origin)
    validation = [day for day in accepted if day < source.TEST_START]
    test = [day for day in accepted if day >= source.TEST_START]
    return {
        "origin_step_days": step_days,
        "target_horizon_days": source.TARGET_HORIZON_DAYS,
        "target_windows_non_overlapping": step_days >= source.TARGET_HORIZON_DAYS,
        "minimum_training_events": min_train_events,
        "scheduled_validation_origins": len([day for day in schedule if day < source.TEST_START]),
        "scheduled_test_origins": len([day for day in schedule if day >= source.TEST_START]),
        "valid_validation_origins": len(validation),
        "valid_test_origins": len(test),
        "validation_minimum_100_met": len(validation) >= source.MIN_VALID_PER_SPLIT,
        "test_minimum_100_met": len(test) >= source.MIN_VALID_PER_SPLIT,
        "missing_feature_origins": missing_feature,
        "known_pectra_bug_feature_origins": known_bug_feature,
        "not_published_by_origin": unavailable_at_origin,
        "observed_training_count_min": min(training_counts) if training_counts else None,
        "observed_training_count_max": max(training_counts) if training_counts else None,
    }


def schedule_grid(history: dict, commit_times: dict | None) -> list[dict]:
    combinations = [
        (6, 60), (5, 60), (5, 30), (5, 20), (5, 15),
        (4, 60), (4, 30), (3, 60), (3, 30),
    ]
    return [
        schedule_feasibility(history, commit_times, step_days=step, min_train_events=warmup)
        for step, warmup in combinations
    ]


def fetch_sources() -> dict:
    source.PARTIAL_EVIDENCE.clear()
    openapi_raw, _ = source.fetch_bytes(source.OPENAPI_URL)
    openapi = source.validate_openapi(source.parse_json(openapi_raw, "CryptoKeyhole OpenAPI"))
    catalog_url, catalog_raw, catalog = source.fetch_eth_catalog()
    series_url = f"{source.SERIES_URL}?{urllib.parse.urlencode({'metric': source.METRIC_ID, 'interval': '24h', 'start': source.unix_seconds(source.QUEUE_START), 'end': source.unix_seconds(source.QUEUE_END_EXCLUSIVE), 'limit': 20000})}"
    series_raw, series_headers = source.fetch_bytes(series_url)
    queue = source.validate_queue_series(
        source.parse_json(series_raw, "CryptoKeyhole queue series"),
        series_headers,
        default_unit=catalog.get("unit"),
    )
    history_raw, _ = source.fetch_bytes(VALIDATORQUEUE_RAW_URL, accept="application/json")
    history = parse_history(history_raw)
    commit_history = fetch_commit_history()
    vintages = build_commit_vintages(history, commit_history)
    return {
        "openapi": openapi,
        "openapi_sha256": source.sha256(openapi_raw),
        "catalog_url": catalog_url,
        "catalog_sha256": source.sha256(catalog_raw),
        "series_url": series_url,
        "series_sha256": source.sha256(series_raw),
        "series_license": series_headers.get("link"),
        "series": queue,
        "history": history,
        "vintages": vintages,
    }


def summarize_sources(fetched: dict) -> dict:
    history = fetched["history"]
    queue = fetched["series"]
    vintages = fetched["vintages"]
    commit_times = vintages.get("commit_times") if vintages.get("mapping_complete") else None
    current_schedule = schedule_feasibility(
        history, commit_times,
        step_days=source.ORIGIN_STEP_DAYS,
        min_train_events=source.MIN_TRAIN_EVENTS,
    )
    return {
        "candidate_id": CANDIDATE_ID,
        "source_commit_sha": SOURCE_SHA,
        "workflow_run_id": RUN_ID,
        "workflow_run_attempt": ATTEMPT,
        "retrieved_at_utc": NOW.isoformat(),
        "status": "PASS" if vintages.get("mapping_complete") else "PARTIAL",
        "model_fit_performed": False,
        "backtest_run": False,
        "raw_observations_saved": False,
        "cryptokeyhole": {
            "metric_id": source.METRIC_ID,
            "series_state": queue["state"],
            "series_sha256": fetched["series_sha256"],
            "catalog_sha256": fetched["catalog_sha256"],
            "openapi_sha256": fetched["openapi_sha256"],
            "license_link": fetched["series_license"],
            "vintage_limitation": (
                "Free current-vintage daily history; first-published vintages require API & Team. "
                "The recorder began 2026-11-08, so historical first-published vintages are unavailable."
            ),
        },
        "validatorqueue": {
            "repository": "https://github.com/etheralpha/validatorqueue-com",
            "raw_history_url": VALIDATORQUEUE_RAW_URL,
            "history_sha256": history["raw_sha256"],
            "row_count": history["row_count"],
            "first_date": history["first_date"].isoformat(),
            "last_date": history["last_date"].isoformat(),
            "expected_days": history["expected_days"],
            "missing_days": history["missing_days"],
            "gap_count": history["gap_count"],
            "gaps": history["gaps"],
            "known_inaccurate_interval": {
                "start": PECTRA_BUG_START.isoformat(),
                "end": PECTRA_BUG_END.isoformat(),
                "reason": "Repository README documents post-Pectra queue values as validator-based rather than balance-based during this interval.",
            },
            "first_read_semantics": (
                "build.py appends one historical row only when the UTC date differs from the last row; "
                "Git commit time is used as a conservative public-availability upper bound."
            ),
            "commit_history": {key: value for key, value in vintages.items() if key != "commit_times"},
        },
        "cross_source_concordance": cross_source_concordance(history, queue),
        "pit_schedule_feasibility": {
            "existing_frozen_schedule": current_schedule,
            "non_overlapping_schedule_grid": schedule_grid(history, commit_times),
            "decision": (
                "The existing 6-day/60-training-event schedule is PIT-source infeasible if either split has fewer than 100 origins. "
                "Any schedule change requires a pre-result design amendment and cannot be selected using model performance."
            ),
        },
        "archive_reconstruction": {
            "public_mirror": "https://mainnet.era.nimbus.team/",
            "format_spec": "https://github.com/eth-clients/e2store-format-specs/blob/main/formats/era.md",
            "observed_era_file_size_bytes_2025": [477210982, 768950346, 873112623],
            "observed_era_file_size_bytes_2026": [660265640, 938248815, 904607902],
            "estimated_era_count_to_2026_11_28": 1923,
            "assessment": (
                "Full-file reconstruction is approximately terabyte-scale. Selective HTTP range reads, "
                "canonical state-root verification and replay cost have not been tested; no archive files were downloaded."
            ),
        },
    }


def write_outputs(result: dict, error: str | None = None) -> tuple[Path, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = OUTPUT_DIR / "pit_concordance.json"
    stamp = NOW.strftime("%Y-%m-%dT%H%M%SZ")
    report_path = SESSION_DIR / f"{stamp}_session-eth-validator-queue-pit-concordance-{RUN_ID}.md"
    manifest_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# Ethereum validator queue — PIT and cross-source concordance audit",
        "",
        f"- **Candidate:** {CANDIDATE_ID}",
        f"- **Status:** {result.get('status', 'INCOMPLETE')}",
        f"- **Run:** {RUN_ID}, attempt {ATTEMPT}",
        f"- **Retrieved:** {NOW.isoformat()}",
        "- **Model fit:** False",
        "- **Backtest:** False",
        "- **Raw observations saved:** False",
        "",
    ]
    if error:
        lines += ["## Retrieval/validation failure", "", f"- Error: {error}", ""]
    if "validatorqueue" in result:
        vq = result["validatorqueue"]
        pit = result["pit_schedule_feasibility"]["existing_frozen_schedule"]
        concordance = result["cross_source_concordance"]
        lines += [
            "## First-read archive and conservative availability",
            "",
            f"- ValidatorQueue.com: {vq['row_count']} daily first-read rows, {vq['first_date']} through {vq['last_date']}.",
            f"- Missing calendar days: {vq['missing_days']} across {vq['gap_count']} gaps.",
            f"- Git history: {vq['commit_history']['commit_count']} commits; "
            f"{vq['commit_history'].get('same_utc_date_commit_count', 'unmapped')} share the row's UTC date.",
            f"- Existing schedule after missing/bad feature dates and conservative commit-time checks: "
            f"{pit['valid_validation_origins']} validation and {pit['valid_test_origins']} test origins.",
            f"- Existing 100/100 split minima: validation {pit['validation_minimum_100_met']}; test {pit['test_minimum_100_met']}.",
            "",
            "## Cross-source concordance",
            "",
            f"- Common dates before known-bug exclusion: {concordance['common_dates_before_known_bug_exclusion']}.",
            f"- Known Pectra bug dates excluded: {concordance['known_pectra_bug_dates_excluded']}.",
            f"- Clean paired dates: {concordance['clean_common_dates']} "
            f"({concordance['clean_first_date']} to {concordance['clean_last_date']}).",
            "",
            "| Regime | n | Entry Pearson | Exit Pearson | Log-asymmetry Pearson | Log-asymmetry MAE |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        for regime, label in (("pre_pectra", "Pre-Pectra"), ("post_pectra", "Post-Pectra"), ("all_clean_overlap", "All clean")):
            stats = concordance["regimes"][regime]
            entry = stats["entry_wait_days"]
            exit_ = stats["exit_wait_days"]
            asym = stats["log1p_entry_minus_exit"]
            lines.append(
                f"| {label} | {stats['n']} | {entry['pearson_r']:.4f} | {exit_['pearson_r']:.4f} | "
                f"{asym['pearson_r']:.4f} | {asym['mae']:.6f} |"
            )
        lines += [
            "",
            "## Archive reconstruction assessment",
            "",
            "- Public Nimbus .era files are large (roughly 0.48–0.94 GB in the sampled 2025–26 listing).",
            "- Full-file reconstruction across roughly 1,923 eras is a terabyte-scale retrieval; no files were downloaded.",
            "- Selective range reads may reduce the cost but remain unverified. A valid reconstruction still needs state-root anchoring, slot alignment and deterministic replay.",
            "",
            "## Decision boundary",
            "",
            "- This is source validation only; it is not a preregistration, model fit, backtest, strategy result or trading authorization.",
            "- The existing PIT archive fails the current validation sample minimum if fewer than 100 validation origins remain.",
            "- Any alternative schedule or current-vintage exploratory association requires a pre-result design amendment before model fitting.",
            "",
        ]
    lines += [
        "## Provenance",
        "",
        f"- CryptoKeyhole chart: {source.CHART_URL}",
        "- ValidatorQueue repository: https://github.com/etheralpha/validatorqueue-com",
        "- Nimbus archive index: https://mainnet.era.nimbus.team/",
        "- Era format: https://github.com/eth-clients/e2store-format-specs/blob/main/formats/era.md",
        f"- Machine-readable manifest: {manifest_path.relative_to(ROOT)}.",
        "",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write(f"## ETH validator queue PIT concordance: {result.get('status', 'INCOMPLETE')}\n\n")
            handle.write(f"- Manifest: {manifest_path.relative_to(ROOT)}\n")
    return manifest_path, report_path


def main() -> int:
    result = {
        "candidate_id": CANDIDATE_ID,
        "source_commit_sha": SOURCE_SHA,
        "workflow_run_id": RUN_ID,
        "workflow_run_attempt": ATTEMPT,
        "retrieved_at_utc": NOW.isoformat(),
        "status": "INCOMPLETE",
        "model_fit_performed": False,
        "backtest_run": False,
        "raw_observations_saved": False,
    }
    try:
        result = summarize_sources(fetch_sources())
        write_outputs(result)
        return 0 if result["status"] == "PASS" else 1
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        write_outputs(result, error=result["error"])
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
