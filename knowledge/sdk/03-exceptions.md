# SDK Exception Hierarchy
chunk_id: sdk-exceptions-001
layer: sdk
type: exception-rules
retrieval_tags: [sdk, exceptions, error-codes, svgate, hierarchy, factory-methods, error-mapping]

---

## Rule: One Exception Class Per SDK

Every SDK has exactly one exception class rooted at a `final` class extending `Exception`.
There is no abstract base in the SDK — that lives in the module layer.

**Correct — svgate:**
```php
// src/Exceptions/SVGateException.php
final class SVGateException extends Exception
{
    public function __construct(
        int $code,
        ?string $message = null,
        ?Throwable $previous = null,
    ) {
        parent::__construct(self::buildMessage($code, $message), $code, $previous);
    }
}
```

The exception class is `final`. It cannot be extended.
All error variants are expressed through static factory methods, not subclasses.

---

## Rule: Static Factory Methods Per Error Category

Every distinct error condition gets its own named static factory method.
Never throw `new SVGateException(1002)` directly from calling code.

**Correct — svgate factory methods:**
```php
SVGateException::connection($previous);           // transport failed
SVGateException::unsuccessfulResponse($previous); // HTTP non-2xx
SVGateException::invalidResponseBody($previous);  // JSON parse failed
SVGateException::invalidResponseId($previous);    // JSON-RPC id mismatch
SVGateException::missingResponseResult($previous);// result key absent
SVGateException::invalidResponseResult($previous);// result not array
SVGateException::invalidBaseUrl($previous);       // HTTPS not enforced
SVGateException::svgateError($code, $message);    // provider error code
```

**Forbidden:**
```php
throw new SVGateException(1002); // raw constructor — no context, unreadable
throw new \Exception('invalid'); // base Exception — loses type
```

---

## Rule: Two Error Code Namespaces

**Client-side errors (1000–1999)** — SDK detected the problem:

| Constant                                        | Code | Meaning                              |
|-------------------------------------------------|------|--------------------------------------|
| `CLIENT_CONNECTION_EXCEPTION`                   | 1000 | Transport layer failed               |
| `CLIENT_UNSUCCESSFUL_RESPONSE`                  | 1001 | HTTP status not 2xx                  |
| `CLIENT_INVALID_RESPONSE_BODY`                  | 1002 | Response body not valid JSON         |
| `CLIENT_INVALID_ERROR_TYPE`                     | 1003 | Error code not integer               |
| `CLIENT_RESPONSE_DOES_NOT_CONTAIN_RESULT`       | 1004 | Result key missing                   |
| `CLIENT_RESPONSE_RESULT_IS_NOT_TYPE_OF_ARRAY`   | 1005 | Result not array                     |
| `CLIENT_INVALID_USERNAME`                       | 1006 | Username failed validation           |
| `CLIENT_INVALID_PASSWORD`                       | 1007 | Password failed validation           |
| `CLIENT_INVALID_BASE_URL`                       | 1008 | Base URL not HTTPS                   |
| `CLIENT_INVALID_RESPONSE_INSTANCE`              | 1009 | Transport did not return response    |
| `CLIENT_INVALID_RESPONSE_ID`                    | 1010 | JSON-RPC id mismatch                 |
| `CLIENT_UNKNOWN_ERROR`                          | 1999 | Fallback unknown error               |

**Provider-side errors (negative codes)** — SVGate returned the error:

| Code range     | Category                        |
|----------------|---------------------------------|
| -100 to -199   | Request / parameter errors      |
| -200 to -299   | Card and account errors         |
| -300 to -399   | Auth and access errors          |
| -400 to -499   | Service availability errors     |
| -32xxx         | JSON-RPC protocol errors        |

Provider errors are thrown via `SVGateException::svgateError($code, $message)`.

---

## Rule: Error Codes Live in a Dedicated Enum Class

Never hardcode error code integers in calling code.
All codes live in `SVGateError` as named constants.

