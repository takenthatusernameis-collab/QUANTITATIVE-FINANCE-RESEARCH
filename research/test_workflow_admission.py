from pathlib import Path
import re
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / ".github" / "workflows"
README = ROOT / "README.md"
ADMISSION_IF = (
    "if: github.event_name != 'push' || "
    "startsWith(github.event.head_commit.message, '[QFR-ADMIT] research:')"
)
NON_RESEARCH_WORKFLOWS = {"workflow-admission-tests.yml", "stablecoin-supply-source-preflight.yml", "wikipedia-attention-source-preflight.yml", "taker-absorption-source-preflight.yml"}


class ResearchWorkflowAdmissionTests(unittest.TestCase):
    def test_admission_gate_requires_exact_research_prefix(self):
        self.assertIn("startsWith(", ADMISSION_IF)
        self.assertIn("[QFR-ADMIT] research:", ADMISSION_IF)
        self.assertNotIn("contains(", ADMISSION_IF)

    def test_readme_documents_atomic_admission_marker(self):
        text = README.read_text(encoding="utf-8")
        self.assertIn("[QFR-ADMIT] research:", text)
        self.assertIn("Enforced research-run admission", text)

    def test_every_research_workflow_has_a_job_level_admission_gate(self):
        workflows = sorted(
            path
            for path in WORKFLOW_DIR.glob("*.yml")
            if path.name not in NON_RESEARCH_WORKFLOWS
        )
        self.assertGreaterEqual(len(workflows), 1)

        for path in workflows:
            with self.subTest(workflow=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertIn("workflow_dispatch:", text)

                lines = text.splitlines()
                jobs_index = lines.index("jobs:")
                job_starts = [
                    index
                    for index in range(jobs_index + 1, len(lines))
                    if re.match(r"^  [A-Za-z0-9_-]+:$", lines[index])
                ]
                self.assertGreaterEqual(len(job_starts), 1)

                for position, start in enumerate(job_starts):
                    end = (
                        job_starts[position + 1]
                        if position + 1 < len(job_starts)
                        else len(lines)
                    )
                    block = lines[start + 1:end]
                    conditions = [
                        line.strip()
                        for line in block
                        if re.match(r"^    if:", line)
                    ]
                    self.assertEqual(
                        conditions,
                        [ADMISSION_IF],
                        msg=f"{path.name}: each job must have exactly one exact admission gate",
                    )

    def test_every_workflow_checks_out_the_immutable_trigger_commit(self):
        for path in sorted(WORKFLOW_DIR.glob("*.yml")):
            with self.subTest(workflow=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertIn("ref: ${{ github.sha }}", text)
                self.assertNotIn("ref: main", text)

    def test_research_workflows_never_cancel_in_progress_runs(self):
        workflows = sorted(
            path
            for path in WORKFLOW_DIR.glob("*.yml")
            if path.name not in NON_RESEARCH_WORKFLOWS
        )
        for path in workflows:
            with self.subTest(workflow=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertRegex(text, r"(?m)^  cancel-in-progress: false$")


    def test_wikipedia_source_preflight_has_narrow_source_only_path_filters(self):
        text = (WORKFLOW_DIR / "wikipedia-attention-source-preflight.yml").read_text(encoding="utf-8")
        self.assertIn('"research/wikipedia_attention_source_preflight.py"', text)
        self.assertIn('"research/test_wikipedia_attention_source_preflight.py"', text)
        self.assertIn('".github/workflows/wikipedia-attention-source-preflight.yml"', text)
        self.assertNotIn('"research/test_workflow_admission.py"', text)
        self.assertNotIn('"research/PREREGISTERED-QFR-2026-11-26-WIKIPEDIA-ATTENTION-BTC-DOWNSIDE-01.md"', text)

    def test_wikipedia_attention_backtest_workflow_validates_before_source_retrieval(self):
        path = WORKFLOW_DIR / "wikipedia-attention-btc-downside.yml"
        text = path.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertIn(ADMISSION_IF, text)
        self.assertIn("ref: ${{ github.sha }}", text)
        self.assertIn("cancel-in-progress: false", text)
        self.assertIn('python -m unittest discover -s research -p "test_wikipedia_attention_btc_downside.py" -v', text)
        self.assertIn('python -m unittest discover -s research -p "test_workflow_admission.py" -v', text)
        self.assertLess(
            text.index("Run deterministic pageview, timing, event, walk-forward and decision tests"),
            text.index("Retrieve frozen Wikimedia and checksummed Binance sources"),
        )
        self.assertIn("contents: write", text)

    def test_wikipedia_attention_workflow_run_blocks_have_valid_bash_syntax(self):
        if not shutil.which("bash"):
            self.skipTest("bash is unavailable")
        text = (WORKFLOW_DIR / "wikipedia-attention-btc-downside.yml").read_text(encoding="utf-8")
        lines = text.splitlines()
        scripts = []
        for index, line in enumerate(lines):
            if line == "        run: |":
                body = []
                for candidate in lines[index + 1:]:
                    if candidate.strip() and not candidate.startswith("          "):
                        break
                    body.append(candidate[10:] if candidate.startswith("          ") else "")
                scripts.append("\n".join(body) + "\n")
        self.assertGreaterEqual(len(scripts), 2)
        for script_index, script in enumerate(scripts):
            with self.subTest(script=script_index):
                result = subprocess.run(
                    ["bash", "-n"], input=script, text=True, capture_output=True, check=False
                )
                self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_wikipedia_attention_persistence_git_add_command_has_balanced_quotes(self):
        text = (WORKFLOW_DIR / "wikipedia-attention-btc-downside.yml").read_text(encoding="utf-8")
        expected = 'git add "$report" "$manifest" research/HYPOTHESIS-REGISTRY.md research/PREREGISTERED-QFR-2026-11-26-WIKIPEDIA-ATTENTION-BTC-DOWNSIDE-01.md'
        self.assertIn(expected, text)
        self.assertNotIn(expected + '"', text)

    def test_readme_requires_difficulty_adjusted_model_timeboxes(self):
        text = README.read_text(encoding="utf-8")
        required = [
            "Mandatory difficulty-adjusted model timeboxes",
            "before work begins",
            "| LOW | 2 substantive cycles | 2 calendar days |",
            "| MEDIUM | 4 substantive cycles | 5 calendar days |",
            "| HIGH | 8 substantive cycles | 10 calendar days |",
            "hard implementation deadline",
            "hard final research-conclusion deadline",
            "INCONCLUSIVE/INFEASIBLE",
            "Do not silently reset the clock",
        ]
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_readme_documents_same_session_replacement_invariant(self):
        text = README.read_text(encoding="utf-8")
        self.assertIn("Same-session replacement invariant", text)
        self.assertIn("same session", text.lower())

    def test_stablecoin_source_preflight_is_read_only_and_not_a_backtest(self):
        path = WORKFLOW_DIR / "stablecoin-supply-source-preflight.yml"
        text = path.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("contents: read", text)
        self.assertNotIn("contents: write", text)
        self.assertIn("stablecoin_supply_source_preflight.py", text)
        self.assertNotIn("stablecoin_supply_btc_downside.py", text)
        self.assertIn("do not run a backtest", text.lower())

    def test_taker_absorption_persistence_merges_into_latest_main(self):
        text = (WORKFLOW_DIR / "taker-absorption-btc-downside.yml").read_text(encoding="utf-8")
        self.assertIn("research/persist_taker_absorption_evidence.py", text)
        self.assertNotIn('cp research/HYPOTHESIS-REGISTRY.md "$tmp/HYPOTHESIS-REGISTRY.md"', text)
        self.assertNotIn('cp research/PREREGISTERED-QFR-2026-11-27-TAKER-ABSORPTION-BTC-DOWNSIDE-01.md "$tmp/prereg.md"', text)
        reset = text.index("git reset --hard origin/main")
        merge = text.index("research/persist_taker_absorption_evidence.py")
        stage = text.index('git add "$report" "$manifest" research/HYPOTHESIS-REGISTRY.md')
        self.assertLess(reset, merge)
        self.assertLess(merge, stage)

    def test_taker_absorption_backtest_workflow_validates_before_source_retrieval(self):
        path = WORKFLOW_DIR / "taker-absorption-btc-downside.yml"
        text = path.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertIn(ADMISSION_IF, text)
        self.assertIn("ref: ${{ github.sha }}", text)
        self.assertIn("cancel-in-progress: false", text)
        self.assertIn("contents: write", text)
        self.assertIn('test_taker_absorption_source_preflight.py', text)
        self.assertIn('test_taker_absorption_btc_downside.py', text)
        self.assertLess(
            text.index("Run deterministic archive, event, model, inference and handoff tests"),
            text.index("Retrieve frozen checksummed Binance sources and run the real-data forecast"),
        )
        self.assertIn("if: always()", text)
        self.assertIn("git fetch origin main", text)
        self.assertIn("git reset --hard origin/main", text)
        self.assertIn("git push origin HEAD:main", text)

    def test_taker_absorption_workflow_run_blocks_have_valid_bash_syntax(self):
        if not shutil.which("bash"):
            self.skipTest("bash is unavailable")
        text = (WORKFLOW_DIR / "taker-absorption-btc-downside.yml").read_text(encoding="utf-8")
        lines = text.splitlines()
        scripts = []
        for index, line in enumerate(lines):
            if line == "        run: |":
                body = []
                for candidate in lines[index + 1:]:
                    if candidate.strip() and not candidate.startswith("          "):
                        break
                    body.append(candidate[10:] if candidate.startswith("          ") else "")
                scripts.append("\n".join(body) + "\n")
        self.assertGreaterEqual(len(scripts), 3)
        for script_index, script in enumerate(scripts):
            with self.subTest(script=script_index):
                result = subprocess.run(
                    ["bash", "-n"], input=script, text=True, capture_output=True, check=False
                )
                self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_taker_absorption_source_preflight_has_narrow_path_filters(self):
        text = (WORKFLOW_DIR / "taker-absorption-source-preflight.yml").read_text(encoding="utf-8")
        self.assertIn('"research/taker_absorption_source_preflight.py"', text)
        self.assertIn('"research/test_taker_absorption_source_preflight.py"', text)
        self.assertIn('".github/workflows/taker-absorption-source-preflight.yml"', text)
        self.assertNotIn('"research/test_workflow_admission.py"', text)
        self.assertNotIn('".github/workflows/workflow-admission-tests.yml"', text)

    def test_taker_absorption_source_preflight_is_read_only_and_not_a_backtest(self):
        path = WORKFLOW_DIR / "taker-absorption-source-preflight.yml"
        text = path.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("contents: read", text)
        self.assertNotIn("contents: write", text)
        self.assertIn("taker_absorption_source_preflight.py", text)
        self.assertNotIn("taker_absorption_btc_downside.py", text)
        self.assertIn("do not run a backtest", text.lower())

    def test_wikipedia_attention_source_preflight_is_read_only_and_not_a_backtest(self):
        path = WORKFLOW_DIR / "wikipedia-attention-source-preflight.yml"
        text = path.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("contents: read", text)
        self.assertNotIn("contents: write", text)
        self.assertIn("wikipedia_attention_source_preflight.py", text)
        self.assertNotIn("wikipedia_attention_btc_downside.py", text)
        self.assertIn("do not run a backtest", text.lower())

    def test_non_research_source_preflight_workflows_are_excluded_from_research_gate(self):
        self.assertIn("stablecoin-supply-source-preflight.yml", NON_RESEARCH_WORKFLOWS)
        self.assertIn("wikipedia-attention-source-preflight.yml", NON_RESEARCH_WORKFLOWS)
        self.assertIn("taker-absorption-source-preflight.yml", NON_RESEARCH_WORKFLOWS)

    def test_non_research_admission_test_workflow_is_excluded_from_research_gate(self):
        path = WORKFLOW_DIR / "workflow-admission-tests.yml"
        text = path.read_text(encoding="utf-8")
        self.assertIn("research/test_workflow_admission.py", text)
        self.assertIn("workflow_dispatch:", text)

    def test_admission_workflow_runs_fed_balance_sheet_regression_suite(self):
        text = (WORKFLOW_DIR / "workflow-admission-tests.yml").read_text(encoding="utf-8")
        self.assertIn("research/fed_balance_sheet_btc_downside_semivariance.py", text)
        self.assertIn("research/test_fed_balance_sheet_btc_downside_semivariance.py", text)

    def test_shared_admission_harness_change_does_not_retrigger_kcprs(self):
        workflow = (WORKFLOW_DIR / "kcprs-policy-skew-dgs2.yml").read_text(encoding="utf-8")
        self.assertNotIn(".github/workflows/workflow-admission-tests.yml", workflow)
        readme = README.read_text(encoding="utf-8")
        self.assertIn("Shared admission-harness changes must not appear in unrelated research workflow path filters", readme)

    def test_fed_evidence_persistence_imports_module_from_research_directory(self):
        workflow = (WORKFLOW_DIR / "fed-balance-sheet-btc-downside-semivariance.yml").read_text(encoding="utf-8")
        self.assertIn('sys.path.insert(0,"research")', workflow)

    def test_shared_admission_harness_change_does_not_retrigger_deribit_relative_dvol(self):
        workflow = (WORKFLOW_DIR / "deribit-relative-dvol-ethbtc-rv.yml").read_text(encoding="utf-8")
        self.assertNotIn(".github/workflows/workflow-admission-tests.yml", workflow)

    def test_shared_admission_harness_change_does_not_retrigger_mexc_funding(self):
        workflow = (WORKFLOW_DIR / "mexc-btc-funding-downside.yml").read_text(encoding="utf-8")
        self.assertNotIn(".github/workflows/workflow-admission-tests.yml", workflow)

    def test_readme_requires_unmarked_repairs_and_dispatch_for_same_hypothesis_retries(self):
        text = README.read_text(encoding="utf-8")
        required = [
            "Failed-admission recovery",
            "never use the `[QFR-ADMIT] research:` prefix on a repair",
            "ordinary unmarked commits",
            "workflow_dispatch",
            "genuinely new, complete atomic hypothesis admission",
            "record the dispatched run's exact `source_commit_sha`",
        ]
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
