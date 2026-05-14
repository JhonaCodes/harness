"""Workflow decision service."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .capabilities import CapabilityRegistry
from .inspection import RepositoryInspector, WorkflowClassifier
from .models import Decision


class WorkflowDecider:
    def __init__(
        self,
        inspector: RepositoryInspector | None = None,
        classifier: WorkflowClassifier | None = None,
    ) -> None:
        self.inspector = inspector or RepositoryInspector()
        self.classifier = classifier or WorkflowClassifier()

    def decide(self, root: Path, repo: str | None, profile: str, task: str, workflow: str, global_skills: Path) -> Decision:
        context = self.inspector.inspect(root, repo, profile)
        selected_workflow, reason = self.classifier.classify(task, context, workflow)
        capabilities = CapabilityRegistry(global_skills).select_all(task, context)
        skills = capabilities["skill"]
        commands = [
            f"python3 scripts/harness.py run --project {json.dumps(str(root))} --task {json.dumps(task)} --workflow {selected_workflow} --dry-run",
        ]
        if selected_workflow != "simple":
            commands.append("./init.sh")
        return Decision(
            workflow=selected_workflow,
            profile=profile,
            reason=reason,
            selected_skills=[asdict(skill) for skill in skills],
            selected_capabilities={kind: [asdict(item) for item in items] for kind, items in capabilities.items()},
            will_install_files=selected_workflow != "simple",
            project_root=str(root),
            repo=repo,
            commands=commands,
        )

