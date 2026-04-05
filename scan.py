#!/usr/bin/env python3
"""
scan.py — scans the real Laravel monorepo against confirmed conventions.

Usage:
  python scan.py                          # scan all packages
  python scan.py --package svgate-sdk    # scan one package
  python scan.py --scope sdk             # scan all SDK packages
  python scan.py --scope module          # scan all module packages
  python scan.py --ingest                # also ingest report into ChromaDB

Output:
  reports/{project}/convention-scan-{timestamp}.json
  reports/{project}/convention-scan-{timestamp}.md
"""

import argparse
import sys

from rich.console import Console
from rich.table   import Table
from rich.panel   import Panel
from rich.rule    import Rule

from project_contract           import ProjectContract
from services.convention_scanner import ConventionScanner
from services.scan_report_writer import ScanReportWriter

console = Console()


def main():
    parser = argparse.ArgumentParser(description="Scan Laravel monorepo against conventions")
    parser.add_argument("--package", help="Scan a single package by name")
    parser.add_argument("--scope",   choices=["sdk", "module", "app"], help="Scan by layer")
    parser.add_argument("--ingest",  action="store_true", help="Ingest report into ChromaDB after scan")
    args = parser.parse_args()

    # ── Load project contract ─────────────────────────────────────────────────
    try:
        project = ProjectContract.from_file()
    except Exception as e:
        console.print(f"[red]Failed to load project contract: {e}[/red]")
        console.print("[dim]Run: cp project.contract.example.json project.contract.json[/dim]")
        sys.exit(1)

    console.print(Panel(
        f"[bold cyan]Convention Scanner[/bold cyan]\n"
        f"Project: [green]{project.name}[/green]\n"
        f"Root:    [dim]{project.root}[/dim]",
        expand=False,
    ))

    # ── Run scan ──────────────────────────────────────────────────────────────
    scanner = ConventionScanner(
        project_root  = project.root,
        package_roots = project.package_roots,
    )

    with console.status("[dim]Scanning packages...[/dim]"):
        if args.package:
            report = scanner.scan_package(args.package)
        elif args.scope:
            report = scanner.scan_layer(args.scope)
        else:
            report = scanner.scan_all()

    # ── Display summary ───────────────────────────────────────────────────────
    console.print()
    console.print(Rule("[bold]Scan Results[/bold]"))
    console.print()

    table = Table(title="Package Summary")
    table.add_column("Package",  style="cyan")
    table.add_column("Layer",    style="dim")
    table.add_column("✅ Pass",   justify="right", style="green")
    table.add_column("❌ Fail",   justify="right", style="red")
    table.add_column("⚠️ Warn",   justify="right", style="yellow")
    table.add_column("🔴 Critical", justify="right", style="bold red")

    for pkg in report.packages:
        crits = len(pkg.critical_failures)
        table.add_row(
            pkg.package,
            pkg.layer,
            str(pkg.passed),
            str(pkg.failed),
            str(pkg.warnings),
            str(crits) if crits else "[dim]0[/dim]",
        )

    console.print(table)
    console.print()

    # ── Critical failures ─────────────────────────────────────────────────────
    if report.all_critical:
        console.print(Rule("[bold red]🔴 Critical Failures[/bold red]"))
        for r in report.all_critical:
            console.print(
                f"  [red]❌[/red] [bold]{r.package}[/bold] [{r.layer}] — {r.convention}"
            )
            console.print(f"     [dim]{r.evidence}[/dim]")
            if r.file:
                console.print(f"     [dim]File: {r.file}[/dim]")
        console.print()

    # ── Write report ──────────────────────────────────────────────────────────
    writer    = ScanReportWriter(project.reports_dir, project.name)
    json_path, md_path = writer.write(report)

    console.print(f"[green]✓ JSON report:[/green] [dim]{json_path}[/dim]")
    console.print(f"[green]✓ Markdown report:[/green] [dim]{md_path}[/dim]")

    # ── Ingest into ChromaDB ──────────────────────────────────────────────────
    if args.ingest:
        console.print()
        with console.status("[dim]Ingesting report into ChromaDB...[/dim]"):
            from app import get_collection, get_embedding
            content   = md_path.read_text(encoding="utf-8")
            embedding = get_embedding(content[:2000])  # embed summary portion
            if embedding:
                get_collection().upsert(
                    ids        = [f"scan:{project.name}:{json_path.stem}"],
                    embeddings = [embedding],
                    documents  = [content[:3000]],
                    metadatas  = [{
                        "type":       "convention_scan",
                        "project":    project.name,
                        "scanned_at": report.scanned_at,
                        "failed":     report.total_failed,
                        "critical":   len(report.all_critical),
                    }],
                )
                console.print("[green]✓ Report ingested into ChromaDB[/green]")
            else:
                console.print("[yellow]⚠ Embedding failed — report not ingested[/yellow]")

    # ── Exit code ─────────────────────────────────────────────────────────────
    console.print()
    if report.all_critical:
        console.print(
            f"[bold red]Scan complete — {len(report.all_critical)} critical failures. Fix before release.[/bold red]"
        )
        sys.exit(1)
    elif report.total_failed:
        console.print(
            f"[yellow]Scan complete — {report.total_failed} failures, no criticals.[/yellow]"
        )
        sys.exit(0)
    else:
        console.print("[bold green]Scan complete — all conventions passed.[/bold green]")
        sys.exit(0)


if __name__ == "__main__":
    main()