**Correct:**
```php
// src/Enums/SVGateError.php
final class SVGateError
{
    public const int CLIENT_CONNECTION_EXCEPTION = 1000;
    public const int INSUFFICIENT_FUNDS = -240;
    public const int CARD_BLOCKED = -205;
    // ...

    public static function map(int $code): string { ... }
    public static function isKnown(int $code): bool { ... }
}
```

**Forbidden:**
```php
throw new SVGateException(-240); // magic number — unreadable
if ($code === -205) { ... }      // hardcoded comparison
```

---

## Rule: Error Messages Are Built From Code, Not Hardcoded

The exception builds its message from the error code via `SVGateError::map()`.
If a provider message is present, it overrides the default.

**Correct — svgate buildMessage:**
```php
private static function buildMessage(int $code, ?string $message): string
{
    if ($message !== null && $message !== '') {
        return $message;  // provider message takes priority
    }

    return SVGateError::map($code); // fallback to known code description
}
```

This means every known error code has a human-readable default message.
Unknown provider codes fall back to `'Unknown error.'`.

---

## Rule: Previous Exception Is Always Chained

Every factory method accepts `?Throwable $previous`.
Transport exceptions, JSON exceptions, and network errors are always chained.

**Correct — svgate ApiCaller:**
```php
try {
    $response = $this->options->transport->post(...);
} catch (Throwable $exception) {
    throw SVGateException::connection($exception); // ← chained
}

try {
    $decoded = json_decode(..., JSON_THROW_ON_ERROR);
} catch (JsonException $exception) {
    throw SVGateException::invalidResponseBody($exception); // ← chained
}
```

**Forbidden:**
```php
} catch (Throwable $e) {
    throw SVGateException::connection(); // ← previous lost, stack trace broken
}
```

---

## Rule: Provider Errors Are Caught and Re-thrown as SDK Exceptions

The SDK never leaks raw provider error codes as untyped exceptions.
Every provider error response is mapped to `SVGateException::svgateError()`.

**Correct — svgate ApiCaller:**
```php
if (array_key_exists('error', $decoded) && $decoded['error'] !== null) {
    $code = ...; // extracted and validated as int
    $message = ...; // extracted as string or null

    throw SVGateException::svgateError($code, $message);
}
```

The consumer catches one type — `SVGateException` — for all error conditions.

---

## Rule: Exception Messages Are Safe for Logs

Exception messages must never contain raw PANs, tokens, passwords, or phone numbers.
The `Redactor` handles payload sanitization before logging.
Exception messages carry only safe operational context.

**Safe exception messages (from SVGateError):**
```
'Card not found.'
'Insufficient funds.'
'Wrong OTP code.'
'Terminal ID and merchant ID already exist in the database.'
```

**Forbidden in exception messages:**
```
'Card 8600XXXXXXXXXXXX not found.' // PAN in message
'Auth failed for password abc123'  // credential in message
```

---

## Rule: SDK Exception Never Extends Module Exception

The SDK exception hierarchy is completely separate from the module exception hierarchy.

```
SDK layer:
  SVGateException extends Exception  ✅

Module layer:
  SVGateModuleException extends ModuleException  ✅

Forbidden:
  SVGateException extends ModuleException  ❌
  SVGateModuleException extends SVGateException  ❌
```

The module catches `SVGateException` and wraps it in a `ModuleException` when needed.

---

## Exception Verification Checklist

Before committing exception code in an SDK:

- [ ] One `final` exception class per SDK
- [ ] Named static factory method for every distinct error condition
- [ ] All error codes defined as named constants in a dedicated enum class
- [ ] No raw integer codes in calling code
- [ ] `?Throwable $previous` accepted and chained in every factory method
- [ ] Provider errors mapped via `svgateError($code, $message)`
- [ ] Messages built from error code enum, never hardcoded strings
- [ ] Messages safe for logs — no credentials, PANs, or tokens
- [ ] SDK exception never extends module exception