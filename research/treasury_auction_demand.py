#!/usr/bin/env python3
"""Walk-forward forecast test: Treasury 10-year auction bidder mix -> next 5-day 10y yield change.

Uses only public official Treasury data. This is a forecasting backtest, not a tradable P&L.
"""
from __future__ import annotations

import bisect
import csv
import datetime as dt
import hashlib
import json
import math
import os
import random
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

HYPOTHESIS_ID = "QFR-2026-11-25-UST-AUCTION-ABSORPTION-01"
REPO = "takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH"
START_DATE = dt.date(2008, 1, 1)
END_DATE = dt.datetime.now(dt.timezone.utc).date() - dt.timedelta(days=1)
LOOKBACK_AUCTIONS = 26
MODEL_WINDOW = 52
TARGET_HORIZON = 5
TEST_START = dt.date(2023, 1, 1)
VALIDATION_START = dt.date(2019, 1, 1)
BOOTSTRAP_REPS = 2000
BOOTSTRAP_BLOCK = 4
RNG_SEED = 20261125
BASE_URL = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/auctions_query"
UPDATED_AUCTION_URL = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/treasury_securities_auctions_v2"
YIELD_URL = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml"
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
ROOT = Path(__file__).resolve().parents[1]
RUN_ID = os.environ.get("GITHUB_RUN_ID", "local")
RUN_ATTEMPT = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
SOURCE_SHA = os.environ.get("GITHUB_SHA", "local")
SESSION_TIME = dt.datetime.now(dt.timezone.utc)
SESSION_STAMP = SESSION_TIME.strftime("%Y-%m-%dT%H%M%SZ")
SESSION_DIR = ROOT / "reports" / "sessions" / SESSION_STAMP[:10]
OUTPUT_DIR = ROOT / "reports" / "generated" / "treasury-auction-demand" / f"{RUN_ID}-attempt-{RUN_ATTEMPT}"
REGISTRY_PATH = ROOT / "research" / "HYPOTHESIS-REGISTRY.md"

FIELD_LIST = ",".join([
    "record_date", "auction_date", "cusip", "security_type", "security_term",
    "original_security_term", "tips", "floating_rate",
    "reopening", "comp_accepted", "total_accepted", "bid_to_cover_ratio",
    "primary_dealer_accepted", "direct_bidder_accepted", "indirect_bidder_accepted",
])


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_date(value: object) -> dt.date | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"null", "none", "nan"}:
        return None
    text = text.replace("datetime'", "").replace("'", "")
    try:
        return dt.date.fromisoformat(text[:10])
    except ValueError:
        return None


def parse_float(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"null", "none", "nan", "."}:
        return None
    try:
        number = float(text.replace(",", ""))
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def parse_bool(value: object) -> bool | None:
    text = str(value).strip().lower()
    if text in {"yes", "y", "true", "1"}:
        return True
    if text in {"no", "n", "false", "0"}:
        return False
    return None


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].split(":")[-1]


def fetch_bytes(url: str, timeout: int = 15) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "QFR-Research/1.0 (public academic research; github.com/" + REPO + ")",
            "Accept": "application/json, application/xml, text/csv, */*",
        },
    )
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read()
                if response.status != 200:
                    raise RuntimeError(f"HTTP {response.status} for {url}")
                if not body:
                    raise RuntimeError(f"Empty response for {url}")
                return body
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in {408, 425, 429, 500, 502, 503, 504}:
                raise RuntimeError(f"Non-retryable HTTP {exc.code} for {url}") from exc
        except (urllib.error.URLError, TimeoutError, OSError, RuntimeError) as exc:
            last_error = exc
        if attempt < 1:
            time.sleep(1)
    raise RuntimeError(f"Request failed after 2 bounded attempts: {url}: {last_error}")

def parse_treasury_result_xml(body: bytes) -> dict:
    root = ET.fromstring(body)
    tag_names = set()
    candidate_values = []
    tokens = ("primary", "prim", "direct", "indir", "competitive", "comp", "accepted", "award", "tender", "bid", "total", "cusip", "date", "yield", "security", "offering", "inflation", "floating", "reopening")
    for node in root.iter():
        name = local_name(node.tag)
        tag_names.add(name)
        value = (node.text or "").strip()
        if value and any(token in name.lower() for token in tokens):
            candidate_values.append({"name": name, "value": value})
        for attr_name, attr_value in node.attrib.items():
            attr_local = local_name(attr_name)
            if any(token in attr_local.lower() for token in tokens):
                candidate_values.append({"name": attr_local, "value": str(attr_value)})
    return {
        "root_tag": local_name(root.tag),
        "tag_names": sorted(tag_names),
        "candidate_values": candidate_values[:250],
    }


UPDATED_AUCTION_XML_FIELD_MAP = (
    ("cusip", "CUSIP", "text", 0.0),
    ("security_type", "SecurityType", "text", 0.0),
    ("security_desc", "SecurityDescription", "text", 0.0),
    ("comp_auction_close_date", "CompetitiveAuctionCloseDate", "date", 0.0),
    ("inflation_protected", "InflationProtected", "boolean", 0.0),
    ("floating_rate", "FloatingRate", "boolean", 0.0),
    ("reopening", "Reopening", "boolean", 0.0),
    ("bid_to_cover_ratio", "BidToCoverRatio", "number", 1e-9),
    ("offering_amt", "OfferingAmount", "number", 1.0),
    ("prim_deal_comp_par_awarded", "PrimaryDealersCompetitiveParAwarded", "number", 1.0),
    ("dir_bid_comp_par_awarded", "DirectBiddersCompetitiveParAwarded", "number", 1.0),
    ("indir_bid_comp_par_awarded", "IndirectBiddersCompetitiveParAwarded", "number", 1.0),
    ("subtot_comp_inside_awrd", "SubtotalCompetitiveParAwardedInsideOfOfferingAmount", "number", 1.0),
    ("subtot_comp_outside_awrd", "SubtotalCompetitiveParAwardedOutsideOfOfferingAmount", "number", 1.0),
    ("grand_total_par_awarded", "GrandTotalParAwarded", "number", 1.0),
    ("prim_deal_comp_par_recog", "PrimaryDealersCompetitiveParRecognized", "number", 1.0),
    ("dir_bid_comp_par_recog", "DirectBiddersCompetitiveParRecognized", "number", 1.0),
    ("indir_bid_comp_par_recog", "IndirectBiddersCompetitiveParRecognized", "number", 1.0),
    ("subtot_comp_inside_recog", "SubtotalCompetitiveParRecognizedInsideOfOfferingAmount", "number", 1.0),
    ("subtot_comp_outside_recog", "SubtotalCompetitiveParRecognizedOutsideOfOfferingAmount", "number", 1.0),
    ("grand_total_par_recog", "GrandTotalParRecognized", "number", 1.0),
)


