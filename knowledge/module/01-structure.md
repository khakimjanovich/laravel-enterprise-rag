# Laravel Module Structure
chunk_id: module-structure-001
layer: module
type: structure-rules
retrieval_tags: [module, structure, service-provider, facade, plugin, filament, factory, contracts, laravel]

---

## Rule: Standard Module Directory Layout

Every Laravel module package MUST follow this exact layout:

```
packages/module-{name}/
├── src/
│   ├── {ModuleName}.php                    # Root service class (not the entrypoint)
│   ├── {ModuleName}ServiceProvider.php     # Wires everything into Laravel
│   ├── {ModuleName}Plugin.php              # Filament plugin — registers resources
│   ├── Contracts/                          # Module-level interfaces
│   ├── Configs/                            # Module config value objects (if needed)
│   ├── Data/                               # Module-level DTOs (separate from SDK DTOs)
│   ├── Enums/                              # Module enums
│   ├── Exceptions/                         # Module exception hierarchy
│   ├── Factories/                          # Processing centre / adapter factories
│   ├── Facades/                            # Laravel facade
│   ├── Filament/                           # Backoffice resources, pages, widgets
│   │   └── Resources/
│   ├── Models/                             # Eloquent models
│   ├── Services/                           # Domain services
│   ├── Events/                             # Domain events
│   ├── Observers/                          # Eloquent observers
│   ├── Listeners/                          # Event listeners
│   ├── Jobs/                               # Queued jobs
│   ├── Commands/                           # Artisan commands
│   ├── Notifications/                      # Laravel notifications
│   ├── Rules/                              # Validation rules
│   └── Support/                            # Internal helpers
├── database/
│   └── migrations/
├── config/
│   └── {module_name}.php
├── composer.json
└── README.md
```

---

## Rule: ServiceProvider Owns All Laravel Wiring

The `ServiceProvider` is the only place that:
- registers config files
- registers console commands
- binds interfaces to implementations
- registers the facade singleton
- sets up install commands

**Correct — pc-manager:**
```php
final class PCManagerServiceProvider extends PackageServiceProvider
{
    public function configurePackage(Package $package): void
    {
        $package
            ->name('pc-manager')
            ->hasConfigFile('pc_manager')
            ->hasConsoleCommands(
                MigrateCommand::class,
                SyncBINCommand::class,
                SyncEPOSCommand::class,
            );

        $this->app->singleton('pc-manager', fn () => new PCManager);
        $this->app->bind(IABSTransactionClientContract::class, IABSTransactionClient::class);
    }
}
```

**Forbidden:**
- Bindings inside `Facade`, `Plugin`, or any service class
- Config publishing from outside the ServiceProvider
- Direct `app()` calls inside SDK or domain classes

---

## Rule: Filament Plugin Is Separate From ServiceProvider

The Filament plugin class is responsible only for registering
backoffice resources and navigation groups into a Filament panel.
It never handles bindings or config.

**Correct — pc-manager PCManagerPlugin:**
```php
final class PCManagerPlugin implements Plugin
{
    public static function make(): self
    {
        return app(self::class);
    }

    public function getId(): string
    {
        return 'pc-manager';
    }

    public function register(Panel $panel): void
    {
        $panel
            ->resources([
                Filament\Resources\EPOSResource::class,
                Filament\Resources\BINResource::class,
                Filament\Resources\TransactionResource::class,
                Filament\Resources\SettingResource::class,
            ])
            ->navigationGroups([
                NavigationGroup::make('PC Manager')
                    ->icon('heroicon-o-credit-card'),
            ]);
    }
}
```

The plugin is registered in the backoffice panel only — not in the API panel.
This enforces the two-runtime separation.

---

## Rule: Facade Provides the Public Module API

The module exposes its domain services through a typed Facade.
The Facade accessor points to the singleton registered in ServiceProvider.

**Correct — pc-manager:**
```php
final class PCManager extends Facade
{
    protected static function getFacadeAccessor(): string
    {
        return 'pc-manager';
    }
}
```

With typed method annotations:
```php
/**
 * @method static BIN bin()
 * @method static Card card()
 * @method static Transaction transaction()
 * @method static EPOS epos()
 * @method static Payment payment()
 * @method static TransactionProcess transactionProcess()
 */
```

Consumers use `PCManager::card()->...` or inject the root class directly.

---

## Rule: Processing Centre Factory Abstracts SDK Wiring

When a module supports multiple provider backends, a Factory resolves
the correct implementation from an enum value.
The factory uses singleton caching to avoid repeated instantiation.

