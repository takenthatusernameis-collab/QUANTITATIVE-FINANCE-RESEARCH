#!/usr/bin/env python3
"""Bounded Coinbase spot-price plausibility check for Kraken PI cap anomalies.

Fetches only exact BTC-USD/ETH-USD product metadata and four short hourly
candle windows around the nine pre-identified Kraken PI exception timestamps.
Raw responses remain in memory; only a compact manifest with selected hourly
candle summaries and response hashes is written. This is not cap validation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_BASE = "https://api.exchange.coinbase.com"
GRANULARITY_SECONDS = 3600
MAX_RESPONSE_BYTES = 2_000_000
REQUEST_TIMEOUT_SECONDS = 20
PRODUCTS = ("BTC-USD", "ETH-USD")
CONTROL_TIMESTAMP = "2026-08-20T12:00:00Z"

# Frozen, compact exception inputs from the completed Kraken API-only census.
# They are not raw API rows; the full source response hashes are in the task handoff.
EXCEPTIONS = (
    {"symbol": "PI_XBTUSD", "product_id": "BTC-USD", "timestamp": "2026-08-20T09:00:00Z",
     "relativeFundingRate": "0.005", "fundingRate": "6.9906751384e-08"},
    {"symbol": "PI_ETHUSD", "product_id": "ETH-USD", "timestamp": "2026-08-20T07:00:00Z",
     "relativeFundingRate": "0.005", "fundingRate": "2.211538036243e-06"},
    {"symbol": "PI_ETHUSD", "product_id": "ETH-USD", "timestamp": "2026-08-20T08:00:00Z",
     "relativeFundingRate": "0.005", "fundingRate": "2.222143212686e-06"},
    {"symbol": "PI_ETHUSD", "product_id": "ETH-USD", "timestamp": "2026-08-20T11:00:00Z",
     "relativeFundingRate": "-0.003835161729166667", "fundingRate": "-1.678422449722e-06"},
    {"symbol": "PI_ETHUSD", "product_id": "ETH-USD", "timestamp": "2026-10-29T09:00:00Z",
     "relativeFundingRate": "0.003261576116071429", "fundingRate": "1.408176479305e-06"},
    {"symbol": "PI_ETHUSD", "product_id": "ETH-USD", "timestamp": "2026-10-30T13:00:00Z",
     "relativeFundingRate": "0.003248896366666667", "fundingRate": "1.455794401876e-06"},
    {"symbol": "PI_ETHUSD", "product_id": "ETH-USD", "timestamp": "2026-10-30T14:00:00Z",
     "relativeFundingRate": "0.005", "fundingRate": "2.249749152969e-06"},
    {"symbol": "PI_ETHUSD", "product_id": "ETH-USD", "timestamp": "2026-10-30T15:00:00Z",
     "relativeFundingRate": "0.005", "fundingRate": "2.237907467002e-06"},
    {"symbol": "PI_ETHUSD", "product_id": "ETH-USD", "timestamp": "2026-10-30T16:00:00Z",
     "relativeFundingRate": "0.005", "fundingRate": "2.248070031878e-06"},
)

# Each request is far below Coinbase's documented 300-candle maximum.
WINDOWS = (
    {"product_id": "BTC-USD", "start": "2026-08-20T08:00:00Z", "end": "2026-08-20T13:00:00Z"},
    {"product_id": "ETH-USD", "start": "2026-08-20T06:00:00Z", "end": "2026-08-20T13:00:00Z"},
    {"product_id": "ETH-USD", "start": "2026-10-29T08:00:00Z", "end": "2026-10-29T11:00:00Z"},
    {"product_id": "ETH-USD", "start": "2026-10-30T12:00:00Z", "end": "2026-10-30T18:00:00Z"},
)


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def epoch_seconds(value: str) -> int:
    return int(parse_utc(value).timestamp())


def iso_utc(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat().replace("+00:00", "Z")


def decimal_text(value: Decimal, places: int | None = None) -> str:
    if places is not None:
        value = value.quantize(Decimal(1).scaleb(-places))
    return format(value.normalize(), "f")


def fetch_json(url: str, timeout: int = REQUEST_TIMEOUT_SECONDS) -> tuple[dict[str, Any], Any | None]:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "qfr-kraken-pi-price-validation/1.0",
        },
    )
    status: int | None = None
    headers: Any = {}
    body = b""
    error: str | None = None
    try:
        with urlopen(request, timeout=timeout) as response:
            status = int(response.status)
            headers = response.headers
            body = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        status = int(exc.code)
        headers = exc.headers or {}
        body = exc.read(MAX_RESPONSE_BYTES + 1)
        error = "http_error"
    except (URLError, TimeoutError, OSError) as exc:
        error = f"network_error:{type(exc).__name__}"
    record: dict[str, Any] = {
        "url": url,
        "http_status": status,
        "content_type": headers.get("Content-Type") if headers else None,
        "response_date": headers.get("Date") if headers else None,
        "response_bytes": len(body),
        "response_sha256": hashlib.sha256(body).hexdigest() if body else None,
        "raw_response_retained": False,
    }
    if error:
        record["error"] = error
        return record, None
    if len(body) > MAX_RESPONSE_BYTES:
        record["error"] = "response_exceeds_size_limit"
        return record, None
    if status != 200:
        record["error"] = "http_status_not_200"
        return record, None
    try:
        return record, json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        record["error"] = "invalid_json"
        return record, None


def product_url(product_id: str) -> str:
    return f"{API_BASE}/products/{product_id}"


def candle_url(window: dict[str, str]) -> str:
    params = urlencode({
        "granularity": str(GRANULARITY_SECONDS),
        "start": window["start"],
        "end": window["end"],
    })
    return f"{API_BASE}/products/{window['product_id']}/candles?{params}"


def validate_product(payload: Any, product_id: str) -> dict[str, Any]:
    expected_base, expected_quote = product_id.split("-", 1)
    item = payload if isinstance(payload, dict) else {}
    observed_id = item.get("id")
    base = item.get("base_currency")
    quote = item.get("quote_currency")
    status = str(item.get("status") or "").lower()
    trading_disabled = bool(item.get("trading_disabled", False))
    errors: list[str] = []
    if observed_id != product_id:
        errors.append("product_id_mismatch")
    if base != expected_base:
        errors.append("base_currency_mismatch")
    if quote != expected_quote:
        errors.append("quote_currency_mismatch")
    if status != "online":
        errors.append("product_not_online")
    if trading_disabled:
        errors.append("trading_disabled")
    return {
        "product_id": product_id,
        "observed_product_id": observed_id,
        "base_currency": base,
        "quote_currency": quote,
        "status": status or None,
        "trading_disabled": trading_disabled,
        "identity_valid": not any(e.endswith("_mismatch") for e in errors),
        "online_control_passed": status == "online" and not trading_disabled,
        "errors": errors,
    }


def parse_candle_payload(
    payload: Any, start_epoch: int, end_epoch: int
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    errors: list[str] = []
    if not isinstance(payload, list):
        return [], {
            "row_count": 0, "valid_row_count": 0, "invalid_row_count": 0,
            "duplicate_timestamp_count": 0, "out_of_window_count": 0,
            "unaligned_timestamp_count": 0, "errors": ["response_not_array"],
            "raw_order": "EMPTY",
        }
    parsed: list[dict[str, Any]] = []
    invalid = 0
    out_of_window = 0
    unaligned = 0
    raw_timestamps: list[int] = []
    for row in payload:
        try:
            if not isinstance(row, (list, tuple)) or len(row) != 6:
                raise ValueError("candle_shape")
            timestamp = int(row[0])
            low, high, open_price, close, volume = (Decimal(str(x)) for x in row[1:])
            if not all(x.is_finite() for x in (low, high, open_price, close, volume)):
                raise ValueError("non_finite_value")
            if min(low, high, open_price, close) <= 0 or volume < 0:
                raise ValueError("non_positive_price_or_negative_volume")
            if low > min(open_price, close) or high < max(open_price, close) or low > high:
                raise ValueError("ohlc_invariant")
            if timestamp % GRANULARITY_SECONDS:
                unaligned += 1
                raise ValueError("unaligned_timestamp")
            if timestamp < start_epoch or timestamp >= end_epoch:
                out_of_window += 1
                raise ValueError("out_of_window")
            raw_timestamps.append(timestamp)
            parsed.append({
                "timestamp": timestamp,
                "low": low,
                "high": high,
                "open": open_price,
                "close": close,
                "volume": volume,
            })
        except (ValueError, TypeError, InvalidOperation, OverflowError) as exc:
            invalid += 1
            if str(exc) not in errors:
                errors.append(str(exc))
    unique_timestamps = {item["timestamp"] for item in parsed}
    duplicates = len(parsed) - len(unique_timestamps)
    if duplicates:
        errors.append("duplicate_timestamps")
    if out_of_window:
        errors.append("out_of_window_rows")
    if unaligned:
        errors.append("unaligned_timestamps")
    if len(raw_timestamps) <= 1:
        raw_order = "ASCENDING_OR_SINGLE"
    elif raw_timestamps == sorted(raw_timestamps):
        raw_order = "ASCENDING"
    elif raw_timestamps == sorted(raw_timestamps, reverse=True):
        raw_order = "DESCENDING"
    else:
        raw_order = "MIXED"
    parsed.sort(key=lambda item: item["timestamp"])
    return parsed, {
        "row_count": len(payload),
        "valid_row_count": len(parsed),
        "invalid_row_count": invalid,
        "duplicate_timestamp_count": duplicates,
        "out_of_window_count": out_of_window,
        "unaligned_timestamp_count": unaligned,
        "errors": errors,
        "raw_order": raw_order,
    }


def candle_summary(candle: dict[str, Any], implied: Decimal | None = None) -> dict[str, Any]:
    result = {
        "timestamp_utc": iso_utc(candle["timestamp"]),
        "open": decimal_text(candle["open"], 8),
        "high": decimal_text(candle["high"], 8),
        "low": decimal_text(candle["low"], 8),
        "close": decimal_text(candle["close"], 8),
        "volume": decimal_text(candle["volume"], 8),
    }
    if implied is not None:
        basis_pct = (candle["close"] - implied) / implied * Decimal(100)
        result["close_basis_vs_implied_pct"] = decimal_text(basis_pct, 6)
        result["implied_within_candle_range"] = candle["low"] <= implied <= candle["high"]
    return result


def compare_exception(
    exception: dict[str, str],
    candles_by_product: dict[str, dict[int, dict[str, Any]]],
    window_hashes: dict[tuple[str, int], str | None],
    product_hashes: dict[str, str | None],
) -> dict[str, Any]:
    timestamp = epoch_seconds(exception["timestamp"])
    relative = Decimal(exception["relativeFundingRate"])
    absolute = Decimal(exception["fundingRate"])
    if absolute == 0:
        implied = None
    else:
        implied = relative / absolute
    product_id = exception["product_id"]
    by_time = candles_by_product.get(product_id, {})
    selected: list[dict[str, Any]] = []
    for offset in (-GRANULARITY_SECONDS, 0, GRANULARITY_SECONDS):
        candle = by_time.get(timestamp + offset)
        if candle is not None:
            selected.append(candle_summary(candle, implied))
    exact = by_time.get(timestamp)
    complete = all(timestamp + offset in by_time for offset in (-GRANULARITY_SECONDS, 0, GRANULARITY_SECONDS))
    lows = [by_time[timestamp + offset]["low"] for offset in (-GRANULARITY_SECONDS, 0, GRANULARITY_SECONDS)
            if timestamp + offset in by_time]
    highs = [by_time[timestamp + offset]["high"] for offset in (-GRANULARITY_SECONDS, 0, GRANULARITY_SECONDS)
             if timestamp + offset in by_time]
    closes = [by_time[timestamp + offset]["close"] for offset in (-GRANULARITY_SECONDS, 0, GRANULARITY_SECONDS)
              if timestamp + offset in by_time]
    same_hour_basis = None
    if exact is not None and implied is not None:
        same_hour_basis = (exact["close"] - implied) / implied * Decimal(100)
    nearest_close_basis = None
    if implied is not None and closes:
        nearest_close_basis = min(abs((close - implied) / implied * Decimal(100)) for close in closes)
    local_low = min(lows) if lows else None
    local_high = max(highs) if highs else None
    return {
        "symbol": exception["symbol"],
        "product_id": product_id,
        "timestamp_utc": exception["timestamp"],
        "relativeFundingRate": exception["relativeFundingRate"],
        "fundingRate": exception["fundingRate"],
        "implied_index_usd": decimal_text(implied, 8) if implied is not None else None,
        "product_metadata_response_sha256": product_hashes.get(product_id),
        "candle_window_response_sha256": window_hashes.get((product_id, timestamp)),
        "exact_timestamp_candle_present": exact is not None,
        "complete_t_minus_1_t_t_plus_1_window": complete,
        "comparison_status": "COMPLETE_3H_WINDOW" if complete else ("EXACT_HOUR_ONLY" if exact else "MISSING_EXACT_HOUR"),
        "same_hour_close_basis_vs_implied_pct": decimal_text(same_hour_basis, 6) if same_hour_basis is not None else None,
        "nearest_3h_close_abs_basis_pct": decimal_text(nearest_close_basis, 6) if nearest_close_basis is not None else None,
        "implied_within_3h_low_high_envelope": (
            local_low <= implied <= local_high if implied is not None and local_low is not None else None
        ),
        "three_hour_low_usd": decimal_text(local_low, 8) if local_low is not None else None,
        "three_hour_high_usd": decimal_text(local_high, 8) if local_high is not None else None,
        "comparison_candles": selected,
        "interpretation": (
            "Coinbase is a separate spot venue; this local comparison is a plausibility check only. "
            "Kraken's derivatives index composition and API timestamp-to-accrual boundary are not established."
        ),
    }


def run_probe(
    output_dir: Path,
    fetcher: Callable[[str], tuple[dict[str, Any], Any | None]] | None = None,
) -> dict[str, Any]:
    fetcher = fetcher or fetch_json
    output_dir.mkdir(parents=True, exist_ok=True)
    fetched_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    product_records: dict[str, dict[str, Any]] = {}
    product_hashes: dict[str, str | None] = {}
    for product_id in PRODUCTS:
        response, payload = fetcher(product_url(product_id))
        validation = validate_product(payload, product_id)
        product_records[product_id] = {
            "request": response,
            "validation": validation,
        }
        product_hashes[product_id] = response.get("response_sha256")

    candles_by_product: dict[str, dict[int, dict[str, Any]]] = {product: {} for product in PRODUCTS}
    window_records: list[dict[str, Any]] = []
    window_hashes: dict[tuple[str, int], str | None] = {}
    for index, window in enumerate(WINDOWS, start=1):
        response, payload = fetcher(candle_url(window))
        start_epoch = epoch_seconds(window["start"])
        end_epoch = epoch_seconds(window["end"])
        candles, validation = parse_candle_payload(payload, start_epoch, end_epoch)
        product_id = window["product_id"]
        for candle in candles:
            if candle["timestamp"] not in candles_by_product[product_id]:
                candles_by_product[product_id][candle["timestamp"]] = candle
        record = {
            "window_id": f"W{index}",
            "product_id": product_id,
            "start_utc_inclusive": window["start"],
            "end_utc_exclusive": window["end"],
            "granularity_seconds": GRANULARITY_SECONDS,
            "request": response,
            "validation": validation,
            "raw_candle_rows_retained": False,
        }
        window_records.append(record)
        for exception in EXCEPTIONS:
            if exception["product_id"] == product_id:
                ts = epoch_seconds(exception["timestamp"])
                if start_epoch <= ts < end_epoch:
                    window_hashes[(product_id, ts)] = response.get("response_sha256")

    exception_results = [
        compare_exception(item, candles_by_product, window_hashes, product_hashes)
        for item in EXCEPTIONS
    ]
    controls: list[dict[str, Any]] = []
    control_epoch = epoch_seconds(CONTROL_TIMESTAMP)
    for product_id in PRODUCTS:
        candle = candles_by_product.get(product_id, {}).get(control_epoch)
        product_valid = product_records[product_id]["validation"]["identity_valid"]
        online = product_records[product_id]["validation"]["online_control_passed"]
        positive_volume = candle is not None and candle["volume"] > 0
        controls.append({
            "product_id": product_id,
            "timestamp_utc": CONTROL_TIMESTAMP,
            "product_identity_valid": product_valid,
            "product_online": online,
            "historical_control_candle_present": candle is not None,
            "historical_control_volume_positive": positive_volume,
            "control_passed": product_valid and online and positive_volume,
            "candle": candle_summary(candle) if candle is not None else None,
            "product_metadata_response_sha256": product_hashes.get(product_id),
        })

    exceptions_exact = sum(item["exact_timestamp_candle_present"] for item in exception_results)
    exceptions_complete = sum(item["complete_t_minus_1_t_t_plus_1_window"] for item in exception_results)
    controls_passed = sum(item["control_passed"] for item in controls)
    windows_clean = all(
        item["request"].get("http_status") == 200
        and item["request"].get("error") is None
        and item["validation"]["invalid_row_count"] == 0
        and item["validation"]["duplicate_timestamp_count"] == 0
        and item["validation"]["out_of_window_count"] == 0
        and item["validation"]["unaligned_timestamp_count"] == 0
        for item in window_records
    )
    products_valid = all(
        item["request"].get("http_status") == 200
        and item["request"].get("error") is None
        and item["validation"]["identity_valid"]
        and item["validation"]["online_control_passed"]
        for item in product_records.values()
    )
    complete = (
        exceptions_exact == len(EXCEPTIONS)
        and exceptions_complete == len(EXCEPTIONS)
        and controls_passed == len(PRODUCTS)
        and windows_clean
        and products_valid
    )
    failure_reasons: list[str] = []
    if exceptions_exact != len(EXCEPTIONS):
        failure_reasons.append("one_or_more_exact_exception_hour_candles_missing")
    if exceptions_complete != len(EXCEPTIONS):
        failure_reasons.append("one_or_more_three_hour_comparison_windows_incomplete")
    if controls_passed != len(PRODUCTS):
        failure_reasons.append("one_or_more_known_active_product_controls_failed")
    if not windows_clean:
        failure_reasons.append("one_or_more_candle_windows_failed_integrity_checks")
    if not products_valid:
        failure_reasons.append("one_or_more_coinbase_products_failed_identity_or_online_check")

    manifest = {
        "schema_version": 1,
        "status": "coinbase_spot_crosscheck_complete" if complete else "coinbase_spot_crosscheck_incomplete",
        "fetched_at_utc": fetched_at,
        "source": "Coinbase Exchange public REST API",
        "api_base": API_BASE,
        "scope": "bounded hourly BTC-USD and ETH-USD spot plausibility cross-check for nine Kraken PI funding-rate cap exceptions",
        "granularity_seconds": GRANULARITY_SECONDS,
        "product_controls": product_records,
        "candle_windows": window_records,
        "known_active_controls": controls,
        "exception_comparisons": exception_results,
        "summary": {
            "exceptions_total": len(EXCEPTIONS),
            "exceptions_with_exact_hour_candle": exceptions_exact,
            "exceptions_with_complete_three_hour_window": exceptions_complete,
            "exceptions_with_implied_level_inside_three_hour_spot_envelope": sum(
                item["implied_within_3h_low_high_envelope"] is True for item in exception_results
            ),
            "known_active_controls_passed": controls_passed,
            "candle_windows_clean": windows_clean,
            "products_valid_and_online": products_valid,
        },
        "failure_reasons": failure_reasons,
        "research_gate": {
            "kraken_funding_status": "PROVISIONAL_NOT_ACCEPTED",
            "cap_exceptions_accepted": False,
            "timestamp_to_accrual_semantics_resolved": False,
            "settlement_population_completeness_resolved": False,
            "backtest_authorized": False,
            "cross_venue_merge_authorized": False,
        },
        "retention": {
            "raw_coinbase_responses_retained": False,
            "raw_candle_arrays_uploaded": False,
            "raw_market_data_committed": False,
            "only_selected_candle_summaries_and_response_hashes_retained": True,
        },
        "interpretation": (
            "Coinbase BTC-USD and ETH-USD are independent spot references, not Kraken derivatives index values. "
            "Hourly bars are timestamped by Coinbase bucket start. The three-hour comparison explicitly spans "
            "the Kraken timestamp and adjacent hours because Kraken API start/end accrual semantics remain unresolved. "
            "Price proximity cannot validate a funding cap, settlement event, or payable-event population."
        ),
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    manifest = run_probe(args.output_dir)
    print(json.dumps({
        "status": manifest["status"],
        "summary": manifest["summary"],
        "failure_reasons": manifest["failure_reasons"],
        "manifest": str(args.output_dir / "manifest.json"),
    }, indent=2, sort_keys=True))
    return 0 if manifest["status"] == "coinbase_spot_crosscheck_complete" else 2


if __name__ == "__main__":
    sys.exit(main())
