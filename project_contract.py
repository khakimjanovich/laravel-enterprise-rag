from dataclasses import dataclass
from pathlib import Path
import json
import os

from project_session import get_active_project_file

@dataclass(slots=True)
class ProjectContract:
    name: str
    root: str
    knowledge_dir: str
    reports_dir: str
    architecture: dict

    @classmethod
    def from_file(cls, path: str = None) -> "ProjectContract":
        explicit_path = path or os.getenv("LER_PROJECT_FILE") or get_active_project_file()

        if explicit_path:
            if not os.path.exists(explicit_path):
                raise FileNotFoundError(
                    "Project contract file not found. "
                    f"Checked: {explicit_path}. Create `project.contract.json` or set `LER_PROJECT_FILE`."
                )
            selected_path = explicit_path
        elif os.path.exists("project.contract.json"):
            selected_path = "project.contract.json"
        elif os.path.exists("project.contract.example.json"):
            selected_path = "project.contract.example.json"
        else:
            raise FileNotFoundError(
                "Project contract file not found. "
                "Checked: project.contract.json. Create `project.contract.json` or set `LER_PROJECT_FILE`."
            )

        with open(selected_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return cls(
            name=data["name"],
            root=data["root"],
            knowledge_dir=data["knowledge_dir"],
            reports_dir=data["reports_dir"],
            architecture=data.get("architecture", {}),
        )

    def knowledge_path(self) -> Path:
        return Path(self.knowledge_dir)

    def reports_path(self) -> Path:
        return Path(self.reports_dir)
