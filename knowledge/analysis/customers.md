# Analysis: customers

 ## Package Name
**MBC (Mobile Banking Client)**

## Type
**sdk | module**

## Public Entrypoint
The single public class is `Khakimjanovich\MBC\MBC`. It is correctly placed in the `src/` directory. The class provides a facade-like interface to access various services and functionalities provided by the package.

## Boundary Violations
**List any illuminate/* dependencies found in an SDK package.**
- Observed: There are several Laravel contracts imported via `require` in `composer.json`, such as `Illuminate\Contracts`. This is typical for a Laravel-specific SDK but could be considered a boundary violation if the intention was to keep the dependency scope minimal.

**List any Laravel facades, helpers (config(), app(), Log::) found in SDK src/.**
- Observed: There are several Laravel facades and helper functions used within the `src/` directory, such as `Http`, `Auth`, `Log`, etc. This is typical for a Laravel-specific SDK but could be considered a boundary violation if encapsulation was intended to limit these usages.

**List any ServiceProvider or Facade classes found in SDK src/.**
- Observed: There are several ServiceProviders defined within the `src/` directory, such as `MBCServiceProvider`, which is part of the package registration and configuration. This is typical for a Laravel package but could be considered a boundary violation if the intention was to keep these tightly coupled with the application context.

## Structure Compliance
The folder structure appears mostly compliant except for:
- **What is missing or misplaced?**
  - The `src/Internal/` directory is absent, which typically contains internal utilities and helpers not meant for direct usage outside the package.

## Observed Conventions
**Patterns:**
- **Confirmed:** Use of Laravel's Service Providers for package registration (`MBCServiceProvider`), configuration files (`mbc.php` under `config/`).
- **Observed:** Use of Facades and global helpers (e.g., `Http`, `Auth`) which is typical in Laravel applications but could be limiting encapsulation if intended to restrict external dependencies.
- **Proposed:** Consideration for creating an internal directory (`src/Internal/`) to house utility functions that are not meant for public consumption, to better comply with the principle of clear separation of concerns and intended usage boundaries.

## Gaps
**What is implemented but not documented?**
- The absence of a dedicated `src/Internal/` directory for utilities not intended for external use. Documentation on such conventions could be added in future updates or documentation files to guide users effectively.

## Recommended Actions
1. **Document the Purpose and Scope**: Clarify in the README or other documentation that this package is specifically designed for Laravel applications, potentially with notes about its modular structure but also emphasizing encapsulation of dependencies like `illuminate/*` contracts and facades within the SDK itself.
2. **Create Internal Directory**: Implement an `src/Internal/` directory to house utilities such as helpers or internal services not intended for public usage, which would help in maintaining a cleaner API surface.
3. **Update Documentation**: Add or update documentation around conventions used, especially concerning Laravel dependencies and the purpose of the `src/Internal/` directory, to better guide users and contributors on expected use cases and boundaries.