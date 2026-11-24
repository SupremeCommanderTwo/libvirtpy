"""Connect to a remote host over SSH: ``qemu+ssh://user@host/system``.

The client runs your ``ssh`` program, so your keys, ``ssh-agent`` and
``~/.ssh/config`` apply. On the host it runs ``virt-ssh-helper`` (or ``nc -U``
when that is missing) and speaks libvirt's protocol over the pipe. Nothing needs
to listen on the network except sshd.

URI parameters (all optional):

    keyfile=/path/to/key      ssh -i
    proxy=native|netcat|auto  how to reach the daemon on the host
    socket=/path              socket for the netcat proxy
    no_tty=1                  never ask for a password (BatchMode)
    known_hosts_verify=ignore do not check the host key (unsafe)

    python examples/real/03_ssh.py 'qemu+ssh://root@kvm1.example.org/system'
"""

import sys

from common import parse_arguments, run, summarize

from libvirtpy.client import LibvirtClient


def main() -> int:
    """Run the example.

    :returns: the exit status.
    """
    arguments = parse_arguments(
        __doc__.splitlines()[0], "qemu+ssh://root@kvm1.example.org/system"
    )

    def work() -> None:
        with LibvirtClient.open(arguments.uri, read_only=True) as client:
            summarize(client)

    return run(work)


if __name__ == "__main__":
    sys.exit(main())
