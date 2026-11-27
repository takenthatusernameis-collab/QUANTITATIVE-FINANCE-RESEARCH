#!/usr/bin/env python3
"""Read-only source-feasibility preflight for relative BTC/ETH ETF flow research."""
from __future__ import annotations

import concurrent.futures
import datetime as dt
import hashlib
import json
import math
import os
from html.parser import HTMLParser
from pathlib import Path

import stlfsi4_btc_downside_semivariance as market
import treasury_auction_demand as base

PROJECT_KEY = "btc-eth-etf-relative-flow-ethbtc"
BTC_FLOW_URL = "https://farside.co.uk/bitcoin-etf-flow-all-data/"
ETH_FLOW_URL = "https://farside.co.uk/ethereum-etf-flow-all-data/"
PRICE_START_DATE = dt.date(2024, 7, 1)
FLOW_START_DATE = dt.date(2024, 7, 23)
FLOW_EMBARGO_DAYS = 5
PRICE_TARGET_DAYS = 5
MAX_PRICE_PUBLICATION_LAG_DAYS = 3
MIN_COMMON_FLOW_ROWS = 450
MAX_UNMATCHED_FLOW_DATES = 5
ARCHIVE_WORKERS = 6

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = os.environ.get("GITHUB_RUN_ID", "local")
ATTEMPT = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
SOURCE_SHA = os.environ.get("GITHUB_SHA", "local")
OUTPUT_DIR = ROOT / "reports" / "generated" / "etf-relative-flow-source-preflight" / f"{RUN_ID}-attempt-{ATTEMPT}"


class TableCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.tables: list[list[list[str]]] = []
        self.rows: list[list[str]] | None = None
        self.row: list[str] | None = None
        self.cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag == "table":
            self.depth += 1
            if self.depth == 1:
                self.rows = []
        elif self.depth == 1:
            if tag == "tr":
                self.row = []
            elif tag in {"td", "th"} and self.row is not None:
                self.cell = []

    def handle_data(self, data: str) -> None:
        if self.depth == 1 and self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self.depth == 1 and tag in {"td", "th"} and self.cell is not None:
            assert self.row is not None
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif self.depth == 1 and tag == "tr" and self.row is not None:
            if self.row and self.rows is not None:
                self.rows.append(self.row)
            self.row = None
        elif tag == "table":
            if self.depth == 1 and self.rows is not None:
                self.tables.append(self.rows)
                self.rows = None
            self.depth = max(0, self.depth - 1)


def parse_flow_value(value: str) -> float | None:
    text = " ".join(str(value).replace("\xa0", " ").split()).strip()
    if text in {"", "-", "–", "—"}:
        return None
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1].strip()
    try:
        number = float(text.replace(",", "").replace("$", ""))
    except ValueError as exc:
        raise ValueError(f"Invalid Farside flow value: {value!r}") from exc
    if not math.isfinite(number):
        raise ValueError(f"Non-finite Farside flow value: {value!r}")
    return -abs(number) if negative else number


def parse_flow_date(value: str) -> dt.date | None:
    text = " ".join(str(value).split()).strip()
    try:
        return dt.datetime.strptime(text, "%d %b %Y").date()
    except ValueError:
        return None


def parse_farside_html(body: bytes, source_name: str) -> tuple[dict[dt.date, float], dict]:
    parser = TableCollector()
    parser.feed(body.decode("utf-8-sig"))
    for table in parser.tables:
        header_index = None
        for index, row in enumerate(table):
            if len(row) >= 4 and row[-1].strip().lower() == "total" and row[0].strip().lower() in {"", "date"}:
                header_index = index
                break
        if header_index is None:
            continue

        header = table[header_index]
        if header[0].strip().lower() == "":
            header = ["Date"] + header[1:]
        values: dict[dt.date, float] = {}
        numeric_component_counts: list[int] = []
        for row_number, row in enumerate(table[header_index + 1:], start=header_index + 2):
            if not row:
                continue
            day = parse_flow_date(row[0])
            if day is None:
                continue
            if len(row) != len(header):
                raise ValueError(
                    f"{source_name}: row {row_number} has {len(row)} cells; expected {len(header)}"
                )
            components = [parse_flow_value(cell) for cell in row[1:-1]]
            numeric = [value for value in components if value is not None]
            if not numeric:
                # An all-dash row is not a zero-flow observation (e.g. a market holiday or unfinished row).
                continue
            total = parse_flow_value(row[-1])
            if total is None:
                raise ValueError(f"{source_name}: numeric fund row has no Total on {day}")
            component_sum = math.fsum(numeric)
            rounding_tolerance = 0.1 * (len(numeric) + 1) + 0.05
            if abs(component_sum - total) > rounding_tolerance:
                raise ValueError(
                    f"{source_name}: fund components do not reconcile to Total on {day}: "
                    f"sum={component_sum}, total={total}, tolerance={rounding_tolerance}"
                )
            if day in values:
                raise ValueError(f"{source_name}: duplicate flow date {day}")
            values[day] = total
            numeric_component_counts.append(len(numeric))

        if not values:
            raise ValueError(f"{source_name}: historical Farside table contains no numeric flow rows")
        ordered = sorted(values)
        if ordered != list(values):
            values = {day: values[day] for day in ordered}
        return values, {
            "source": source_name,
            "header": header,
            "fund_columns": header[1:-1],
            "first_date": min(values).isoformat(),
            "last_date": max(values).isoformat(),
            "numeric_flow_rows": len(values),
            "minimum_numeric_fund_components": min(numeric_component_counts),
            "maximum_numeric_fund_components": max(numeric_component_counts),
            "raw_html_sha256": hashlib.sha256(body).hexdigest(),
        }
    raise ValueError(f"{source_name}: no historical table with Date/fund columns/Total was found")