def reconcile_updated_auction_sample(sample: dict | None) -> dict:
    """Reconcile one updated-table API row against its official auction-result XML.

    Only awarded amounts map to the legacy accepted-amount fields. Recognized
    amounts are separately cross-checked and deliberately excluded from the
    competitive-award denominator.
    """
    if not sample:
        return {"status": "NO_SAMPLE"}
    record_date = parse_date(sample.get("record_date"))
    auction_date = parse_date(sample.get("comp_auction_close_date"))
    if record_date is None or auction_date is None:
        return {"status": "INCOMPLETE", "reason": "Record date or competitive auction close date is missing"}
    if record_date < auction_date:
        return {"status": "MISMATCH", "reason": "Record date precedes competitive auction close date"}
    if parse_bool(sample.get("inflation_protected")) is not False:
        return {"status": "INCOMPLETE", "reason": "Inflation-protection status is not verified false"}
    if parse_bool(sample.get("floating_rate")) is not False:
        return {"status": "INCOMPLETE", "reason": "Floating-rate status is not verified false"}
    result_xml = sample.get("result_xml") or {}
    if result_xml.get("status") != "PARSED":
        return {
            "status": "UNAVAILABLE",
            "reason": f"Result XML status is {result_xml.get('status', 'MISSING')}",
        }

    xml_values = {}
    required_xml_names = {item[1] for item in UPDATED_AUCTION_XML_FIELD_MAP}
    for item in result_xml.get("candidate_values", []):
        name = str(item.get("name") or "")
        value = str(item.get("value") or "").strip()
        if name not in required_xml_names:
            continue
        if name in xml_values and xml_values[name] != value:
            return {
                "status": "MISMATCH",
                "reason": f"Conflicting duplicate XML values for {name}",
            }
        xml_values[name] = value

    result_fields = sample.get("result_fields") or {}
    checks = []
    missing = []
    for api_field, xml_field, kind, tolerance in UPDATED_AUCTION_XML_FIELD_MAP:
        api_value = sample.get(api_field) if api_field in sample else result_fields.get(api_field)
        xml_value = xml_values.get(xml_field)
        if api_value is None or xml_value is None:
            missing.append({"api_field": api_field, "xml_field": xml_field})
            continue
        if kind == "number":
            left = parse_float(api_value)
            right = parse_float(xml_value)
            if left is None or right is None:
                missing.append({"api_field": api_field, "xml_field": xml_field})
                continue
            difference = left - right
            matched = abs(difference) <= tolerance
        elif kind == "date":
            left = parse_date(api_value)
            right = parse_date(xml_value)
            difference = None
            matched = left is not None and left == right
        elif kind == "boolean":
            left = parse_bool(api_value)
            right = parse_bool(xml_value)
            if left is None or right is None:
                missing.append({"api_field": api_field, "xml_field": xml_field})
                continue
            difference = None
            matched = left == right
        else:
            left = str(api_value).strip().lower()
            right = str(xml_value).strip().lower()
            difference = None
            matched = bool(left) and left == right
        checks.append({
            "api_field": api_field,
            "xml_field": xml_field,
            "api_value": str(api_value),
            "xml_value": str(xml_value),
            "matched": matched,
            "difference": difference,
        })
        if not matched:
            return {
                "status": "MISMATCH",
                "reason": f"API/XML mismatch for {api_field} versus {xml_field}",
                "field_checks": checks,
            }

    if missing:
        return {
            "status": "INCOMPLETE",
            "reason": "Required API/XML crosswalk fields are missing or non-numeric",
            "missing_fields": missing,
            "field_checks": checks,
        }

    primary = parse_float(result_fields.get("prim_deal_comp_par_awarded"))
    direct = parse_float(result_fields.get("dir_bid_comp_par_awarded"))
    indirect = parse_float(result_fields.get("indir_bid_comp_par_awarded"))
    inside = parse_float(result_fields.get("subtot_comp_inside_awrd"))
    outside = parse_float(result_fields.get("subtot_comp_outside_awrd"))
    bid_to_cover = parse_float(result_fields.get("bid_to_cover_ratio"))
    if any(value is None or value < 0 for value in (primary, direct, indirect, inside, outside)):
        return {"status": "INCOMPLETE", "reason": "Competitive awarded amounts are missing or negative"}
    competitive_awards = inside + outside
    bidder_awards = primary + direct + indirect
    award_difference = bidder_awards - competitive_awards
    if competitive_awards <= 0 or abs(award_difference) > 1.0:
        return {
            "status": "MISMATCH",
            "reason": "Primary/direct/indirect awards do not sum to the competitive award denominator",
            "competitive_awards": competitive_awards,
            "bidder_awards": bidder_awards,
            "difference": award_difference,
        }
    if bid_to_cover is None or bid_to_cover <= 0:
        return {"status": "INCOMPLETE", "reason": "Bid-to-cover ratio is missing or non-positive"}

    recognized_primary = parse_float(result_fields.get("prim_deal_comp_par_recog"))
    recognized_competitive = parse_float(result_fields.get("subtot_comp_inside_recog"))
    return {
        "status": "RECONCILED_SAMPLE_ONLY",
        "field_checks": checks,
        "award_identity": {
            "primary_direct_indirect_sum": bidder_awards,
            "competitive_awards_inside_plus_outside": competitive_awards,
            "difference": award_difference,
        },
        "legacy_crosswalk": {
            "record_date": sample.get("record_date"),
            "auction_date": sample.get("comp_auction_close_date"),
            "cusip": sample.get("cusip"),
            "bid_to_cover_ratio": bid_to_cover,
            "comp_accepted": competitive_awards,
            "primary_dealer_accepted": primary,
            "direct_bidder_accepted": direct,
            "indirect_bidder_accepted": indirect,
            "dealer_share": primary / competitive_awards,
        },
        "recognized_amounts_not_used_for_award_share": {
            "primary_dealer_competitive_recognized": recognized_primary,
            "competitive_inside_recognized": recognized_competitive,
            "reason": "Recognized amounts are separately reported from awarded amounts; the accepted-share crosswalk uses the awarded fields only.",
        },
    }


def is_updated_ten_year_note(row: dict) -> bool:
    if str(row.get("security_type") or "").strip().lower() != "note":
        return False
    original_term = normalize_term(row.get("original_security_term"))
    if original_term:
        return original_term == "10year"
    description = normalize_term(row.get("security_desc"))
    if "10year" in description:
        return True
    return normalize_term(row.get("security_term")) == "10year"


def build_updated_auction_sample(row: dict, candidate_result_fields: list[str]) -> dict:
    metadata_fields = (
        "record_date", "cusip", "security_type", "security_desc",
        "comp_auction_close_date", "issue_date", "maturity_date",
        "security_term", "original_security_term", "inflation_protected",
        "floating_rate", "reopening", "xml_filenm_comp_results",
        "pdf_filenm_comp_results",
    )
    sample = {key: row.get(key) for key in metadata_fields if key in row}
    sample["result_fields"] = {
        key: row.get(key) for key in candidate_result_fields if key in row
    }
    xml_file_name = str(row.get("xml_filenm_comp_results") or "").strip()
    if not xml_file_name:
        sample["result_xml"] = {"status": "NO_FILENAME"}
        sample["reconciliation"] = reconcile_updated_auction_sample(sample)
        return sample

    safe_name = urllib.parse.quote(xml_file_name, safe="._-")
    xml_url = (
        "https://fiscaldata.treasury.gov/static-data/published-reports/"
        f"auctions-query/results/{safe_name}"
    )
    try:
        xml_body = fetch_bytes(xml_url, timeout=20)
        sample["result_xml"] = {
            "status": "PARSED",
            "file_name": xml_file_name,
            "url": xml_url,
            "sha256": sha256(xml_body),
            **parse_treasury_result_xml(xml_body),
        }
    except Exception as xml_exc:
        sample["result_xml"] = {
            "status": "UNAVAILABLE",
            "file_name": xml_file_name,
            "url": xml_url,
            "error": f"{type(xml_exc).__name__}: {xml_exc}",
        }
    sample["reconciliation"] = reconcile_updated_auction_sample(sample)
    return sample


def compare_updated_auction_sample_to_legacy(
    sample: dict, legacy_auctions: list[dict] | None
) -> dict:
    if legacy_auctions is None:
        return {"status": "NOT_CHECKED"}
    reconciliation = sample.get("reconciliation") or {}
    if reconciliation.get("status") != "RECONCILED_SAMPLE_ONLY":
        return {"status": "NOT_COMPARABLE", "reason": "API/XML reconciliation did not pass"}

    crosswalk = reconciliation.get("legacy_crosswalk") or {}
    cusip = str(crosswalk.get("cusip") or "").strip()
    auction_date = parse_date(crosswalk.get("auction_date"))
    legacy = next(
        (
            row for row in legacy_auctions
            if str(row.get("cusip") or "").strip() == cusip
            and row.get("auction_date") == auction_date
        ),
        None,
    )
    if legacy is None:
        return {"status": "NO_LEGACY_MATCH", "cusip": cusip, "auction_date": auction_date.isoformat() if auction_date else None}

    checks = []
    comparisons = (
        ("record_date", parse_date(crosswalk.get("record_date")), legacy.get("record_date"), None),
        ("bid_to_cover", parse_float(crosswalk.get("bid_to_cover_ratio")), legacy.get("bid_to_cover"), 1e-9),
        ("comp_accepted", parse_float(crosswalk.get("comp_accepted")), legacy.get("comp_accepted"), 1.0),
        ("primary_dealer_accepted", parse_float(crosswalk.get("primary_dealer_accepted")), legacy.get("primary_dealer_accepted"), 1.0),
        ("direct_bidder_accepted", parse_float(crosswalk.get("direct_bidder_accepted")), legacy.get("direct_bidder_accepted"), 1.0),
        ("indirect_bidder_accepted", parse_float(crosswalk.get("indirect_bidder_accepted")), legacy.get("indirect_bidder_accepted"), 1.0),
    )
    for field, updated_value, legacy_value, tolerance in comparisons:
        if field == "record_date":
            matched = updated_value is not None and updated_value == legacy_value
            difference = None
        else:
            legacy_number = parse_float(legacy_value)
            matched = updated_value is not None and legacy_number is not None and abs(updated_value - legacy_number) <= tolerance
            difference = updated_value - legacy_number if updated_value is not None and legacy_number is not None else None
        checks.append({
            "field": field,
            "updated_value": str(updated_value) if updated_value is not None else None,
            "legacy_value": str(legacy_value) if legacy_value is not None else None,
            "difference": difference,
            "matched": matched,
        })
    return {
        "status": "MATCH" if all(item["matched"] for item in checks) else "MISMATCH",
        "cusip": cusip,
        "auction_date": auction_date.isoformat() if auction_date else None,
        "field_checks": checks,
    }


