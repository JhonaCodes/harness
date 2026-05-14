import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "harness.py"


class HarnessCliTests(unittest.TestCase):
    def run_harness(self, *args):
        return subprocess.run(
            ["python3", str(SCRIPT), *args],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_simple_task_installs_no_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            result = self.run_harness("run", "--project", str(project), "--task", "summarize status", "--dry-run")
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout.split("}\n# Harness Apply Report", 1)[0] + "}")
            self.assertEqual(payload["workflow"], "simple")
            self.assertFalse((project / "HARNESS.md").exists())

    def test_bug_with_tests_selects_tdd(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "tests").mkdir()
            result = self.run_harness("inspect", "--project", str(project), "--task", "fix failing login test")
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["decision"]["workflow"], "tdd")

    def test_backlog_selects_sdd(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            result = self.run_harness("inspect", "--project", str(project), "--task", "triage github issues and create API contract specs")
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["decision"]["workflow"], "sdd")


if __name__ == "__main__":
    unittest.main()
