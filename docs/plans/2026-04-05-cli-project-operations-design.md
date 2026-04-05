# CLI Project Operations Design

**Date:** 2026-04-05

## Goal

Add a CLI-first operational surface for working with Laravel enterprise projects and SDK client packages so users can:
- register and switch projects
- work at app or package scope
- ingest and refresh project knowledge / ChromaDB entries
- detect gaps between module logic and SDK implementation
- review and resolve inconsistencies
- report bugs and missing SDK capabilities

The CLI is the first delivery target. The internal logic should be reusable later by an HTTP API without redesigning the execution model.

## Problem

The repo already contains pieces of project/session state and review state:
- `project_session.py`
- `project_contract.py`
- `memory_review.py`
- `chat.py`

But these are exposed only through low-level helpers and ad hoc chat commands. There is no stable operational interface for:
- listing and selecting projects
- working at app level vs package level
- running ingestion against the active scope
- identifying what app/module logic expects but the SDK package does not implement
- recording and resolving repair workflows

That makes the tool hard to use as a repeatable operational system.

## Source Of Truth

The system should use these truths in order:

1. Project contract
- defines project identity, roots, type metadata, and package discovery boundaries

2. Scope inventory
- defines whether operations run at app level or package level

3. Code analysis
- app/module logic defines expected service capabilities
- SDK package code defines implemented capabilities

4. Review/report state
- findings are persisted as structured records under the active project reports directory

5. Chroma knowledge state
- derived from the contract, knowledge files, findings, and generated analysis artifacts

## Operating Model

### Project

A project is the root operational unit. For this use case, the project is typically a Laravel application repository that may contain one or more SDK client packages under `packages/`.

### Scope

Each command operates against a scope:
- `app`
- `package:<name>`

`app` scope gives an overview across module logic and package implementations.
`package:<name>` scope focuses on one SDK package such as `svgate-sdk`.

### Main Detection Rule

For app-level overview, “not implemented yet” is detected primarily by comparing:
- expected service behavior inferred from app/module logic
against
- implemented SDK capabilities inferred from package code

This means the main gap detector is:
- module/app intent vs SDK implementation

Service API documents remain useful supporting inputs, especially for SDK-focused work, but they are not the primary truth for app-level missing implementation detection.

## Contract Shape

The project contract should be extended to support scoped analysis and SDK-oriented inputs.

Example:

```json
{
  "name": "laravel-enterprise-app",
  "root": "/path/to/app",
  "project_type": "laravel-app",
  "knowledge_dir": "/path/to/app/knowledge",
  "reports_dir": "/path/to/app/reports",
  "package_roots": [
    "/path/to/app/packages"
  ],
  "service_docs": [
    "/path/to/docs/svgate-api.pdf",
    "/path/to/docs/svgate-errors.docx",
    "/path/to/docs/svgate-notes.md"
  ],
  "architecture": {}
}
```

### Required Fields
- `name`
- `root`
- `knowledge_dir`
- `reports_dir`

### New Fields
- `project_type`
- `package_roots`
- `service_docs`

## CLI Surface

The CLI should be a dedicated entrypoint separate from the chat loop.

Suggested entrypoint:
- `python cli.py ...`

### Project Commands
- `project list`
- `project add --name <name> --contract <path>`
- `project use <name>`
- `project current`

### Scope Commands
- `scope list`
- `scope use app`
- `scope use package <name>`
- `scope current`

### Ingest Commands
- `ingest run`
- `ingest run --scope app`
- `ingest run --scope package:<name>`
- `ingest status`

### Analysis Commands
- `analyze gaps --scope app`
- `analyze gaps --scope package:<name>`
- `analyze capabilities --scope app`
- `analyze capabilities --scope package:<name>`

### Review Commands
- `review list`
- `review list --scope app`
- `review list --scope package:<name>`
- `review resolve <id> --action update-memory`
- `review resolve <id> --action fix-inconsistency`

### Reporting Commands
- `report bug --scope <scope> --title <title> --details <details>`
- `report missing-sdk --scope <scope> --title <title> --details <details>`

## Internal Architecture

The CLI should stay thin. Shared services should hold the business logic so the future HTTP API can call the same code.

### Proposed Services

#### `project_registry_service`
Responsibilities:
- list registered projects
- add/register a project
- set active project
- return current project

Backed by:
- `projects.json`
- `.active_project`

#### `scope_service`
Responsibilities:
- discover packages from the active project
- list valid scopes
- set active scope
- return current scope

