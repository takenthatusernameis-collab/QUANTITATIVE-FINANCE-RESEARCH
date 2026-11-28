from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import json
import math
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Iterable

HYPOTHESIS_ID = "QFR-2026-11-28-H8-CI-CREDIT-IMPULSE-BTC-DOWNSIDE-01"
SERIES_ID = "TOTCI"
ALFRED_GRAPH_URL = "https://alfred.stlouisfed.org/graph/alfredgraph.csv"
SAMPLE_VINTAGES = (
    "2017-08-20",
    "2020-03-15",
    "2022-01-02",
    "2024-01-07",
    "2026-11-22",
)
HISTORY_START = dt.date(2017, 8, 16)
MIN_HISTORY_ROWS = 450
MAX_STALE_DAYS = 14
REQUEST_TIMEOUT_SECONDS = 45


def build_url(vintages: Iterable[str] = SAMPLE_VINTAGES) -> str:
    dates = tuple(vintages)
    if not dates or len(dates) > 12:
        raise ValueError("ALFRED request must contain between one and twelve vintages")
    parsed = [dt.date.fromisoformat(value) for value in dates]
    if len(parsed) != len(set(parsed)):
        raise ValueError("duplicate vintage dates are not allowed")
    if any(value.weekday() != 6 for value in parsed):
        raise ValueError("all frozen sample vintage dates must be Sundays")
    params = {
        "id": ",".join([SERIES_ID] * len(dates)),
        "vintage_date": ",".join(dates),
    }
    return f"{ALFRED_GRAPH_URL}?{urllib.parse.urlencode(params)}"


def parse_vintage_csv(raw: bytes, vintages: Iterable[str] = SAMPLE_VINTAGES) -> dict[str, dict[dt.date, float]]:
    dates = tuple(vintages)
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("ALFRED CSV is not valid UTF-8") from exc

    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
    except StopIteration as exc:
        raise ValueError("ALFRED CSV is empty") from exc

    expected = ["observation_date"] + [
        f"{SERIES_ID}_{value.replace('-', '')}" for value in dates
    ]
    if header != expected:
        raise ValueError(f"unexpected ALFRED columns: {header!r}")

    panel: dict[str, dict[dt.date, float]] = {value: {} for value in dates}
    seen: set[dt.date] = set()
    previous: dt.date | None = None

    for line_number, row in enumerate(reader, start=2):
        if not row or all(not cell.strip() for cell in row):
            continue
        if len(row) != len(expected):
            raise ValueError(f"CSV line {line_number} has {len(row)} cells; expected {len(expected)}")
        try:
            observation_date = dt.date.fromisoformat(row[0].strip())
        except ValueError as exc:
            raise ValueError(f"CSV line {line_number} has an invalid observation date") from exc
        if observation_date in seen:
            raise ValueError(f"duplicate observation date: {observation_date.isoformat()}")
        if previous is not None and observation_date <= previous:
            raise ValueError("observation dates are not strictly increasing")
        seen.add(observation_date)
        previous = observation_date

        for vintage, raw_value in zip(dates, row[1:]):
            value = raw_value.strip()
            if value in ("", "."):
                continue
            try:
                number = float(value)
            except ValueError as exc:
                raise ValueError(
                    f"invalid {SERIES_ID} value for {vintage} at {observation_date.isoformat()}"
                ) from exc
            if not math.isfinite(number) or number <= 0:
                raise ValueError(
                    f"non-positive or non-finite {SERIES_ID} value for {vintage} "
                    f"at {observation_date.isoformat()}"
                )
            panel[vintage][observation_date] = number

    if not seen:
        raise ValueError("ALFRED CSV contains no observation rows")
    return panel


