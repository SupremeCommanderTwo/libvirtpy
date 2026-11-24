# Client

`LibvirtClient` (blocking) and `AsyncLibvirtClient` (`async`/`await`) offer the same
methods. They are generated from one set of operations, so they never differ.

## References

Wherever a method needs an object you can pass:

| Reference | Example |
|---|---|
| an id (running domains) | `client.start_domain(3)` |
| a name | `client.lookup_domain("vm")` |
| a UUID (`UUID`, or text that looks like one) | `client.lookup_domain(UUID("..."))` |
| a model | `client.destroy_domain(domain)` |

## Proxies

`client.domain(ref)` (and `network`, `pool`, `volume`, `secret`, ...) returns a small
proxy that fills in the reference:

```python
vm = client.domain("vm")
vm.start()
vm.set_vcpus(4)
```

## Replies

- one value: returned as is (a count is returned as an `int`);
- an object: a model (`Domain`, `Network`, ...);
- typed parameters: a `dict`;
- several values: the generated reply struct, for example `DomainGetBlockInfoRet`.

Flags are plain integers; each method's docstring names the libvirt enum.

## Errors

`LibvirtError` carries the daemon's `code` and `domain`; common codes have a subclass:
`NoDomainError`, `NoNetworkError`, `OperationInvalidError`, `ExistsError`,
`AuthFailedError`, `NotSupportedError`, ... All derive from
{class}`libvirtpy.errors.LibvirtPyError`.

```python
from libvirtpy.client import LibvirtError
from libvirtpy.rpc.errors import NoDomainError

try:
    client.lookup_domain("missing")
except NoDomainError:
    ...
```

See {doc}`reference/client` for all operations.
