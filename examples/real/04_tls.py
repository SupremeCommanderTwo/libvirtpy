"""Connect to a remote host with TLS: ``qemu+tls://host/system``.

Port 16514, with a client certificate. The certificate files are looked up as
libvirt does: ``cacert.pem``, ``clientcert.pem`` and ``clientkey.pem`` in
``pkipath=DIR`` if you give it, else in ``/etc/pki`` (root) or
``~/.pki/libvirt``. The server certificate must match the host name; add
``no_verify=1`` only to test.

    python examples/real/04_tls.py 'qemu+tls://kvm1.example.org/system?pkipath=/home/me/pki'
"""

import sys

from common import parse_arguments, run, summarize

from libvirtpy.client import LibvirtClient


def main() -> int:
    """Run the example.

    :returns: the exit status.
    """
    arguments = parse_arguments(
        __doc__.splitlines()[0], "qemu+tls://kvm1.example.org/system"
    )

    def work() -> None:
        with LibvirtClient.open(arguments.uri, read_only=True) as client:
            summarize(client)

    return run(work)


if __name__ == "__main__":
    sys.exit(main())
