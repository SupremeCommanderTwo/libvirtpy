"""Watch what happens to domains, as it happens (no polling).

The daemon pushes an event when a domain is defined, started, suspended, stopped
or crashes. Start and stop a VM in another terminal (``virsh start vm``) and watch.
Press Ctrl-C to stop.

    python examples/real/09_watch_events.py [URI]
"""

import sys

from common import parse_arguments, run

from libvirtpy.client import DomainEventKind, LibvirtClient


def watch(client: LibvirtClient) -> None:
    """Print domain events until interrupted.

    :param client: an open client.
    """
    kinds = [
        DomainEventKind.LIFECYCLE,
        DomainEventKind.REBOOT,
        DomainEventKind.IO_ERROR,
    ]
    print("waiting for events, Ctrl-C to stop")

    with client.events("domain", kinds) as events:
        try:
            for event in events:
                what = event.lifecycle or event.kind
                print(f"{event.name}: {what}")
        except KeyboardInterrupt:
            print("stopped")


def main() -> int:
    """Run the example.

    :returns: the exit status.
    """
    arguments = parse_arguments(__doc__.splitlines()[0], "qemu:///system")

    def work() -> None:
        with LibvirtClient.open(arguments.uri, read_only=True) as client:
            watch(client)

    return run(work)


if __name__ == "__main__":
    sys.exit(main())