def fetch_updated_auction_probe(
    end_date: dt.date, legacy_auctions: list[dict] | None = None
) -> dict:
    """Reconcile every identifiable nominal fixed-rate 10-year Note in the updated API slice.

    This remains a diagnostic sample: rows are not merged into the historical
    model until the updated population's historical coverage and legacy overlap
    are independently established.
    """
    params = {
        "filter": f"record_date:gte:2026-10-01,record_date:lte:{end_date.isoformat()}",
        "sort": "record_date",
        "page[size]": "1000",
        "page[number]": "1",
    }
    base_url = UPDATED_AUCTION_URL + "?" + urllib.parse.urlencode(params)
    try:
        all_rows: list[dict] = []
        page_hashes: dict[str, str] = {}
        total_pages = None
        total_count = None
        page_errors = []
        page_limit = 20
        first_page_url = base_url

        for page_number in range(1, page_limit + 1):
            page_params = dict(params)
            page_params["page[number]"] = str(page_number)
            page_url = UPDATED_AUCTION_URL + "?" + urllib.parse.urlencode(page_params)
            try:
                body = fetch_bytes(page_url, timeout=20)
                payload = json.loads(body.decode("utf-8"))
                page_rows = payload.get("data")
                if not isinstance(page_rows, list):
                    raise RuntimeError("Updated Treasury auctions response has no data array")
                meta = payload.get("meta") or {}
                if page_number == 1:
                    for key, target in (("total-pages", "pages"), ("total-count", "count")):
                        raw = meta.get(key) or meta.get(key.replace("-", "_"))
                        try:
                            parsed = int(raw) if raw is not None else None
                        except (TypeError, ValueError):
                            parsed = None
                        if target == "pages":
                            total_pages = parsed
                        else:
                            total_count = parsed
                all_rows.extend(page_rows)
                page_hashes[f"page_{page_number}"] = sha256(body)
            except Exception as page_exc:
                page_errors.append(f"page {page_number}: {type(page_exc).__name__}: {page_exc}")
                break

            if total_pages is None or total_pages < 1 or page_number >= min(total_pages, page_limit):
                break
            time.sleep(0.1)

        page_complete = (
            bool(all_rows)
            and total_pages is not None
            and total_count is not None
            and total_pages <= page_limit
            and len(page_hashes) == total_pages
            and len(all_rows) == total_count
            and not page_errors
        )
        record_dates = sorted(
            date for date in (parse_date(row.get("record_date")) for row in all_rows) if date is not None
        )
        auction_dates = sorted(
            date for date in (parse_date(row.get("comp_auction_close_date")) for row in all_rows) if date is not None
        )
        schema_fields = sorted({str(key) for row in all_rows for key in row})
        result_tokens = (
            "accepted", "bidder", "bid_to_cover", "dealer", "direct", "indirect",
            "competitive", "tender", "offering", "par_awarded", "par_recog",
            "inside_awrd", "outside_awrd", "comp_par", "subtot_comp", "xml_filenm", "pdf_filenm",
        )
        candidate_result_fields = sorted(
            field for field in schema_fields if any(token in field.lower() for token in result_tokens)
        )

        ten_year_rows = [row for row in all_rows if is_updated_ten_year_note(row)]
        nominal_rows = []
        excluded_tips_or_floating = 0
        unclassified_rows = []
        for row in ten_year_rows:
            inflation = parse_bool(row.get("inflation_protected"))
            floating = parse_bool(row.get("floating_rate"))
            if inflation is True or floating is True:
                excluded_tips_or_floating += 1
            elif inflation is None or floating is None:
                unclassified_rows.append({
                    "cusip": row.get("cusip"),
                    "comp_auction_close_date": row.get("comp_auction_close_date"),
                    "reason": "inflation_protected or floating_rate is missing or unrecognized",
                })
            else:
                nominal_rows.append(row)

        candidate_samples = []
        seen_identities = set()
        duplicate_identities = 0
        for row in nominal_rows:
            sample = build_updated_auction_sample(row, candidate_result_fields)
            cusip = str(sample.get("cusip") or "").strip()
            auction_date = parse_date(sample.get("comp_auction_close_date"))
            identity = (cusip, auction_date.isoformat() if auction_date else None)
            if not cusip or auction_date is None:
                sample["reconciliation"] = {
                    "status": "INCOMPLETE",
                    "reason": "CUSIP or competitive auction close date is missing",
                }
            elif identity in seen_identities:
                duplicate_identities += 1
                sample["reconciliation"] = {
                    "status": "INCOMPLETE",
                    "reason": "Duplicate CUSIP and auction-date identity in updated API page",
                }
            else:
                seen_identities.add(identity)
            sample["legacy_overlap"] = compare_updated_auction_sample_to_legacy(sample, legacy_auctions)
            candidate_samples.append(sample)

        target_samples = [
            sample for sample in candidate_samples
            if parse_date(sample.get("comp_auction_close_date")) == dt.date(2026, 11, 10)
        ]
        reconciliation_statuses = [
            (sample.get("reconciliation") or {}).get("status") for sample in candidate_samples
        ]
        if not page_complete or unclassified_rows or duplicate_identities:
            population_status = "INCOMPLETE"
        elif "MISMATCH" in reconciliation_statuses:
            population_status = "MISMATCH"
        elif "UNAVAILABLE" in reconciliation_statuses:
            population_status = "UNAVAILABLE"
        elif "INCOMPLETE" in reconciliation_statuses or not candidate_samples:
            population_status = "INCOMPLETE" if candidate_samples else "NO_CANDIDATES"
        elif all(status == "RECONCILED_SAMPLE_ONLY" for status in reconciliation_statuses):
            population_status = "RECONCILED_SAMPLE_ONLY"
        else:
            population_status = "INCOMPLETE"

        status_counts = {
            status: reconciliation_statuses.count(status)
            for status in sorted(set(reconciliation_statuses))
        }
        overlap_statuses = [
            (sample.get("legacy_overlap") or {}).get("status") for sample in candidate_samples
        ]
        overlap_count = overlap_statuses.count("MATCH") + overlap_statuses.count("MISMATCH")
        overlap_mismatch_count = overlap_statuses.count("MISMATCH")
        if legacy_auctions is None:
            overlap_status = "NOT_CHECKED"
        elif overlap_mismatch_count:
            overlap_status = "DISCREPANCY"
        elif overlap_count:
            overlap_status = "VERIFIED"
        else:
            overlap_status = "NO_OVERLAP"

        target_sample = target_samples[0] if target_samples else None
        page_digest = sha256("\n".join(f"{key}:{value}" for key, value in sorted(page_hashes.items())).encode("utf-8"))
        return {
            "status": "SAMPLE_ONLY" if page_complete else ("PARTIAL" if all_rows else "NO_DATA"),
            "url": first_page_url,
            "rows_returned": len(all_rows),
            "total_pages": total_pages,
            "total_count": total_count,
            "pages_fetched": len(page_hashes),
            "page_size": 1000,
            "page_errors": page_errors,
            "first_record_date": record_dates[0].isoformat() if record_dates else None,
            "last_record_date": record_dates[-1].isoformat() if record_dates else None,
            "first_auction_date": auction_dates[0].isoformat() if auction_dates else None,
            "last_auction_date": auction_dates[-1].isoformat() if auction_dates else None,
            "schema_fields": schema_fields,
            "candidate_result_fields": candidate_result_fields,
            "target_matches": len(target_samples),
            "target_sample": target_sample,
            "candidate_samples": candidate_samples,
            "candidate_population": {
                "status": population_status,
                "ten_year_note_rows": len(ten_year_rows),
                "nominal_fixed_rows": len(nominal_rows),
                "excluded_tips_or_floating": excluded_tips_or_floating,
                "unclassified_rows": unclassified_rows,
                "reconciled_rows": status_counts.get("RECONCILED_SAMPLE_ONLY", 0),
                "status_counts": status_counts,
                "duplicate_identities": duplicate_identities,
                "historical_completeness": "NOT_ESTABLISHED",
                "page_complete": page_complete,
            },
            "legacy_overlap": {
                "status": overlap_status,
                "overlap_rows": overlap_count,
                "matched_rows": overlap_statuses.count("MATCH"),
                "mismatched_rows": overlap_mismatch_count,
                "no_legacy_match_rows": overlap_statuses.count("NO_LEGACY_MATCH"),
                "not_comparable_rows": overlap_statuses.count("NOT_COMPARABLE"),
            },
            "page_sha256": page_hashes,
            "sha256": page_digest,
            "page_complete": page_complete,
            "limitations": [
                "Diagnostic only: updated-table rows are not merged into the historical model sample.",
                "Page completeness requires every API page and a matching API total-count.",
                "Every identifiable nominal fixed-rate 10-year Note in the retrieved page is reconciled against its official result XML; missing, ambiguous or duplicate identities fail closed.",
                "The API slice begins 2026-10-01 and does not establish historical population completeness.",
                "Legacy overlap is checked by CUSIP and auction date; rows without a legacy match remain unmerged.",
                "Only competitive awarded amounts map to legacy accepted fields; recognized amounts are cross-checked but excluded from the accepted-share denominator.",
            ],
        }
    except Exception as exc:
        return {
            "status": "UNAVAILABLE",
            "url": base_url,
            "error": f"{type(exc).__name__}: {exc}",
            "rows_returned": 0,
            "target_matches": 0,
            "candidate_samples": [],
            "candidate_population": {"status": "UNAVAILABLE", "historical_completeness": "NOT_ESTABLISHED"},
            "legacy_overlap": {"status": "NOT_CHECKED"},
            "page_complete": False,
        }

