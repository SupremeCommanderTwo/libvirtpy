"""Ask several hosts at once with the async client.

Every URI may be of any kind (local, ssh, tls). The connections are opened and
queried concurrently, so the slowest host decides how long it takes, not the
sum. A host that fails is reported and does not stop the others.

    python examples/real/06_async_many_hosts.py qemu:///system 'qemu+ssh://root@kvm1/system'
"""

import argparse
import asyncio
import sys

from libvirtpy.client import AsyncLibvirtClient, LibvirtError


async def inspect(uri: str) -> str:
    """Connect to one host and describe it in a line.

    :param uri: the libvirt URI of the host.
    :returns: the line to print: the host name and its domain count, or the error.
    """
    try:
        async with await AsyncLibvirtClient.open(uri, read_only=True) as client:
            hostname, domains = await asyncio.gather(
                client.get_hostname(), client.list_domains()
            )
    except (ConnectionError, LibvirtError) as error:
        return f"{uri}: FAILED: {error}"
    return f"{uri}: {hostname}, {len(domains)} domains"


async def main() -> int:
    """Run the example.

    :returns: the exit status.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "uris", nargs="*", default=["qemu:///system"], help="libvirt URIs"
    )
    arguments = parser.parse_args()

    for line in await asyncio.gather(*(inspect(uri) for uri in arguments.uris)):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
