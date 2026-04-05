import argparse

from project_contract import ProjectContract
from services.project_registry_service import add_project, current_project, list_projects, use_project
from services.scope_service import current_scope, list_scopes, set_scope


def _load_current_contract() -> ProjectContract:
    return ProjectContract.from_file()


def _handle_project_command(args: argparse.Namespace) -> int:
    if args.project_command == "list":
        for project in list_projects():
            print(f"{project['name']}: {project['contract_path']}")
        return 0

    if args.project_command == "add":
        add_project(args.name, args.contract)
        print(f"Added project {args.name}")
        return 0

    if args.project_command == "use":
        if not use_project(args.name):
            print(f"Project not found: {args.name}")
            return 1
        print(f"Using project {args.name}")
        return 0

    if args.project_command == "current":
        project = current_project()
        if project is None:
            print("No active project")
            return 1
        print(f"{project['name']}: {project['contract_path']}")
        return 0

    return 1


def _handle_scope_command(args: argparse.Namespace) -> int:
    contract = _load_current_contract()

    if args.scope_command == "list":
        for scope in list_scopes(contract):
            print(scope)
        return 0

    if args.scope_command == "use":
        selected_scope = "app" if args.scope_type == "app" else f"package:{args.package_name}"
        try:
            set_scope(selected_scope, contract)
        except ValueError as exc:
            print(str(exc))
            return 1
        print(f"Using scope {selected_scope}")
        return 0

    if args.scope_command == "current":
        print(current_scope(contract))
        return 0

    return 1


def _handle_analyze_command(args: argparse.Namespace) -> int:
    if args.analyze_command == "gaps":
        print(f"Not implemented yet analysis for scope {args.scope}")
        return 0

    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ops")
    domain_subparsers = parser.add_subparsers(dest="domain")

    for domain_name in ("ai", "project"):
        domain_parser = domain_subparsers.add_parser(domain_name)
        command_subparsers = domain_parser.add_subparsers(dest="command")

        project_parser = command_subparsers.add_parser("project")
        project_subparsers = project_parser.add_subparsers(dest="project_command")
        project_subparsers.add_parser("list")
        project_add = project_subparsers.add_parser("add")
        project_add.add_argument("--name", required=True)
        project_add.add_argument("--contract", required=True)
        project_use = project_subparsers.add_parser("use")
        project_use.add_argument("name")
        project_subparsers.add_parser("current")

        scope_parser = command_subparsers.add_parser("scope")
        scope_subparsers = scope_parser.add_subparsers(dest="scope_command")
        scope_subparsers.add_parser("list")
        scope_use = scope_subparsers.add_parser("use")
        scope_use_subparsers = scope_use.add_subparsers(dest="scope_type")
        scope_use_subparsers.add_parser("app")
        scope_use_package = scope_use_subparsers.add_parser("package")
        scope_use_package.add_argument("package_name")
        scope_subparsers.add_parser("current")

        if domain_name == "project":
            analyze_parser = command_subparsers.add_parser("analyze")
            analyze_subparsers = analyze_parser.add_subparsers(dest="analyze_command")
            analyze_gaps = analyze_subparsers.add_parser("gaps")
            analyze_gaps.add_argument("--scope", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.domain is None:
        parser.print_help()
        return 1

    if args.command == "project":
        return _handle_project_command(args)

    if args.command == "scope":
        return _handle_scope_command(args)

    if args.domain == "project" and args.command == "analyze":
        return _handle_analyze_command(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
