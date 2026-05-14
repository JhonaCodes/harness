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
            self.assertFalse((project / "AGENTS.md").exists())
            self.assertFalse((project / ".harness").exists())

    def test_bug_with_tests_selects_tdd(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "tests").mkdir()
            result = self.run_harness("inspect", "--project", str(project), "--task", "fix failing login test")
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["decision"]["workflow"], "tdd")

    def test_tdd_dry_run_lists_auto_adoption_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            result = self.run_harness("run", "--project", str(project), "--task", "fix failing login test", "--dry-run")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("/AGENTS.md", result.stdout)
            self.assertIn("/CLAUDE.md", result.stdout)
            self.assertIn("/GEMINI.md", result.stdout)
            self.assertIn("/.harness/ENTRYPOINT.md", result.stdout)
            self.assertIn("/.harness/config.json", result.stdout)
            self.assertIn("/.harness/workflow.json", result.stdout)
            self.assertIn("/.harness/adapters.json", result.stdout)
            self.assertIn("/.harness/skills.json", result.stdout)
            self.assertIn("/.harness/memory.json", result.stdout)

    def test_adapters_none_installs_only_universal_entrypoints(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            result = self.run_harness(
                "run",
                "--project",
                str(project),
                "--task",
                "fix failing login test",
                "--adapters",
                "none",
                "--dry-run",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("/HARNESS.md", result.stdout)
            self.assertIn("/.harness/ENTRYPOINT.md", result.stdout)
            self.assertNotIn("/AGENTS.md", result.stdout)
            self.assertNotIn("/CLAUDE.md", result.stdout)
            self.assertNotIn("/GEMINI.md", result.stdout)

    def test_existing_entrypoint_gets_managed_section_appended(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            agents = project / "AGENTS.md"
            agents.write_text("# Existing Rules\n\nKeep this.\n", encoding="utf-8")
            result = self.run_harness("run", "--project", str(project), "--task", "fix failing login test")
            self.assertEqual(result.returncode, 0, result.stderr)
            content = agents.read_text(encoding="utf-8")
            self.assertIn("Keep this.", content)
            self.assertIn("BEGIN HARNESS_MANAGED", content)

    def test_backlog_selects_sdd(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            result = self.run_harness("inspect", "--project", str(project), "--task", "triage github issues and create API contract specs")
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["decision"]["workflow"], "sdd")

    def test_sdd_dry_run_lists_sdd_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            result = self.run_harness("run", "--project", str(project), "--task", "triage github issues and create API contract specs", "--dry-run")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("/.harness/ENTRYPOINT.md", result.stdout)
            self.assertIn("/.harness/workflow.json", result.stdout)
            self.assertIn("/feature_list.json", result.stdout)
            self.assertIn("/CHECKPOINTS.md", result.stdout)
            self.assertIn("/specs/.gitkeep", result.stdout)
            self.assertIn("/.harness/agents/leader.md", result.stdout)
            self.assertIn("/.claude/agents/leader.md", result.stdout)

    def test_skill_add_and_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            result = self.run_harness(
                "skill",
                "add",
                "--project",
                str(project),
                "--name",
                "backend-api",
                "--triggers",
                "api,endpoint,auth",
                "--path",
                "/tmp/SKILL.md",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            result = self.run_harness("skill", "list", "--project", str(project))
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload[0]["name"], "backend-api")
            self.assertEqual(payload[0]["triggers"], ["api", "endpoint", "auth"])

    def test_memory_add_and_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            result = self.run_harness("memory", "add", "--project", str(project), "--key", "api_style", "--value", "Use /v1")
            self.assertEqual(result.returncode, 0, result.stderr)
            result = self.run_harness("memory", "list", "--project", str(project))
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["entries"]["api_style"], "Use /v1")


if __name__ == "__main__":
    unittest.main()
