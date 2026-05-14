"""Argparse CLI assembly and command dispatch."""

from __future__ import annotations

import argparse

from .commands import HarnessCommands
from .constants import DEFAULT_GLOBAL_SKILLS, DEFAULT_PROJECT_MAP


class HarnessCli:
    def __init__(self, commands: HarnessCommands | None = None) -> None:
        self.commands = commands or HarnessCommands()

    def build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(description="Harness runtime for simple, TDD, and SDD workflows.")
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
        run.add_argument("--dry-run", action="store_true")

        inspect_cmd = sub.add_parser("inspect", help="Inspect and decide without applying files.")
        add_common(inspect_cmd)

        register = sub.add_parser("register", help="Register a user-local project alias.")
        add_config(register)
        register.add_argument("--alias", required=True)
        register.add_argument("--path", required=True)

        skill = sub.add_parser("skill", help="Manage project skill registry.")
        skill_sub = skill.add_subparsers(dest="skill_command", required=True)
        skill_add = skill_sub.add_parser("add", help="Add or replace a project skill.")
        add_config(skill_add)
        skill_add.add_argument("--project", required=True)
        skill_add.add_argument("--checkout-root", default="~/Projects")
        skill_add.add_argument("--name", required=True)
        skill_add.add_argument("--triggers", required=True, help="Comma-separated trigger terms")
        skill_add.add_argument("--path", required=True)
        skill_add.add_argument("--description", default="")
        skill_list = skill_sub.add_parser("list", help="List project skills.")
        add_config(skill_list)
        skill_list.add_argument("--project", required=True)
        skill_list.add_argument("--checkout-root", default="~/Projects")

        def add_registry_command(command_name: str, singular: str, plural: str, require_context: bool = False) -> None:
            registry = sub.add_parser(command_name, help=f"Manage project {singular} registry.")
            registry_sub = registry.add_subparsers(dest=f"{singular}_command", required=True)
            registry_add = registry_sub.add_parser("add", help=f"Add or replace a project {singular}.")
            add_config(registry_add)
            registry_add.add_argument("--project", required=True)
            registry_add.add_argument("--checkout-root", default="~/Projects")
            registry_add.add_argument("--name", required=True)
            registry_add.add_argument("--triggers", required=True, help="Comma-separated trigger terms")
            registry_add.add_argument("--path", required=True)
            registry_add.add_argument("--description", default="")
            registry_add.add_argument("--context", required=require_context, default="", help="Explicit context for when and why an LLM should use this entry")
            registry_list = registry_sub.add_parser("list", help=f"List project {plural}.")
            add_config(registry_list)
            registry_list.add_argument("--project", required=True)
            registry_list.add_argument("--checkout-root", default="~/Projects")

        add_registry_command("agent", "agent", "agents")
        add_registry_command("doc", "doc", "docs")
        add_registry_command("rule", "rule", "rules")
        add_registry_command("mcp", "mcp", "mcps", require_context=True)

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
        if args.command == "run":
            return self.commands.run(args)
        if args.command == "skill":
            if args.skill_command == "add":
                return self.commands.registry_add(args, "skill")
            if args.skill_command == "list":
                return self.commands.registry_list(args, "skill")
        if args.command in {"agent", "doc", "rule", "mcp"}:
            subcommand = getattr(args, f"{args.command}_command")
            if subcommand == "add":
                return self.commands.registry_add(args, args.command)
            if subcommand == "list":
                return self.commands.registry_list(args, args.command)
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
