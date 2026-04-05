# SDK Boundaries
chunk_id: sdk-boundaries-001
layer: sdk
type: boundary-rules
retrieval_tags: [sdk, boundaries, forbidden, illuminate, laravel, psr, transport, contracts]

---

## Rule: Zero Laravel Dependencies

Every SDK `composer.json` must contain zero `illuminate/*` dependencies.
The SDK is a pure PHP library. It must run outside Laravel without modification.

**Correct — svgate SDK:**
```json
{
    "require": {
        "php": "^8.4",
        "psr/log": "^3.0"
    }
}
```

**Forbidden in any SDK `composer.json`:**
- `laravel/framework`
- `illuminate/http`
- `illuminate/support`
- `illuminate/container`
- Any `illuminate/*` package

If `illuminate/*` appears in an SDK `composer.json`, it is a boundary violation.
The fix is to extract the Laravel dependency into the module adapter layer.

---

## Rule: Transport Is Always Injected

The SDK never instantiates an HTTP client directly.
The consumer provides the transport implementation via `TransportInterface`.

**Correct — svgate:**
```php
// src/Contracts/TransportInterface.php
interface TransportInterface
{
    public function post(string $url, array $payload, array $headers = []): TransportResponse;
}

// src/Configs/ClientOptions.php
final readonly class ClientOptions
{
    public function __construct(
        public string $baseUrl,
        public string $username,
        public string $password,
        public TransportInterface $transport,  // ← injected by consumer
        public ?LoggerInterface $logger = null,
    ) {}
}
```

**Forbidden:**
```php
// Never instantiate Guzzle, curl, or Laravel HTTP inside SDK
$client = new \GuzzleHttp\Client();
$response = Http::post($url, $payload); // Laravel facade — forbidden
```

The module adapter provides the concrete transport:
```php
// In module: src/Adapters/SVGateTransport.php
// Uses Illuminate\Http\Client\Factory so Telescope can observe it
```

---

## Rule: Logger Is Always Optional and PSR-3

The SDK accepts a PSR-3 logger via `ClientOptions`.
If no logger is provided, it falls back to `NullLogger` — never to `Log::` facade.

**Correct — svgate ApiCaller:**
```php
public function __construct(
    private readonly ClientOptions $options,
) {
    $this->logger = $this->options->logger ?? new NullLogger();
}
```

**Forbidden:**
```php
Log::debug('svgate.request');      // Laravel facade — forbidden in SDK
\Illuminate\Support\Facades\Log::info('...'); // forbidden
```

---

## Rule: No Laravel Helpers Inside SDK Source

The following are forbidden anywhere inside `src/`:

| Forbidden call        | Reason                              | Correct alternative          |
|-----------------------|-------------------------------------|------------------------------|
| `config('svgate.*')` | Runtime Laravel dependency          | Pass via `ClientOptions`     |
| `app()`              | Container access                    | Constructor injection        |
| `Log::debug()`       | Laravel facade                      | Injected PSR-3 logger        |
| `Http::post()`       | Laravel HTTP facade                 | Injected `TransportInterface`|
| `cache()`            | Laravel cache helper                | Not in SDK                   |
| `event()`            | Laravel event helper                | Not in SDK                   |
| `dispatch()`         | Laravel queue helper                | Not in SDK                   |

---

## Rule: No ServiceProvider, Facade, or Container Binding in SDK

The following classes must never exist inside `src/`:

- `ServiceProvider`
- `Facade`
- Any class that references `Illuminate\Support\ServiceProvider`
- Any class that calls `$this->app->bind()`

These belong in the module package, not the SDK.

**Correct location for Laravel wiring:**
```
packages/module-svgate/
└── src/
    └── Providers/
        └── SVGateServiceProvider.php  ← bindings live here, not in SDK
```

---

## Rule: Config Is a Value Object, Never a Laravel Config File

The SDK receives its configuration as a readonly value object.
It never reads from `config()` helper or publishes a config file.

**Correct — svgate:**
```php
final readonly class ClientOptions
{
    public function __construct(
        public string $baseUrl,
        public string $username,
        public string $password,
        public TransportInterface $transport,
        public ?LoggerInterface $logger = null,
    ) {
        $scheme = parse_url($this->baseUrl, PHP_URL_SCHEME);
        if (! is_string($scheme) || mb_strtolower($scheme) !== 'https') {
            throw SVGateException::invalidBaseUrl();
        }
    }
}
```

The module constructs this from Laravel config:
```php
// In module ServiceProvider:
new ClientOptions(
    baseUrl: config('svgate.base_url'),
    username: config('svgate.username'),
    password: config('svgate.password'),
    transport: app(SVGateTransport::class),
    logger: app(LoggerInterface::class),
);
```

---

## Rule: Sensitive Data Is Redacted Before Logging

The SDK must never log raw credentials, tokens, PANs, or phone numbers.
The `Redactor` class handles this inside `Internal/`.

**Correct — svgate Redactor:**
```php
private const array SENSITIVE_KEYS = [
    'authorization', 'cardid', 'code', 'hpan',
    'pan', 'pan2', 'password', 'phone', 'pinfl',
    'recipient', 'requestorphone', 'sender', 'token',
];
```

**Correct usage in ApiCaller:**
```php
$this->logger->debug('svgate.request.created', [
    'method' => $method,
    'request_id' => $requestId,
    'headers' => $this->redactor->redact($headers),    // ← redacted
    'payload' => $this->redactor->redact($payload),    // ← redacted
]);
```

**Forbidden:**
```php
$this->logger->debug('request', [
    'payload' => $payload,   // raw payload — may contain PAN, token, password
]);
```

---

## Rule: Internal Classes Are Never Public

Everything in `Internal/` is an implementation detail.
No class in `Internal/` appears in public API, README examples, or consumer code.

**Correct — svgate:**
```
src/Internal/
├── ApiCaller.php           ← wired only inside SVGate.php
├── Redactor.php            ← wired only inside ApiCaller.php
└── RequestIdGenerator.php  ← wired only inside ApiCaller.php
```

Consumer code never references `ApiCaller`, `Redactor`, or `RequestIdGenerator` directly.

---

## Rule: HTTPS Is Enforced at Config Construction

The SDK validates transport security at construction time, not at call time.

**Correct — svgate ClientOptions:**
```php
$scheme = parse_url($this->baseUrl, PHP_URL_SCHEME);
if (! is_string($scheme) || mb_strtolower($scheme) !== 'https') {
    throw SVGateException::invalidBaseUrl();
}
```

This means a misconfigured SDK fails immediately on boot,
not silently on the first production request.

---

## Boundary Verification Checklist

Before committing an SDK package:

- [ ] `composer.json` contains zero `illuminate/*` dependencies
- [ ] No `config()`, `app()`, `Log::`, `Http::` calls anywhere in `src/`
- [ ] No `ServiceProvider`, `Facade`, or container binding in `src/`
- [ ] Transport is injected via interface, never instantiated inside SDK
- [ ] Logger is injected as PSR-3, falls back to `NullLogger` not Laravel facade
- [ ] Config is a readonly value object with validation in constructor
- [ ] Sensitive fields are redacted before any log call
- [ ] `Internal/` classes are never referenced in consumer-facing code or README
- [ ] HTTPS is enforced at construction, not at call time