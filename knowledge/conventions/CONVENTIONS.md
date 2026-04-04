# Conventions Registry
chunk_id: conventions-registry-001
layer: all
type: conventions
retrieval_tags: [conventions, rules, confirmed, observed, proposed, standards]

---

## How To Use This File

This file is the single source of truth for all project conventions.

Before the model writes any convention into generated code or docs, it must
check this file. A convention that does not appear here must not be treated
as established project history.

Status labels:
- `confirmed`  — implemented in code AND documented. Treat as law.
- `observed`   — implemented in code, not yet formally documented. Treat as current truth.
- `proposed`   — not yet implemented. Treat as a proposal, not history.
- `deprecated` — was confirmed, now being removed. Do not use in new code.

---

## Monorepo Layout

| Convention                                              | Status    |
|---------------------------------------------------------|-----------|
| SDK packages live in `packages/service-{name}-sdk/`    | confirmed |
| Module packages live in `packages/module-{name}/`      | confirmed |
| Laravel app lives in `app/`                             | confirmed |
| Each package has its own `composer.json`                | confirmed |
| Path repositories used for local package resolution     | confirmed |

---

## SDK Package Conventions

| Convention                                                        | Status    |
|-------------------------------------------------------------------|-----------|
| One public entrypoint class per SDK (`Service{Name}.php`)         | confirmed |
| Interfaces live in `src/Contracts/`                               | confirmed |
| DTOs live in `src/Data/Requests/` and `src/Data/Responses/`       | confirmed |
| Config value objects live in `src/Configs/`                       | confirmed |
| Internal callers live in `src/Internal/Callers/`                  | confirmed |
| Exception hierarchy rooted at abstract `SdkException`             | confirmed |
| SDK has zero `illuminate/*` dependencies                          | confirmed |
| PSR-3 logger injected via `LoggerInterface` (extends psr/log)     | confirmed |
| HTTP client injected via `HttpClientInterface`                     | confirmed |
| Events dispatched via `EventDispatcherInterface`                  | confirmed |
| Config constructed via `fromArray(array $config): self`           | confirmed |
| No ServiceProvider, Facade, or container binding in SDK           | confirmed |
| No `config()`, `app()`, `Log::` helper calls in SDK               | confirmed |

---

## Module Package Conventions

| Convention                                                        | Status    |
|-------------------------------------------------------------------|-----------|
| Module wires SDK interfaces in `src/Adapters/`                    | confirmed |
| `TelescopeHttpClient` implements `HttpClientInterface`            | confirmed |
| `TelescopeHttpClient` uses `Illuminate\Http\Client\Factory`       | confirmed |
| `LaravelEventDispatcher` implements `EventDispatcherInterface`    | confirmed |
| Module service provider registers all bindings                    | confirmed |
| Module owns its migrations in `database/migrations/`             | confirmed |
| Domain events live in `src/Events/`                               | confirmed |
| Listeners live in `src/Listeners/`                                | confirmed |
| Artisan commands live in `src/Commands/`                          | confirmed |
| Filament resources live in `src/Filament/`                        | confirmed |
| Eloquent models live in `src/Models/`                             | confirmed |
| Business actions live in `src/Actions/`                           | confirmed |
| Module exception hierarchy rooted at abstract `ModuleException`   | confirmed |

---

## Exception Conventions

| Convention                                                         | Status    |
|--------------------------------------------------------------------|-----------|
| Every exception carries `correlationId`                            | confirmed |
| Every exception carries `operation` name                           | confirmed |
| Every exception carries `layer` tag (sdk/adapter/module)           | confirmed |
| SDK exceptions never extend module exceptions                      | confirmed |
| Module exceptions never extend SDK exceptions                      | confirmed |
| `ProviderException` carries `providerCode` and `safeBusinessId`    | confirmed |
| Exception messages are safe for logs (no secrets, no PANs)        | confirmed |
| Multi-layer failures use `previous` chain                         | confirmed |

---

## Logging Conventions

| Convention                                                         | Status    |
|--------------------------------------------------------------------|-----------|
| Every log entry carries `layer` field                              | confirmed |
| Every log entry carries `correlationId`                            | confirmed |
| Every log entry carries `operation` name                           | confirmed |
| Secrets and sensitive identifiers are redacted before logging      | confirmed |
| `safeBusinessId` used instead of raw identifiers                  | confirmed |
| SDK uses injected PSR-3 logger only                               | confirmed |
| Module uses Laravel `Log::` facade or injected logger             | confirmed |

---

## Correlation ID Conventions

| Convention                                                         | Status    |
|--------------------------------------------------------------------|-----------|
| `correlationId` generated once at request/job boundary            | confirmed |
| `correlationId` is a UUID                                         | confirmed |
| `correlationId` propagated through all layers                     | confirmed |
| `correlationId` never generated inside SDK — only propagated      | confirmed |
| `correlationId` registered in Laravel container as singleton      | proposed  |

---

## DTO Conventions

| Convention                                                         | Status    |
|--------------------------------------------------------------------|-----------|
| Request DTOs are readonly classes                                  | confirmed |
| Response DTOs are readonly classes                                 | confirmed |
| DTOs use `fromArray(array $data): self` for hydration             | confirmed |
| DTOs use `toArray(): array` for serialization                     | confirmed |
| DTOs never extend each other across SDK/module boundary            | confirmed |
| Module DTOs and SDK DTOs are separate classes                     | confirmed |

---

## Telescope Conventions

| Convention                                                         | Status    |
|--------------------------------------------------------------------|-----------|
| All outbound HTTP from SDK must be visible in Telescope            | confirmed |
| Telescope visibility guaranteed by using Laravel HTTP client       | confirmed |
| Raw Guzzle or curl in adapters is a boundary violation             | confirmed |

---

## Proposed Conventions (Not Yet Implemented)

These are proposals. Do not generate code that treats them as established.

| Convention                                                         | Status    |
|--------------------------------------------------------------------|-----------|
| `correlationId` middleware auto-generates and stores in container  | proposed  |
| SDK emits structured events for every provider operation           | proposed  |
| Module publishes ELK-formatted log channel                        | proposed  |
| Fine-tuning dataset built from confirmed SDK + module examples     | proposed  |

---

## Deprecated Conventions (Do Not Use)

| Convention                                                         | Status     | Replaced By                    |
|--------------------------------------------------------------------|------------|--------------------------------|
| Direct Guzzle injection into SDK                                  | deprecated | `HttpClientInterface`          |
| Monolithic service class with all provider methods                | deprecated | Grouped `Internal/Callers/`    |