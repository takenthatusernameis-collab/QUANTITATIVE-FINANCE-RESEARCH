#!/usr/bin/env python3
"""Safely inspect the specific OKX Funding rate download control.

No login, cookie consent, CAPTCHA bypass, network workaround, form submission, or
file save is performed. If clicking starts a direct download, cancel immediately.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

URL = "https://www.okx.com/historical-data"


def snapshot(page) -> dict:
    return page.evaluate("""() => {
      const visible = el => {
        const r = el.getBoundingClientRect(), s = getComputedStyle(el);
        return r.width > 0 && r.height > 0 && s.display !== 'none' &&
          s.visibility !== 'hidden' && Number(s.opacity || 1) > 0;
      };
      const clean = s => (s || '').replace(/\\s+/g, ' ').trim();
      const controls = Array.from(document.querySelectorAll(
        'button,a,[role=button],input,select,textarea,[role=dialog],[aria-modal=true]'
      )).filter(visible).slice(0,80).map(el => ({
        tag: el.tagName.toLowerCase(), role: el.getAttribute('role'),
        text: clean(el.innerText || el.textContent).slice(0,180),
        ariaLabel: el.getAttribute('aria-label'), title: el.getAttribute('title'),
        type: el.getAttribute('type'), disabled: !!el.disabled,
        href: el.tagName === 'A' ? el.href : null,
        value: (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT')
          ? (el.type === 'password' ? '[redacted]' : (el.value || '').slice(0,100)) : null
      }));
      const dialogs = Array.from(document.querySelectorAll(
        '[role=dialog],[aria-modal=true],dialog,[class*="modal" i],[class*="dialog" i],[class*="popover" i],[class*="tooltip" i]'
      )).filter(visible).map(el => ({
        tag: el.tagName.toLowerCase(), text: clean(el.innerText).slice(0,2500),
        controls: Array.from(el.querySelectorAll('button,input,select,textarea,[role=button]'))
          .filter(visible).slice(0,30).map(c => ({
            tag:c.tagName.toLowerCase(), role:c.getAttribute('role'),
            text:clean(c.innerText || c.textContent).slice(0,150),
            ariaLabel:c.getAttribute('aria-label'), type:c.getAttribute('type'),
            value:(c.tagName==='INPUT'||c.tagName==='SELECT'||c.tagName==='TEXTAREA')
              ? (c.type==='password'?'[redacted]':String(c.value||'').slice(0,100)) : null,
            disabled:!!c.disabled
          }))
      }));
      return {
        title:document.title, url:location.href,
        bodyText:clean(document.body?.innerText).slice(0,6500),
        controls, dialogs,
        passwordInputsVisible:Array.from(document.querySelectorAll('input[type=password]')).some(visible),
        captchaFrames:Array.from(document.querySelectorAll('iframe')).map(f=>f.src)
          .filter(s=>/captcha|verify/i.test(s)).slice(0,10)
      };
    }""")


def identify_funding_download(page) -> dict:
    return page.evaluate("""() => {
      const clean = s => (s || '').replace(/\\s+/g, ' ').trim();
      const visible = el => {
        const r = el.getBoundingClientRect(), s = getComputedStyle(el);
        return r.width > 0 && r.height > 0 && s.display !== 'none' &&
          s.visibility !== 'hidden' && Number(s.opacity || 1) > 0;
      };
      const labels = Array.from(document.querySelectorAll(
        'h1,h2,h3,h4,h5,[role=heading],div,span,p'
      )).filter(el => visible(el) && clean(el.innerText || el.textContent) === 'Funding rate');
      const found = new Map();
      for (const label of labels) {
        let ancestor = label;
        for (let depth=0; depth<10 && ancestor; depth++, ancestor=ancestor.parentElement) {
          const downloads = Array.from(ancestor.querySelectorAll('button')).filter(
            b => visible(b) && !b.disabled && clean(b.innerText || b.textContent) === 'Download'
          );
          if (downloads.length === 1) {
            const index = Array.from(document.querySelectorAll('button')).indexOf(downloads[0]);
            const text = clean(ancestor.innerText || ancestor.textContent);
            if (index >= 0 && text.includes('Funding rate')) {
              found.set(index, {
                button_index:index, button_text:clean(downloads[0].innerText || downloads[0].textContent),
                button_aria:downloads[0].getAttribute('aria-label'),
                button_title:downloads[0].getAttribute('title'),
                card_text:text.slice(0,1200),
                card_tag:ancestor.tagName.toLowerCase(),
                card_class:String(ancestor.className || '').slice(0,300),
                ancestor_depth:depth
              });
              break;
            }
          }
        }
      }
      return {candidates:Array.from(found.values()), visible_exact_download_buttons:
        Array.from(document.querySelectorAll('button')).filter(
          b => visible(b) && clean(b.innerText || b.textContent) === 'Download'
        ).length};
    }""")


def collect_visible_option_texts(modal) -> dict:
    """Collect visible option-like text inside the selector modal without JS evaluation."""
    selector_counts = {}
    unique_texts = []
    selectors = ("[role=option]", "li", "[class*=option]", "[class*=Option]")
    for selector in selectors:
        locator = modal.locator(selector)
        count = locator.count()
        selector_counts[selector] = count
        for index in range(min(count, 100)):
            item = locator.nth(index)
            try:
                if not item.is_visible():
                    continue
                text = (item.inner_text(timeout=1000) or "").strip()
            except Exception:
                continue
            if text and text not in unique_texts:
                unique_texts.append(text[:200])
            if len(unique_texts) >= 100:
                break
    return {"selector_counts": selector_counts, "unique_option_texts": unique_texts}


def run_probe(output_dir: Path, inspect_field_info: bool = False, inspect_symbol_options: bool = False) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "probe": "okx_funding_download_button_click",
        "target_url": URL,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "access_mode": "anonymous_browser",
        "auth_used": False,
        "cookie_consent_clicked": False,
        "captcha_bypass_used": False,
        "network_workaround_used": False,
        "form_submitted": False,
        "file_saved": False,
        "field_info_mode": inspect_field_info,
        "symbol_options_mode": inspect_symbol_options,
        "status": "not_started",
    }
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(accept_downloads=True, viewport={"width":1440,"height":1000})
            page = context.new_page()
            downloads = []
            popups = []
            page.on("popup", lambda popup: popups.append(popup))

            def cancel_download(download):
                record = {"suggested_filename": download.suggested_filename, "cancel_called": False}
                try:
                    download.cancel()
                    record["cancel_called"] = True
                except Exception as exc:
                    record["cancel_error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
                downloads.append(record)

            page.on("download", cancel_download)
            response = page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            manifest["http_status"] = response.status if response else None
            try:
                page.wait_for_load_state("networkidle", timeout=12000)
            except PlaywrightTimeout:
                manifest["networkidle_timeout"] = True
            page.wait_for_timeout(1000)
            initial = snapshot(page)
            manifest["initial_snapshot"] = initial
            initial_screenshot = output_dir / "okx-funding-button-before.png"
            page.screenshot(path=str(initial_screenshot), full_page=False)
            manifest["initial_screenshot"] = initial_screenshot.name

            body = (initial.get("bodyText") or "").lower()
            restricted = any(term in body for term in (
                "restricted ip", "not available in your region", "not available in your country",
                "restricted in your location", "access restricted in your region"
            ))
            if restricted:
                manifest["status"] = "blocked_by_access_restriction"
            elif initial.get("passwordInputsVisible") or initial.get("captchaFrames"):
                manifest["status"] = "blocked_by_login_or_captcha"
            else:
                target = identify_funding_download(page)
                manifest["target_identification"] = target
                candidates = target.get("candidates", [])
                if len(candidates) != 1:
                    manifest["status"] = "target_not_unique_or_not_found"
                else:
                    index = candidates[0]["button_index"]
                    button = page.locator("button").nth(index)
                    button.scroll_into_view_if_needed(timeout=5000)
                    state = page.evaluate("""idx => {
                      const b=document.querySelectorAll('button')[idx];
                      if(!b) return {found:false};
                      const r=b.getBoundingClientRect(), x=r.left+r.width/2, y=r.top+r.height/2;
                      const top=document.elementFromPoint(x,y);
                      const clean=s=>(s||'').replace(/\\s+/g,' ').trim();
                      return {found:true, visible:r.width>0&&r.height>0,
                        disabled:!!b.disabled, center:{x,y},
                        unobstructed:!!top && (top===b || b.contains(top)),
                        blocker:top?{tag:top.tagName.toLowerCase(),text:clean(top.innerText||top.textContent).slice(0,160),
                          aria:top.getAttribute('aria-label'),class:String(top.className||'').slice(0,160)}:null
                      };
                    }""", index)
                    manifest["target_actionability"] = state
                    if not state.get("found") or not state.get("visible") or state.get("disabled"):
                        manifest["status"] = "target_not_actionable"
                    elif not state.get("unobstructed"):
                        manifest["status"] = "target_obstructed_no_click"
                    else:
                        try:
                            button.click(timeout=5000)
                            manifest["button_clicked"] = True
                            page.wait_for_timeout(2500)
                            manifest["after_click_snapshot"] = snapshot(page)
                            if popups:
                                try:
                                    popups[0].wait_for_load_state("domcontentloaded", timeout=5000)
                                except PlaywrightTimeout:
                                    manifest["popup_load_timeout"] = True
                                manifest["popup_snapshot"] = snapshot(popups[0])
                            after_screenshot = output_dir / "okx-funding-button-after.png"
                            page.screenshot(path=str(after_screenshot), full_page=False)
                            manifest["after_click_screenshot"] = after_screenshot.name
                            dialogs = manifest["after_click_snapshot"].get("dialogs", [])
                            initial_dialogs = initial.get("dialogs", [])
                            new_dialogs = [d for d in dialogs if d not in initial_dialogs]
                            manifest["new_modal_like_surfaces"] = new_dialogs
                            if downloads:
                                manifest["status"] = "direct_download_detected_and_cancel_attempted"
                            elif new_dialogs:
                                manifest["status"] = "modal_opened_inspected_no_submission"
                                if inspect_field_info:
                                    field_info = page.get_by_role("button", name="Field information", exact=True)
                                    manifest["field_info_control_count"] = field_info.count()
                                    if field_info.count() != 1 or not field_info.first.is_visible():
                                        manifest["field_info_status"] = "control_not_found_or_not_visible"
                                        manifest["status"] = "field_info_control_not_found"
                                    else:
                                        field_info.first.scroll_into_view_if_needed(timeout=5000)
                                        field_info_action = field_info.first.evaluate("""el => {
                                          const r=el.getBoundingClientRect(), x=r.left+r.width/2, y=r.top+r.height/2;
                                          const top=document.elementFromPoint(x,y);
                                          const clean=s=>(s||'').replace(/\\s+/g,' ').trim();
                                          return {visible:r.width>0&&r.height>0,disabled:!!el.disabled,
                                            unobstructed:!!top&&(top===el||el.contains(top)),
                                            blocker:top?{tag:top.tagName.toLowerCase(),text:clean(top.innerText||top.textContent).slice(0,160),
                                              aria:top.getAttribute('aria-label'),class:String(top.className||'').slice(0,160)}:null};
                                        }""")
                                        manifest["field_info_actionability"] = field_info_action
                                        if not field_info_action.get("visible") or field_info_action.get("disabled"):
                                            manifest["field_info_status"] = "control_not_actionable"
                                            manifest["status"] = "field_info_control_not_actionable"
                                        elif not field_info_action.get("unobstructed"):
                                            manifest["field_info_status"] = "control_obstructed_no_click"
                                            manifest["status"] = "field_info_control_obstructed_no_click"
                                        else:
                                            try:
                                                field_info.first.click(timeout=5000)
                                                manifest["field_info_clicked"] = True
                                                page.wait_for_timeout(1500)
                                                field_info_snapshot = snapshot(page)
                                                manifest["field_info_snapshot"] = field_info_snapshot
                                                modal_surfaces_before = manifest["after_click_snapshot"].get("dialogs", [])
                                                manifest["field_info_new_surfaces"] = [
                                                    surface for surface in field_info_snapshot.get("dialogs", [])
                                                    if surface not in modal_surfaces_before
                                                ]
                                                field_info_screenshot = output_dir / "okx-funding-field-info.png"
                                                page.screenshot(path=str(field_info_screenshot), full_page=False)
                                                manifest["field_info_screenshot"] = field_info_screenshot.name
                                                manifest["field_info_status"] = "clicked_and_inspected"
                                                if downloads:
                                                    manifest["status"] = "unexpected_download_cancelled_after_field_info_click"
                                                else:
                                                    manifest["status"] = "field_information_clicked_inspected_no_submission"
                                            except Exception as exc:
                                                manifest["field_info_clicked"] = False
                                                manifest["field_info_error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
                                                manifest["status"] = "field_info_click_failed"
                                elif inspect_symbol_options:
                                    symbol_select = page.get_by_text("Select", exact=True)
                                    manifest["symbol_select_count"] = symbol_select.count()
                                    if symbol_select.count() != 1 or not symbol_select.first.is_visible():
                                        manifest["symbol_options_status"] = "control_not_found_or_not_visible"
                                        manifest["status"] = "symbol_select_control_not_found"
                                    elif not symbol_select.first.is_enabled():
                                        manifest["symbol_options_status"] = "control_not_enabled"
                                        manifest["status"] = "symbol_select_control_not_enabled"
                                    else:
                                        try:
                                            symbol_select.first.click(timeout=5000)
                                            manifest["symbol_select_clicked"] = True
                                            page.wait_for_timeout(1000)
                                            symbol_options_snapshot = snapshot(page)
                                            manifest["symbol_options_snapshot"] = symbol_options_snapshot
                                            body_text = symbol_options_snapshot.get("bodyText", "")
                                            manifest["symbol_dropdown_open"] = (
                                                "Select All" in body_text and
                                                any(c.get("role") == "combobox" for c in symbol_options_snapshot.get("controls", []))
                                            )
                                            modal = page.get_by_role("dialog")
                                            manifest["symbol_modal_count"] = modal.count()
                                            if modal.count() == 1:
                                                manifest["symbol_options"] = collect_visible_option_texts(modal)
                                            else:
                                                manifest["symbol_options"] = {"error": "symbol modal not unique"}
                                            symbol_screenshot = output_dir / "okx-funding-symbol-options.png"
                                            page.screenshot(path=str(symbol_screenshot), full_page=False)
                                            manifest["symbol_options_screenshot"] = symbol_screenshot.name
                                            search_input = modal.locator('input[type="search"]')
                                            manifest["symbol_search_input_count"] = search_input.count()
                                            manifest["symbol_search_results"] = {}
                                            if search_input.count() == 1 and search_input.first.is_visible() and search_input.first.is_enabled():
                                                manifest["symbol_search_terms"] = ["ETH", "BTC"]
                                                for term in ("ETH", "BTC"):
                                                    search_input.first.fill(term, timeout=5000)
                                                    page.wait_for_timeout(1000)
                                                    manifest["symbol_search_results"][term] = {
                                                        "modal_text": (modal.first.inner_text(timeout=2000) or "")[-2500:],
                                                        "options": collect_visible_option_texts(modal),
                                                    }
                                                    search_screenshot = output_dir / f"okx-funding-symbol-options-{term}.png"
                                                    page.screenshot(path=str(search_screenshot), full_page=False)
                                                search_input.first.fill("", timeout=5000)
                                                page.wait_for_timeout(300)
                                                manifest["symbol_search_status"] = "searched_eth_btc_no_selection"
                                            else:
                                                manifest["symbol_search_status"] = "search_input_not_unique_or_not_actionable"
                                            if downloads:
                                                manifest["status"] = "unexpected_download_cancelled_after_symbol_dropdown"
                                            elif manifest["symbol_dropdown_open"]:
                                                manifest["symbol_options_status"] = "clicked_and_inspected_no_selection"
                                                manifest["status"] = "symbol_options_opened_inspected_no_selection"
                                            else:
                                                manifest["symbol_options_status"] = "selector_clicked_but_dropdown_not_confirmed"
                                                manifest["status"] = "symbol_dropdown_not_confirmed"
                                        except Exception as exc:
                                            manifest["symbol_select_clicked"] = False
                                            manifest["symbol_options_error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
                                            manifest["status"] = "symbol_options_click_failed"
                            elif popups:
                                manifest["status"] = "popup_opened_inspected_no_submission"
                            else:
                                manifest["status"] = "clicked_no_download_modal_or_popup"
                        except Exception as exc:
                            manifest["button_clicked"] = False
                            manifest["click_error"] = f"{type(exc).__name__}: {str(exc)[:400]}"
                            manifest["status"] = "click_failed"
            manifest["download_events"] = downloads
            browser.close()
    except Exception as exc:
        manifest["status"] = "probe_error"
        manifest["error"] = f"{type(exc).__name__}: {str(exc)[:500]}"
    manifest["finished_utc"] = datetime.now(timezone.utc).isoformat()
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--inspect-field-info", action="store_true",
                      help="Click only the Field information control after the modal opens.")
    parser.add_argument("--inspect-symbol-options", action="store_true",
                      help="Open the Symbol selector and inspect options without selecting.")
    args = parser.parse_args()
    result = run_probe(args.output_dir, inspect_field_info=args.inspect_field_info,
                      inspect_symbol_options=args.inspect_symbol_options)
    print(json.dumps({
        "status": result.get("status"),
        "http_status": result.get("http_status"),
        "target_identification": result.get("target_identification"),
        "target_actionability": result.get("target_actionability"),
        "button_clicked": result.get("button_clicked"),
        "field_info_status": result.get("field_info_status"),
        "field_info_snapshot": result.get("field_info_snapshot"),
        "symbol_options_status": result.get("symbol_options_status"),
        "symbol_options": result.get("symbol_options"),
        "download_events": result.get("download_events"),
        "click_error": result.get("click_error"),
        "error": result.get("error"),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