def fetch_auction_pages(end_date: dt.date) -> tuple[list[dict], dict]:
    all_rows: list[dict] = []
    hashes: dict[str, str] = {}
    attempts: list[str] = []
    date_filter = f"auction_date:gte:{START_DATE.isoformat()},auction_date:lte:{end_date.isoformat()}"
    filter_modes = [
        (date_filter + ",security_type:eq:Note,original_security_term:eq:10-Year,tips:eq:false,floating_rate:eq:false", "narrow nominal fixed-rate 10-year filter"),
        (date_filter + ",security_type:eq:Note", "broad Note filter"),
    ]
    last_error: Exception | None = None

    for filter_text, filter_label in filter_modes:
        for fields in (FIELD_LIST, None):
            try:
                page = 1
                total_pages = 1
                mode_rows: list[dict] = []
                mode_hashes: dict[str, str] = {}
                while page <= total_pages:
                    params = {
                        "filter": filter_text,
                        "sort": "auction_date",
                        "page[size]": "10000",
                        "page[number]": str(page),
                    }
                    if fields:
                        params["fields"] = fields
                    url = BASE_URL + "?" + urllib.parse.urlencode(params)
                    body = fetch_bytes(url)
                    payload = json.loads(body.decode("utf-8"))
                    rows = payload.get("data")
                    if not isinstance(rows, list):
                        raise RuntimeError("Treasury auction response has no data array")
                    mode_rows.extend(rows)
                    mode_hashes[f"auction_page_{page}"] = sha256(body)
                    meta = payload.get("meta") or {}
                    try:
                        total_pages = int(meta.get("total-pages") or meta.get("total_pages") or 1)
                    except (TypeError, ValueError):
                        total_pages = 1
                    if not rows:
                        break
                    page += 1
                    time.sleep(0.15)
                if mode_rows:
                    all_rows = mode_rows
                    hashes = mode_hashes
                    attempts.append(f"Treasury Fiscal Data legacy auctions_query succeeded: {filter_label}; " + ("selected fields" if fields else "full-row fallback"))
                    break
                raise RuntimeError("Treasury auction endpoint returned zero rows")
            except Exception as exc:
                last_error = exc
                attempts.append(f"Auction route failed ({filter_label}; {'selected fields' if fields else 'full-row fallback'}): {exc}")
        if all_rows:
            break
    if not all_rows:
        raise RuntimeError("No usable Treasury auction data. " + " | ".join(attempts)) from last_error
    return all_rows, {"hashes": hashes, "attempts": attempts, "rows_returned": len(all_rows)}

def is_no(value: object) -> bool:
    return str(value).strip().lower() in {"no", "false", "0", "n"}


def normalize_term(value: object) -> str:
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


def attach_updated_target_window(probe: dict, yields: dict[dt.date, float]) -> None:
    yield_dates = sorted(yields)

    def window_for(record_date_value: object) -> dict:
        record_date = parse_date(record_date_value)
        if record_date is None or not yield_dates:
            return {"status": "UNKNOWN"}
        start_index = next((i for i, date in enumerate(yield_dates) if date > record_date), None)
        if start_index is None:
            return {
                "status": "NO_POST_PUBLICATION_YIELD",
                "record_date": record_date.isoformat(),
                "latest_yield_date": yield_dates[-1].isoformat(),
            }
        end_index = start_index + TARGET_HORIZON
        target_start = yield_dates[start_index]
        if end_index >= len(yield_dates):
            return {
                "status": "INCOMPLETE",
                "record_date": record_date.isoformat(),
                "target_start": target_start.isoformat(),
                "target_end": None,
                "latest_yield_date": yield_dates[-1].isoformat(),
                "required_observations_after_start": TARGET_HORIZON,
            }
        return {
            "status": "COMPLETE",
            "record_date": record_date.isoformat(),
            "target_start": target_start.isoformat(),
            "target_end": yield_dates[end_index].isoformat(),
            "latest_yield_date": yield_dates[-1].isoformat(),
        }

    samples = probe.get("candidate_samples") or []
    for sample in samples:
        sample["target_window"] = window_for(sample.get("record_date"))

    target_sample = probe.get("target_sample")
    if target_sample:
        target_sample["target_window"] = window_for(target_sample.get("record_date"))
        probe["target_window"] = target_sample["target_window"]
    elif not samples:
        probe["target_window"] = {"status": "NO_TARGET_SAMPLE"}

    population = probe.get("candidate_population")
    if population is not None:
        counts: dict[str, int] = {}
        for sample in samples:
            status = (sample.get("target_window") or {}).get("status", "UNKNOWN")
            counts[status] = counts.get(status, 0) + 1
        population["target_window_counts"] = counts

def select_ten_year_nominal_auctions(rows: list[dict]) -> tuple[list[dict], dict]:
    selected: list[dict] = []
    counts = {
        "rows_returned": len(rows),
        "not_note": 0,
        "not_original_10y": 0,
        "unknown_or_tips": 0,
        "unknown_or_floating": 0,
        "missing_fields": 0,
        "duplicate_cusip": 0,
        "selected": 0,
        "record_date_fallback_to_auction_date": 0,
        "denominator_mismatch_over_5pct": 0,
    }
    seen: set[tuple[str, str]] = set()
    for row in rows:
        if str(row.get("security_type", "")).strip().lower() != "note":
            counts["not_note"] += 1
            continue
        term = normalize_term(row.get("original_security_term") or row.get("security_term"))
        if term != "10year":
            counts["not_original_10y"] += 1
            continue
        inflation = row.get("tips")
        if inflation is None:
            inflation = row.get("inflation_index_security")
        floating = row.get("floating_rate")
        if inflation is None or not is_no(inflation):
            counts["unknown_or_tips"] += 1
            continue
        if floating is None or not is_no(floating):
            counts["unknown_or_floating"] += 1
            continue
        auction_date = parse_date(row.get("auction_date"))
        record_date = parse_date(row.get("record_date"))
        if auction_date is None:
            counts["missing_fields"] += 1
            continue
        if record_date is None:
            record_date = auction_date
            counts["record_date_fallback_to_auction_date"] += 1
        if record_date < auction_date:
            counts["missing_fields"] += 1
            continue
        cusip = str(row.get("cusip") or "").strip()
        key = (cusip, auction_date.isoformat())
        if not cusip or key in seen:
            counts["duplicate_cusip"] += 1
            continue
        btc = parse_float(row.get("bid_to_cover_ratio"))
        comp_accepted = parse_float(row.get("comp_accepted"))
        primary = parse_float(row.get("primary_dealer_accepted"))
        direct = parse_float(row.get("direct_bidder_accepted"))
        indirect = parse_float(row.get("indirect_bidder_accepted"))
        if btc is None or btc <= 0 or comp_accepted is None or comp_accepted <= 0 or primary is None or direct is None or indirect is None:
            counts["missing_fields"] += 1
            continue
        dealer_share = primary / comp_accepted
        if not (0 <= dealer_share <= 1.05):
            counts["missing_fields"] += 1
            continue
        bidder_total = primary + direct + indirect
        if bidder_total > 0 and abs(bidder_total - comp_accepted) / comp_accepted > 0.05:
            counts["denominator_mismatch_over_5pct"] += 1
        seen.add(key)
        selected.append({
            "cusip": cusip,
            "auction_date": auction_date,
            "record_date": record_date,
            "bid_to_cover": btc,
            "dealer_share": dealer_share,
            "comp_accepted": comp_accepted,
            "primary_dealer_accepted": primary,
            "direct_bidder_accepted": direct,
            "indirect_bidder_accepted": indirect,
            "bidder_total": bidder_total,
            "security_term": row.get("security_term"),
            "original_security_term": row.get("original_security_term"),
            "reopening": row.get("reopening"),
        })
    selected.sort(key=lambda item: (item["record_date"], item["auction_date"], item["cusip"]))
    counts["selected"] = len(selected)
    return selected, counts


def parse_fred_dgs10(body: bytes) -> dict[dt.date, float]:
    reader = csv.DictReader(body.decode("utf-8-sig").splitlines())
    values: dict[dt.date, float] = {}
    for row in reader:
        obs_date = parse_date(row.get("observation_date") or row.get("DATE"))
        value = parse_float(row.get("DGS10"))
        if obs_date is not None and value is not None:
            values[obs_date] = value
    return values


def parse_treasury_xml_page(body: bytes, end_date: dt.date) -> tuple[dict[dt.date, float], int]:
    root = ET.fromstring(body)
    values: dict[dt.date, float] = {}
    entry_count = 0
    for entry in root.iter():
        if local_name(entry.tag) != "entry":
            continue
        entry_count += 1
        fields: dict[str, str] = {}
        for node in entry.iter():
            name = local_name(node.tag)
            if name in {"NEW_DATE", "BC_10YEAR"}:
                fields[name] = (node.text or "").strip()
        obs_date = parse_date(fields.get("NEW_DATE"))
        value = parse_float(fields.get("BC_10YEAR"))
        if obs_date is not None and value is not None and START_DATE <= obs_date <= end_date:
            values[obs_date] = value
    return values, entry_count


def parse_treasury_xml_year(body: bytes, end_date: dt.date) -> dict[dt.date, float]:
    values, _ = parse_treasury_xml_page(body, end_date)
    return values


def fetch_treasury_xml_all_pages(end_date: dt.date) -> tuple[dict[dt.date, float], dict]:
    values: dict[dt.date, float] = {}
    hashes: dict[str, str] = {}
    attempts: list[str] = []
    page_limit = 64
    for page in range(page_limit):
        params = {
            "data": "daily_treasury_yield_curve",
            "field_tdr_date_value": "all",
            "page": str(page),
        }
        url = YIELD_URL + "?" + urllib.parse.urlencode(params)
        body = fetch_bytes(url, timeout=20)
        page_values, entry_count = parse_treasury_xml_page(body, end_date)
        hashes[f"treasury_yield_curve_all_page_{page}"] = sha256(body)
        attempts.append(
            f"Treasury XML all-years page {page}: {entry_count} feed entries; "
            f"{len(page_values)} in-scope 10-year observations"
        )
        if entry_count == 0:
            if page == 0:
                raise RuntimeError("Treasury XML all-years feed returned no entries on page 0")
            break
        for obs_date, value in page_values.items():
            prior = values.get(obs_date)
            if prior is not None and abs(prior - value) > 1e-9:
                raise RuntimeError(
                    f"Treasury XML pagination returned conflicting duplicate {obs_date}: {prior} vs {value}"
                )
            values[obs_date] = value
        time.sleep(0.1)
    else:
        raise RuntimeError(f"Treasury XML all-years feed did not terminate within {page_limit} pages")
    if not values:
        raise RuntimeError("Treasury XML all-years feed contained no in-scope 10-year observations")
    return values, {
        "hashes": hashes,
        "attempts": attempts,
        "pages_fetched": len(hashes),
        "rows": len(values),
    }

