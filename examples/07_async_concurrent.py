"""The async client: the same methods, awaited, and many at once."""

import asyncio

from common import make_domain

from libvirtpy.client import AsyncFakeTransport, AsyncLibvirtClient


async def main() -> None:
    async with AsyncLibvirtClient(AsyncFakeTransport()) as client:
        names = [f"node{n}" for n in range(1, 6)]

        # Define and start five domains concurrently.
        await asyncio.gather(*(client.define_domain(make_domain(n)) for n in names))
        await asyncio.gather(*(client.start_domain(n) for n in names))

        states = await asyncio.gather(*(client.get_domain_state(n) for n in names))
        print({n: s.name for n, s in zip(names, states, strict=True)})

        # Wait on a mix of different resources.
        version, hostname, running = await asyncio.gather(
            client.get_version(),
            client.get_hostname(),
            client.list_domains(active=True),
        )
        print(f"{hostname}: libvirt {version}, {len(running)} domains running")


asyncio.run(main())
