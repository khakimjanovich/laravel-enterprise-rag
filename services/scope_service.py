from pathlib import Path

from project_contract import ProjectContract
from project_session import get_active_scope, set_active_scope


def list_scopes(contract: ProjectContract) -> list[str]:
    scopes = ["app"]
    package_names: set[str] = set()

    for package_root in contract.package_roots:
        root = Path(package_root)
        if not root.exists():
            continue

        for child in root.iterdir():
            if child.is_dir():
                package_names.add(child.name)

    scopes.extend(f"package:{name}" for name in sorted(package_names))
    return scopes


def set_scope(scope: str, contract: ProjectContract) -> None:
    if scope not in list_scopes(contract):
        raise ValueError(f"Unknown scope: {scope}")

    set_active_scope(scope)


def current_scope(contract: ProjectContract) -> str:
    scope = get_active_scope()
    if scope and scope in list_scopes(contract):
        return scope

    return "app"
