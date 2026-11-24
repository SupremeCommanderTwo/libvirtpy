"""Read the configuration of every domain as typed models.

``lookup_domain`` returns a ``libvirtpy.xml.Domain``, so the XML libvirt sends is
already parsed: memory, vCPUs, disks and interfaces are attributes, not strings.

    python examples/real/07_inspect_domains.py [URI]
"""

import sys

from common import parse_arguments, run

from libvirtpy.client import LibvirtClient


def describe(client: LibvirtClient, name: str) -> None:
    """Print the main settings of one domain.

    :param client: an open client.
    :param name: the domain name.
    """
    domain = client.lookup_domain(name)
    devices = domain.devices
    memory = (
        f"{domain.memory.value} {domain.memory.unit or 'KiB'}" if domain.memory else "?"
    )
    vcpus = domain.vcpu.value if domain.vcpu else "?"
    print(f"{domain.name}: type={domain.type}, memory={memory}, vcpus={vcpus}")

    for disk in devices.disks if devices else []:
        target = disk.target.dev if disk.target else "?"
        print(f"  disk {target}: {type(disk).__name__}")
    for interface in devices.interfaces if devices else []:
        print(f"  interface: {type(interface).__name__}")


def main() -> int:
    """Run the example.

    :returns: the exit status.
    """
    arguments = parse_arguments(__doc__.splitlines()[0], "qemu:///system")

    def work() -> None:
        with LibvirtClient.open(arguments.uri, read_only=True) as client:
            for domain in client.list_domains():
                describe(client, str(domain.name))

    return run(work)


if __name__ == "__main__":
    sys.exit(main())