def fetch_treasury_yields(end_date: dt.date) -> tuple[dict[dt.date, float], dict]:
    attempts: list[str] = []
    fred_url = FRED_URL + "?" + urllib.parse.urlencode({
        "id": "DGS10",
        "cosd": START_DATE.isoformat(),
        "coed": end_date.isoformat(),
    })
    try:
        fred_body = fetch_bytes(fred_url, timeout=15)
        fred_values = parse_fred_dgs10(fred_body)
        if len(fred_values) < 1000:
            raise RuntimeError(f"FRED DGS10 returned only {len(fred_values)} observations")
        hashes = {"fred_dgs10_primary": sha256(fred_body)}
        attempts.append(f"FRED DGS10 primary succeeded with {len(fred_values)} observations")

        try:
            treasury_values, treasury_meta = fetch_treasury_xml_all_pages(end_date)
            hashes.update(treasury_meta["hashes"])
            attempts.extend(treasury_meta["attempts"])
            overlap = sorted(set(fred_values).intersection(treasury_values))
            if overlap:
                differences = [abs(fred_values[date] - treasury_values[date]) * 100.0 for date in overlap]
                crosscheck = {
                    "status": "VERIFIED" if max(differences) <= 0.5 else "DISCREPANCY",
                    "rows": len(overlap),
                    "pages_fetched": treasury_meta["pages_fetched"],
                    "max_abs_difference_bp": max(differences),
                    "mean_abs_difference_bp": statistics.fmean(differences),
                    "first_date": overlap[0].isoformat(),
                    "last_date": overlap[-1].isoformat(),
                }
            else:
                crosscheck = {
                    "status": "NO_OVERLAP",
                    "rows": 0,
                    "pages_fetched": treasury_meta["pages_fetched"],
                }
        except Exception as treasury_error:
            attempts.append(
                f"Treasury XML all-years cross-check unavailable: "
                f"{type(treasury_error).__name__}: {treasury_error}"
            )
            crosscheck = {
                "status": "UNAVAILABLE",
                "rows": 0,
                "error": f"{type(treasury_error).__name__}: {treasury_error}",
            }

        return fred_values, {
            "provider": "FRED DGS10 (Board of Governors H.15 via FRED); Treasury XML all-years cross-check attempted",
            "hashes": hashes,
            "attempts": attempts,
            "treasury_xml_crosscheck": crosscheck,
            "primary_url": fred_url,
        }
    except Exception as fred_error:
        attempts.append(f"FRED DGS10 primary failed: {type(fred_error).__name__}: {fred_error}")
        treasury_values, treasury_meta = fetch_treasury_xml_all_pages(end_date)
        attempts.extend(treasury_meta["attempts"])
        if len(treasury_values) < 1000:
            raise RuntimeError(
                f"FRED failed and Treasury XML returned only {len(treasury_values)} observations"
            ) from fred_error
        return treasury_values, {
            "provider": "U.S. Treasury daily par-yield curve XML all-years feed (FRED unavailable)",
            "hashes": treasury_meta["hashes"],
            "attempts": attempts,
            "treasury_xml_crosscheck": {
                "status": "PRIMARY_SOURCE",
                "rows": len(treasury_values),
                "pages_fetched": treasury_meta["pages_fetched"],
            },
        }

def fetch_fred_crosscheck(end_date: dt.date) -> tuple[dict[dt.date, float] | None, dict]:
    params = {
        "id": "DGS10",
        "cosd": START_DATE.isoformat(),
        "coed": end_date.isoformat(),
    }
    url = FRED_URL + "?" + urllib.parse.urlencode(params)
    try:
        body = fetch_bytes(url)
        reader = csv.DictReader(body.decode("utf-8-sig").splitlines())
        values: dict[dt.date, float] = {}
        for row in reader:
            obs_date = parse_date(row.get("observation_date") or row.get("DATE"))
            value = parse_float(row.get("DGS10"))
            if obs_date is not None and value is not None:
                values[obs_date] = value
        if not values:
            raise RuntimeError("FRED CSV contained no numeric DGS10 values")
        return values, {"status": "VERIFIED", "sha256": sha256(body), "rows": len(values), "url": url}
    except Exception as exc:
        return None, {"status": "UNAVAILABLE", "error": str(exc), "url": url}


def add_weak_demand_scores(auctions: list[dict], lookback: int = LOOKBACK_AUCTIONS) -> None:
    for index, event in enumerate(auctions):
        history = auctions[max(0, index - lookback):index]
        if len(history) < lookback:
            event["weak_score"] = None
            event["weak_demand"] = None
            continue
        dealer_percentile = sum(item["dealer_share"] <= event["dealer_share"] for item in history) / lookback
        low_btc_percentile = sum(item["bid_to_cover"] >= event["bid_to_cover"] for item in history) / lookback
        event["weak_score"] = 0.5 * (dealer_percentile + low_btc_percentile)
        event["weak_demand"] = event["weak_score"] >= 0.75


def build_events(auctions: list[dict], yields: dict[dt.date, float]) -> tuple[list[dict], dict]:
    yield_dates = sorted(yields)
    yield_values = [yields[date] for date in yield_dates]
    events: list[dict] = []
    skipped = {"no_future_yield_window": 0, "insufficient_pre_history": 0}
    for auction in auctions:
        start_index = bisect.bisect_right(yield_dates, auction["record_date"])
        if start_index + TARGET_HORIZON >= len(yield_dates):
            skipped["no_future_yield_window"] += 1
            continue
        pre_index = start_index - 1
        if pre_index - 5 < 0:
            skipped["insufficient_pre_history"] += 1
            continue
        target_bp = (yield_values[start_index + TARGET_HORIZON] - yield_values[start_index]) * 100.0
        pre_yield_5d_bp = (yield_values[pre_index] - yield_values[pre_index - 5]) * 100.0
        event = dict(auction)
        event.update({
            "yield_start_date": yield_dates[start_index],
            "yield_end_date": yield_dates[start_index + TARGET_HORIZON],
            "yield_start": yield_values[start_index],
            "yield_end": yield_values[start_index + TARGET_HORIZON],
            "target_bp": target_bp,
            "pre_yield_5d_bp": pre_yield_5d_bp,
        })
        events.append(event)
    events.sort(key=lambda item: (item["record_date"], item["auction_date"], item["cusip"]))
    add_weak_demand_scores(events)
    return events, skipped


