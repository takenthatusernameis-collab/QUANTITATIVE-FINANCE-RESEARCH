from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "research" / "okx_funding_button_probe.py"


class OKXFundingButtonProbeTests(unittest.TestCase):
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

    def test_probe_never_accepts_cookies_or_submits_forms(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"cookie_consent_clicked": False', source)
        self.assertIn('"form_submitted": False', source)
        self.assertNotIn("Accept All Cookies", source)
        self.assertNotIn("Cookies Settings", source)


if __name__ == "__main__":
    unittest.main()