def build_flow_panel(
    btc_flows: dict[dt.date, float],
    eth_flows: dict[dt.date, float],
    cutoff_date: dt.date,
    min_rows: int = MIN_COMMON_FLOW_ROWS,
    max_unmatched: int = MAX_UNMATCHED_FLOW_DATES,
) -> tuple[list[dict], dict]:
    btc = {day: value for day, value in btc_flows.items() if FLOW_START_DATE <= day <= cutoff_date}
    eth = {day: value for day, value in eth_flows.items() if FLOW_START_DATE <= day <= cutoff_date}
    btc_dates, eth_dates = set(btc), set(eth)
    unmatched = sorted(btc_dates.symmetric_difference(eth_dates))
    if len(unmatched) > max_unmatched:
        raise ValueError(
            f"BTC/ETH Farside dates do not align: {len(unmatched)} unmatched dates exceeds {max_unmatched}"
        )
    common = sorted(btc_dates.intersection(eth_dates))
    if len(common) < min_rows:
        raise ValueError(f"Only {len(common)} common BTC/ETH flow observations; require {min_rows}")
    panel = [
        {"date": day, "btc_total_usdm": btc[day], "eth_total_usdm": eth[day]}
        for day in common
    ]
    canonical = "".join(
        f"{row['date'].isoformat()}|{row['btc_total_usdm']:.1f}|{row['eth_total_usdm']:.1f}\n"
        for row in panel
    ).encode("utf-8")
    return panel, {
        "rows": len(panel),
        "first_date": panel[0]["date"].isoformat(),
        "last_date": panel[-1]["date"].isoformat(),
        "cutoff_date": cutoff_date.isoformat(),
        "unmatched_dates": [day.isoformat() for day in unmatched],
        "sha256": hashlib.sha256(canonical).hexdigest(),
    }


def build_archive_specs_for_symbol(
    symbol: str, start: dt.date, end: dt.date, as_of_date: dt.date
) -> list[dict]:
    specs = market.build_archive_specs(start, end, as_of_date)
    return [
        {
            **spec,
            "filename": spec["filename"].replace("BTCUSDT", symbol),
            "url": spec["url"].replace("BTCUSDT", symbol),
        }
        for spec in specs
    ]


def resolve_latest_available_end_date(
    symbol: str, start: dt.date, requested_end: dt.date, as_of_date: dt.date
) -> tuple[dt.date, list[dict]]:
    probes = []
    for lag in range(MAX_PRICE_PUBLICATION_LAG_DAYS + 1):
        candidate = requested_end - dt.timedelta(days=lag)
        specs = build_archive_specs_for_symbol(symbol, start, candidate, as_of_date)
        if not specs:
            raise RuntimeError(f"No Binance archive specs for {symbol} through {candidate}")
        spec = specs[-1]
        try:
            rows, record = market.download_binance_archive(spec)
            if candidate not in rows:
                raise ValueError(f"{symbol} latest archive does not contain requested date {candidate}")
            probes.append({"date": candidate.isoformat(), "status": "available", "archive_sha256": record["archive_sha256"]})
            return candidate, probes
        except Exception as exc:
            if "HTTP 404" not in str(exc):
                raise
            probes.append({"date": candidate.isoformat(), "status": "not_yet_published", "error": f"{type(exc).__name__}: {exc}"})
    raise RuntimeError(f"No published {symbol} daily archive within {MAX_PRICE_PUBLICATION_LAG_DAYS} days: {probes}")