State:
- active scope should be persisted separately from active project

#### `ingest_service`
Responsibilities:
- enumerate relevant knowledge/doc/code inputs for a scope
- refresh Chroma entries for the active project and scope
- write generated artifacts needed for later chat/review use

#### `capability_inventory_service`
Responsibilities:
- infer expected capabilities from app/module logic
- infer implemented capabilities from SDK package code
- optionally ingest supporting service-doc capabilities for SDK-focused analysis

Outputs:
- structured capability inventory

#### `gap_analysis_service`
Responsibilities:
- diff expected capabilities vs implemented capabilities
- emit findings such as:
  - `missing_sdk_client`
  - `missing_sdk_operation`
  - `inconsistency`

#### `review_service`
Responsibilities:
- list open findings
- resolve findings
- persist resolution state

Extends existing `memory_review.py` behavior from chat-only to CLI-safe structured use

#### `report_service`
Responsibilities:
- create bug reports
- create missing SDK reports
- normalize all findings into one persisted schema

## Data Model

All findings should be stored as structured items under the project reports directory.

Suggested normalized record:

```json
{
  "id": 12,
  "kind": "missing_sdk_operation",
  "scope": "package:svgate-sdk",
  "title": "Refund API missing in SDK",
  "details": "Module payment reversal flow expects refund creation but svgate-sdk has no refund client.",
  "source": "gap_analysis",
  "status": "open"
}
```

### Supported `kind`
- `gap`
- `inconsistency`
- `missing_sdk_client`
- `missing_sdk_operation`
- `bug_report`

### Supported `status`
- `open`
- `update_memory`
- `fix_inconsistency`
- `accepted`
- `closed`

## Detection Strategy

### App Scope

Input:
- Laravel app/module logic
- discovered SDK packages

Behavior:
- infer expected service operations from module/application code paths
- infer implemented operations from package SDK code
- compute diff

Primary outcome:
- what module logic expects that the SDK does not implement yet

### Package Scope

Input:
- one SDK package
- optional service docs for that service

Behavior:
- inspect package clients, DTOs, actions, transports, and exposed entrypoints
- optionally compare package implementation to service docs for SDK-only work

Primary outcome:
- what the package implements
- what the package appears to be missing

## Chroma Integration

Chroma should not only contain static knowledge markdown. It should also contain generated operational knowledge.

The following should be ingestable:
- project profile
- package inventory
- gap analysis summaries
- open review/report items
- service-doc derived notes for SDK packages

This allows the chat layer and future API to answer questions such as:
- what package is active
- what gaps exist for `svgate-sdk`
- which missing SDK operations are still unresolved

## Error Handling

The CLI should fail explicitly for:
- missing active project
- invalid contract path
- invalid scope
- unknown package name
- unsupported document type
- ingestion errors

Expected behavior:
- clear user-facing error
- non-zero exit code
- optional persisted bug report when appropriate

## Testing Strategy

The first implementation should be hermetic by default.

### Unit/CLI Tests
- temporary contracts
- temporary project registry
- temporary active scope state
- fake capability inventory inputs
- temporary reports directory
- temporary Chroma storage

### Integration Tests
- optional, explicitly marked
- real package discovery from fixture trees
- optional service-doc parsing for `.pdf`, `.docx`, `.md`

## Incremental Delivery

### Slice 1
- `project list|add|use|current`
- `scope list|use|current`
- contract extension for package roots / project type

### Slice 2
- `ingest run`
- `review list|resolve`
- normalized report persistence

### Slice 3
- `analyze gaps --scope app|package:<name>`
- capability inventory and diff logic

### Slice 4
- `report bug`
- `report missing-sdk`
- generated findings ingestion into Chroma

## Future HTTP API

The future HTTP API should wrap the same services, not reimplement behavior.

Likely endpoints later:
- `GET /projects`
- `POST /projects`
- `POST /projects/active`
- `GET /scopes`
- `POST /scopes/active`
- `POST /ingest`
- `POST /analyze/gaps`
- `GET /reviews`
- `POST /reviews/{id}/resolve`
- `POST /reports/bug`
- `POST /reports/missing-sdk`

## Recommendation

Implement `CLI first, HTTP API later` with a reusable service layer and scope-aware analysis.

The first useful CLI should ship:
- project management
- scope management
- gap analysis
- review resolution

That gives a real operational workflow immediately while keeping the path to HTTP clean.