**Correct — pc-manager ProcessingCentreFactory:**
```php
final class ProcessingCentreFactory
{
    private static array $instances = [];

    public static function make(ProcessingCentre $processing_centre): ProcessingCentreContract
    {
        if (isset(self::$instances[$processing_centre->value])) {
            return self::$instances[$processing_centre->value];
        }

        $instance = match ($processing_centre) {
            ProcessingCentre::HUMO   => new ProcessingCentres\HUMO,
            ProcessingCentre::SVGATE => new ProcessingCentres\SVGATE,
            default => throw new InvalidArgumentException,
        };

        return self::$instances[$processing_centre->value] = $instance;
    }
}
```

---

## Rule: Processing Centre Classes Wrap SDK Calls

Each processing centre class implements `ProcessingCentreContract`
and wraps SDK calls with module-level exception mapping.

**Correct — pc-manager SVGATE processing centre:**
```php
final class SVGATE implements ProcessingCentreContract
{
    public function cardAddInit(CardAddInitPayload $data): CardAddInitResource
    {
        try {
            return CardAddInitResource::fromSVResponse(
                SVGateClient::cardsNewOTP($data->toSVCardsNewOTPPayload())
            );
        } catch (SVGateException $exception) {
            throw CardAddInitException::handle($exception, ProcessingCentre::SVGATE);
        }
    }
}
```

Pattern:
1. Call SDK via Facade or injected client
2. Map SDK DTOs to module DTOs via `fromSVResponse()` / `toSVXxxPayload()`
3. Catch `SVGateException` and re-throw as module exception

---

## Rule: Module DTOs Are Separate From SDK DTOs

Module DTOs live in `src/Data/` and are completely separate from SDK DTOs.
They are never the same class.

```
SDK DTO:    Khakimjanovich\SVGate\Data\TerminalGet\Resource
Module DTO: Khakimjanovich\PCManager\Data\ProcessingCentre\DebitResource
```

Module DTOs have static methods to convert from SDK DTOs:
```php
public static function fromSVResponse(SVGateResource $response): static
{
    return new self(
        terminal_id: $response->terminal_id,
        merchant_id: $response->merchant_id,
    );
}
```

And to convert to SDK DTOs:
```php
public function toSVCardsNewOTPPayload(): SVGateCardsNewOTPPayload
{
    return new SVGateCardsNewOTPPayload(
        pan: $this->pan,
    );
}
```

---

## Rule: Module Exception Hierarchy Is Rooted at PCMException

All module exceptions extend the abstract base `PCMException`.
SDK exceptions are never extended — they are caught and re-thrown.

**Correct — pc-manager PCMException:**
```php
class PCMException extends Exception
{
    public function __construct(
        ExceptionCodes $exception_code,
        ?ProcessingCentre $processing_centre = null,
        ?Throwable $previous = null,
    ) {
        $this->exception_code = $exception_code;
        $this->processing_centre = $processing_centre;

        parent::__construct(
            $processing_centre?->value . ':' . $exception_code->value,
            0,
            $previous,
        );
    }
}
```

Every module exception carries:
- `ExceptionCodes` enum value — the operation that failed
- `ProcessingCentre` enum value — which provider caused the failure
- `$previous` — the chained SDK exception

---

## Rule: Two Runtimes, One Module

The module registers into both application runtimes via one ServiceProvider.
The Filament Plugin activates backoffice resources only in the backoffice panel.

```
Laravel Application
├── Backoffice panel   → registers PCManagerPlugin
│                        → Filament resources visible
└── API panel          → does NOT register PCManagerPlugin
                          → only API routes and services available
```

The ServiceProvider always runs.
The Plugin only runs when registered in the backoffice panel configuration.

---

## Module Structure Verification Checklist

Before committing a module package:

- [ ] `ServiceProvider` owns all bindings, config, and command registration
- [ ] `Plugin` only registers Filament resources and navigation groups
- [ ] `Facade` has typed `@method` annotations for all domain services
- [ ] Processing centre classes implement a shared `Contract` interface
- [ ] Processing centre factory caches instances by enum value
- [ ] Module DTOs are separate from SDK DTOs with `fromSVResponse()` converters
- [ ] All module exceptions extend module base exception — never SDK exception
- [ ] Module base exception carries `ExceptionCodes` + `ProcessingCentre` + `$previous`
- [ ] SDK exceptions always caught and re-thrown as module exceptions
- [ ] Filament Plugin registered only in backoffice panel — not in API panel
- [ ] No `illuminate/*` boundary violations in SDK packages this module depends on