def fetch_symbol_prices(
    symbol: str, start: dt.date, end: dt.date, as_of_date: dt.date
) -> tuple[dict[dt.date, float], dict]:
    specs = build_archive_specs_for_symbol(symbol, start, end, as_of_date)
    rows: dict[dt.date, float] = {}
    records: list[dict] = []
    failures: list[dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=ARCHIVE_WORKERS) as pool:
        future_map = {pool.submit(market.download_binance_archive, spec): spec for spec in specs}
        for future in concurrent.futures.as_completed(future_map):
            spec = future_map[future]
            try:
                part, record = future.result()
                part = {day: close for day, close in part.items() if start <= day <= end}
                overlap = set(rows).intersection(part)
                if overlap:
                    raise ValueError(f"{symbol} duplicate dates across archives: {sorted(overlap)[:3]}")
                rows.update(part)
                records.append(record)
            except Exception as exc:
                failures.append({
                    "period": spec["tag"],
                    "url": spec["url"],
                    "error": f"{type(exc).__name__}: {exc}",
                })
    if failures:
        raise RuntimeError(f"{symbol}: {len(failures)} Binance archives failed: {failures[:5]}")
    expected_days = (end - start).days + 1
    expected = {start + dt.timedelta(days=i) for i in range(expected_days)}
    missing = sorted(expected - set(rows))
    outside = sorted(set(rows) - expected)
    if missing or outside:
        raise ValueError(
            f"{symbol} daily price coverage mismatch: missing={len(missing)} "
            f"first_missing={missing[0] if missing else None}; outside={len(outside)}"
        )
    records.sort(key=lambda item: item["period"])
    manifest_bytes = json.dumps(records, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return rows, {
        "symbol": symbol,
        "interval": "1d UTC",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "archive_count": len(records),
        "archive_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "archives": records,
        "rows": len(rows),
        "missing_dates": [],
    }


def fetch_common_prices(start: dt.date, requested_end: dt.date) -> tuple[dict, dict, dict]:
    today = dt.datetime.now(dt.timezone.utc).date()
    btc_end, btc_probes = resolve_latest_available_end_date("BTCUSDT", start, requested_end, today)
    eth_end, eth_probes = resolve_latest_available_end_date("ETHUSDT", start, requested_end, today)
    common_end = min(btc_end, eth_end)
    btc_rows, btc_manifest = fetch_symbol_prices("BTCUSDT", start, common_end, today)
    eth_rows, eth_manifest = fetch_symbol_prices("ETHUSDT", start, common_end, today)
    return btc_rows, eth_rows, {
        "common_end_date": common_end.isoformat(),
        "requested_end_date": requested_end.isoformat(),
        "btc_end_probes": btc_probes,
        "eth_end_probes": eth_probes,
        "btc": btc_manifest,
        "eth": eth_manifest,
    }


def run_preflight() -> dict:
    retrieved_at = dt.datetime.now(dt.timezone.utc)
    btc_html = base.fetch_bytes(BTC_FLOW_URL, timeout=30)
    eth_html = base.fetch_bytes(ETH_FLOW_URL, timeout=30)
    btc_flows, btc_meta = parse_farside_html(btc_html, "Farside Bitcoin ETF all-data")
    eth_flows, eth_meta = parse_farside_html(eth_html, "Farside Ethereum ETF all-data")

    requested_end = retrieved_at.date() - dt.timedelta(days=1)
    btc_prices, eth_prices, price_meta = fetch_common_prices(PRICE_START_DATE, requested_end)
    common_end = dt.date.fromisoformat(price_meta["common_end_date"])
    cutoff = min(
        retrieved_at.date() - dt.timedelta(days=FLOW_EMBARGO_DAYS),
        common_end - dt.timedelta(days=FLOW_EMBARGO_DAYS + PRICE_TARGET_DAYS),
    )
    panel, panel_meta = build_flow_panel(btc_flows, eth_flows, cutoff)
    return {
        "project_key": PROJECT_KEY,
        "status": "PASS",
        "retrieved_at_utc": retrieved_at.isoformat(),
        "source_commit_sha": SOURCE_SHA,
        "flow_embargo_calendar_days": FLOW_EMBARGO_DAYS,
        "target_sessions": PRICE_TARGET_DAYS,
        "btc_flow_source": btc_meta,
        "eth_flow_source": eth_meta,
        "flow_panel": panel_meta,
        "price_sources": price_meta,
        "eligible_signal_start_date": (panel[0]["date"] + dt.timedelta(days=FLOW_EMBARGO_DAYS)).isoformat(),
        "eligible_signal_end_date": (
            panel[-1]["date"] + dt.timedelta(days=FLOW_EMBARGO_DAYS)
        ).isoformat(),
        "model_backtest_run": False,
        "raw_observations_saved": False,
        "interpretation": (
            "Source feasibility only. Farside current-vintage aggregator tables were reconciled; "
            "both Binance Spot price series passed official archive checksum and daily-continuity checks. "
            "No model was fitted and no forecast/backtest metric was calculated."
        ),
    }


def main() -> int:
    try:
        result = run_preflight()
    except Exception as exc:
        result = {
            "project_key": PROJECT_KEY,
            "status": "FAIL",
            "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "source_commit_sha": SOURCE_SHA,
            "error": f"{type(exc).__name__}: {exc}",
            "model_backtest_run": False,
            "raw_observations_saved": False,
        }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = OUTPUT_DIR / "preflight.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    rendered = json.dumps(result, indent=2, sort_keys=True)
    print(rendered)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write("# BTC/ETH ETF relative-flow source preflight\n\n")
            handle.write(f"- Status: **{result['status']}**\n")
            handle.write("- Model/backtest executed: **No**\n\n")
            handle.write(rendered + "\n")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
