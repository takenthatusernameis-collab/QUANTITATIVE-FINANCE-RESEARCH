#!/usr/bin/env python3
"""Read-only source feasibility check for the preregistered stablecoin-supply hypothesis."""
from __future__ import annotations
import datetime as dt, hashlib, json, math, os, time, urllib.error, urllib.request
from pathlib import Path

HYPOTHESIS_ID = "QFR-2026-11-26-DEFILLAMA-STABLECOIN-SUPPLY-BTC-DOWNSIDE-01"
STABLECOIN_URL = "https://stablecoins.llama.fi/stablecoincharts/all"
BINANCE_EXCHANGE_INFO_URL = "https://data-api.binance.vision/api/v3/exchangeInfo?symbol=BTCUSDT"
SAMPLE_START, SAMPLE_END = dt.date(2021, 1, 1), dt.date(2026, 11, 24)
SUPPLY_LAG_DAYS, MIN_ROWS, MAX_GAP_DAYS = 2, 1800, 2
ROOT = Path(__file__).resolve().parents[1]
RUN_ID, ATTEMPT = os.environ.get("GITHUB_RUN_ID", "local"), os.environ.get("GITHUB_RUN_ATTEMPT", "1")
NOW = dt.datetime.now(dt.timezone.utc)


def fetch_bytes(url: str, timeout: int = 30) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "QFR-Research/1.0 (public academic research; GitHub Actions)", "Accept": "application/json"})
    last_error = None
    for attempt in range(2):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read()
                if response.status != 200 or not body:
                    raise RuntimeError(f"HTTP {response.status} or empty response for {url}")
                return body
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in {408, 425, 429, 500, 502, 503, 504}:
                raise RuntimeError(f"Non-retryable HTTP {exc.code} for {url}") from exc
        except (urllib.error.URLError, TimeoutError, OSError, RuntimeError) as exc:
            last_error = exc
        if attempt == 0:
            time.sleep(1)
    raise RuntimeError(f"Request failed after two bounded attempts: {url}: {last_error}")


def parse_number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def parse_utc_date(value) -> dt.date:
    if isinstance(value, bool) or value is None:
        raise ValueError(f"Invalid DeFiLlama date: {value!r}")
    text = str(value).strip()
    if not text:
        raise ValueError("Empty DeFiLlama date")
    if "-" in text:
        try:
            return dt.date.fromisoformat(text[:10])
        except ValueError as exc:
            raise ValueError(f"Invalid ISO date: {text!r}") from exc
    try:
        timestamp = int(text)
    except ValueError as exc:
        raise ValueError(f"Invalid Unix timestamp: {text!r}") from exc
    if timestamp <= 0:
        raise ValueError(f"Non-positive Unix timestamp: {timestamp}")
    return dt.datetime.fromtimestamp(timestamp, tz=dt.timezone.utc).date()


def parse_stablecoin_history(body: bytes) -> dict[dt.date, float]:
    try:
        payload = json.loads(body.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"DeFiLlama response is not valid UTF-8 JSON: {exc}") from exc
    if not isinstance(payload, list) or not payload:
        raise ValueError("DeFiLlama stablecoin chart must be a non-empty JSON array")
    values = {}
    for index, row in enumerate(payload):
        if not isinstance(row, dict):
            raise ValueError(f"DeFiLlama row {index} is not an object")
        day = parse_utc_date(row.get("date"))
        circulating = row.get("totalCirculatingUSD")
        if not isinstance(circulating, dict) or "peggedUSD" not in circulating:
            raise ValueError(f"DeFiLlama row {index} lacks totalCirculatingUSD.peggedUSD")
        market_cap = parse_number(circulating.get("peggedUSD"))
        if market_cap is None or market_cap <= 0:
            raise ValueError(f"DeFiLlama row {index} has non-positive/invalid USD-pegged circulating value")
        if day in values:
            raise ValueError(f"Duplicate DeFiLlama UTC date: {day}")
        values[day] = market_cap
    return dict(sorted(values.items()))


