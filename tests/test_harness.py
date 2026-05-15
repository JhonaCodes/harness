import json
import importlib.util
import os
import pty
import select
import subprocess
import tempfile
import time
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

    def run_install_in_pty(self, home: Path, input_text: str) -> tuple[int, str]:
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
        master, slave = pty.openpty()
        proc = subprocess.Popen(
            ["bash", str(ROOT / "install.sh")],
            stdin=slave,
            stdout=slave,
            stderr=slave,
            env=env,
        )
        os.close(slave)
        output = bytearray()
        sent = False
        deadline = time.time() + 10
        try:
            while time.time() < deadline:
                ready, _, _ = select.select([master], [], [], 0.1)
                if ready:
                    chunk = os.read(master, 4096)
                    if not chunk:
                        break
                    output.extend(chunk)
                    if not sent and b"> " in output:
                        os.write(master, input_text.encode("utf-8"))
                        sent = True
                if proc.poll() is not None:
                    break
            proc.wait(timeout=5)
        finally:
            os.close(master)
            if proc.poll() is None:
                proc.kill()
        return proc.returncode or 0, output.decode("utf-8", errors="replace")

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
            self.assertIn("/.harness/rules/data_storage.md", result.stdout)
            self.assertIn("/.harness/mcps.json", result.stdout)
            self.assertIn("/.harness/memory.json", result.stdout)
            self.assertIn("/.harness/agents/tdd_lead.md", result.stdout)
            self.assertIn("/.harness/agents/red_test_author.md", result.stdout)
            self.assertIn("/.harness/agents/green_implementer.md", result.stdout)
            self.assertIn("/.harness/agents/refactor_specialist.md", result.stdout)
            self.assertIn("/.harness/agents/architecture_lead.md", result.stdout)
            self.assertIn("/.harness/agents/context_auditor.md", result.stdout)
            self.assertIn("/.harness/agents/test_verifier.md", result.stdout)
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
            self.assertIn("/.harness/agents/architecture_lead.md", result.stdout)
            self.assertIn("/.harness/agents/blueprint_architect.md", result.stdout)
            self.assertIn("/.harness/agents/confidence_reporter.md", result.stdout)
            self.assertIn("/.harness/rules/data_storage.md", result.stdout)
            forbidden_agent_path = "/" + ".claude" + "/agents/leader.md"
            self.assertNotIn(forbidden_agent_path, result.stdout)

    def test_installed_harness_registers_default_tdd_sdd_audit_agents_and_storage_rule(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            result = self.run_harness("run", "--project", str(project), "--task", "triage github issues and create API contract specs", "--adapters", "none")
            self.assertEqual(result.returncode, 0, result.stderr)
            agents = json.loads((project / ".harness" / "agents.json").read_text(encoding="utf-8"))
            names = {item["name"] for item in agents}
            for name in {
                "leader",
                "spec-author",
                "implementer",
                "reviewer",
                "auditor",
                "tdd-lead",
                "red-test-author",
                "green-implementer",
                "refactor-specialist",
                "architecture-lead",
                "blueprint-architect",
                "context-auditor",
                "business-rule-auditor",
                "code-quality-auditor",
                "test-verifier",
                "confidence-reporter",
            }:
                self.assertIn(name, names)
            rules = json.loads((project / ".harness" / "rules.json").read_text(encoding="utf-8"))
            self.assertEqual(rules[0]["name"], "data-storage")
            workflow = json.loads((project / ".harness" / "workflow.json").read_text(encoding="utf-8"))
            self.assertEqual(workflow["rules"]["data_storage_rule"], ".harness/rules/data_storage.md")
            init_script = (project / "scripts" / "init.sh").read_text(encoding="utf-8")
            self.assertIn(".harness/rules/data_storage.md", init_script)
            self.assertTrue((project / ".harness" / "rules" / "data_storage.md").exists())

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

    def test_mcp_add_list_select_and_reference_in_audit_doc(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            result = self.run_harness(
                "mcp",
                "add",
                "--project",
                str(project),
                "--name",
                "server-mcp",
                "--triggers",
                "widget,ui",
                "--path",
                "/tmp/server-mcp.md",
                "--description",
                "Architecture MCP context",
                "--context",
                "Use before UI architecture decisions.",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            result = self.run_harness("mcp", "list", "--project", str(project))
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload[0]["name"], "server-mcp")
            self.assertEqual(payload[0]["context"], "Use before UI architecture decisions.")

            result = self.run_harness("inspect", "--project", str(project), "--task", "fix failing widget test")
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            selected_mcps = payload["decision"]["selected_capabilities"]["mcp"]
            self.assertEqual(selected_mcps[0]["name"], "server-mcp")
            self.assertEqual(selected_mcps[0]["context"], "Use before UI architecture decisions.")

            result = self.run_harness("run", "--project", str(project), "--task", "fix failing widget test", "--adapters", "none")
            self.assertEqual(result.returncode, 0, result.stderr)
            content = (project / "docs" / "audit.md").read_text(encoding="utf-8")
            self.assertIn("Selected MCP contexts", content)
            self.assertIn("server-mcp", content)
            self.assertIn("Use before UI architecture decisions.", content)
            self.assertIn("/tmp/server-mcp.md", content)

    def test_existing_mcp_registry_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            registry = project / ".harness" / "mcps.json"
            registry.parent.mkdir()
            registry.write_text(
                json.dumps(
                    [
                        {
                            "name": "existing-mcp",
                            "triggers": ["api"],
                            "path": "/tmp/existing-mcp.md",
                            "context": "Existing context",
                        }
                    ],
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            result = self.run_harness("run", "--project", str(project), "--task", "fix failing login test", "--adapters", "none")
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(registry.read_text(encoding="utf-8"))
            self.assertEqual(payload[0]["name"], "existing-mcp")

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
            ".harness/mcps.json",
            ".harness/memory.json",
            ".harness/rules/data_storage.md",
            ".harness/agents/tdd_lead.md",
            ".harness/agents/red_test_author.md",
            ".harness/agents/green_implementer.md",
            ".harness/agents/refactor_specialist.md",
            ".harness/agents/leader.md",
            ".harness/agents/spec_author.md",
            ".harness/agents/implementer.md",
            ".harness/agents/reviewer.md",
            ".harness/agents/auditor.md",
            ".harness/agents/architecture_lead.md",
            ".harness/agents/blueprint_architect.md",
            ".harness/agents/context_auditor.md",
            ".harness/agents/business_rule_auditor.md",
            ".harness/agents/code_quality_auditor.md",
            ".harness/agents/test_verifier.md",
            ".harness/agents/confidence_reporter.md",
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
            self.assertNotIn(str(home), result.stdout)
            self.assertIn("$HOME/.codex/skills/harness", result.stdout)
            self.assertIn("$HOME/.claude/commands/harness.md", result.stdout)
            self.assertIn("$HOME/.gemini/GEMINI.md", result.stdout)
            self.assertIn("$HOME/.config/opencode/AGENTS.md", result.stdout)
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

    def test_install_manual_target_prints_instructions_without_entrypoints(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            result = self.run_install(home, "--targets", "manual")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn(str(home), result.stdout)
            self.assertIn("Manual Harness setup for any LLM", result.stdout)
            self.assertIn("$HOME/.harness/harness", result.stdout)
            self.assertIn("$HOME/.local/bin/harness", result.stdout)
            self.assertIn("Prompt to paste into any LLM", result.stdout)
            self.assertIn("Installed LLM entrypoints: none", result.stdout)
            self.assertIn("Manual setup instructions printed.", result.stdout)
            self.assertTrue((home / ".local" / "bin" / "harness").exists())
            self.assertFalse((home / ".codex" / "skills" / "harness").exists())
            self.assertFalse((home / ".claude" / "commands" / "harness.md").exists())
            self.assertFalse((home / ".gemini" / "GEMINI.md").exists())
            self.assertFalse((home / ".config" / "opencode" / "AGENTS.md").exists())

    def test_install_interactive_prompt_is_visible_and_accepts_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            returncode, output = self.run_install_in_pty(home, "5\n")
            self.assertEqual(returncode, 0, output)
            self.assertIn("Where should Harness install LLM entrypoints?", output)
            self.assertIn("5) none", output)
            self.assertIn("6) manual", output)
            self.assertIn("Installed LLM entrypoints: none", output)
            self.assertTrue((home / ".local" / "bin" / "harness").exists())
            self.assertFalse((home / ".codex" / "skills" / "harness").exists())


    # ---- New tests for Fix 1, 4, 6, 8, 9, 10 ----

    def test_init_sh_path_is_scripts(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            result = self.run_harness(
                "run", "--project", str(project),
                "--task", "triage github issues and create API contract specs",
                "--adapters", "none",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((project / "scripts" / "init.sh").exists(),
                            "scripts/init.sh must exist")
            self.assertFalse((project / "init.sh").exists(),
                             "init.sh must not be written at project root")
            mode = (project / "scripts" / "init.sh").stat().st_mode
            self.assertTrue(mode & 0o111, "scripts/init.sh must be executable")

    def test_init_sh_runs_from_project_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            self.run_harness(
                "run", "--project", str(project),
                "--task", "fix failing login test",
                "--adapters", "none", "--profile", "generic",
            )
            script = project / "scripts" / "init.sh"
            self.assertTrue(script.exists())
            # Execute from project root; the script must cd internally
            result = subprocess.run(
                ["bash", "scripts/init.sh"],
                cwd=str(project),
                check=False, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            self.assertEqual(result.returncode, 0,
                             f"scripts/init.sh failed:\n{result.stdout}\n{result.stderr}")
            self.assertIn("Harness environment ready", result.stdout)

    def test_adapter_idempotent_after_double_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            for _ in range(2):
                result = self.run_harness(
                    "run", "--project", str(project),
                    "--task", "fix failing login test",
                )
                self.assertEqual(result.returncode, 0, result.stderr)
            claude_md = (project / "CLAUDE.md").read_text(encoding="utf-8")
            self.assertEqual(claude_md.count("# Claude Adapter"), 1,
                             f"Duplicate adapter heading:\n{claude_md}")
            self.assertEqual(claude_md.count("<!-- BEGIN HARNESS_MANAGED -->"), 1)

    def test_sdd_superset_after_tdd_preserves_custom_registry(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            self.run_harness(
                "run", "--project", str(project),
                "--task", "fix failing login test",
                "--workflow", "tdd",
            )
            # Register a custom agent that must survive the sdd re-run.
            self.run_harness(
                "agent", "add",
                "--project", str(project),
                "--name", "custom-rn-expert",
                "--triggers", "reactive",
                "--path", "agent:custom-rn-expert",
            )
            result = self.run_harness(
                "run", "--project", str(project),
                "--task", "design and implement a new module with specs",
                "--workflow", "sdd",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            for rel in [
                "feature_list.json",
                "CHECKPOINTS.md",
                "specs/.gitkeep",
                ".harness/agents/leader.md",
                ".harness/agents/spec_author.md",
                ".harness/agents/implementer.md",
                ".harness/agents/reviewer.md",
                ".harness/agents/auditor.md",
            ]:
                self.assertTrue((project / rel).exists(), f"missing SDD file: {rel}")
            agents = json.loads(
                (project / ".harness" / "agents.json").read_text(encoding="utf-8")
            )
            names = {item["name"] for item in agents}
            self.assertIn("custom-rn-expert", names,
                          "custom agent must be preserved across sdd re-run")

    def test_harness_init_no_args_installs_sdd_scaffolding(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            result = subprocess.run(
                ["python3", str(SCRIPT), "init"],
                cwd=str(project),
                check=False, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((project / "scripts" / "init.sh").exists())
            self.assertTrue((project / "feature_list.json").exists())
            self.assertTrue((project / ".harness" / "agents" / "leader.md").exists())
            self.assertTrue((project / "CLAUDE.md").exists())

    def test_adapter_block_instructs_inspect_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            self.run_harness(
                "run", "--project", str(project),
                "--task", "fix failing login test",
            )
            claude = (project / "CLAUDE.md").read_text(encoding="utf-8")
            self.assertIn("harness inspect --project . --task", claude)
            self.assertIn("mandatory if installed", claude)
            # The inspect command must appear before any "Default fallback" line
            inspect_idx = claude.index("harness inspect --project . --task")
            fallback_idx = claude.index("Default fallback")
            self.assertLess(inspect_idx, fallback_idx)

    def test_detect_all_llms_injects_into_cursorrules(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".cursorrules").write_text(
                "# My Cursor Rules\n\nUse 2-space indent.\n", encoding="utf-8"
            )
            result = self.run_harness(
                "run", "--project", str(project),
                "--task", "fix failing login test",
                "--detect-all-llms",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            content = (project / ".cursorrules").read_text(encoding="utf-8")
            self.assertIn("BEGIN HARNESS_MANAGED", content)
            self.assertIn("Use 2-space indent.", content)
            # User content must survive; harness block at top after H1
            self.assertTrue(
                content.index("BEGIN HARNESS_MANAGED") < content.index("Use 2-space indent.")
            )

    def test_registry_add_with_positional_and_auto_triggers(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".harness").mkdir()
            (project / ".harness" / "agents.json").write_text("[]\n")
            result = self.run_harness(
                "agent", "add",
                "rn-expert", "agent:rn-expert",
                "--project", str(project),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            registry = json.loads(
                (project / ".harness" / "agents.json").read_text(encoding="utf-8")
            )
            entry = next(e for e in registry if e["name"] == "rn-expert")
            self.assertEqual(entry["path"], "agent:rn-expert")
            self.assertIn("rn", entry["triggers"])
            self.assertIn("expert", entry["triggers"])

    def test_version_flag_reports_semver_and_runtime_info(self):
        result = self.run_harness("--version")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("harness 0.1.0", result.stdout)
        self.assertIn("Python:", result.stdout)
        self.assertIn("Runtime:", result.stdout)
        self.assertIn("Config dir:", result.stdout)
        # Short flag equivalent
        result_short = self.run_harness("-V")
        self.assertEqual(result_short.returncode, 0, result_short.stderr)
        self.assertIn("harness 0.1.0", result_short.stdout)

    def test_no_framework_specific_default_triggers(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            self.run_harness(
                "run", "--project", str(project),
                "--task", "design and implement a new module with specs",
                "--adapters", "none",
            )
            agents = json.loads(
                (project / ".harness" / "agents.json").read_text(encoding="utf-8")
            )
            for entry in agents:
                trigs = set(entry["triggers"])
                self.assertFalse(
                    trigs & {"flutter_contract", "rust_api", "reactive_notifier", "dart"},
                    f"framework-specific trigger leaked in default agent {entry['name']}: {trigs}"
                )


if __name__ == "__main__":
    unittest.main()
