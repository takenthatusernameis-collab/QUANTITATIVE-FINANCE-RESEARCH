from pathlib import Path
import unittest

from okx_funding_button_probe import collect_visible_option_texts


class FakeItem:
    def __init__(self, text, visible=True):
        self.text = text
        self.visible = visible

    def is_visible(self):
        return self.visible

    def inner_text(self, timeout=1000):
        return self.text


class FakeLocator:
    def __init__(self, items):
        self.items = items

    def count(self):
        return len(self.items)

    def nth(self, index):
        return self.items[index]


class FakeModal:
    def __init__(self, selectors):
        self.selectors = selectors

    def locator(self, selector):
        return FakeLocator(self.selectors.get(selector, []))


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "research" / "okx_funding_button_probe.py"


class OKXFundingButtonProbeTests(unittest.TestCase):
    def test_option_text_collection_filters_hidden_and_deduplicates(self):
        modal = FakeModal({
            "[role=option]": [FakeItem("ETHUSDT")],
            "li": [FakeItem("hidden", visible=False), FakeItem("BTCUSDT"), FakeItem("ETHUSDT")],
            "[class*=option]": [FakeItem("ETHUSDT"), FakeItem("Select All")],
            "[class*=Option]": [FakeItem("All")],
        })
        result = collect_visible_option_texts(modal)
        self.assertEqual(result["unique_option_texts"], ["ETHUSDT", "BTCUSDT", "Select All", "All"])
        self.assertEqual(result["selector_counts"]["li"], 3)

    def test_symbol_options_searches_eth_btc_without_selecting(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('for term in ("ETH", "BTC")', source)
        self.assertIn("search_input.first.fill(term, timeout=5000)", source)
        self.assertIn("search_input.first.fill(\"\", timeout=5000)", source)
        self.assertIn("symbol_search_results", source)
        self.assertIn('input[type="search"]', source)
        self.assertNotIn("select_option", source)

    def test_probe_script_compiles(self):
        source = SCRIPT.read_text(encoding="utf-8")
        compile(source, str(SCRIPT), "exec")

    def test_target_is_exact_funding_card_download_button(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("Funding rate", source)
        self.assertIn("clean(b.innerText || b.textContent) === 'Download'", source)
        self.assertIn("target_not_unique_or_not_found", source)
        self.assertIn("button.click(timeout=5000)", source)
        self.assertNotIn("force=True", source)

    def test_direct_download_is_cancelled_and_never_saved(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('page.on("download", cancel_download)', source)
        self.assertIn("download.cancel()", source)
        self.assertIn('"file_saved": False', source)
        self.assertNotIn("download.save_as", source)
        self.assertNotIn("download.path(", source)

    def test_field_information_mode_is_bounded_and_read_only(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("--inspect-field-info", source)
        self.assertIn('get_by_role("button", name="Field information", exact=True)', source)
        self.assertIn("field_info.first.click(timeout=5000)", source)
        self.assertIn("field_information_clicked_inspected_no_submission", source)
        self.assertNotIn('get_by_role("button", name="Confirm"', source)

    def test_symbol_options_mode_opens_dropdown_without_selecting(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("--inspect-symbol-options", source)
        self.assertIn('get_by_text("Select", exact=True)', source)
        self.assertIn("symbol_select.first.click(timeout=5000)", source)
        self.assertIn("collect_visible_option_texts(modal)", source)
        self.assertIn("symbol_options_opened_inspected_no_selection", source)
        self.assertNotIn('[class*="option" i]', source)
        self.assertNotIn("symbol_options = page.evaluate", source)
        self.assertNotIn("select_option", source)

    def test_probe_never_accepts_cookies_or_submits_forms(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"cookie_consent_clicked": False', source)
        self.assertIn('"form_submitted": False', source)
        self.assertNotIn("Accept All Cookies", source)
        self.assertNotIn("Cookies Settings", source)


if __name__ == "__main__":
    unittest.main()
