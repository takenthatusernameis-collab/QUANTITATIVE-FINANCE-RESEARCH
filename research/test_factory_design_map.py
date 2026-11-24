from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "docs" / "QUANTITATIVE-RESEARCH-FACTORY-DESIGN-MAP.md"
README = ROOT / "README.md"
DOC_INDEX = ROOT / "docs" / "README.md"
COMPAT_PROMPT = ROOT / "archive" / "ORIGINAL-AGENT-LOOP-PROMPT.md"
LEGACY_PROMPT = ROOT / "archive" / "WAKE-UP-PROMPT-LEGACY-2026-11-24.md"

LEGACY_TEXT = (
    "COMMIT TO REPOSITORY THE PENDING TASK\n\n"
    "# Original agent-loop prompt\n\n"
    "Commit a pending task in this repository for the next agent to execute, and execute the pending task commited by the last agent!\n\n"
    "**No verified repository commit means no completed commit assignment.**\n"
)


class FactoryDesignMapTests(unittest.TestCase):
    def test_readme_points_to_canonical_factory_map(self):
        readme = README.read_text(encoding="utf-8")
        self.assertIn("docs/QUANTITATIVE-RESEARCH-FACTORY-DESIGN-MAP.md", readme)
        self.assertNotIn("read the full [original agent-loop prompt]", readme.lower())

    def test_documentation_index_points_to_factory_map(self):
        index = DOC_INDEX.read_text(encoding="utf-8")
        self.assertIn("QUANTITATIVE-RESEARCH-FACTORY-DESIGN-MAP.md", index)
        self.assertIn("not a replacement for the detailed policies", index)

    def test_old_wakeup_prompt_is_preserved_verbatim(self):
        self.assertEqual(LEGACY_PROMPT.read_text(encoding="utf-8"), LEGACY_TEXT)

    def test_legacy_prompt_path_is_only_a_compatibility_redirect(self):
        content = COMPAT_PROMPT.read_text(encoding="utf-8")
        self.assertIn("no longer an active wake-up instruction", content)
        self.assertIn("QUANTITATIVE-RESEARCH-FACTORY-DESIGN-MAP.md", content)
        self.assertNotIn("Commit a pending task in this repository", content)

    def test_map_contains_the_production_stages_and_stage_gates(self):
        content = MAP.read_text(encoding="utf-8")
        for phrase in (
            "Opportunity and incident intake",
            "Predecessor learning",
            "Environment and opportunity mapping",
            "Portfolio and flow control",
            "Research design",
            "Data acquisition and curation",
            "Model implementation",
            "Independent empirical validation",
            "Research decision",
            "Retrospective and factory improvement",
            "Data contract accepted?",
        ):
            self.assertIn(phrase, content)

    def test_role_hats_do_not_require_a_fixed_agent_swarm(self):
        content = MAP.read_text(encoding="utf-8")
        self.assertIn("accountability hat", content)
        self.assertIn("not a mandatory separate agent", content)
        self.assertIn("must not be its only validator", content)

    def test_factory_map_prohibits_github_cron_as_primary_clock(self):
        content = MAP.read_text(encoding="utf-8").lower()
        self.assertIn("never use github actions `schedule`/cron as the primary clock", content)
        self.assertIn("independent external scheduler", content)
        self.assertIn("durable dispatch ledger", content)
        self.assertIn("separate independent watchdog", content)
        self.assertIn("never tell a user or the next agent to wait for another github cron tick", content)
        self.assertIn("first authorized agent wake-up after it passes", content)
        self.assertIn("directly perform the smallest safe", content)

    def test_research_and_operational_outcomes_remain_separate(self):
        content = MAP.read_text(encoding="utf-8")
        for phrase in ("Engineering", "Data", "Empirical research", "Operations", "INCONCLUSIVE", "DELIVERY_VERIFIED"):
            self.assertIn(phrase, content)

    def test_map_preserves_stop_line_and_reproducibility_controls(self):
        content = MAP.read_text(encoding="utf-8").lower()
        for phrase in ("stop the line", "never forward-fill", "untouched holdout", "trial history", "source-backed, versioned and auditable"):
            self.assertIn(phrase, content)

    def test_map_has_a_compounding_loop_but_bounds_process_changes(self):
        content = MAP.read_text(encoding="utf-8").lower()
        self.assertIn("observe → identify the binding constraint", content)
        self.assertIn("cost ceiling", content)
        self.assertIn("expiry", content)
        self.assertIn("rollback/stop rule", content)


if __name__ == "__main__":
    unittest.main()
