"""Connect to your own (unprivileged) libvirt daemon: ``qemu:///session``.

The socket is in ``$XDG_RUNTIME_DIR/libvirt``. The daemon starts on demand with
the first ``virsh --connect qemu:///session`` or ``virt-manager`` session, so
this fails with "no libvirt socket reachable" until one has run.

    python examples/real/02_local_session.py
"""

import sys

from common import parse_arguments, run, summarize

from libvirtpy.client import LibvirtClient


def main() -> int:
    """Run the example.

    :returns: the exit status.
    """
    arguments = parse_arguments(__doc__.splitlines()[0], "qemu:///session")

    def work() -> None:
        with LibvirtClient.open(arguments.uri) as client:
            summarize(client)

    return run(work)


if __name__ == "__main__":
    sys.exit(main())
