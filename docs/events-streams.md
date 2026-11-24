# Events and streams

## Events

The daemon pushes a message when something happens. `client.events()` returns a
subscription you iterate:

```python
from libvirtpy.client import DomainEventKind

kinds = [DomainEventKind.LIFECYCLE, DomainEventKind.REBOOT]
with client.events("domain", kinds) as events:
    for event in events:
        print(event)
```

The async client has the same with `async with` and `async for`. A lost connection ends
a subscription with `ConnectionLostError`. Events need a real daemon connection; the
fake daemon raises `NotSupportedError`.

## Streams

Consoles, screenshots and volume upload/download return a file-like stream:

```python
with client.download_pool_volume("pool", "disk.img") as source:
    data = source.read()

with client.open_domain_console("vm") as console:
    console.write(b"\n")
    print(console.read(100))
```

`RemoteStream` is a real `io.RawIOBase` (`read`, `write`, `with`,
`shutil.copyfileobj`); `AsyncRemoteStream` has the same methods as coroutines and
supports `async for`.
