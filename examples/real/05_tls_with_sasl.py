"""Connect with TLS and a user name and password (SASL).

Daemons that use ``auth_tls = "sasl"`` ask for a login after the TLS handshake.
The client does SCRAM-SHA-256, SCRAM-SHA-1, DIGEST-MD5 or PLAIN, whichever the
server offers first in that order. The login comes from the environment:

    export LIBVIRT_USER=alice
    export LIBVIRT_PASSWORD=...
    python examples/real/05_tls_with_sasl.py 'qemu+tls://kvm1.example.org/system'

SASL is refused on plain ``qemu+tcp://`` (no security layer) and Kerberos
(GSSAPI) is not supported.
"""

import sys

from common import credentials_from_environment, parse_arguments, run, summarize

from libvirtpy.client import LibvirtClient


def main() -> int:
    """Run the example.

    :returns: the exit status.
    """
    arguments = parse_arguments(
        __doc__.splitlines()[0], "qemu+tls://kvm1.example.org/system"
    )
    credentials = credentials_from_environment()
    if credentials is None:
        print("set LIBVIRT_USER and LIBVIRT_PASSWORD first", file=sys.stderr)
        return 2

    def work() -> None:
        with LibvirtClient.open(
            arguments.uri, read_only=True, sasl=credentials
        ) as client:
            summarize(client)

    return run(work)


if __name__ == "__main__":
    sys.exit(main())
