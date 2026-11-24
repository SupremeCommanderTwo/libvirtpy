# Using asyncio

`AsyncLibvirtClient` has the same methods as `LibvirtClient`, awaited. Opening is a
coroutine too, so the idiom is `async with await AsyncLibvirtClient.open(uri)`.

```python
import asyncio

from libvirtpy.client import AsyncLibvirtClient


async def main() -> None:
    async with await AsyncLibvirtClient.open("qemu:///system") as client:
        version, hostname, running = await asyncio.gather(
            client.get_version(),
            client.get_hostname(),
            client.list_domains(active=True),
        )
        print(f"{hostname}: libvirt {version}, {len(running)} running")


asyncio.run(main())
```

Calls issued at the same time share one connection and are matched to their replies by
serial number, so `asyncio.gather` really overlaps the round trips.

## Many hosts at once

Open and query every host concurrently; a failing host is reported and does not stop
the others:

```python
async def inspect(uri: str) -> str:
    try:
        async with await AsyncLibvirtClient.open(uri, read_only=True) as client:
            hostname, domains = await asyncio.gather(
                client.get_hostname(), client.list_domains()
            )
    except (ConnectionError, LibvirtError) as error:
        return f"{uri}: FAILED: {error}"
    return f"{uri}: {hostname}, {len(domains)} domains"


results = await asyncio.gather(*(inspect(uri) for uri in uris))
```

The slowest host decides how long it takes, not the sum.

## Events and streams

```python
async with client.events("domain") as events:
    async for event in events:
        print(event)

async with client.download_pool_volume("pool", "disk.img") as source:
    async for chunk in source:
        handle(chunk)
```

`AsyncRemoteStream` also has `await read(size)`, `await read_chunk()` and
`await write(data)`.

## In tests

`AsyncLibvirtClient(AsyncFakeTransport())` is the async twin of
`LibvirtClient(FakeLibvirt())` ({doc}`testing`).
