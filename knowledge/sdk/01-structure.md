# SDK Package Structure
chunk_id: sdk-structure-001
layer: sdk
type: structure-rules
retrieval_tags: [sdk, package, structure, layout, composer, namespace, entrypoint]

---

## Rule: One Public Entrypoint

Every SDK package exposes exactly ONE public class as its root entrypoint.

```
src/ServiceA.php        ← the only class a consumer should instantiate
```

All other classes are internal implementation details.
The consumer should never need to instantiate anything else directly.

**Correct:**
```php
$client = new ServiceA($httpClient, $logger, $config);
$result = $client->createTransaction($dto);
```

**Wrong:**
```php
$caller = new Internal\TransactionCaller($httpClient);  // never
$result = $caller->call($dto);
```

---

## Rule: Standard Directory Layout

Every SDK package MUST follow this exact layout:

```
packages/service-{name}-sdk/
├── src/
│   ├── Service{Name}.php          # Single public entrypoint
│   ├── Contracts/                 # Interfaces the SDK exposes
│   │   ├── HttpClientInterface.php
│   │   ├── LoggerInterface.php
│   │   └── EventDispatcherInterface.php
│   ├── Configs/                   # Runtime config value objects
│   │   └── Service{Name}Config.php
│   ├── Data/                      # Request + Response DTOs
│   │   ├── Requests/
│   │   └── Responses/
│   ├── Exceptions/                # SDK exception hierarchy
│   │   ├── SdkException.php       # abstract base
│   │   ├── ProviderException.php
│   │   ├── TransportException.php
│   │   ├── ResponseShapeException.php
│   │   ├── AuthException.php
│   │   └── RequestValidationException.php
│   └── Internal/                  # Never referenced by consumers
│       ├── Callers/               # Protocol callers per operation group
│       ├── Redactors/             # Log-safe redaction
│       └── RequestIdGenerator.php
├── tests/
│   ├── Unit/
│   └── Integration/
├── composer.json
└── README.md
```

---

## Rule: composer.json Must Have Zero Laravel Dependencies

```json
{
    "name": "org/service-{name}-sdk",
    "type": "library",
    "require": {
        "php": "^8.2",
        "psr/log": "^3.0"
    },
    "require-dev": {
        "phpunit/phpunit": "^11.0",
        "phpstan/phpstan": "^1.0"
    },
    "autoload": {
        "psr-4": {
            "Service{Name}\\": "src/"
        }
    }
}
```

**Forbidden in SDK composer.json:**
- `laravel/framework`
- `illuminate/*`
- `laravel/telescope`
- Any Laravel package

If you see `illuminate/*` in an SDK `composer.json`, it is a boundary violation.

---

## Rule: Contracts Directory Contains Only Interfaces

```php
// src/Contracts/HttpClientInterface.php
namespace ServiceA\Contracts;

use ServiceA\Data\Requests\HttpRequest;
use ServiceA\Data\Responses\HttpResponse;

interface HttpClientInterface
{
    public function send(HttpRequest $request): HttpResponse;
}
```

```php
// src/Contracts/LoggerInterface.php
namespace ServiceA\Contracts;

// Extend PSR-3 only — do not add custom methods
interface LoggerInterface extends \Psr\Log\LoggerInterface {}
```

```php
// src/Contracts/EventDispatcherInterface.php
namespace ServiceA\Contracts;

use ServiceA\Data\Events\SdkEvent;

interface EventDispatcherInterface
{
    public function dispatch(SdkEvent $event): void;
}
```

---

## Rule: Configs Directory Contains Value Objects Only

```php
// src/Configs/ServiceAConfig.php
namespace ServiceA\Configs;

final readonly class ServiceAConfig
{
    public function __construct(
        public string $baseUrl,
        public string $apiKey,
        public int    $timeoutSeconds = 30,
        public bool   $sandboxMode    = false,
    ) {}

    public static function fromArray(array $config): self
    {
        return new self(
            baseUrl:        $config['base_url'],
            apiKey:         $config['api_key'],
            timeoutSeconds: $config['timeout'] ?? 30,
            sandboxMode:    $config['sandbox'] ?? false,
        );
    }
}
```

Config objects are immutable value objects.
They are never injected via the container — they are constructed from raw arrays.

---

## Rule: Internal Directory Is Never Public

Everything in `Internal/` is an implementation detail.
No class in `Internal/` should appear in any public API, README example, or consumer code.

```php
// src/Internal/Callers/TransactionCaller.php
namespace ServiceA\Internal\Callers;

// This class is internal — consumers never reference it
final class TransactionCaller
{
    public function __construct(
        private readonly HttpClientInterface $http,
        private readonly LoggerInterface     $logger,
    ) {}
}
```

---

## Rule: Public Entrypoint Wires Everything

```php
// src/ServiceA.php
namespace ServiceA;

final class ServiceA
{
    public function __construct(
        private readonly HttpClientInterface      $httpClient,
        private readonly LoggerInterface          $logger,
        private readonly EventDispatcherInterface $eventDispatcher,
        private readonly ServiceAConfig           $config,
    ) {}

    // Public methods map to provider operations
    public function createTransaction(CreateTransactionRequest $request): CreateTransactionResponse
    {
        // delegates to Internal\Callers\TransactionCaller
    }

    public function getTransactionStatus(string $transactionId): TransactionStatusResponse
    {
        // delegates to Internal\Callers\StatusCaller
    }
}
```

---

## What SDK Must Never Contain

The following are FORBIDDEN inside any SDK package:

| Forbidden                        | Reason                                      |
|----------------------------------|---------------------------------------------|
| `ServiceProvider`                | Laravel concern — belongs in module         |
| `Facade`                         | Laravel concern — belongs in module         |
| Container bindings               | Laravel concern — belongs in module         |
| Config file publishing           | Laravel concern — belongs in module         |
| `config()` helper calls          | Runtime Laravel dependency                  |
| `app()` helper calls             | Runtime Laravel dependency                  |
| `Log::` facade calls             | Laravel dependency — use injected PSR-3     |
| Business workflow orchestration  | Application concern — belongs in module     |
| Queue dispatching                | Application concern — belongs in module     |
| Authentication logic             | Application concern — belongs in module     |
| Raw HTTP client (Guzzle/Laravel) | Consumer provides this via HttpClientInterface |

---

## Verification Checklist

Before committing an SDK package, verify:

- [ ] `composer.json` contains zero `illuminate/*` dependencies
- [ ] Only `src/Service{Name}.php` is the public entrypoint
- [ ] `Internal/` classes are never referenced in README examples
- [ ] All interfaces live in `Contracts/`
- [ ] Config is a readonly value object with `fromArray()`
- [ ] Every exception extends `SdkException`
- [ ] No `ServiceProvider`, `Facade`, or container binding exists
- [ ] PSR-3 logger is injected, never called as a facade