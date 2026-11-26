from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / ".github" / "workflows"
README = ROOT / "README.md"
ADMISSION_IF = (
    "if: github.event_name != 'push' || "
    "contains(github.event.head_commit.message, '[QFR-ADMIT]')"
)
NON_RESEARCH_WORKFLOWS = {"workflow-admission-tests.yml"}


class ResearchWorkflowAdmissionTests(unittest.TestCase):
    def test_readme_documents_atomic_admission_marker(self):
        text = README.read_text(encoding="utf-8")
        self.assertIn("[QFR-ADMIT]", text)
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

    def test_readme_documents_same_session_replacement_invariant(self):
        text = README.read_text(encoding="utf-8")
        self.assertIn("Same-session replacement invariant", text)
        self.assertIn("same session", text.lower())

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


if __name__ == "__main__":
    unittest.main()
