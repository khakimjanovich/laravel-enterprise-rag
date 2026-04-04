import json
import os

PROJECTS_REGISTRY = "projects.json"
ACTIVE_PROJECT_FILE = ".active_project"


def load_projects() -> dict:
    if os.path.exists(PROJECTS_REGISTRY):
        with open(PROJECTS_REGISTRY, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"projects": {}}


def save_projects(data: dict) -> None:
    with open(PROJECTS_REGISTRY, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def register_project(name: str, contract_path: str) -> None:
    data = load_projects()
    data["projects"][name] = contract_path
    save_projects(data)


def set_active_project(name: str) -> bool:
    data = load_projects()
    contract_path = data["projects"].get(name)

    if not contract_path:
        return False

    with open(ACTIVE_PROJECT_FILE, "w", encoding="utf-8") as f:
        f.write(contract_path)

    return True


def get_active_project_file() -> str | None:
    if not os.path.exists(ACTIVE_PROJECT_FILE):
        return None

    with open(ACTIVE_PROJECT_FILE, "r", encoding="utf-8") as f:
        return f.read().strip() or None