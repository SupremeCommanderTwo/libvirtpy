"""Helpers shared by the examples that connect to a real libvirt daemon.

Everything here only reads: connections are opened read-only.
"""

import argparse
import os
import sys
from collections.abc import Sequence

from libvirtpy.client import LibvirtClient, LibvirtError, SaslCredentials


def parse_arguments(
    description: str, default_uri: str, argv: Sequence[str] | None = None
) -> argparse.Namespace:
    """Read the command line shared by the examples.

    :param description: what the example does, for ``--help``.
    :param default_uri: the URI used when none is given.
    :param argv: the arguments; ``sys.argv`` if left out.
    :returns: the parsed arguments (``uri``).
    """
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "uri",
        nargs="?",
        default=os.environ.get("LIBVIRT_URI", default_uri),
        help=f"libvirt URI (default: $LIBVIRT_URI or {default_uri})",
    )
    return parser.parse_args(argv)


def credentials_from_environment() -> SaslCredentials | None:
    """Read SASL credentials from ``LIBVIRT_USER`` and ``LIBVIRT_PASSWORD``.

    They come from the environment, not the command line, so that the password
    stays out of the process list and the shell history.

    :returns: the credentials, or ``None`` if the variables are not set.
    """
    user = os.environ.get("LIBVIRT_USER")
    password = os.environ.get("LIBVIRT_PASSWORD")
    if not user or password is None:
        return None
    return SaslCredentials(user, password)


def summarize(client: LibvirtClient) -> None:
    """Print what the host runs: version, domains, networks and pools.

    :param client: an open client.
    """
    print(f"host: {client.get_hostname()}, hypervisor version {client.get_version()}")

    domains = client.list_domains()
    print(f"{len(domains)} domains:")
    for domain in domains:
        state = client.get_domain_state(domain).name.lower()
        print(f"  {domain.name} ({state})")

    print("networks:", [network.name for network in client.list_networks()])
    print("storage pools:", [pool.name for pool in client.list_pools()])


def run(action: object) -> int:
    """Call ``action()`` and turn connection problems into a message.

    :param action: a function without arguments that does the example's work.
    :returns: the exit status: 0, or 1 after printing the problem.
    """
    try:
        action()  # type: ignore[operator]
    except (ConnectionError, LibvirtError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0
