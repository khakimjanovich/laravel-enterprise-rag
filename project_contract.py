from dataclasses import dataclass
from pathlib import Path
import json
import os


@dataclass(slots=True)
class ProjectContract:
    name: str
    root: str
    knowledge_dir: str
    reports_dir: str
    architecture: dict

    @classmethod
    def from_file(cls, path: str = None) -> "ProjectContract":
        path = path or os.getenv("LER_PROJECT_FILE", "project.contract.json")
        architecture=data.get("architecture", {}),

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return cls(
            name=data["name"],
            root=data["root"],
            knowledge_dir=data["knowledge_dir"],
            reports_dir=data["reports_dir"],
        )

    def knowledge_path(self) -> Path:
        return Path(self.knowledge_dir)

    def reports_path(self) -> Path:
        return Path(self.reports_dir)