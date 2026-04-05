# SDK Data Transfer Objects (DTOs)
chunk_id: sdk-dtos-001
layer: sdk
type: dto-rules
retrieval_tags: [sdk, dtos, payload, resource, data, from, toArray, hydration, serialization]

---

## Rule: Two DTO Types Per Operation

Every SDK operation has exactly two DTO types:
- `Payload` — the request DTO sent to the provider
- `Resource` — the response DTO returned to the consumer

```
src/Data/TerminalGet/
├── Payload.php    ← consumer builds this, SDK sends it
└── Resource.php   ← SDK builds this, consumer reads it

src/Data/P2PUniversalCredit/
├── Payload.php
├── Resource.php
├── CreditData.php  ← nested request data object
└── SenderData.php  ← nested request data object
```

---

## Rule: Payload Extends BasePayload

Every request DTO extends `BasePayload` and implements two methods:
- `getMethodName(): string` — the provider method or endpoint
- `toArray(): array` — serializes to raw array for transport

**Correct — simple payload:**
```php
final class Payload extends BasePayload
{
    public function __construct(
        public ?string $request_id = null,
    ) {}

    public function getMethodName(): string
    {
        return 'terminal.get';
    }

    public function toArray(): array
    {
        return [
            'request_id' => $this->request_id,
        ];
    }
}
```

**Correct — complex payload with nested data:**
```php
final class Payload extends BasePayload
{
    public function __construct(
        public CreditData $credit,
    ) {}

    public function getMethodName(): string
    {
        return 'p2p.universal.credit';
    }

    public function toArray(): array
    {
        return [
            'credit' => $this->credit->toArray(), // ← nested DTO serialized
        ];
    }
}
```

---

## Rule: Resource Is a Final Readonly-Style Class With Static from()

Every response DTO is a `final` class with:
- constructor with typed properties
- static `from(array $data): static` for hydration
- `toArray(): array` for serialization

**Correct — simple resource:**
```php
final class Resource
{
    public function __construct(
        public string $pid,
        public string $terminal_id,
        public string $merchant_id,
        public string $username,
        public int $t_type,
        public int $terminal_type,
        public string $inst_id,
        public string $name,
        public string $port,
        public string $purpose,
    ) {}

    public static function from(array $data): static
    {
        return new self(
            pid: (string) ($data['pid'] ?? $data['Pid'] ?? ''),
            terminal_id: (string) ($data['terminal_id'] ?? $data['TerminalId'] ?? ''),
            // ...
        );
    }

    public function toArray(): array
    {
        return [
            'pid' => $this->pid,
            'terminal_id' => $this->terminal_id,
            // ...
        ];
    }
}
```

---

## Rule: Hydration Always Uses from(array $data)

DTOs are never constructed directly by the consumer from raw arrays.
The `from()` static method is the only hydration path.

**Correct:**
```php
// In SVGate.php
private function mapResource(BasePayload $payload, string $resourceClass): object
{
    $result = $this->call($payload);
    return $resourceClass::from($result); // ← always via from()
}

private function mapCollection(BasePayload $payload, string $resourceClass): array
{
    $result = $this->call($payload);
    $items = [];
    foreach ($result as $item) {
        $items[] = $resourceClass::from($item); // ← always via from()
    }
    return $items;
}
```

**Forbidden:**
```php
$resource = new Resource($data['pid'], $data['terminal_id'], ...); // raw constructor
```

---

## Rule: from() Handles Provider Naming Inconsistencies

Providers often return fields in multiple naming formats.
The `from()` method normalizes these silently — the consumer never sees them.

**Correct — svgate handles both snake_case and PascalCase:**
```php
public static function from(array $data): static
{
    return new self(
        pid: (string) ($data['pid'] ?? $data['Pid'] ?? ''),
        terminal_id: (string) ($data['terminal_id'] ?? $data['TerminalId'] ?? ''),
        merchant_id: (string) ($data['merchant_id'] ?? $data['MerchantId'] ?? ''),
        username: (string) ($data['username'] ?? $data['Username'] ?? ''),
    );
}
```