def solve_linear_system(matrix: list[list[float]], vector: list[float]) -> list[float]:
    size = len(vector)
    augmented = [matrix[row][:] + [vector[row]] for row in range(size)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-10:
            raise ValueError("Singular OLS normal-equation matrix")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        for j in range(column, size + 1):
            augmented[column][j] /= divisor
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            for j in range(column, size + 1):
                augmented[row][j] -= factor * augmented[column][j]
    return [augmented[row][size] for row in range(size)]


def fit_ols_predict(train: list[dict], current: dict, feature_names: list[str]) -> float:
    means = [statistics.fmean(row[name] for row in train) for name in feature_names]
    scales = []
    for column, name in enumerate(feature_names):
        sd = statistics.pstdev(row[name] for row in train)
        scales.append(sd if sd > 1e-9 else 1.0)

    design: list[list[float]] = []
    targets: list[float] = []
    for row in train:
        design.append([1.0] + [(row[name] - means[i]) / scales[i] for i, name in enumerate(feature_names)])
        targets.append(row["target_bp"])
    width = len(feature_names) + 1
    xtx = [[0.0] * width for _ in range(width)]
    xty = [0.0] * width
    for xrow, target in zip(design, targets):
        for i in range(width):
            xty[i] += xrow[i] * target
            for j in range(width):
                xtx[i][j] += xrow[i] * xrow[j]
    for i in range(1, width):
        xtx[i][i] += 1e-8
    coefficients = solve_linear_system(xtx, xty)
    current_x = [1.0] + [(current[name] - means[i]) / scales[i] for i, name in enumerate(feature_names)]
    return sum(coef * value for coef, value in zip(coefficients, current_x))


def walk_forward_predictions(events: list[dict]) -> list[dict]:
    predictions: list[dict] = []
    baseline_features = ["bid_to_cover", "pre_yield_5d_bp"]
    augmented_features = ["bid_to_cover", "dealer_share", "pre_yield_5d_bp"]
    for current in events:
        train = [
            row for row in events
            if row["record_date"] < current["record_date"]
            and row["yield_end_date"] < current["record_date"]
        ][-MODEL_WINDOW:]
        if len(train) < MODEL_WINDOW:
            continue
        try:
            baseline = fit_ols_predict(train, current, baseline_features)
            augmented = fit_ols_predict(train, current, augmented_features)
        except (ValueError, ZeroDivisionError, OverflowError):
            continue
        predictions.append({
            "record_date": current["record_date"],
            "cusip": current["cusip"],
            "target_bp": current["target_bp"],
            "baseline_prediction_bp": baseline,
            "augmented_prediction_bp": augmented,
            "weak_score": current["weak_score"],
            "weak_demand": current["weak_demand"],
            "yield_end_date": current["yield_end_date"],
        })
    return predictions


def forecast_metrics(rows: list[dict], prediction_key: str) -> dict | None:
    if not rows:
        return None
    errors = [row[prediction_key] - row["target_bp"] for row in rows]
    actual = [row["target_bp"] for row in rows]
    predictions = [row[prediction_key] for row in rows]
    directional = [
        (prediction > 0 and target > 0) or (prediction < 0 and target < 0)
        for prediction, target in zip(predictions, actual)
        if abs(target) > 1e-12 and abs(prediction) > 1e-12
    ]
    mean_actual = statistics.fmean(actual)
    denominator = sum((value - mean_actual) ** 2 for value in actual)
    sse = sum(error ** 2 for error in errors)
    return {
        "n": len(rows),
        "mae_bp": statistics.fmean(abs(error) for error in errors),
        "rmse_bp": math.sqrt(sse / len(errors)),
        "directional_accuracy": (sum(directional) / len(directional)) if directional else None,
        "oos_r2_vs_mean": (1.0 - sse / denominator) if denominator > 1e-12 else None,
        "mean_actual_bp": mean_actual,
    }


def circular_block_sample(rows: list[dict], rng: random.Random, block_size: int) -> list[dict]:
    sample: list[dict] = []
    n = len(rows)
    while len(sample) < n:
        start = rng.randrange(n)
        for offset in range(block_size):
            sample.append(rows[(start + offset) % n])
            if len(sample) == n:
                break
    return sample


def bootstrap_mean_difference(rows: list[dict], reps: int = BOOTSTRAP_REPS) -> dict | None:
    if len(rows) < 30:
        return None
    if sum(row["weak_demand"] is True for row in rows) < 5 or sum(row["weak_demand"] is False for row in rows) < 5:
        return None
    rng = random.Random(RNG_SEED)
    differences: list[float] = []
    for _ in range(reps):
        sample = circular_block_sample(rows, rng, BOOTSTRAP_BLOCK)
        weak = [row["target_bp"] for row in sample if row["weak_demand"] is True]
        other = [row["target_bp"] for row in sample if row["weak_demand"] is False]
        if weak and other:
            differences.append(statistics.fmean(weak) - statistics.fmean(other))
    if not differences:
        return None
    differences.sort()
    return {
        "reps": len(differences),
        "block_size_events": BOOTSTRAP_BLOCK,
        "ci_95_low_bp": differences[int(0.025 * (len(differences) - 1))],
        "ci_95_high_bp": differences[int(0.975 * (len(differences) - 1))],
    }


def summarize_weak_demand(rows: list[dict]) -> dict:
    weak = [row["target_bp"] for row in rows if row["weak_demand"] is True]
    other = [row["target_bp"] for row in rows if row["weak_demand"] is False]
    result = {
        "weak_n": len(weak),
        "other_n": len(other),
        "weak_mean_bp": statistics.fmean(weak) if weak else None,
        "other_mean_bp": statistics.fmean(other) if other else None,
        "difference_bp": (statistics.fmean(weak) - statistics.fmean(other)) if weak and other else None,
        "bootstrap": bootstrap_mean_difference(rows),
    }
    return result


def compare_fred(primary: dict[dt.date, float], secondary: dict[dt.date, float] | None) -> dict:
    if not secondary:
        return {"status": "UNAVAILABLE"}
    overlap = sorted(set(primary).intersection(secondary))
    if not overlap:
        return {"status": "NO_OVERLAP", "rows": 0}
    diffs = [abs(primary[date] - secondary[date]) * 100.0 for date in overlap]
    return {
        "status": "VERIFIED" if max(diffs) <= 0.5 else "DISCREPANCY",
        "rows": len(overlap),
        "max_abs_difference_bp": max(diffs),
        "mean_abs_difference_bp": statistics.fmean(diffs),
        "first_date": overlap[0].isoformat(),
        "last_date": overlap[-1].isoformat(),
    }


def safe_round(value: float | None, digits: int = 4) -> float | None:
    return round(value, digits) if value is not None and math.isfinite(value) else None


def json_safe(value):
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def update_registry(status: str, disposition: str, data_scope: str, evidence_path: str, metrics_text: str) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if REGISTRY_PATH.exists():
        text = REGISTRY_PATH.read_text(encoding="utf-8")
    else:
        text = "# Hypothesis Registry\n\n| Hypothesis ID | Status | Mechanism / falsifiable claim | Data scope | Disposition | Evidence |\n|---|---|---|---|---|---|\n"
    row = (
        f"| {HYPOTHESIS_ID} | {status} | Primary-dealer accepted share adds incremental walk-forward predictive information about the next five-business-day 10-year yield change beyond bid-to-cover and recent yield movement; weak demand is expected to precede higher yields. | {data_scope} | {disposition}; {metrics_text} | [{evidence_path}]({evidence_path}) |"
    )
    lines = text.splitlines()
    found = False
    for index, line in enumerate(lines):
        if line.startswith(f"| {HYPOTHESIS_ID} |"):
            lines[index] = row
            found = True
            break
    if not found:
        if lines and not lines[-1].strip():
            lines = lines[:-1]
        lines.append(row)
    REGISTRY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_outputs(result: dict, report: str) -> tuple[str, str]:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = SESSION_DIR / f"{SESSION_STAMP}_session-treasury-auction-{RUN_ID}.md"
    manifest_path = OUTPUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(json_safe(result), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(report, encoding="utf-8")
    status = result.get("status", "INCONCLUSIVE")
    disposition = result.get("disposition", "INCONCLUSIVE")
    metrics = result.get("summary_metrics") or {}
    updated_probe = result.get("updated_auction_probe") or {}
    metrics_text = (
        f"test OOS n={metrics.get('test_n', 0)}, augmented RMSE={metrics.get('test_augmented_rmse_bp')} bp, "
        f"baseline RMSE={metrics.get('test_baseline_rmse_bp')} bp, RMSE improvement={metrics.get('test_rmse_improvement_pct')}%, "
        f"weak-demand events={((result.get('test_metrics') or {}).get('weak_demand_event_study') or {}).get('weak_n', 0)}; "
        f"updated auctions API probe={updated_probe.get('status', 'UNAVAILABLE')}, "
        f"10-year nominal rows={((updated_probe.get('candidate_population') or {}).get('nominal_fixed_rows', 0))}, "
        f"population crosswalk={((updated_probe.get('candidate_population') or {}).get('status', 'NOT_ATTEMPTED'))}, "
        f"legacy overlap={((updated_probe.get('legacy_overlap') or {}).get('status', 'NOT_CHECKED'))}"
    )
    data_scope = result.get("data_scope", "Data scope unresolved")
    update_registry(status, disposition, data_scope, '../' + str(report_path.relative_to(ROOT)), metrics_text)
    return str(report_path.relative_to(ROOT)), str(manifest_path.relative_to(ROOT))


def run_research() -> dict:
    end_date = END_DATE
    auction_rows, auction_meta = fetch_auction_pages(end_date)
    auctions, auction_quality = select_ten_year_nominal_auctions(auction_rows)
    updated_auction_probe = fetch_updated_auction_probe(end_date, legacy_auctions=auctions)
    if len(auctions) < MODEL_WINDOW + 30:
        raise RuntimeError(
            f"Insufficient selected 10-year nominal auctions ({len(auctions)}); "
            f"need at least {MODEL_WINDOW + 30} for rolling training plus evaluation."
        )
    yields, yield_meta = fetch_treasury_yields(end_date)
    attach_updated_target_window(updated_auction_probe, yields)
    if len(yields) < 1000:
        raise RuntimeError(f"Insufficient Treasury 10-year yield observations: {len(yields)}")
    treasury_xml_crosscheck = yield_meta.get("treasury_xml_crosscheck", {"status": "NOT_AVAILABLE"})

    events, event_quality = build_events(auctions, yields)
    predictions = walk_forward_predictions(events)
    validation_rows = [row for row in predictions if VALIDATION_START <= row["record_date"] < TEST_START]
    test_rows = [row for row in predictions if row["record_date"] >= TEST_START]
    all_rows = [row for row in predictions if row["record_date"] >= VALIDATION_START]
    baseline_all = forecast_metrics(all_rows, "baseline_prediction_bp")
    augmented_all = forecast_metrics(all_rows, "augmented_prediction_bp")
    baseline_validation = forecast_metrics(validation_rows, "baseline_prediction_bp")
    augmented_validation = forecast_metrics(validation_rows, "augmented_prediction_bp")
    baseline_test = forecast_metrics(test_rows, "baseline_prediction_bp")
    augmented_test = forecast_metrics(test_rows, "augmented_prediction_bp")
    weak_test = summarize_weak_demand([row for row in test_rows if row["weak_demand"] is not None])
    weak_test_rows = [row for row in test_rows if row["weak_demand"] is not None]

    test_n = len(test_rows)
    mae_improvement = None
    rmse_improvement = None
    if baseline_test and augmented_test:
        mae_improvement = 100.0 * (baseline_test["mae_bp"] - augmented_test["mae_bp"]) / baseline_test["mae_bp"] if baseline_test["mae_bp"] else None
        rmse_improvement = 100.0 * (baseline_test["rmse_bp"] - augmented_test["rmse_bp"]) / baseline_test["rmse_bp"] if baseline_test["rmse_bp"] else None

    valid_backtest = test_n >= 30 and baseline_test is not None and augmented_test is not None
    event_effect_positive = weak_test.get("difference_bp") is not None and weak_test["difference_bp"] > 0
    model_improves = rmse_improvement is not None and rmse_improvement > 0
    bootstrap = weak_test.get("bootstrap") or {}
    ci_supports_positive = bootstrap.get("ci_95_low_bp") is not None and bootstrap["ci_95_low_bp"] > 0

    if not valid_backtest:
        status = "INCONCLUSIVE"
        disposition = "INCONCLUSIVE — fewer than 30 test-period walk-forward forecasts or incomplete model metrics"
    elif model_improves and event_effect_positive and ci_supports_positive:
        status = "BACKTESTED"
        disposition = "PROMISING BUT UNVALIDATED — incremental forecast improvement and positive weak-demand effect; robustness and tradable-price validation remain outstanding"
    elif not model_improves and not event_effect_positive:
        status = "REJECTED"
        disposition = "REJECTED — dealer-composition signal did not improve out-of-sample RMSE and the weak-demand event effect was not positive"
    else:
        status = "INCONCLUSIVE"
        disposition = "INCONCLUSIVE — mixed predictive evidence; do not promote or claim an economic edge"

    yield_dates = sorted(yields)
    max_gap_days = max(((yield_dates[i] - yield_dates[i - 1]).days for i in range(1, len(yield_dates))), default=0)
    source_hashes = {}
    source_hashes.update(auction_meta["hashes"])
    source_hashes.update(yield_meta["hashes"])
    if updated_auction_probe.get("sha256"):
        source_hashes["updated_auction_probe"] = updated_auction_probe["sha256"]
    target_xml = ((updated_auction_probe.get("target_sample") or {}).get("result_xml") or {})
    if target_xml.get("sha256"):
        source_hashes["updated_auction_result_xml"] = target_xml["sha256"]
    for index, sample in enumerate(updated_auction_probe.get("candidate_samples") or [], start=1):
        xml_meta = sample.get("result_xml") or {}
        if xml_meta.get("sha256"):
            identity = str(sample.get("cusip") or index)
            source_hashes[f"updated_auction_result_xml_{identity}"] = xml_meta["sha256"]

    summary_metrics = {
        "all_oos_n": len(all_rows),
        "validation_n": len(validation_rows),
        "test_n": test_n,
        "test_baseline_mae_bp": safe_round(baseline_test["mae_bp"] if baseline_test else None),
        "test_augmented_mae_bp": safe_round(augmented_test["mae_bp"] if augmented_test else None),
        "test_baseline_rmse_bp": safe_round(baseline_test["rmse_bp"] if baseline_test else None),
        "test_augmented_rmse_bp": safe_round(augmented_test["rmse_bp"] if augmented_test else None),
        "test_rmse_improvement_pct": safe_round(rmse_improvement),
        "test_baseline_directional_accuracy": safe_round(baseline_test["directional_accuracy"] if baseline_test else None),
        "test_augmented_directional_accuracy": safe_round(augmented_test["directional_accuracy"] if augmented_test else None),
        "weak_demand_mean_difference_bp": safe_round(weak_test.get("difference_bp")),
        "weak_demand_bootstrap_ci_low_bp": safe_round(bootstrap.get("ci_95_low_bp")),
        "weak_demand_bootstrap_ci_high_bp": safe_round(bootstrap.get("ci_95_high_bp")),
    }
    return {
        "hypothesis_id": HYPOTHESIS_ID,
        "status": status,
        "disposition": disposition,
        "daily_kpi": "MET" if valid_backtest else "MISSED",
        "run_id": RUN_ID,
        "run_attempt": RUN_ATTEMPT,
        "source_commit_sha": SOURCE_SHA,
        "retrieved_at_utc": SESSION_TIME.isoformat(),
        "sample_start": START_DATE.isoformat(),
        "sample_end_cutoff": end_date.isoformat(),
        "data_scope": f"10-year nominal Treasury notes, {auctions[0]['auction_date']} to {auctions[-1]['auction_date']}; {yield_meta['provider']} daily yield observations {yield_dates[0]} to {yield_dates[-1]}",
        "updated_auction_probe": updated_auction_probe,
        "auction_source": {
            "url": BASE_URL,
            "rows_returned": auction_meta["rows_returned"],
            "quality": auction_quality,
            "attempts": auction_meta["attempts"],
        },
        "yield_source": {
            "provider": yield_meta["provider"],
            "observations": len(yields),
            "first_date": yield_dates[0],
            "last_date": yield_dates[-1],
            "max_calendar_gap_days": max_gap_days,
            "attempts": yield_meta["attempts"],
        },
        "treasury_xml_crosscheck": treasury_xml_crosscheck,
        "source_sha256": source_hashes,
        "event_construction": {
            "events_with_targets": len(events),
            "skipped": event_quality,
            "target_horizon_business_days": TARGET_HORIZON,
            "rolling_demand_lookback_auctions": LOOKBACK_AUCTIONS,
            "rolling_model_window_events": MODEL_WINDOW,
            "model_training_rule": "Only prior events whose five-business-day target end date is strictly before the current auction record_date are eligible.",
        },
        "validation_metrics": {
            "baseline": baseline_validation,
            "augmented": augmented_validation,
        },
        "test_metrics": {
            "baseline": baseline_test,
            "augmented": augmented_test,
            "weak_demand_event_study": weak_test,
        },
        "summary_metrics": summary_metrics,
        "limitations": [
            "This is a yield-forecasting backtest, not a tradable futures/ETF P&L.",
            "No CAGR, Sharpe, Sortino, turnover or drawdown is claimed.",
            "The run uses H.15 DGS10 from the Board of Governors via FRED when that source succeeds; it is not assumed identical to the direct Treasury daily par-yield curve.",
            "The direct Treasury daily par-yield XML all-years feed is independently cross-checked when accessible; its status is recorded separately and a failed request is not treated as a zero-observation source.",
            "Auction result publication is conservatively lagged: the target starts at the first yield-series observation strictly after record_date.",
            "The yield series is a reference series, not an executable quote.",
            "No forward-filling or synthetic observations are used.",
            "Every identifiable nominal fixed-rate 10-year Note in the retrieved post-2026-10-01 Treasury auctions API slice is cross-checked against official result XML and compared with any CUSIP/auction-date legacy overlap; this remains diagnostic because historical population completeness is not established and no updated rows are merged.",
            "Incremental predictive value requires independent robustness and a separate tradable-instrument data source before any economic interpretation.",
        ],
    }


def render_report(result: dict, error: str | None = None) -> str:
    summary = result.get("summary_metrics") or {}
    test = result.get("test_metrics") or {}
    validation = result.get("validation_metrics") or {}
    auction = result.get("auction_source") or {}
    yield_source = result.get("yield_source") or {}
    treasury_crosscheck = result.get("treasury_xml_crosscheck") or {}
    updated_probe = result.get("updated_auction_probe") or {}
    updated_reconciliation = (updated_probe.get("target_sample") or {}).get("reconciliation") or {}
    crosswalk = updated_reconciliation.get("legacy_crosswalk") or {}
    lines = [
        f"# Session report — Treasury auction bidder-composition forecast ({SESSION_STAMP})",
        "",
        f"- Hypothesis: {HYPOTHESIS_ID}",
        f"- Status: {result.get('status', 'INCONCLUSIVE')}",
        f"- Disposition: {result.get('disposition', 'INCONCLUSIVE')}",
        f"- Daily research KPI: {result.get('daily_kpi', 'MISSED')}",
        f"- GitHub run: {RUN_ID}, attempt {RUN_ATTEMPT}",
        f"- Triggering commit: {SOURCE_SHA}",
        f"- Research scope: {result.get('data_scope', 'not established')}",
        "",
        "## Research question and preregistered test",
        "",
        "Does primary-dealer accepted share add walk-forward predictive information about the next five-business-day change in the 10-year yield beyond the published bid-to-cover ratio and the latest five-business-day yield move? The directional prediction is that weak auction demand (high dealer absorption and low bid-to-cover) precedes higher yields. When FRED DGS10 is the available primary series, this is explicitly an H.15 constant-maturity-yield proxy test; it is not represented as a direct Treasury par-yield-curve test.",
        "",
        "The baseline model uses bid-to-cover and the latest five-business-day yield change. The augmented model adds primary-dealer accepted share. Both use a rolling 52-event OLS window. Training observations are admitted only when their target window ended strictly before the current auction record_date. Weak-demand scores use only the preceding 26 auctions; the fixed weak-score threshold is 0.75 (not a guaranteed 25% event share).",
        "",
        "## Verified data and provenance",
        "",
        f"- Auction rows returned: {auction.get('rows_returned', 'unknown')}",
        f"- Selected nominal 10-year auctions: {auction.get('quality', {}).get('selected', 'unknown')}",
        f"- Auction-source attempts: {'; '.join(auction.get('attempts', []))}",
        f"- Yield provider: {yield_source.get('provider', 'unknown')}",
        f"- Yield observations: {yield_source.get('observations', 'unknown')}",
        f"- Yield coverage: {yield_source.get('first_date', 'unknown')} to {yield_source.get('last_date', 'unknown')}",
        f"- Maximum calendar gap between observed yield dates: {yield_source.get('max_calendar_gap_days', 'unknown')} days",
        f"- Direct Treasury XML cross-check: {treasury_crosscheck.get('status', 'unknown')} ({treasury_crosscheck.get('rows', 0)} overlapping observations)",
        "",
        "## Updated Treasury auctions API probe (diagnostic only)",
        "",
        f"- Status: {updated_probe.get('status', 'UNAVAILABLE')}",
        f"- Rows returned: {updated_probe.get('rows_returned', 0)}; API pages: {updated_probe.get('total_pages', 'unknown')}",
        f"- Record-date coverage: {updated_probe.get('first_record_date', 'unknown')} to {updated_probe.get('last_record_date', 'unknown')}",
        f"- 2026-11-10 10-year note matches: {updated_probe.get('target_matches', 0)}",
        f"- API total-count: {updated_probe.get('total_count', 'unknown')}; pages fetched: {updated_probe.get('pages_fetched', 0)}; page complete: {updated_probe.get('page_complete', False)}",
        f"- Candidate bidder/result fields: {', '.join(updated_probe.get('candidate_result_fields', []))}",
        f"- Nominal fixed-rate 10-year rows: {((updated_probe.get('candidate_population') or {}).get('nominal_fixed_rows', 0))}; row-level XML population status: {((updated_probe.get('candidate_population') or {}).get('status', 'UNKNOWN'))}",
        f"- Row-level reconciliation counts: {((updated_probe.get('candidate_population') or {}).get('status_counts', {}))}",
        f"- Legacy CUSIP/auction-date overlap: {((updated_probe.get('legacy_overlap') or {}).get('status', 'NOT_CHECKED'))}; matched={((updated_probe.get('legacy_overlap') or {}).get('matched_rows', 0))}; mismatched={((updated_probe.get('legacy_overlap') or {}).get('mismatched_rows', 0))}; no legacy match={((updated_probe.get('legacy_overlap') or {}).get('no_legacy_match_rows', 0))}",
        f"- Target 2026-11-10 result XML: {((updated_probe.get('target_sample') or {}).get('result_xml') or {}).get('status', 'NOT_ATTEMPTED')}",
        f"- Target API/XML award crosswalk: {updated_reconciliation.get('status', 'NOT_ATTEMPTED')}",
        f"- Target reconciled competitive award denominator: {crosswalk.get('comp_accepted', 'unknown')}",
        f"- Target reconciled primary-dealer award share: {safe_round(crosswalk.get('dealer_share'))}",
        f"- Candidate five-business-day target windows: {((updated_probe.get('candidate_population') or {}).get('target_window_counts', {}))}",
        "- This is a row-level crosswalk of the retrieved post-2026-10-01 slice only; historical completeness is not established and no updated-table rows are merged into the model.",
        "",
        "## Out-of-sample forecast results",
        "",
        "| Metric | Validation 2019–2022 | Test 2023 onward |",
        "|---|---:|---:|",
        f"| Forecast count | {summary.get('validation_n', 0)} | {summary.get('test_n', 0)} |",
        f"| Baseline RMSE (bp) | {safe_round((validation.get('baseline') or {}).get('rmse_bp'))} | {summary.get('test_baseline_rmse_bp')} |",
        f"| Augmented RMSE (bp) | {safe_round((validation.get('augmented') or {}).get('rmse_bp'))} | {summary.get('test_augmented_rmse_bp')} |",
        f"| Test RMSE improvement | n/a | {summary.get('test_rmse_improvement_pct')}% |",
        f"| Baseline directional accuracy | {safe_round((validation.get('baseline') or {}).get('directional_accuracy'))} | {summary.get('test_baseline_directional_accuracy')} |",
        f"| Augmented directional accuracy | {safe_round((validation.get('augmented') or {}).get('directional_accuracy'))} | {summary.get('test_augmented_directional_accuracy')} |",
        "",
        "### Weak-demand event study (test period)",
        "",
        f"- Weak-demand events: {test.get('weak_demand_event_study', {}).get('weak_n', 0)}",
        f"- Other events: {test.get('weak_demand_event_study', {}).get('other_n', 0)}",
        f"- Mean five-day yield change, weak demand (bp): {safe_round(test.get('weak_demand_event_study', {}).get('weak_mean_bp'))}",
        f"- Mean five-day yield change, other events (bp): {safe_round(test.get('weak_demand_event_study', {}).get('other_mean_bp'))}",
        f"- Difference (bp): {summary.get('weak_demand_mean_difference_bp')}",
        f"- Moving-block bootstrap 95% CI (bp): [{summary.get('weak_demand_bootstrap_ci_low_bp')}, {summary.get('weak_demand_bootstrap_ci_high_bp')}]",
        "",
        "## Scientific interpretation",
        "",
        result.get("disposition", "No disposition established."),
        "",
        "This experiment is a predictive forecast backtest, not a trading strategy backtest. No tradable P&L, CAGR, Sharpe, Sortino, Calmar, turnover or drawdown is claimed. A promising forecast would still require robustness testing and an independently sourced, executable 10-year futures or ETF price series before any economic-value claim.",
        "",
        "## Failure handling and alternatives",
        "",
        f"- Primary yield source: {yield_source.get('provider', 'unknown')}.",
        f"- Independent direct Treasury XML cross-check: {treasury_crosscheck.get('status', 'unknown')} ({treasury_crosscheck.get('rows', 0)} overlapping observations).",
        f"- Yield-source retrieval attempts: {'; '.join(yield_source.get('attempts', []))}",
        "- Direct Treasury XML all-years pagination is attempted as a materially different route from the previously timed-out per-year requests.",
        "- Auction source: Treasury Fiscal Data legacy auctions_query endpoint; selected-field query with full-row fallback.",
        "- Raw market/source rows are not committed; response SHA-256 hashes are retained in the generated manifest.",
        "",
        "## Reproducibility",
        "",
        f"- Generated manifest: reports/generated/treasury-auction-demand/{RUN_ID}-attempt-{RUN_ATTEMPT}/manifest.json",
        f"- Source code: research/treasury_auction_demand.py",
        f"- Tests: research/test_treasury_auction_demand.py",
        f"- Triggering commit: {SOURCE_SHA}",
        f"- GitHub run: https://github.com/{REPO}/actions/runs/{RUN_ID}",
        "",
        "## Daily KPI and next action",
        "",
        f"- DAILY KPI: {result.get('daily_kpi', 'MISSED')}.",
        "- Next: if the incremental forecast survives, run regime/term controls and obtain a separately authorized public or licensed-free tradable 10-year futures/ETF price source. If rejected, preserve the negative result and test a different market mechanism.",
        "",
        "## Claims ledger",
        "",
        "- VERIFIED: facts explicitly backed by retrieved source responses, hashes and completed model output in the manifest.",
        "- UNVERIFIED: economic tradability, causal interpretation, future persistence and any live execution feasibility.",
        "",
        "## Effort allocation",
        "",
        "- Research and empirical work: approximately 70%.",
        "- Runner and repository operations: approximately 30%.",
        "",
    ]
    if error:
        lines.extend(["## Blocker", "", f"- INCONCLUSIVE: {error}", ""])
    return "\n".join(lines)


def main() -> int:
    try:
        result = run_research()
        report = render_report(result)
        report_path, manifest_path = write_outputs(result, report)
        print(json.dumps({
            "hypothesis_id": HYPOTHESIS_ID,
            "status": result["status"],
            "disposition": result["disposition"],
            "daily_kpi": result["daily_kpi"],
            "report_path": report_path,
            "manifest_path": manifest_path,
            "summary_metrics": result.get("summary_metrics"),
        }, indent=2))
        return 0
    except Exception as exc:
        result = {
            "hypothesis_id": HYPOTHESIS_ID,
            "status": "INCONCLUSIVE",
            "disposition": f"INCONCLUSIVE — {type(exc).__name__}: {exc}",
            "daily_kpi": "MISSED",
            "run_id": RUN_ID,
            "run_attempt": RUN_ATTEMPT,
            "source_commit_sha": SOURCE_SHA,
            "retrieved_at_utc": SESSION_TIME.isoformat(),
            "sample_start": START_DATE.isoformat(),
            "sample_end_cutoff": END_DATE.isoformat(),
            "data_scope": "Treasury 10-year nominal note auction and daily par-yield pilot; complete scope not verified",
            "alternatives_attempted": [
                "Treasury Fiscal Data legacy auctions_query selected-field route",
                "Treasury Fiscal Data legacy auctions_query full-row fallback",
                "Official Treasury daily par-yield XML all-years paginated feed",
                "FRED DGS10 CSV primary/fallback",
            ],
            "error": f"{type(exc).__name__}: {exc}",
        }
        report = render_report(result, error=result["error"])
        report_path, manifest_path = write_outputs(result, report)
        print(json.dumps({
            "hypothesis_id": HYPOTHESIS_ID,
            "status": "INCONCLUSIVE",
            "daily_kpi": "MISSED",
            "error": result["error"],
            "report_path": report_path,
            "manifest_path": manifest_path,
        }, indent=2))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