def summarize_vintages(
    panel: dict[str, dict[dt.date, float]],
    vintages: Iterable[str] = SAMPLE_VINTAGES,
    *,
    min_history_rows: int = 0,
) -> list[dict]:
    dates = tuple(vintages)
    summaries: list[dict] = []

    for vintage in dates:
        vintage_date = dt.date.fromisoformat(vintage)
        observations = panel.get(vintage, {})
        if not observations:
            raise ValueError(f"{vintage}: no published {SERIES_ID} observations")
        future_dates = sorted(value for value in observations if value > vintage_date)
        if future_dates:
            raise ValueError(
                f"{vintage}: vintage contains future observation {future_dates[-1].isoformat()}"
            )

        observation_dates = sorted(observations)
        latest_date = observation_dates[-1]
        age_days = (vintage_date - latest_date).days
        if age_days < 3 or age_days > MAX_STALE_DAYS:
            raise ValueError(
                f"{vintage}: latest observation age {age_days} is outside 3..{MAX_STALE_DAYS} days"
            )
        if latest_date.weekday() != 2:
            raise ValueError(f"{vintage}: latest H.8 observation is not a Wednesday")

        if len(observation_dates) < 5:
            raise ValueError(f"{vintage}: fewer than five observations for four-interval change")
        tail = observation_dates[-5:]
        gaps = [(tail[index] - tail[index - 1]).days for index in range(1, len(tail))]
        if any(gap < 5 or gap > 9 for gap in gaps):
            raise ValueError(f"{vintage}: last five H.8 observations are not weekly")
        lag_date = tail[0]
        lag_days = (latest_date - lag_date).days
        if not 21 <= lag_days <= 35:
            raise ValueError(f"{vintage}: four-observation lag spans {lag_days} days")

        latest_value = observations[latest_date]
        lag_value = observations[lag_date]
        change_pct = 100.0 * math.log(latest_value / lag_value)
        if not math.isfinite(change_pct):
            raise ValueError(f"{vintage}: four-observation log change is not finite")

        rows_since_start = sum(value >= HISTORY_START for value in observation_dates)
        if vintage == dates[-1] and rows_since_start < min_history_rows:
            raise ValueError(
                f"{vintage}: only {rows_since_start} observations since {HISTORY_START}; "
                f"need {min_history_rows}"
            )

        summaries.append({
            "vintage_date": vintage,
            "latest_observation_date": latest_date.isoformat(),
            "latest_observation_age_days": age_days,
            "latest_value_billions_usd_sa": latest_value,
            "fourth_prior_observation_date": lag_date.isoformat(),
            "four_observation_log_change_pct": change_pct,
            "four_observation_span_days": lag_days,
            "weekly_gaps_days": gaps,
            "observation_count": len(observation_dates),
            "observations_since_2017_08_16": rows_since_start,
            "history_start": observation_dates[0].isoformat(),
        })

    return summaries


def revision_stats(
    panel: dict[str, dict[dt.date, float]],
    older_vintage: str = "2020-03-15",
    newer_vintage: str = "2026-11-22",
) -> dict:
    older = panel.get(older_vintage, {})
    newer = panel.get(newer_vintage, {})
    common = sorted(set(older).intersection(newer))
    changed = sum(
        not math.isclose(older[value], newer[value], rel_tol=0.0, abs_tol=1e-10)
        for value in common
    )
    return {
        "older_vintage": older_vintage,
        "newer_vintage": newer_vintage,
        "common_observations": len(common),
        "changed_observations": changed,
    }


def canonical_sha256(panel: dict[str, dict[dt.date, float]]) -> str:
    canonical = {
        vintage: [
            (observation_date.isoformat(), format(value, ".12g"))
            for observation_date, value in sorted(values.items())
        ]
        for vintage, values in sorted(panel.items())
    }
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def fetch_once(url: str) -> tuple[bytes, str, int]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "QFR-H8-CI-credit-source-preflight/1.0"},
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        status = int(getattr(response, "status", 200))
        body = response.read()
        final_url = response.geturl()
    if status != 200:
        raise RuntimeError(f"ALFRED returned HTTP {status}")
    if not body:
        raise RuntimeError("ALFRED returned an empty body")
    return body, final_url, status


def output_path() -> Path:
    run_id = os.environ.get("GITHUB_RUN_ID", "local")
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
    return (
        Path("reports/generated/h8-ci-credit-impulse-source-preflight")
        / f"{run_id}-attempt-{attempt}"
        / "preflight.json"
    )


def main() -> int:
    destination = output_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    url = build_url()
    base_manifest = {
        "schema_version": 1,
        "hypothesis_id": HYPOTHESIS_ID,
        "source": {
            "provider": "Federal Reserve Board H.8 via ALFRED",
            "series_id": SERIES_ID,
            "series_title": "Commercial and Industrial Loans, All Commercial Banks",
            "frequency": "weekly ending Wednesday",
            "units": "billions of U.S. dollars, seasonally adjusted",
            "vintage_endpoint": ALFRED_GRAPH_URL,
            "vintage_dates": list(SAMPLE_VINTAGES),
        },
        "source_url": url,
        "api_key_used": False,
        "paid_data_used": False,
        "network_requests": 1,
        "network_retries": 0,
        "raw_observations_saved": False,
        "model_fit": False,
        "backtest_run": False,
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "manifest_path": str(destination),
    }

    try:
        raw, final_url, status = fetch_once(url)
        panel = parse_vintage_csv(raw)
        summaries = summarize_vintages(
            panel,
            min_history_rows=MIN_HISTORY_ROWS,
        )
        revisions = revision_stats(panel)
        manifest = {
            **base_manifest,
            "status": "PASS",
            "http_status": status,
            "final_url": final_url,
            "raw_response_sha256": hashlib.sha256(raw).hexdigest(),
            "canonical_panel_sha256": canonical_sha256(panel),
            "vintage_summaries": summaries,
            "revision_comparison": revisions,
            "acceptance": {
                "exact_vintage_columns": True,
                "no_future_observations": True,
                "latest_observation_age_days_within_3_to_14": True,
                "latest_observation_is_wednesday": True,
                "four_prior_weekly_observations": True,
                "minimum_history_rows_met": True,
            },
        }
        exit_code = 0
    except Exception as exc:  # evidence is still written on a source failure
        manifest = {
            **base_manifest,
            "status": "FAILED",
            "error": f"{type(exc).__name__}: {exc}",
        }
        exit_code = 1

    destination.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
