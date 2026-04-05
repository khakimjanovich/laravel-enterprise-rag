# Hybrid Ops CLI Design

**Date:** 2026-04-05

## Goal

Design a hybrid CLI that supports both:
- interactive shell usage for humans
- scriptable subcommands for automation

The CLI must be separated by domain:
- `ai` domain: improve the AI’s project understanding and operational memory
- `project` domain: improve the target project itself

The UX target is closer to an operator shell than a plain command parser, while remaining fully scriptable.

## Core Idea

One executable, two domains, one shared context.

The CLI should feel stateful and guided in interactive mode, but expose the same operations through deterministic subcommands.

## Domains

### `ai` Domain

Purpose:
- make the AI better at working on the active project

Responsibilities:
- project registration and switching
- scope selection
- Chroma ingestion and refresh
- knowledge/review visibility
- inconsistency tracking
- missing SDK tracking as operational memory
- bug reporting as structured context for future AI work

Examples:
- `ops ai project list`
- `ops ai ingest run`
- `ops ai review list`
- `ops ai report bug ...`

### `project` Domain

Purpose:
- make the actual codebase better

Responsibilities:
- capability analysis
- module-vs-SDK gap detection
- package-focused missing implementation analysis
- fix-oriented reports
- “not implemented yet” detection from app/module intent vs SDK implementation

Examples:
- `ops project analyze gaps --scope app`
- `ops project analyze gaps --scope package:svgate-sdk`
- `ops project capabilities --scope package:svgate-sdk`

## Shared Context

Both domains should share:
- active project
- active scope

Prompt examples:
- `[ai | billing-app | package:svgate-sdk] >`
- `[project | billing-app | app] >`

This allows the user to switch domains without losing the current project/scope context.

## Interaction Model

### Interactive Shell

Entry:
- `ops`

Interactive features:
- persistent prompt with domain/project/scope
- slash commands
- concise summaries
- predictable command syntax
- guided workflows for high-frequency operations

Example shell commands:
- `/domain ai`
- `/domain project`
- `/project list`
- `/project use billing-app`
- `/scope use app`
- `/scope use package svgate-sdk`
- `/ingest`
- `/review`
- `/analyze gaps`
- `/help`

### Scriptable Commands

Entry:
- `ops ai ...`
- `ops project ...`

Requirements:
- machine-readable success/failure
- explicit non-zero exit codes on failure
- stable text output
- future option for JSON output without redesign

## Scope Model

Supported scopes:
- `app`
- `package:<name>`

### `app`

Use for:
- cross-module project overview
- what the application expects but packages do not implement yet

### `package:<name>`

Use for:
- one SDK client package
- package-specific capability and gap analysis

## Detection Rule

For project-domain app overview, missing implementation should be detected primarily by comparing:
- expected service capabilities inferred from app/module logic
against
- implemented capabilities inferred from SDK package code

This means app-level “not implemented yet” is derived from:
- module/app intent vs SDK implementation

Service API docs remain useful supporting inputs, especially for SDK package analysis, but are not the primary source for app-level implementation gaps.

## Command Surface

### Shared Commands

Available in both shell and scriptable form:
- project list
- project add
- project use
- project current
- scope list
- scope use
- scope current

### `ai` Domain Commands

- `project list`
- `project add --name <name> --contract <path>`
- `project use <name>`
- `project current`
- `scope list`
- `scope use app`
- `scope use package <name>`
- `scope current`
- `ingest run`
- `ingest status`
- `review list`
- `review resolve <id> --action update-memory|fix-inconsistency`
- `report bug --scope <scope> --title <title> --details <details>`
- `report missing-sdk --scope <scope> --title <title> --details <details>`

### `project` Domain Commands

- `analyze gaps --scope app`
- `analyze gaps --scope package:<name>`
- `analyze capabilities --scope app`
- `analyze capabilities --scope package:<name>`
- `review list --scope <scope>`
- `review resolve <id> --action <action>`
- `report bug --scope <scope> --title <title> --details <details>`
- `report missing-sdk --scope <scope> --title <title> --details <details>`

## UX Rules

### Interactive Mode

- favor short, stateful output
- show active context in every prompt
- preview destructive or broad operations
- keep defaults aligned with active project and active scope

### Scriptable Mode

- no hidden prompt behavior
- require explicit arguments when context is ambiguous
- exit non-zero for invalid domain, project, scope, or operation

## Internal Architecture

Keep one service layer and multiple frontends.

### Frontends
- interactive shell frontend
- scriptable command frontend

### Shared Services
- `project_registry_service`
- `scope_service`
- `ingest_service`
- `review_service`
- `report_service`
- `capability_inventory_service`
- `gap_analysis_service`

## Data Model

All findings should include:
- `id`
- `kind`
- `scope`
- `title`
- `details`
- `source`
- `status`

Supported `kind`:
- `gap`
- `inconsistency`
- `missing_sdk_client`
- `missing_sdk_operation`
- `bug_report`

## Delivery Strategy

### Phase 1
- scriptable shared commands
- project and scope context management

### Phase 2
- interactive shell with domain switching
- `ai` domain ingestion/review/report flows

### Phase 3
- `project` domain capability and gap analysis flows

### Phase 4
- polish shell UX, summaries, and guided workflows

## Recommendation

Build one `ops` executable with:
- shared context
- two top-level domains: `ai` and `project`
- full support for both shell and subcommands

This gives a domain-separated operator UX now and keeps the future HTTP API clean because it can wrap the same shared services.