The consumer always gets `snake_case` properties regardless of what the provider sent.

---

## Rule: All Fields Have Safe Defaults in from()

`from()` never throws on missing fields.
Every field has a typed default via the null coalescing operator.

**Correct:**
```php
pid: (string) ($data['pid'] ?? ''),         // string defaults to ''
t_type: (int) ($data['t_type'] ?? 0),       // int defaults to 0
field48: isset($data['field48'])             // nullable stays null
    ? (string) $data['field48']
    : null,
```

**Forbidden:**
```php
pid: $data['pid'],           // throws if missing
t_type: $data['t_type'],     // throws if missing, no type cast
```

---

## Rule: Nested Data Objects Follow the Same Pattern

Complex payloads use nested data objects.
Each nested object is also `final` with `from(array $data)` and `toArray()`.

**Correct — svgate CreditData inside Payload:**
```php
final class CreditData
{
    public function __construct(
        public string $ext,
        public int $amount,
        public string $merchantId,
        public string $terminalId,
        public string $recipient,
        public SenderData $sender, // ← nested further
    ) {}

    public static function from(array $data): static
    {
        $sender = $data['sender'] ?? [];
        return new self(
            ext: (string) ($data['ext'] ?? ''),
            amount: (int) ($data['amount'] ?? 0),
            sender: $sender instanceof SenderData
                ? $sender
                : SenderData::from(is_array($sender) ? $sender : []),
        );
    }

    public function toArray(): array
    {
        return [
            'ext' => $this->ext,
            'amount' => $this->amount,
            'sender' => $this->sender->toArray(), // ← nested serialized
        ];
    }
}
```

Nesting follows the same `from()` / `toArray()` contract at every level.

---

## Rule: Payload Also Has a Static from() for Testing

Every `Payload` implements a static `from(mixed ...$payloads)` factory.
This enables test construction from raw arrays without using the constructor directly.

**Correct:**
```php
public static function from(mixed ...$payloads): static
{
    $data = isset($payloads[0]) && is_array($payloads[0]) ? $payloads[0] : [];
    $credit = $data['credit'] ?? [];

    return new self(
        credit: $credit instanceof CreditData
            ? $credit
            : CreditData::from(is_array($credit) ? $credit : []),
    );
}
```

---

## Rule: BasePayload Owns JSON-RPC Envelope Construction

The consumer never builds the JSON-RPC envelope.
`BasePayload::toPayload()` handles it — method name, id, jsonrpc version, params.

**Correct — BasePayload:**
```php
final public function toPayload(): array
{
    $data = $this->toArray();
    $rawRequestId = $data['request_id'] ?? null;
    $id = is_scalar($rawRequestId)
        ? (string) $rawRequestId
        : bin2hex(random_bytes(16));
    unset($data['request_id']);

    return [
        'jsonrpc' => '2.0',
        'method' => $this->getMethodName(),
        'id' => $id,
        'params' => $data,
    ];
}
```

The consumer calls `$payload->toArray()` for their own use.
The SDK calls `$payload->toPayload()` for transport.

---

## Rule: DTOs Never Contain Business Logic

DTOs are data containers only. They must never:
- call other services
- make HTTP requests
- throw provider exceptions
- contain validation logic beyond type casting

Validation belongs in the entrypoint or the caller layer.

---

## DTO Verification Checklist

Before committing DTO code in an SDK:

- [ ] Every operation has a `Payload` and a `Resource` in its own subfolder
- [ ] `Payload` extends `BasePayload` and implements `getMethodName()` and `toArray()`
- [ ] `Resource` is `final` with `from(array $data)` and `toArray()`
- [ ] `from()` handles all provider naming variants (snake_case, PascalCase)
- [ ] All fields have safe typed defaults in `from()` — never throws on missing key
- [ ] Nested data objects follow the same `from()` / `toArray()` contract
- [ ] `Payload` has a static `from(mixed ...$payloads)` factory for test construction
- [ ] DTOs contain no business logic, no service calls, no HTTP calls
- [ ] `BasePayload::toPayload()` is used by transport, not by consumer