import json
import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "harness.py"
QUICK_VALIDATE = ROOT / "quick_validate.py"


class HarnessCliTests(unittest.TestCase):
    def run_harness(self, *args):
        return subprocess.run(
            ["python3", str(SCRIPT), *args],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def run_install(self, home: Path, *args):
        env = os.environ.copy()
        env.update(
            {
                "HOME": str(home),
                "HARNESS_HOME": str(home / ".harness"),
                "BIN_DIR": str(home / ".local" / "bin"),
                "CODEX_HOME": str(home / ".codex"),
                "CLAUDE_HOME": str(home / ".claude"),
                "GEMINI_HOME": str(home / ".gemini"),
                "OPENCODE_HOME": str(home / ".config" / "opencode"),
            }
        )
        return subprocess.run(
            ["bash", str(ROOT / "install.sh"), *args],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
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
            self.assertIn("/.harness/agents.json", result.stdout)
            self.assertIn("/.harness/docs.json", result.stdout)
            self.assertIn("/.harness/rules.json", result.stdout)
            self.assertIn("/.harness/memory.json", result.stdout)
            self.assertIn("/docs/audit.md", result.stdout)

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
            self.assertIn("/docs/audit.md", result.stdout)
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
            self.assertIn("/.harness/agents/auditor.md", result.stdout)
            forbidden_agent_path = "/" + ".claude" + "/agents/leader.md"
            self.assertNotIn(forbidden_agent_path, result.stdout)

    def test_workflow_json_includes_audit_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            result = self.run_harness("run", "--project", str(project), "--task", "fix failing login test", "--adapters", "none")
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads((project / ".harness" / "workflow.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["rules"]["audit_policy"], "risk_based")
            self.assertTrue(payload["rules"]["mandatory_audit_before_closure"])

    def test_sdd_checkpoints_require_audit_verdict_before_done(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            result = self.run_harness("run", "--project", str(project), "--task", "triage github issues and create API contract specs", "--adapters", "none")
            self.assertEqual(result.returncode, 0, result.stderr)
            content = (project / "CHECKPOINTS.md").read_text(encoding="utf-8")
            self.assertIn("progress/audit_<feature>.md", content)
            self.assertIn("GO-WITH-RISK", content)

    def test_registered_rule_is_referenced_in_audit_doc(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            result = self.run_harness(
                "rule",
                "add",
                "--project",
                str(project),
                "--name",
                "ui-audit-rules",
                "--triggers",
                "widget,ui",
                "--path",
                "/tmp/ui-rules.md",
                "--description",
                "Project UI audit rules",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            result = self.run_harness("run", "--project", str(project), "--task", "fix failing widget test", "--adapters", "none")
            self.assertEqual(result.returncode, 0, result.stderr)
            content = (project / "docs" / "audit.md").read_text(encoding="utf-8")
            self.assertIn("Selected rules", content)
            self.assertIn("ui-audit-rules", content)
            self.assertIn("/tmp/ui-rules.md", content)

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

    def test_agent_doc_and_rule_add_and_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            for command, name in [("agent", "security-auditor"), ("doc", "api-contract"), ("rule", "api-layering")]:
                result = self.run_harness(
                    command,
                    "add",
                    "--project",
                    str(project),
                    "--name",
                    name,
                    "--triggers",
                    "api,auth",
                    "--path",
                    f"/tmp/{name}.md",
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                result = self.run_harness(command, "list", "--project", str(project))
                self.assertEqual(result.returncode, 0, result.stderr)
                payload = json.loads(result.stdout)
                self.assertEqual(payload[0]["name"], name)

    def test_memory_add_and_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            result = self.run_harness("memory", "add", "--project", str(project), "--key", "api_style", "--value", "Use /v1")
            self.assertEqual(result.returncode, 0, result.stderr)
            result = self.run_harness("memory", "list", "--project", str(project))
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["entries"]["api_style"], "Use /v1")

    def test_quick_validate_detects_generated_absolute_user_paths(self):
        spec = importlib.util.spec_from_file_location("quick_validate", QUICK_VALIDATE)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "leak.txt").write_text("/" + "Users" + "/example/project\n", encoding="utf-8")
            errors = []
            module.check_private_refs(project, errors)
            self.assertTrue(errors)

    def test_claude_command_template_exists(self):
        content = (ROOT / "commands" / "harness.md").read_text(encoding="utf-8")
        self.assertIn("$ARGUMENTS", content)
        self.assertIn("harness inspect", content)
        self.assertIn("harness run", content)

    def test_cli_converges_through_main_entrypoint(self):
        wrapper = (ROOT / "scripts" / "harness.py").read_text(encoding="utf-8")
        main = (ROOT / "scripts" / "main.py").read_text(encoding="utf-8")
        cli = (ROOT / "scripts" / "harness_core" / "cli.py").read_text(encoding="utf-8")
        self.assertIn("from main import main", wrapper)
        self.assertIn("harness_core.cli", main)
        self.assertIn("class HarnessCli", cli)

    def test_runtime_is_split_into_context_modules(self):
        required = [
            "apply.py",
            "capabilities.py",
            "cli.py",
            "commands.py",
            "constants.py",
            "decisioning.py",
            "inspection.py",
            "io.py",
            "models.py",
            "projects.py",
            "rendering.py",
        ]
        for rel in required:
            with self.subTest(module=rel):
                self.assertTrue((ROOT / "scripts" / "harness_core" / rel).exists())

    def test_required_project_templates_exist(self):
        required = [
            "README.md",
            "HARNESS.tdd.md",
            "HARNESS.sdd.md",
            "init.sh",
            ".harness/ENTRYPOINT.md",
            ".harness/config.json",
            ".harness/workflow.json",
            ".harness/adapters.json",
            ".harness/skills.json",
            ".harness/agents.json",
            ".harness/docs.json",
            ".harness/rules.json",
            ".harness/memory.json",
            ".harness/agents/leader.md",
            ".harness/agents/spec_author.md",
            ".harness/agents/implementer.md",
            ".harness/agents/reviewer.md",
            ".harness/agents/auditor.md",
            "docs/verification.md",
            "docs/audit.md",
            "docs/conventions.md",
            "docs/architecture.md",
            "docs/specs.md",
            "progress/current.md",
            "progress/history.md",
            "feature_list.json",
            "CHECKPOINTS.md",
            "adapters/tool.md",
        ]
        for rel in required:
            with self.subTest(template=rel):
                path = ROOT / "templates" / rel
                self.assertTrue(path.exists(), f"Missing template: {rel}")

    def test_install_targets_all_installs_selected_llm_entrypoints(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            result = self.run_install(home, "--targets", "codex,claude,gemini,opencode")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((home / ".local" / "bin" / "harness").exists())
            self.assertTrue((home / ".harness" / "harness" / "scripts" / "harness.py").exists())
            self.assertTrue((home / ".codex" / "skills" / "harness" / "SKILL.md").exists())
            self.assertTrue((home / ".claude" / "commands" / "harness.md").exists())
            self.assertIn("BEGIN HARNESS_GLOBAL", (home / ".gemini" / "GEMINI.md").read_text(encoding="utf-8"))
            self.assertIn(
                "BEGIN HARNESS_GLOBAL",
                (home / ".config" / "opencode" / "AGENTS.md").read_text(encoding="utf-8"),
            )

    def test_install_targets_none_installs_only_runtime_and_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            result = self.run_install(home, "--targets", "none")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((home / ".local" / "bin" / "harness").exists())
            self.assertTrue((home / ".harness" / "harness" / "scripts" / "harness.py").exists())
            self.assertFalse((home / ".codex" / "skills" / "harness").exists())
            self.assertFalse((home / ".claude" / "commands" / "harness.md").exists())
            self.assertFalse((home / ".gemini" / "GEMINI.md").exists())
            self.assertFalse((home / ".config" / "opencode" / "AGENTS.md").exists())

    def test_install_targets_accepts_numbers_and_empty_separators(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            result = self.run_install(home, "--targets", "1,,3")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((home / ".codex" / "skills" / "harness" / "SKILL.md").exists())
            self.assertFalse((home / ".claude" / "commands" / "harness.md").exists())
            self.assertIn("BEGIN HARNESS_GLOBAL", (home / ".gemini" / "GEMINI.md").read_text(encoding="utf-8"))
            self.assertFalse((home / ".config" / "opencode" / "AGENTS.md").exists())


if __name__ == "__main__":
    unittest.main()
