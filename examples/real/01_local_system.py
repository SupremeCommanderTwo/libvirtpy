"""Connect to the libvirt daemon of this machine: ``qemu:///system``.

The client finds the daemon's UNIX socket by itself: the modular daemons
(``virtqemud``, ``virtnetworkd``, ...) first, the monolithic ``libvirtd`` after.
The polkit authentication the daemon asks for is done automatically.

    python examples/real/01_local_system.py
"""

import sys

from common import parse_arguments, run, summarize

from libvirtpy.client import LibvirtClient


def main() -> int:
    """Run the example.

    :returns: the exit status.
    """
    arguments = parse_arguments(__doc__.splitlines()[0], "qemu:///system")

    def work() -> None:
        with LibvirtClient.open(arguments.uri, read_only=True) as client:
            summarize(client)

    return run(work)


if __name__ == "__main__":
    sys.exit(main())
