"""Argparse CLI assembly and command dispatch."""

from __future__ import annotations

import argparse
import platform
import sys
from pathlib import Path

from .commands import HarnessCommands
from .constants import DEFAULT_CONFIG_DIR, DEFAULT_GLOBAL_SKILLS, DEFAULT_PROJECT_MAP, __version__


def _version_text() -> str:
    runtime_dir = Path(__file__).resolve().parents[2]
    bin_path = Path("~/.local/bin/harness").expanduser()
    bin_status = str(bin_path) if bin_path.exists() else f"{bin_path} (not installed)"
    return (
        f"harness {__version__}\n"
        f"  Python:       {platform.python_version()} ({sys.executable})\n"
        f"  Platform:     {platform.system()} {platform.release()} ({platform.machine()})\n"
        f"  Runtime:      {runtime_dir}\n"
        f"  Global CLI:   {bin_status}\n"
        f"  Config dir:   {DEFAULT_CONFIG_DIR}\n"
        f"  Project map:  {DEFAULT_PROJECT_MAP}\n"
        f"  Global reg:   {DEFAULT_GLOBAL_SKILLS}"
    )


class HarnessCli:
    def __init__(self, commands: HarnessCommands | None = None) -> None:
        self.commands = commands or HarnessCommands()

    def build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(description="Harness runtime for simple, TDD, and SDD workflows.")
        parser.add_argument("--version", "-V", action="version", version=_version_text())
        parser.add_argument("--project-map", default=str(DEFAULT_PROJECT_MAP), help="Alias map JSON. Default: ~/.harness/projects.json")
        parser.add_argument("--global-skills", default=str(DEFAULT_GLOBAL_SKILLS), help="Global skills registry JSON. Default: ~/.harness/skills.json")
        sub = parser.add_subparsers(dest="command", required=True)

        def add_config(p: argparse.ArgumentParser) -> None:
            p.add_argument("--project-map", default=str(DEFAULT_PROJECT_MAP), help="Alias map JSON. Default: ~/.harness/projects.json")
            p.add_argument("--global-skills", default=str(DEFAULT_GLOBAL_SKILLS), help="Global skills registry JSON. Default: ~/.harness/skills.json")

        def add_common(p: argparse.ArgumentParser) -> None:
            add_config(p)
            p.add_argument("--project", help="Local path, alias, GitHub owner/name, or GitHub URL")
            p.add_argument("--task", required=True, help="Natural-language task to evaluate")
            p.add_argument("--checkout-root", default="~/Projects", help="Where to clone GitHub repos when --project is remote")
            p.add_argument("--workflow", choices=["auto", "simple", "tdd", "sdd"], default="auto")
            p.add_argument("--profile", choices=["auto", "rust", "flutter", "python", "node", "generic"], default="auto")

        run = sub.add_parser("run", help="Inspect, decide, select skills, and apply the selected workflow.")
        add_common(run)
        run.add_argument("--adapters", default="all", help="Adapter set to install: all, none, or comma-separated names such as agents,claude,gemini")
        run.add_argument("--detect-all-llms", action="store_true", help="Also inject Harness block into Cursor/Windsurf/Junie/Roo rules files when present.")
        run.add_argument("--dry-run", action="store_true")

        inspect_cmd = sub.add_parser("inspect", help="Inspect and decide without applying files.")
        add_common(inspect_cmd)

        init_cmd = sub.add_parser("init", help="Initialize Harness in the current project (shortcut for `run --project . --workflow sdd`).")
        add_config(init_cmd)
        init_cmd.add_argument("--workflow", choices=["auto", "simple", "tdd", "sdd"], default="sdd",
                              help="Workflow scaffolding to install. Default: sdd (superset includes tdd).")
        init_cmd.add_argument("--profile", choices=["auto", "rust", "flutter", "python", "node", "generic"], default="auto")
        init_cmd.add_argument("--adapters", default="all")
        init_cmd.add_argument("--detect-all-llms", action="store_true", help="Also inject Harness block into Cursor/Windsurf/Junie/Roo rules files when present.")
        init_cmd.add_argument("--dry-run", action="store_true")
        init_cmd.add_argument("--task", default="prepare this project with harness",
                              help="Optional task description used by the workflow classifier.")
        init_cmd.add_argument("--checkout-root", default="~/Projects")

        register = sub.add_parser("register", help="Register a user-local project alias.")
        add_config(register)
        register.add_argument("--alias", required=True)
        register.add_argument("--path", required=True)

        def add_registry_command(command_name: str, singular: str, plural: str, require_context: bool = False) -> None:
            registry = sub.add_parser(command_name, help=f"Manage project {singular} registry.")
            registry_sub = registry.add_subparsers(dest=f"{singular}_command", required=True)
            registry_add = registry_sub.add_parser("add", help=f"Add or replace a project {singular}. Positional: NAME [PATH].")
            add_config(registry_add)
            registry_add.add_argument("name_pos", nargs="?", help="Name (positional). Use --name to override.")
            registry_add.add_argument("path_pos", nargs="?", help="Path (positional). Accepts short-forms: agent:<name>, mcp:<server>, /slash-command, or filesystem path. Use --path to override.")
            registry_add.add_argument("--project", default=".", help="Project path or alias. Default: current directory.")
            registry_add.add_argument("--checkout-root", default="~/Projects")
            registry_add.add_argument("--name", default=None)
            registry_add.add_argument("--triggers", default=None, help="Comma-separated trigger terms. If omitted, derived from name.")
            registry_add.add_argument("--path", default=None)
            registry_add.add_argument("--description", default="")
            registry_add.add_argument("--context", default="", help="Explicit context for when and why an LLM should use this entry")
            registry_add.set_defaults(_require_context=require_context)
            registry_list = registry_sub.add_parser("list", help=f"List project {plural}.")
            add_config(registry_list)
            registry_list.add_argument("--project", default=".")
            registry_list.add_argument("--checkout-root", default="~/Projects")

        add_registry_command("skill", "skill", "skills")
        add_registry_command("agent", "agent", "agents")
        add_registry_command("doc", "doc", "docs")
        add_registry_command("rule", "rule", "rules")
        add_registry_command("mcp", "mcp", "mcps", require_context=True)

        import_cmd = sub.add_parser("import", help="Bulk import skills/agents/docs/rules/mcps from a YAML or JSON file.")
        add_config(import_cmd)
        import_cmd.add_argument("file", help="Path to a YAML or JSON file containing a list of entries.")
        import_cmd.add_argument("--project", default=".")
        import_cmd.add_argument("--checkout-root", default="~/Projects")

        memory = sub.add_parser("memory", help="Manage project harness memory.")
        memory_sub = memory.add_subparsers(dest="memory_command", required=True)
        memory_add = memory_sub.add_parser("add", help="Add or replace a memory entry.")
        add_config(memory_add)
        memory_add.add_argument("--project", required=True)
        memory_add.add_argument("--checkout-root", default="~/Projects")
        memory_add.add_argument("--key", required=True)
        memory_add.add_argument("--value", required=True)
        memory_list = memory_sub.add_parser("list", help="List project memory.")
        add_config(memory_list)
        memory_list.add_argument("--project", required=True)
        memory_list.add_argument("--checkout-root", default="~/Projects")

        return parser

    def dispatch(self, args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
        if args.command == "register":
            return self.commands.register(args)
        if args.command == "inspect":
            return self.commands.inspect(args)
        if args.command == "init":
            args.project = "."
            return self.commands.run(args)
        if args.command == "run":
            return self.commands.run(args)
        if args.command in {"skill", "agent", "doc", "rule", "mcp"}:
            subcommand = getattr(args, f"{args.command}_command")
            if subcommand == "add":
                return self.commands.registry_add(args, args.command)
            if subcommand == "list":
                return self.commands.registry_list(args, args.command)
        if args.command == "import":
            return self.commands.bulk_import(args)
        if args.command == "memory":
            if args.memory_command == "add":
                return self.commands.memory_add(args)
            if args.memory_command == "list":
                return self.commands.memory_list(args)
        parser.error(f"Unknown command: {args.command}")
        return 2

    def main(self) -> int:
        parser = self.build_parser()
        args = parser.parse_args()
        return self.dispatch(args, parser)


def main() -> int:
    return HarnessCli().main()
