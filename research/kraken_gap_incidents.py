"""Evidence-pinned correlation of Kraken API funding gaps with status incidents.

A status incident overlapping a gap is evidence of contemporaneous service
degradation, not proof that a funding settlement was skipped or that the
historical funding API omitted a valid record.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


GAPS = (
    {
        "start_utc": "2025-12-04T08:00:00Z",
        "end_utc": "2025-12-04T10:00:00Z",
        "symbols": ("PF_XBTUSD", "PF_ETHUSD", "PI_XBTUSD", "PI_ETHUSD"),
    },
    {
        "start_utc": "2026-02-04T11:00:00Z",
        "end_utc": "2026-02-04T13:00:00Z",
        "symbols": ("PF_XBTUSD", "PF_ETHUSD", "PI_XBTUSD", "PI_ETHUSD"),
    },
    {
        "start_utc": "2026-02-13T17:00:00Z",
        "end_utc": "2026-02-13T19:00:00Z",
        "symbols": ("PF_XBTUSD", "PF_ETHUSD", "PI_XBTUSD", "PI_ETHUSD"),
    },
    {
        "start_utc": "2026-05-09T05:00:00Z",
        "end_utc": "2026-05-09T07:00:00Z",
        "symbols": ("PF_XBTUSD", "PF_ETHUSD", "PI_XBTUSD", "PI_ETHUSD"),
    },
    {
        "start_utc": "2026-10-30T02:00:00Z",
        "end_utc": "2026-10-30T04:00:00Z",
        "symbols": ("PF_XBTUSD", "PF_ETHUSD", "PI_XBTUSD", "PI_ETHUSD"),
    },
)

INCIDENTS = (
    {
        "id": "unichain-funding-2025-12-04",
        "title": "Unichain Funding Delays",
        "start_utc": "2025-12-04T02:01:00Z",
        "end_utc": "2025-12-04T05:52:00Z",
        "api_affected": False,
        "derivatives_affected": False,
        "source_type": "independent_status_history_mirror",
        "source_url": "https://sevanalysis.com/vendors/kraken/",
    },
    {
        "id": "spot-futures-connectivity-2026-02-04",
        "title": "Connectivity and Trading Issues (Spot & Futures) - Web & Mobile",
        "start_utc": "2026-02-04T11:36:00Z",
        "end_utc": "2026-02-04T13:18:00Z",
        "api_affected": True,
        "derivatives_affected": True,
        "source_type": "independent_status_history_mirror",
        "source_url": "https://sevanalysis.com/vendors/kraken/",
    },
    {
        "id": "futures-connectivity-2026-02-13",
        "title": "Futures Exchange Connectivity Issues - Web, Mobile & API (Rest & Websockets)",
        "start_utc": "2026-02-13T17:39:00Z",
        "end_utc": "2026-02-13T18:30:00Z",
        "api_affected": True,
        "derivatives_affected": True,
        "source_type": "independent_status_history_mirror",
        "source_url": "https://sevanalysis.com/vendors/kraken/",
    },
    {
        "id": "api-web-mobile-connectivity-2026-05-09",
        "title": "Connectivity Issues - Web & Mobile",
        "start_utc": "2026-05-09T05:10:00Z",
        "end_utc": "2026-05-11T18:15:00Z",
        "api_affected": True,
        "derivatives_affected": False,
        "source_type": "official_status_page",
        "source_url": "https://status.kraken.com/incidents/0qxsndnx8q3s",
    },
    {
        "id": "spot-derivatives-connectivity-2026-10-30",
        "title": "Spot Exchange Connectivity Issues - Web, Mobile & API (Rest & Websockets)",
        "start_utc": "2026-10-30T02:42:00Z",
        "end_utc": "2026-10-30T03:42:00Z",
        "api_affected": True,
        "derivatives_affected": True,
        "source_type": "official_status_page",
        "source_url": "https://status.kraken.com/incidents/zkqc9db292h5",
    },
)


def _parse_utc(value: str) -> datetime:
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def correlate_gap(gap: dict[str, Any], incidents: tuple[dict[str, Any], ...] = INCIDENTS) -> dict[str, Any]:
    """Return incident overlap evidence without inferring funding settlement causality."""
    gap_start = _parse_utc(gap["start_utc"])
    gap_end = _parse_utc(gap["end_utc"])
    if gap_end <= gap_start:
        raise ValueError("gap end must be after gap start")

    matches = []
    for incident in incidents:
        if not (incident.get("api_affected") or incident.get("derivatives_affected")):
            continue
        incident_start = _parse_utc(incident["start_utc"])
        incident_end = _parse_utc(incident["end_utc"])
        overlap_start = max(gap_start, incident_start)
        overlap_end = min(gap_end, incident_end)
        overlap_seconds = (overlap_end - overlap_start).total_seconds()
        if overlap_seconds > 0:
            matches.append({
                "id": incident["id"],
                "title": incident["title"],
                "overlap_minutes": int(overlap_seconds // 60),
                "api_affected": bool(incident.get("api_affected")),
                "derivatives_affected": bool(incident.get("derivatives_affected")),
                "source_type": incident["source_type"],
                "source_url": incident["source_url"],
            })

    missing_expected = []
    cursor = gap_start + timedelta(hours=1)
    while cursor < gap_end:
        missing_expected.append(cursor.isoformat().replace("+00:00", "Z"))
        cursor += timedelta(hours=1)

    if any(item["derivatives_affected"] for item in matches):
        classification = "DERIVATIVES_CONNECTIVITY_INCIDENT_OVERLAP"
    elif matches:
        classification = "GENERAL_API_CONNECTIVITY_INCIDENT_OVERLAP"
    else:
        classification = "UNEXPLAINED_NO_MATCHING_API_OR_DERIVATIVES_INCIDENT"

    return {
        "gap_start_utc": gap["start_utc"],
        "gap_end_utc": gap["end_utc"],
        "missing_expected_hourly_timestamps": missing_expected,
        "incident_matches": matches,
        "classification": classification,
        "funding_settlement_status": "UNVERIFIED",
        "causal_claim": "NOT_ESTABLISHED",
        "scheduled_funding_pause_evidence": False,
    }


def audit_all_gaps() -> list[dict[str, Any]]:
    return [correlate_gap(gap) for gap in GAPS]
