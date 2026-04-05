from project_session import get_active_project_file, load_projects, register_project, set_active_project


def list_projects() -> list[dict]:
    projects = load_projects()["projects"]
    return [
        {"name": name, "contract_path": contract_path}
        for name, contract_path in sorted(projects.items())
    ]


def add_project(name: str, contract_path: str) -> None:
    register_project(name, contract_path)


def use_project(name: str) -> bool:
    return set_active_project(name)


def current_project() -> dict | None:
    active_path = get_active_project_file()
    if active_path is None:
        return None

    for project in list_projects():
        if project["contract_path"] == active_path:
            return project

    return {"name": None, "contract_path": active_path}
