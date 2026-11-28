from pathlib import Path
import datetime as dt
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
NON_RESEARCH_WORKFLOWS = {
    "workflow-admission-tests.yml",
    "stablecoin-supply-source-preflight.yml",
    "wikipedia-attention-source-preflight.yml",
    "taker-absorption-source-preflight.yml",
    "btc-cross-venue-funding-dispersion-source-preflight.yml",
    "btc-mining-difficulty-closure-tests.yml",
    "etf-relative-flow-source-preflight.yml",
    "btc-blockspace-fee-rate-source-preflight.yml",
    "initial-claims-source-preflight.yml",
    "mexc-funding-dispersion-source-preflight.yml",
    "ethereum-dex-turnover-eth-rv-source-preflight.yml",
    "eth-validator-queue-source-preflight.yml",
    "eth-validator-queue-pit-concordance.yml",
    "h8-ci-credit-impulse-source-preflight.yml",
    "chatgpt-control-pr-dispatch.yml",
    "dispatch-bridge-probe.yml",
}
NON_RESEARCH_NO_CHECKOUT_WORKFLOWS = {
    "chatgpt-control-pr-dispatch.yml",
    "dispatch-bridge-probe.yml",
}


TIMEBOX_POLICY_CUTOVER = dt.datetime.fromisoformat("2026-11-26T10:12:25+00:00")
TIMEBOX_BUDGETS = {
    "LOW": (2, 2),
    "MEDIUM": (4, 5),
    "HIGH": (8, 10),
}


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
        for path in sorted(
            path for path in WORKFLOW_DIR.glob("*.yml")
            if path.name not in NON_RESEARCH_NO_CHECKOUT_WORKFLOWS
        ):
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



    def test_mexc_funding_dispersion_model_workflow_has_exact_admission_gate(self):
        text = (WORKFLOW_DIR / "mexc-funding-dispersion-btc-rv.yml").read_text(encoding="utf-8")
        self.assertIn(ADMISSION_IF, text)
        self.assertIn("ref: ${{ github.sha }}", text)
        self.assertIn("forecast_rows.csv", text)
        self.assertIn("mexc_funding_dispersion_btc_rv.py", text)
        self.assertIn("cancel-in-progress: false", text)
        self.assertIn("pip install --disable-pip-version-check -r research/requirements.txt", text)

    def test_mexc_funding_dispersion_source_preflight_has_narrow_source_only_path_filters(self):
        text = (WORKFLOW_DIR / "mexc-funding-dispersion-source-preflight.yml").read_text(encoding="utf-8")
        self.assertIn('"research/mexc_funding_dispersion_source_preflight.py"', text)
        self.assertIn('"research/test_mexc_funding_dispersion_source_preflight.py"', text)
        self.assertIn('"research/PREREGISTERED-QFR-2026-11-27-MEXC-FUNDING-DISPERSION-BTC-RV-01.md"', text)
        self.assertNotIn('"research/mexc_funding_dispersion_btc_rv.py"', text)
        self.assertNotIn('"research/test_workflow_admission.py"', text)
        self.assertIn("no model fitting", text.lower())

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

    def test_eth_dex_preregistration_records_pre_result_sparse_gap_amendments(self):
        text = (
            ROOT / "research" /
            "PREREGISTERED-QFR-2026-11-28-ETHEREUM-DEX-TURNOVER-ETH-RV-01.md"
        ).read_text(encoding="utf-8")
        required = [
            "Initial pre-result data-integrity amendment",
            "Superseding pre-result sparse-gap amendment",
            "14 missing hourly ETHUSDT bars",
            "51,120 expected hours",
            "four consecutive missing hours",
            "Seven additional official daily archives",
            "No price, close or return is forward-filled, interpolated or synthesized",
            "The 300-forecast minimum in each split remains binding",
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
        merge = text.index("PYTHONPATH=research python research/persist_taker_absorption_evidence.py")
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

    def test_eth_validator_queue_pit_concordance_workflow_is_source_only(self):
        path = WORKFLOW_DIR / "eth-validator-queue-pit-concordance.yml"
        text = path.read_text(encoding="utf-8")
        self.assertIn("eth_validator_queue_pit_concordance.py", text)
        self.assertIn("test_eth_validator_queue_pit_concordance.py", text)
        self.assertIn("do not run a backtest", text.lower())
        self.assertIn("no raw observations persisted", text.lower())
        self.assertIn("contents: write", text)
        self.assertIn("ref: " + "${{ github.sha }}", text)
        self.assertIn("cancel-in-progress: false", text)
    def test_non_research_source_preflight_workflows_are_excluded_from_research_gate(self):
        self.assertIn("stablecoin-supply-source-preflight.yml", NON_RESEARCH_WORKFLOWS)
        self.assertIn("wikipedia-attention-source-preflight.yml", NON_RESEARCH_WORKFLOWS)
        self.assertIn("taker-absorption-source-preflight.yml", NON_RESEARCH_WORKFLOWS)
        self.assertIn("eth-validator-queue-pit-concordance.yml", NON_RESEARCH_WORKFLOWS)
        self.assertIn("h8-ci-credit-impulse-source-preflight.yml", NON_RESEARCH_WORKFLOWS)

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
            "authenticated ChatGPT control-PR comment bridge",
            "/qfr-run-initial-claims-btc-downside",
            "Direct manual `workflow_dispatch` is break-glass only.",
            "genuinely new, complete atomic hypothesis admission",
            "exact `source_commit_sha`",
        ]
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_canonical_decision_hierarchy_is_executable_and_guarded(self):
        text = README.read_text(encoding="utf-8")
        required = [
            "Canonical research decision and failover hierarchy",
            "Hard invariants",
            "Remove demonstrated compounding process bottlenecks",
            "Test independent providers in a frozen, research-specific order",
            "Change the data architecture after provider failure",
            "Replace the hypothesis when distinct alternatives are exhausted",
            "two distinct providers",
            "MEXC",
            "Coinbase USD-quoted legs",
            "Kraken OHLCVT",
            "Unaccepted final funding settlements block perpetual-futures claims",
        ]
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

        policy = ROOT / "research" / "decision_hierarchy.py"
        self.assertTrue(policy.is_file())
        workflow = (WORKFLOW_DIR / "workflow-admission-tests.yml").read_text(encoding="utf-8")
        self.assertIn("research/decision_hierarchy.py", workflow)
        self.assertIn('test_decision_hierarchy.py', workflow)


    def test_cross_venue_funding_source_preflight_has_narrow_path_filters(self):
        text = (WORKFLOW_DIR / "btc-cross-venue-funding-dispersion-source-preflight.yml").read_text(encoding="utf-8")
        self.assertIn('"research/btc_cross_venue_funding_dispersion_source_preflight.py"', text)
        self.assertIn('"research/test_btc_cross_venue_funding_dispersion_source_preflight.py"', text)
        self.assertIn('"research/PREREGISTERED-QFR-2026-11-27-BTC-CROSS-VENUE-FUNDING-DISPERSION-DOWNSIDE-01.md"', text)
        self.assertIn('".github/workflows/btc-cross-venue-funding-dispersion-source-preflight.yml"', text)
        self.assertNotIn('"research/test_workflow_admission.py"', text)
        self.assertNotIn('".github/workflows/workflow-admission-tests.yml"', text)

    def test_cross_venue_funding_source_preflight_is_read_only_and_not_a_backtest(self):
        path = WORKFLOW_DIR / "btc-cross-venue-funding-dispersion-source-preflight.yml"
        text = path.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("contents: read", text)
        self.assertNotIn("contents: write", text)
        self.assertIn("btc_cross_venue_funding_dispersion_source_preflight.py", text)
        self.assertNotIn("btc_cross_venue_funding_dispersion_downside.py", text)
        self.assertIn("do not run a backtest", text.lower())
        self.assertIn("cancel-in-progress: false", text)
        self.assertIn("ref: ${{ github.sha }}", text)

    def test_cross_venue_source_preflight_is_excluded_from_research_admission_gate(self):
        self.assertIn("btc-cross-venue-funding-dispersion-source-preflight.yml", NON_RESEARCH_WORKFLOWS)


    def test_mining_difficulty_closure_workflow_is_read_only_and_never_runs_research(self):
        path = WORKFLOW_DIR / "btc-mining-difficulty-closure-tests.yml"
        text = path.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("contents: read", text)
        self.assertNotIn("contents: write", text)
        self.assertIn("test_btc_mining_difficulty_btc_downside.py", text)
        self.assertIn("do not run empirical", text.lower())
        self.assertIn("ref: ${{ github.sha }}", text)
        self.assertIn("cancel-in-progress: false", text)
        self.assertIn("btc-mining-difficulty-closure-tests.yml", NON_RESEARCH_WORKFLOWS)

    def test_mining_difficulty_identity_is_closed_and_guarded(self):
        closure = (ROOT / "research" / "CLOSED-QFR-2026-11-27-BTC-DIFFICULTY-CUT-DOWNSIDE-01.md").read_text(encoding="utf-8")
        module = (ROOT / "research" / "btc_mining_difficulty_btc_downside.py").read_text(encoding="utf-8")
        self.assertIn("not a preregistration", closure.lower())
        self.assertIn("mandatory preregistration", closure.lower())
        self.assertIn("assert_empirical_execution_allowed()", module)


    def test_every_hypothesis_module_has_preregistration_or_explicit_closure(self):
        # The Treasury auction module is a shared legacy engine, not a standalone
        # hypothesis admission. All new hypotheses built on it still need their own prereg.
        shared_core_helpers = {"treasury_auction_demand.py"}
        research_dir = ROOT / "research"
        prereg_by_id = {}

        for prereg_path in sorted(research_dir.glob("PREREGISTERED-*.md")):
            prereg_text = prereg_path.read_text(encoding="utf-8")
            prereg_id = re.search(
                r"(?mi)^-\s*\*\*Hypothesis ID:\*\*\s*[\x60]?([A-Z0-9-]+)[\x60]?",
                prereg_text,
            )
            self.assertIsNotNone(prereg_id, msg=f"{prereg_path.name} has no embedded Hypothesis ID")
            hypothesis_id = prereg_id.group(1)
            self.assertNotIn(
                hypothesis_id,
                prereg_by_id,
                msg=f"duplicate preregistrations for {hypothesis_id}",
            )
            prereg_by_id[hypothesis_id] = prereg_path

        for path in sorted(research_dir.glob("*.py")):
            if path.name.startswith("test_") or path.name in shared_core_helpers:
                continue
            source = path.read_text(encoding="utf-8")
            match = re.search(
                r"(?m)^HYPOTHESIS_ID\s*=\s*['\"]([^'\"]+)['\"]",
                source,
            )
            if not match:
                continue

            hypothesis_id = match.group(1)
            prereg = prereg_by_id.get(hypothesis_id)
            closure = research_dir / f"CLOSED-{hypothesis_id}.md"
            with self.subTest(module=path.name, hypothesis_id=hypothesis_id):
                self.assertTrue(
                    prereg is not None or closure.is_file(),
                    msg=f"{path.name} has no preregistration whose embedded ID matches, or explicit closure",
                )
                if closure.is_file():
                    closure_text = closure.read_text(encoding="utf-8")
                    self.assertIn("CLOSED", closure_text.upper())
                    self.assertIn(
                        "assert_empirical_execution_allowed()",
                        source,
                        msg=f"{path.name} has a closure record but no fail-closed execution guard",
                    )

    def test_post_cutover_preregistrations_have_complete_bounded_timeboxes(self):
        research_dir = ROOT / "research"
        prereg_paths = sorted(research_dir.glob("PREREGISTERED-*.md"))

        for path in prereg_paths:
            content = path.read_text(encoding="utf-8")
            registration_match = re.search(
                r"(?mi)^-\s*\*\*(?:Registered|Preregistration freeze):\*\*\s*"
                r"[\x60]?(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)[\x60]?",
                content,
            )
            hypothesis_id_match = re.search(
                r"(?mi)^-\s*\*\*Hypothesis ID:\*\*\s*[\x60]?([A-Z0-9-]+)[\x60]?",
                content,
            )

            if registration_match is None:
                legacy_commit_match = re.search(
                    r"(?mi)^-\s*\*\*Mainline admission commit timestamp:\*\*\s*"
                    r"[\x60]?(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)[\x60]?",
                    content,
                )
                if legacy_commit_match:
                    legacy_commit_at = dt.datetime.fromisoformat(
                        legacy_commit_match.group(1).replace("Z", "+00:00")
                    )
                    self.assertLess(
                        legacy_commit_at,
                        TIMEBOX_POLICY_CUTOVER,
                        msg=f"{path.name} legacy commit timestamp is not pre-cutover",
                    )
                    continue
                if hypothesis_id_match:
                    hypothesis_date_match = re.search(
                        r"QFR-(\d{4}-\d{2}-\d{2})",
                        hypothesis_id_match.group(1),
                    )
                    if hypothesis_date_match:
                        hypothesis_date = dt.date.fromisoformat(hypothesis_date_match.group(1))
                        if hypothesis_date >= TIMEBOX_POLICY_CUTOVER.date():
                            self.fail(f"{path.name} has no exact UTC registration/freeze timestamp")
                continue

            registered_at = dt.datetime.fromisoformat(
                registration_match.group(1).replace("Z", "+00:00")
            )
            if registered_at < TIMEBOX_POLICY_CUTOVER:
                continue

            with self.subTest(preregistration=path.name):
                difficulty_match = re.search(
                    r"(?mi)^-\s*\*\*(?:Expected )?Difficulty:\*\*\s*[\x60]?(LOW|MEDIUM|HIGH)\b",
                    content,
                )
                rationale_match = re.search(
                    r"(?mi)^-\s*\*\*Difficulty rationale:\*\*\s*\S",
                    content,
                )
                start_match = re.search(
                    r"(?mi)^-\s*\*\*Timebox start:\*\*\s*[\x60]?"
                    r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)[\x60]?",
                    content,
                )
                cycles_match = re.search(
                    r"(?mi)^-\s*\*\*Maximum substantive cycles:\*\*\s*(\d+)\b",
                    content,
                )
                implementation_match = re.search(
                    r"(?mi)^-\s*\*\*(?:Hard )?Implementation deadline:\*\*\s*[\x60]?"
                    r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)[\x60]?",
                    content,
                )
                conclusion_match = re.search(
                    r"(?mi)^-\s*\*\*(?:Hard )?Final research-conclusion deadline:\*\*\s*[\x60]?"
                    r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)[\x60]?",
                    content,
                )
                expiry_match = re.search(
                    r"(?mi)^-\s*\*\*Expiry rule:\*\*\s*\S",
                    content,
                )

                self.assertIsNotNone(difficulty_match, "missing LOW/MEDIUM/HIGH difficulty")
                self.assertIsNotNone(rationale_match, "missing difficulty rationale")
                self.assertIsNotNone(start_match, "missing exact UTC timebox start")
                self.assertIsNotNone(cycles_match, "missing maximum substantive cycles")
                self.assertIsNotNone(implementation_match, "missing implementation deadline")
                self.assertIsNotNone(conclusion_match, "missing final research-conclusion deadline")
                self.assertIsNotNone(expiry_match, "missing explicit expiry outcome rule")

                difficulty = difficulty_match.group(1)
                maximum_cycles, maximum_days = TIMEBOX_BUDGETS[difficulty]
                cycles = int(cycles_match.group(1))
                start = dt.datetime.fromisoformat(start_match.group(1).replace("Z", "+00:00"))
                implementation = dt.datetime.fromisoformat(
                    implementation_match.group(1).replace("Z", "+00:00")
                )
                conclusion = dt.datetime.fromisoformat(
                    conclusion_match.group(1).replace("Z", "+00:00")
                )

                self.assertGreaterEqual(start, registered_at, "timebox starts before preregistration")
                self.assertGreater(cycles, 0)
                self.assertLessEqual(cycles, maximum_cycles, "cycle cap exceeds difficulty tier")
                self.assertGreater(implementation, start, "implementation deadline must follow start")
                self.assertGreater(conclusion, implementation, "final deadline must follow implementation deadline")
                self.assertLessEqual(
                    conclusion - start,
                    dt.timedelta(days=maximum_days),
                    "final deadline exceeds the difficulty-tier calendar budget",
                )

    def test_readme_documents_mainline_timebox_cutover_and_machine_enforcement(self):
        text = README.read_text(encoding="utf-8")
        self.assertIn("2026-11-26T10:12:25Z", text)
        self.assertIn("exactly one preregistration whose embedded `Hypothesis ID` matches", text)
        self.assertIn("matching by embedded ID, not by filename slug", text)
        self.assertIn("explicit `CLOSED-{HYPOTHESIS_ID}.md`", text)
        self.assertIn("post-cutover preregistration", text.lower())
        self.assertIn("research/test_workflow_admission.py", text)



    def test_etf_relative_flow_source_preflight_is_registered_as_non_research_workflow(self):
        self.assertIn("etf-relative-flow-source-preflight.yml", NON_RESEARCH_WORKFLOWS)

    def test_etf_relative_flow_source_preflight_is_read_only_and_not_a_backtest(self):
        path = WORKFLOW_DIR / "etf-relative-flow-source-preflight.yml"
        text = path.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("contents: read", text)
        self.assertNotIn("contents: write", text)
        self.assertIn("etf_relative_flow_source_preflight.py", text)
        self.assertNotIn("etf_relative_flow_ethbtc.py", text)
        self.assertIn("do not run a backtest", text.lower())


    def test_etf_relative_flow_backtest_workflow_validates_before_source_retrieval(self):
        path = WORKFLOW_DIR / "etf-relative-flow-ethbtc.yml"
        text = path.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertIn(ADMISSION_IF, text)
        self.assertIn("ref: ${{ github.sha }}", text)
        self.assertIn("cancel-in-progress: false", text)
        self.assertIn("contents: write", text)
        self.assertIn("test_etf_relative_flow_source_preflight.py", text)
        self.assertIn("test_etf_relative_flow_ethbtc.py", text)
        self.assertIn("test_persist_etf_relative_flow_evidence.py", text)
        self.assertLess(
            text.index("Run deterministic flow, embargo, event, walk-forward, inference and persistence tests"),
            text.index("Retrieve frozen Farside and checksummed Binance sources"),
        )
        self.assertIn("if: always()", text)
        self.assertIn("git fetch origin main", text)
        self.assertIn("git reset --hard origin/main", text)
        self.assertIn("git push origin HEAD:main", text)


    def test_etf_relative_flow_source_preflight_has_narrow_source_only_path_filters(self):
        text = (WORKFLOW_DIR / "etf-relative-flow-source-preflight.yml").read_text(encoding="utf-8")
        self.assertIn('"research/etf_relative_flow_source_preflight.py"', text)
        self.assertIn('"research/test_etf_relative_flow_source_preflight.py"', text)
        self.assertIn('".github/workflows/etf-relative-flow-source-preflight.yml"', text)
        self.assertNotIn('"research/test_workflow_admission.py"', text)
        self.assertNotIn('"research/etf_relative_flow_ethbtc.py"', text)
        self.assertNotIn('"research/PREREGISTERED-QFR-2026-11-27-BTC-ETH-ETF-RELATIVE-FLOW-ETHBTC-01.md"', text)


    def test_btc_blockspace_fee_rate_source_preflight_is_registered_as_non_research_workflow(self):
        self.assertIn("btc-blockspace-fee-rate-source-preflight.yml", NON_RESEARCH_WORKFLOWS)

    def test_btc_blockspace_fee_rate_source_preflight_is_read_only_and_not_a_backtest(self):
        path = WORKFLOW_DIR / "btc-blockspace-fee-rate-source-preflight.yml"
        text = path.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("contents: read", text)
        self.assertNotIn("contents: write", text)
        self.assertIn("btc_blockspace_fee_rate_source_preflight.py", text)
        self.assertNotIn("btc_blockspace_fee_rate_btc_downside.py", text)
        self.assertIn("do not run a backtest", text.lower())
        self.assertIn("ref: " + "$" + "{{ github.sha }}", text)
        self.assertIn("cancel-in-progress: false", text)

    def test_btc_blockspace_fee_rate_source_preflight_has_narrow_path_filters(self):
        text = (WORKFLOW_DIR / "btc-blockspace-fee-rate-source-preflight.yml").read_text(encoding="utf-8")
        self.assertIn('"research/btc_blockspace_fee_rate_source_preflight.py"', text)
        self.assertIn('"research/test_btc_blockspace_fee_rate_source_preflight.py"', text)
        self.assertNotIn('".github/workflows/btc-blockspace-fee-rate-source-preflight.yml"', text)
        self.assertNotIn('"research/PREREGISTERED-QFR-2026-11-27-BTC-BLOCKSPACE-FEERATE-DOWNSIDE-01.md"', text)
        self.assertNotIn('"research/test_workflow_admission.py"', text)
        self.assertNotIn('".github/workflows/workflow-admission-tests.yml"', text)


    def test_btc_blockspace_fee_rate_backtest_workflow_validates_before_source_retrieval(self):
        path = WORKFLOW_DIR / "btc-blockspace-fee-rate-btc-downside.yml"
        text = path.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertIn(ADMISSION_IF, text)
        self.assertIn("ref: " + "$" + "{{ github.sha }}", text)
        self.assertIn("cancel-in-progress: false", text)
        self.assertIn("contents: write", text)
        self.assertIn('python -m unittest discover -s research -p "test_btc_blockspace_fee_rate_btc_downside.py" -v', text)
        self.assertIn('python -m unittest discover -s research -p "test_btc_blockspace_fee_rate_source_preflight.py" -v', text)
        self.assertLess(
            text.index("Run deterministic source, timing, event, model and admission tests"),
            text.index("Retrieve frozen Mempool and previously accepted checksummed Binance sources"),
        )
        self.assertIn("git fetch origin main", text)
        self.assertIn("git reset --hard origin/main", text)
        self.assertIn(
            'git add "$report" "$manifest" research/HYPOTHESIS-REGISTRY.md research/PREREGISTERED-QFR-2026-11-27-BTC-BLOCKSPACE-FEERATE-DOWNSIDE-01.md',
            text,
        )

    def test_btc_blockspace_fee_rate_backtest_workflow_run_blocks_have_valid_bash_syntax(self):
        if not shutil.which("bash"):
            self.skipTest("bash is unavailable")
        text = (WORKFLOW_DIR / "btc-blockspace-fee-rate-btc-downside.yml").read_text(encoding="utf-8")
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

    def test_btc_blockspace_prereg_changes_trigger_global_admission_guard(self):
        text = (WORKFLOW_DIR / "workflow-admission-tests.yml").read_text(encoding="utf-8")
        self.assertIn(
            '"research/PREREGISTERED-QFR-2026-11-27-BTC-BLOCKSPACE-FEERATE-DOWNSIDE-01.md"',
            text,
        )

    def test_btc_blockspace_fee_rate_backtest_workflow_has_narrow_path_filters(self):
        text = (WORKFLOW_DIR / "btc-blockspace-fee-rate-btc-downside.yml").read_text(encoding="utf-8")
        for path in (
            '"research/PREREGISTERED-QFR-2026-11-27-BTC-BLOCKSPACE-FEERATE-DOWNSIDE-01.md"',
            '"research/btc_blockspace_fee_rate_btc_downside.py"',
            '"research/test_btc_blockspace_fee_rate_btc_downside.py"',
            '"research/btc_blockspace_fee_rate_source_preflight.py"',
            '"research/test_btc_blockspace_fee_rate_source_preflight.py"',
            '".github/workflows/btc-blockspace-fee-rate-btc-downside.yml"',
        ):
            with self.subTest(path=path):
                self.assertIn(path, text)
        self.assertNotIn('"research/test_workflow_admission.py"', text)
        self.assertNotIn('".github/workflows/workflow-admission-tests.yml"', text)


    def test_initial_claims_source_preflight_has_narrow_source_only_path_filters(self):
        text = (WORKFLOW_DIR / "initial-claims-source-preflight.yml").read_text(encoding="utf-8")
        self.assertIn('"research/initial_claims_source_preflight.py"', text)
        self.assertIn('"research/test_initial_claims_source_preflight.py"', text)
        self.assertNotIn('"research/PREREGISTERED-QFR-2026-11-27-INITIAL-CLAIMS-BTC-DOWNSIDE-01.md"', text)
        self.assertIn('".github/workflows/initial-claims-source-preflight.yml"', text)
        self.assertNotIn('"research/test_workflow_admission.py"', text)

    def test_initial_claims_source_preflight_is_read_only_and_never_runs_backtest(self):
        path = WORKFLOW_DIR / "initial-claims-source-preflight.yml"
        text = path.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("contents: read", text)
        self.assertNotIn("contents: write", text)
        self.assertIn("initial_claims_source_preflight.py", text)
        self.assertNotIn("initial_claims_btc_downside.py", text)
        self.assertIn("do not run a backtest", text.lower())
        self.assertIn("cancel-in-progress: false", text)
        self.assertIn("ref: ${{ github.sha }}", text)
        self.assertIn("initial-claims-source-preflight.yml", NON_RESEARCH_WORKFLOWS)



    def test_initial_claims_backtest_workflow_uses_atomic_admission_and_immutable_checkout(self):
        text = (WORKFLOW_DIR / "initial-claims-btc-downside.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertIn(ADMISSION_IF, text)
        self.assertIn("ref: ${{ github.sha }}", text)
        self.assertIn("cancel-in-progress: false", text)
        self.assertIn("contents: write", text)
        self.assertLess(
            text.index("Run deterministic source, timing, event, model and admission tests"),
            text.index("Retrieve frozen sources and run the one preregistered real-data forecast"),
        )
        self.assertIn("forecast_rows.csv", text)
        self.assertIn("completed_backtest", text)
        self.assertIn('"$manifest"', text)

    def test_initial_claims_backtest_workflow_run_blocks_have_valid_bash_syntax(self):
        if not shutil.which("bash"):
            self.skipTest("bash is unavailable")
        text = (WORKFLOW_DIR / "initial-claims-btc-downside.yml").read_text(encoding="utf-8")
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

    def test_chatgpt_control_pr_dispatch_bridge_is_exactly_gated_and_least_privilege(self):
        path = WORKFLOW_DIR / "chatgpt-control-pr-dispatch.yml"
        text = path.read_text(encoding="utf-8")
        required = [
            "issue_comment:",
            "types: [created]",
            "github.event.issue.number == 15",
            "github.event.issue.pull_request != null",
            "github.event.comment.user.login == 'takenthatusernameis-collab'",
            "github.event.comment.body == '/qfr-probe-dispatch-bridge'",
            "github.event.comment.body == '/qfr-run-initial-claims-btc-downside'",
            "actions: write",
            "pull-requests: write",
            "cancel-in-progress: false",
            "dispatch-bridge-probe.yml",
            "initial-claims-btc-downside.yml",
            "issues/comments/$COMMENT_ID/reactions",
        ]
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        self.assertNotIn("pull_request_target", text)
        self.assertNotIn("actions/checkout", text)
        self.assertNotIn("GITHUB_HEAD_REF", text)
        self.assertNotIn("github.event.pull_request.head.sha", text)
        self.assertNotIn("contents: write", text)
        self.assertNotIn("workflow_dispatch:", text)

    def test_dispatch_bridge_probe_is_a_noop_and_uses_no_token_permissions(self):
        path = WORKFLOW_DIR / "dispatch-bridge-probe.yml"
        text = path.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("source_comment_id", text)
        self.assertIn("source_control_pr", text)
        self.assertIn("source_actor", text)
        self.assertIn("permissions: {}", text)
        self.assertIn('test "$GITHUB_REF" = "refs/heads/main"', text)
        self.assertNotIn("actions/checkout", text)
        self.assertNotIn("contents: write", text)
        self.assertNotIn("secrets.", text)

    def test_initial_claims_workflow_records_comment_dispatch_provenance(self):
        text = (WORKFLOW_DIR / "initial-claims-btc-downside.yml").read_text(encoding="utf-8")
        for field in ("source_comment_id", "source_control_pr", "source_actor"):
            with self.subTest(field=field):
                self.assertIn(field, text)
        self.assertIn("Record authenticated dispatch provenance", text)
        self.assertIn("ref: ${{ github.sha }}", text)

    def test_control_dispatch_shell_blocks_have_valid_bash_syntax(self):
        if not shutil.which("bash"):
            self.skipTest("bash is unavailable")
        for filename in ("chatgpt-control-pr-dispatch.yml", "dispatch-bridge-probe.yml"):
            text = (WORKFLOW_DIR / filename).read_text(encoding="utf-8")
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
            self.assertGreaterEqual(len(scripts), 1, msg=filename)
            for script_index, script in enumerate(scripts):
                with self.subTest(workflow=filename, script=script_index):
                    result = subprocess.run(
                        ["bash", "-n"], input=script, text=True, capture_output=True, check=False
                    )
                    self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_readme_closes_initial_claims_gate_with_verified_bridge_and_result(self):
        text = README.read_text(encoding="utf-8")
        self.assertIn("CLOSED — INCONCLUSIVE", text)
        self.assertIn("actions/runs/46066725930", text)
        self.assertIn("pull-requests: write", text)
        self.assertIn("7227943059", text)
        self.assertNotIn("Only remaining action:", text)
        self.assertNotIn("If no authorized dispatch occurs by the final deadline", text)

    def test_dispatch_bridge_documentation_records_security_and_verification(self):
        path = ROOT / "docs" / "CHATGPT-CONTROL-PR-DISPATCH.md"
        text = path.read_text(encoding="utf-8")
        for phrase in (
            "draft control PR",
            "exact control PR number",
            "pull-requests: write",
            "Do not merge it;",
            "does not checkout code",
            "GITHUB_TOKEN",
            "workflow_dispatch",
            "rocket",
            "46066725930",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)


    def test_ethereum_dex_turnover_preregistration_has_frozen_identity_and_timebox(self):
        path = ROOT / "research" / "PREREGISTERED-QFR-2026-11-28-ETHEREUM-DEX-TURNOVER-ETH-RV-01.md"
        text = path.read_text(encoding="utf-8")
        for phrase in (
            "- **Hypothesis ID:** `QFR-2026-11-28-ETHEREUM-DEX-TURNOVER-ETH-RV-01`",
            "- **Registered:** 2026-11-28T01:42:11Z",
            "- **Timebox start:** 2026-11-28T01:42:11Z",
            "- **Maximum substantive cycles:** 4",
            "- **Difficulty:** MEDIUM",
            "- **Status:** COMPLETED — INCONCLUSIVE; Cycle 3 empirical backtest and Cycle 4 independent audit completed at 2026-11-28T02:58:40Z",
            "46097000508",
            "1dbf0878593b45b84e9a9e7d9a13ccc3761b10d53510c5852e60da274f62f1c6",
            "- **Expiry rule:**",
            "INCONCLUSIVE/INFEASIBLE",
            "DEX notional turnover relative to Ethereum DeFi total value locked",
            "Cycle 4 independent audit",
            "CLOSED — INCONCLUSIVE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
    def test_ethereum_dex_turnover_source_preflight_has_narrow_path_filters(self):
        path = WORKFLOW_DIR / "ethereum-dex-turnover-eth-rv-source-preflight.yml"
        text = path.read_text(encoding="utf-8")
        for expected in (
            '"research/ethereum_dex_turnover_eth_rv_source_preflight.py"',
            '"research/test_ethereum_dex_turnover_eth_rv_source_preflight.py"',
            '".github/workflows/ethereum-dex-turnover-eth-rv-source-preflight.yml"',
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)
        self.assertNotIn('"research/PREREGISTERED-QFR-2026-11-28-ETHEREUM-DEX-TURNOVER-ETH-RV-01.md"', text)
        self.assertNotIn('"research/test_workflow_admission.py"', text)
        self.assertNotIn('"research/ethereum_dex_turnover_eth_rv.py"', text)

    def test_ethereum_dex_turnover_model_module_declares_the_registered_hypothesis(self):
        path = ROOT / "research" / "ethereum_dex_turnover_eth_rv.py"
        text = path.read_text(encoding="utf-8")
        self.assertIn('HYPOTHESIS_ID = "QFR-2026-11-28-ETHEREUM-DEX-TURNOVER-ETH-RV-01"', text)
        self.assertIn('EXPECTED_PREFLIGHT_RUN_ID = "46097000508"', text)
        self.assertIn("EXPECTED_PREFLIGHT_MANIFEST_SHA256", text)

    def test_ethereum_dex_turnover_model_workflow_has_atomic_admission_and_frozen_sources(self):
        path = WORKFLOW_DIR / "ethereum-dex-turnover-eth-rv.yml"
        text = path.read_text(encoding="utf-8")
        for expected in (
            '"research/ethereum_dex_turnover_eth_rv.py"',
            '"research/test_ethereum_dex_turnover_eth_rv.py"',
            '"research/PREREGISTERED-QFR-2026-11-28-ETHEREUM-DEX-TURNOVER-ETH-RV-01.md"',
            '".github/workflows/ethereum-dex-turnover-eth-rv.yml"',
            "if: github.event_name != 'push' || startsWith(github.event.head_commit.message, '[QFR-ADMIT] research:')",
            "cancel-in-progress: false",
            "ref: ${{ github.sha }}",
            "persist-credentials: true",
            "actions: read",
            "contents: write",
            "15243896011",
            "5faf791cc3a6c6ef31ede46af0208d41b31ca563cef808190d31634bb5be2d49",
            "1dbf0878593b45b84e9a9e7d9a13ccc3761b10d53510c5852e60da274f62f1c6",
            "test_ethereum_dex_turnover_eth_rv.py",
            "if: always()",
            "git reset --hard origin/main",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)
        self.assertNotIn("pull_request_target", text)

    def test_ethereum_dex_turnover_source_preflight_is_read_only_and_not_a_backtest(self):
        path = WORKFLOW_DIR / "ethereum-dex-turnover-eth-rv-source-preflight.yml"
        text = path.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("contents: read", text)
        self.assertNotIn("contents: write", text)
        self.assertIn("ethereum_dex_turnover_eth_rv_source_preflight.py", text)
        self.assertNotIn("ethereum_dex_turnover_eth_rv.py", text)
        self.assertIn("do not run a backtest", text.lower())
        self.assertIn("actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02", text)
        self.assertIn("retention-days: 30", text)


    def test_eth_validator_queue_source_preflight_is_registered_as_non_research_workflow(self):
        self.assertIn("eth-validator-queue-source-preflight.yml", NON_RESEARCH_WORKFLOWS)

    def test_eth_validator_queue_source_preflight_is_source_only_and_persists_evidence(self):
        path = WORKFLOW_DIR / "eth-validator-queue-source-preflight.yml"
        text = path.read_text(encoding="utf-8")
        for expected in (
            "workflow_dispatch:",
            "contents: read",
            "contents: write",
            "ref: ${{ github.sha }}",
            "cancel-in-progress: false",
            "eth_validator_queue_source_preflight.py",
            "no model fitting",
            "do not run a backtest",
            "if: always()",
            "git fetch origin main",
            "git reset --hard origin/main",
            "git push origin HEAD:main",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)
        self.assertNotIn("eth_validator_queue_asymmetry.py", text)
        self.assertNotIn("pull_request_target", text)

    def test_eth_validator_queue_source_preflight_has_narrow_source_only_path_filters(self):
        path = WORKFLOW_DIR / "eth-validator-queue-source-preflight.yml"
        text = path.read_text(encoding="utf-8")
        for expected in (
            '\"research/eth_validator_queue_source_preflight.py\"',
            '\"research/test_eth_validator_queue_source_preflight.py\"',
            '\".github/workflows/eth-validator-queue-source-preflight.yml\"',
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)
        self.assertNotIn('\"research/eth_validator_queue_asymmetry.py\"', text)
        self.assertNotIn('\"research/test_workflow_admission.py\"', text)
        self.assertNotIn('\"research/PREREGISTERED-', text)

    def test_eth_validator_queue_source_preflight_shell_blocks_have_valid_bash_syntax(self):
        if not shutil.which("bash"):
            self.skipTest("bash is unavailable")
        text = (WORKFLOW_DIR / "eth-validator-queue-source-preflight.yml").read_text(encoding="utf-8")
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
        self.assertGreaterEqual(len(scripts), 4)
        for script_index, script in enumerate(scripts):
            with self.subTest(script=script_index):
                result = subprocess.run(
                    ["bash", "-n"], input=script, text=True, capture_output=True, check=False
                )
                self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_eth_validator_queue_pit_workflow_pins_external_history_without_credentials(self):
        text = (WORKFLOW_DIR / "eth-validator-queue-pit-concordance.yml").read_text(encoding="utf-8")
        self.assertIn("repository: etheralpha/validatorqueue-com", text)
        self.assertIn("ref: 6d90783883b84129db6f17b3d454f702dc1f8f1f", text)
        self.assertIn("fetch-depth: 0", text)
        self.assertIn("persist-credentials: false", text)
        self.assertNotIn("ref: main", text)

    def test_h8_ci_credit_impulse_preregistration_has_frozen_identity_and_timebox(self):
        path = ROOT / "research" / "PREREGISTERED-QFR-2026-11-28-H8-CI-CREDIT-IMPULSE-BTC-DOWNSIDE-01.md"
        text = path.read_text(encoding="utf-8")
        required = [
            "Hypothesis ID:",
            "QFR-2026-11-28-H8-CI-CREDIT-IMPULSE-BTC-DOWNSIDE-01",
            "2026-11-28T05:49:20Z",
            "2026-12-01T05:49:20Z",
            "2026-12-03T05:49:20Z",
            "Maximum substantive cycles:** 4",
            "Difficulty:** MEDIUM",
            "ALFRED",
            "TOTCI",
            "No current-vintage FRED",
            "INCONCLUSIVE/INFEASIBLE",
        ]
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_h8_ci_credit_impulse_source_preflight_is_read_only_and_not_a_backtest(self):
        path = WORKFLOW_DIR / "h8-ci-credit-impulse-source-preflight.yml"
        text = path.read_text(encoding="utf-8")
        required = [
            "workflow_dispatch:",
            "contents: read",
            "ref: ${{ github.sha }}",
            "persist-credentials: false",
            "cancel-in-progress: false",
            "h8_ci_credit_impulse_source_preflight.py",
            "test_h8_ci_credit_impulse_source_preflight.py",
            "do not run a backtest",
            "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
            "retention-days: 30",
        ]
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        self.assertNotIn("contents: write", text)
        self.assertNotIn("h8_ci_credit_impulse_btc_downside.py", text)
        self.assertNotIn("[QFR-ADMIT] research:", text)
        self.assertNotIn('"research/PREREGISTERED-', text)
        self.assertNotIn('"research/test_workflow_admission.py"', text)

    def test_h8_ci_credit_impulse_source_preflight_has_narrow_path_filters(self):
        text = (WORKFLOW_DIR / "h8-ci-credit-impulse-source-preflight.yml").read_text(encoding="utf-8")
        for expected in (
            '"research/h8_ci_credit_impulse_source_preflight.py"',
            '"research/test_h8_ci_credit_impulse_source_preflight.py"',
            '".github/workflows/h8-ci-credit-impulse-source-preflight.yml"',
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)
        self.assertNotIn('"research/PREREGISTERED-', text)
        self.assertNotIn('"research/test_workflow_admission.py"', text)
        self.assertNotIn('"research/h8_ci_credit_impulse_btc_downside.py"', text)


if __name__ == "__main__":
    unittest.main()
