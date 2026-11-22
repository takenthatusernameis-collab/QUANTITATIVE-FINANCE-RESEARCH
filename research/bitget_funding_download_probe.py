#!/usr/bin/env python3
"""Anonymous, bounded UI probe of Bitget's public funding-history download page.

No login, CAPTCHA bypass, private API keys, account data, or network workarounds.
Only the UI snapshot and compact file metadata are emitted; raw downloads stay on
the ephemeral runner and are deleted after inspection.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

URL = "https://www.bitget.com/trade-info/funding_rate"
MAX_DOWNLOAD_BYTES = 10 * 1024 * 1024
MAX_ZIP_CSV_BYTES = 50 * 1024 * 1024
TIME_KEYS = {"time", "timestamp", "ts", "datetime", "date", "fundingtime",
              "fundingtimestamp", "fundingratetimestamp", "settlementtime",
              "fundingtimeutc"}
RATE_KEYS = {"rate", "fundingrate", "fundrate", "fundingratevalue"}


def norm_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def analyze_csv_stream(stream: Any) -> dict[str, Any]:
    reader = csv.DictReader(stream)
    headers = reader.fieldnames or []
    time_col = next((h for h in headers if norm_key(h) in TIME_KEYS), None)
    rate_col = next((h for h in headers if norm_key(h) in RATE_KEYS), None)
    count = 0
    duplicate_timestamps = 0
    seen: set[str] = set()
    invalid_rates = 0
    rate_min: float | None = None
    rate_max: float | None = None
    first_timestamp: str | None = None
    last_timestamp: str | None = None
    samples: list[dict[str, str]] = []
    for row in reader:
        if not row or all(v is None or not str(v).strip() for v in row.values()):
            continue
        count += 1
        clean = {str(k): (str(v)[:200] if v is not None else "") for k, v in row.items() if k is not None}
        if len(samples) < 3:
            samples.append(clean)
        if time_col:
            stamp = str(row.get(time_col, "")).strip()
            if count == 1:
                first_timestamp = stamp
            last_timestamp = stamp
            if stamp in seen:
                duplicate_timestamps += 1
            seen.add(stamp)
        if rate_col:
            try:
                rate = float(str(row.get(rate_col, "")).strip())
                if not math.isfinite(rate):
                    raise ValueError("nonfinite")
                rate_min = rate if rate_min is None else min(rate_min, rate)
                rate_max = rate if rate_max is None else max(rate_max, rate)
            except (ValueError, TypeError):
                invalid_rates += 1
    return {
        "format": "csv",
        "headers": headers,
        "row_count": count,
        "time_column": time_col,
        "first_timestamp_raw": first_timestamp,
        "last_timestamp_raw": last_timestamp,
        "duplicate_timestamp_count": duplicate_timestamps if time_col else None,
        "rate_column": rate_col,
        "invalid_rate_count": invalid_rates if rate_col else None,
        "rate_min": rate_min,
        "rate_max": rate_max,
        "first_rows": samples,
    }


def analyze_download(path: Path) -> dict[str, Any]:
    size = path.stat().st_size
    hasher = hashlib.sha256()
    with path.open("rb") as digest_file:
        for chunk in iter(lambda: digest_file.read(1024 * 1024), b""):
            hasher.update(chunk)
    digest = hasher.hexdigest()
    summary: dict[str, Any] = {
        "filename": path.name,
        "size_bytes": size,
        "sha256": digest,
    }
    if size > MAX_DOWNLOAD_BYTES:
        summary["inspection"] = "size_limit_exceeded"
        return summary
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            entries = [i for i in archive.infolist() if not i.is_dir()]
            summary["zip_entries"] = [
                {"name": i.filename, "size_bytes": i.file_size}
                for i in entries[:20]
            ]
            csv_entry = next((i for i in entries if i.filename.lower().endswith(".csv")), None)
            if csv_entry and csv_entry.file_size <= MAX_ZIP_CSV_BYTES:
                with archive.open(csv_entry) as raw:
                    text_stream = io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace", newline="")
                    summary["data_summary"] = analyze_csv_stream(text_stream)
            elif csv_entry:
                summary["inspection"] = "zip_csv_size_limit_exceeded"
            else:
                summary["inspection"] = "zip_without_csv"
        return summary
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
            summary["data_summary"] = analyze_csv_stream(f)
    except Exception as exc:
        summary["inspection_error"] = f"{type(exc).__name__}: {str(exc)[:250]}"
    return summary


def snapshot_page(page) -> dict[str, Any]:
    return page.evaluate("""() => {
      const visible = el => {
        const r = el.getBoundingClientRect();
        const s = getComputedStyle(el);
        return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
      };
      const els = Array.from(document.querySelectorAll('button,a,[role=button],[role=tab],input,select,textarea,[role=dialog]'))
        .filter(visible).slice(0,100).map(el => ({
          tag: el.tagName.toLowerCase(),
          role: el.getAttribute('role'),
          text: (el.innerText || el.textContent || '').trim().slice(0,180),
          ariaLabel: el.getAttribute('aria-label'),
          title: el.getAttribute('title'),
          placeholder: el.getAttribute('placeholder'),
          type: el.getAttribute('type'),
          value: (el.tagName === 'SELECT' || el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') ? (el.type === 'password' ? '[redacted]' : (el.value || '').slice(0,100)) : null,
          options: el.tagName === 'SELECT' ? Array.from(el.options).slice(0,30).map(o => ({text:o.text.slice(0,100),value:o.value,selected:o.selected})) : null,
          href: el.tagName === 'A' ? el.href : null,
          disabled: !!el.disabled
        }));
      return {
        title: document.title,
        url: location.href,
        bodyText: (document.body?.innerText || '').slice(0,8000),
        interactive: els,
        passwordInputsVisible: Array.from(document.querySelectorAll('input[type=password]')).some(visible),
        captchaFrames: Array.from(document.querySelectorAll('iframe')).map(f => f.src).filter(s => /captcha|verify/i.test(s)).slice(0,10)
      };
    }""")


def run_probe(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "probe": "bitget_public_funding_rate_history_ui",
        "target_url": URL,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "access_mode": "anonymous_browser",
        "auth_used": False,
        "captcha_bypass_used": False,
        "network_workaround_used": False,
        "raw_download_uploaded": False,
        "status": "not_started",
    }
    page = None
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(accept_downloads=True, viewport={"width": 1440, "height": 1000})
            page = context.new_page()
            errors: list[str] = []
            page.on("pageerror", lambda e: errors.append(str(e)[:300]))
            response = page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            manifest["http_status"] = response.status if response else None
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except PlaywrightTimeout:
                manifest["networkidle_timeout"] = True
            page.wait_for_timeout(1500)
            initial = snapshot_page(page)
            manifest["initial_page"] = initial
            history_tab = page.get_by_role("tab", name=re.compile("funding rate history", re.I))
            if history_tab.count() == 0:
                history_tab = page.get_by_text("Funding rate history", exact=True)
            if history_tab.count() > 0 and history_tab.first.is_visible():
                history_tab.first.click(timeout=5000)
                manifest["history_tab_clicked"] = True
                page.wait_for_timeout(1500)
            else:
                manifest["history_tab_clicked"] = False
            history_state = snapshot_page(page)
            manifest["history_state"] = history_state
            screenshot1 = output_dir / "bitget-funding-history-ui.png"
            page.screenshot(path=str(screenshot1), full_page=False)
            manifest["screenshot"] = screenshot1.name

            auth_block = bool(history_state.get("passwordInputsVisible")) or bool(history_state.get("captchaFrames"))
            body_lower = (history_state.get("bodyText") or "").lower()
            auth_block = auth_block or any(phrase in body_lower for phrase in (
                "login to download", "log in to download", "sign in to download", "please login to download"
            ))
            candidates = []
            for button in page.locator("button,[role=button]").all():
                try:
                    if not button.is_visible() or button.is_disabled():
                        continue
                    text = (button.inner_text(timeout=1000) or "").strip()
                    aria = button.get_attribute("aria-label") or ""
                    title = button.get_attribute("title") or ""
                    label = " ".join((text, aria, title)).strip()
                    if re.search(r"download", label, re.I):
                        candidates.append({"locator": button, "label": label[:180]})
                except Exception:
                    continue
            manifest["download_buttons"] = [c["label"] for c in candidates[:10]]
            if auth_block:
                manifest["status"] = "blocked_login_or_captcha"
            elif not candidates:
                manifest["status"] = "ui_inspection_complete_no_download_button"
            else:
                manifest["download_button_clicked"] = True
                download = None
                try:
                    with page.expect_download(timeout=8000) as download_event:
                        candidates[0]["locator"].click(timeout=5000)
                    download = download_event.value
                except PlaywrightTimeout:
                    manifest["download_outcome"] = "no_download_event_within_8s"
                if download:
                    suggested = Path(download.suggested_filename).name[:180] or "download.bin"
                    raw_path = output_dir / "ephemeral-download" / suggested
                    raw_path.parent.mkdir(parents=True, exist_ok=True)
                    download.save_as(str(raw_path))
                    manifest["download"] = analyze_download(raw_path)
                    raw_path.unlink(missing_ok=True)
                    try:
                        raw_path.parent.rmdir()
                    except OSError:
                        pass
                    manifest["status"] = "download_inspected"
                else:
                    manifest["status"] = "button_clicked_no_download"
                after = snapshot_page(page)
                manifest["after_click_state"] = after
                screenshot2 = output_dir / "bitget-after-download-click.png"
                page.screenshot(path=str(screenshot2), full_page=False)
                manifest["after_click_screenshot"] = screenshot2.name
            manifest["page_errors"] = errors[:20]
            browser.close()
    except Exception as exc:
        manifest["status"] = "probe_error"
        manifest["error"] = f"{type(exc).__name__}: {str(exc)[:500]}"
        if page:
            try:
                screenshot = output_dir / "bitget-probe-error.png"
                page.screenshot(path=str(screenshot), full_page=False)
                manifest["error_screenshot"] = screenshot.name
            except Exception:
                pass
    manifest["finished_utc"] = datetime.now(timezone.utc).isoformat()
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    manifest = run_probe(args.output_dir)
    print(json.dumps({
        "status": manifest.get("status"),
        "http_status": manifest.get("http_status"),
        "history_tab_clicked": manifest.get("history_tab_clicked"),
        "download_buttons": manifest.get("download_buttons"),
        "download": manifest.get("download"),
        "error": manifest.get("error"),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
