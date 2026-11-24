"""Read the host's hardware and the tuning of a domain.

Typed parameters (memory, CPU scheduler, block I/O, NUMA) come back as plain
dicts. The matching ``set_domain_*_parameters`` take a dict too; the example
only reads.

    python examples/real/08_host_and_tuning.py [URI] [DOMAIN]
"""

import sys

from common import parse_arguments, run

from libvirtpy.client import LibvirtClient


def show_host(client: LibvirtClient) -> None:
    """Print the hardware and the load of the host.

    :param client: an open client.
    """
    info = client.get_host_info()
    print(f"{info.cpus} CPUs at {info.mhz} MHz, {info.memory // 1024} MiB of memory")
    print("CPU time (ns):", client.get_host_cpu_stats())
    print("memory (KiB):", client.get_host_memory_stats())
    print("free memory per NUMA cell:", client.get_host_cells_free_memory())


def show_tuning(client: LibvirtClient, name: str) -> None:
    """Print the tuning of one domain.

    :param client: an open client.
    :param name: the domain name.
    """
    print(f"\n{name}:")
    print("  scheduler:", client.get_domain_scheduler_parameters(name))
    print("  memory limits:", client.get_domain_memory_parameters(name))
    print("  block I/O weight:", client.get_domain_blkio_parameters(name))
    print("  running:", client.is_domain_active(name))


def main() -> int:
    """Run the example.

    :returns: the exit status.
    """
    arguments = parse_arguments(__doc__.splitlines()[0], "qemu:///system")

    def work() -> None:
        with LibvirtClient.open(arguments.uri) as client:
            show_host(client)
            for domain in client.list_domains()[:3]:
                show_tuning(client, str(domain.name))

    return run(work)


if __name__ == "__main__":
    sys.exit(main())
