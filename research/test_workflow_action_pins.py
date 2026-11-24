import re
import unittest
from pathlib import Path


class WorkflowActionPinTests(unittest.TestCase):
    def test_external_actions_are_pinned_to_full_commit_sha(self):
        workflow_dir = Path(__file__).resolve().parent.parent / ".github" / "workflows"
        workflows = sorted(workflow_dir.glob("*.yml"))
        self.assertTrue(workflows, "expected workflow files")
        failures = []
        pattern = re.compile(r"^\s*uses:\s*([^\s#]+)\s*(?:#\s*(v[0-9][^\s]*))?\s*$", re.MULTILINE)
        for path in workflows:
            for reference, version_comment in pattern.findall(path.read_text(encoding="utf-8")):
                if reference.startswith("./"):
                    continue
                if "@" not in reference:
                    failures.append(f"{path.name}: unversioned action {reference}")
                    continue
                owner_repo, revision = reference.rsplit("@", 1)
                if not re.fullmatch(r"[0-9a-f]{40}", revision):
                    failures.append(f"{path.name}: {reference} is not pinned to a full commit SHA")
                if owner_repo.startswith("actions/") and not version_comment:
                    failures.append(f"{path.name}: {reference} is missing its reviewed version comment")
        self.assertEqual(failures, [], "\n".join(failures))


if __name__ == "__main__":
    unittest.main()