def validate_stablecoin_coverage(values: dict[dt.date, float]) -> dict:
    sample_end = SAMPLE_END - dt.timedelta(days=SUPPLY_LAG_DAYS)
    sample = {day: value for day, value in values.items() if SAMPLE_START <= day <= sample_end}
    if not sample:
        raise ValueError("No DeFiLlama observations inside the frozen sample window")
    dates = sorted(sample)
    if dates[0] > SAMPLE_START:
        raise ValueError(f"DeFiLlama starts after frozen sample start: {dates[0]}")
    if dates[-1] < sample_end:
        raise ValueError(f"DeFiLlama ends before required lagged sample cutoff {sample_end}: {dates[-1]}")
    if len(dates) < MIN_ROWS:
        raise ValueError(f"Insufficient DeFiLlama observations: {len(dates)} < {MIN_ROWS}")
    gaps = [(right - left).days for left, right in zip(dates, dates[1:])]
    maximum_gap = max(gaps, default=0)
    if maximum_gap > MAX_GAP_DAYS:
        raise ValueError(f"DeFiLlama maximum daily observation gap {maximum_gap} exceeds {MAX_GAP_DAYS}")
    return {"rows_in_frozen_window": len(dates), "first_date": dates[0].isoformat(), "last_date": dates[-1].isoformat(), "minimum_required_last_date": sample_end.isoformat(), "maximum_gap_days": maximum_gap, "minimum_market_cap_usd": min(sample.values()), "maximum_market_cap_usd": max(sample.values())}


def validate_binance_exchange_info(body: bytes) -> dict:
    try:
        payload = json.loads(body.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Binance exchangeInfo is not valid JSON: {exc}") from exc
    symbols = payload.get("symbols") if isinstance(payload, dict) else None
    if not isinstance(symbols, list) or len(symbols) != 1 or not isinstance(symbols[0], dict):
        raise ValueError("Binance exchangeInfo did not return exactly one BTCUSDT symbol")
    symbol = symbols[0]
    if (symbol.get("symbol"), symbol.get("status"), symbol.get("baseAsset"), symbol.get("quoteAsset")) != ("BTCUSDT", "TRADING", "BTC", "USDT"):
        raise ValueError(f"Binance BTCUSDT is not the expected active Spot market: {symbol}")
    if symbol.get("isSpotTradingAllowed") is False:
        raise ValueError("Binance BTCUSDT does not allow Spot trading")
    return {"symbol": "BTCUSDT", "status": symbol.get("status"), "base_asset": symbol.get("baseAsset"), "quote_asset": symbol.get("quoteAsset"), "spot_trading_allowed": symbol.get("isSpotTradingAllowed")}


def run_preflight() -> dict:
    stable_body = fetch_bytes(STABLECOIN_URL, timeout=40)
    stable = parse_stablecoin_history(stable_body)
    coverage = validate_stablecoin_coverage(stable)
    exchange_body = fetch_bytes(BINANCE_EXCHANGE_INFO_URL, timeout=20)
    market = validate_binance_exchange_info(exchange_body)
    return {"hypothesis_id": HYPOTHESIS_ID, "status": "PASS", "retrieved_at_utc": NOW.isoformat(), "stablecoin_source": {"endpoint": STABLECOIN_URL, "definition": "DeFiLlama totalCirculatingUSD.peggedUSD", "response_sha256": hashlib.sha256(stable_body).hexdigest(), **coverage}, "binance_source": {"endpoint": BINANCE_EXCHANGE_INFO_URL, "response_sha256": hashlib.sha256(exchange_body).hexdigest(), **market}, "frozen_sample": {"start": SAMPLE_START.isoformat(), "btc_end": SAMPLE_END.isoformat(), "stablecoin_required_end": (SAMPLE_END - dt.timedelta(days=SUPPLY_LAG_DAYS)).isoformat(), "supply_lag_days": SUPPLY_LAG_DAYS}, "raw_observations_saved": False, "backtest_run": False}


def main() -> int:
    try:
        result = run_preflight()
    except Exception as exc:
        result = {"hypothesis_id": HYPOTHESIS_ID, "status": "FAIL", "retrieved_at_utc": NOW.isoformat(), "error": f"{type(exc).__name__}: {exc}", "raw_observations_saved": False, "backtest_run": False}
    output_dir = ROOT / "reports" / "generated" / "stablecoin-supply-source-preflight" / f"{RUN_ID}-attempt-{ATTEMPT}"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "preflight.json"
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    rendered = json.dumps(result, indent=2, sort_keys=True)
    print(rendered)
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write("## DeFiLlama stablecoin source preflight\n\n")
            handle.write(f"- Status: **{result['status']}**\n")
            handle.write(f"- Hypothesis: {HYPOTHESIS_ID}\n\n")
            handle.write(rendered + "\n")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
