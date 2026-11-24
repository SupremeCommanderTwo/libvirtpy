"""Throwaway objects on a real libvirt daemon, always removed afterwards.

Everything a write test creates is named ``lvxtest-<random>`` and registered here.
The cleanup removes only registered objects whose name still has the prefix, so
a bug in a test can never delete one of the machine's own domains, networks or
pools.
"""

import contextlib
import glob
import uuid

from libvirtpy.client import LibvirtClient
from libvirtpy.rpc.errors import LibvirtError

PREFIX = "lvxtest-"
UNDEFINE_MANAGED_SAVE = 1
UNDEFINE_SNAPSHOTS_METADATA = 2
UNDEFINE_NVRAM = 4
UNDEFINE_CHECKPOINTS_METADATA = 16


class Scratch:
    """Names and cleanup of the objects one test creates."""

    def __init__(self, client: LibvirtClient) -> None:
        """Create an empty registry.

        :param client: the connection to clean up with.
        """
        self.client = client
        self.domains: list[str] = []
        self.networks: list[str] = []
        self.pools: list[str] = []
        self.secrets: list[str] = []
        self.filters: list[str] = []

    def name(self, kind: str = "") -> str:
        """Make a unique name with the safety prefix.

        :param kind: a short word that says what the name is for.
        :returns: e.g. ``lvxtest-vm-3fa9c1d2``.
        """
        return f"{PREFIX}{kind + '-' if kind else ''}{uuid.uuid4().hex[:8]}"

    def cleanup(self) -> None:
        """Remove every registered object, newest first, ignoring what is gone."""
        for domain in reversed(self.domains):
            self._remove_domain(domain)
        for network in reversed(self.networks):
            self._remove_network(network)
        for pool in reversed(self.pools):
            self._remove_pool(pool)
        for secret in self.secrets:
            self._ignoring(lambda s=secret: self.client.undefine_secret(s))
        for filter_name in self.filters:
            self._ignoring(lambda f=filter_name: self.client.undefine_nwfilter(f))

    def leftovers(self) -> list[str]:
        """List the test objects still on the daemon.

        :returns: the names that start with the prefix, of any kind.
        """
        client = self.client
        names: list[str | None] = [d.name for d in client.list_domains()]
        names += [n.name for n in client.list_networks()]
        names += [p.name for p in client.list_pools()]
        found = [str(name) for name in names if name and name.startswith(PREFIX)]
        return found + sorted(glob.glob(f"/var/tmp/{PREFIX}*"))

    def _remove_domain(self, name: str) -> None:
        """Stop and undefine a test domain.

        :param name: the domain name; must have the prefix.
        """
        self._check(name)
        self._ignoring(lambda: self.client.destroy_domain(name))
        self._ignoring(lambda: self.client.remove_domain_managed_save(name))
        flags = UNDEFINE_MANAGED_SAVE | UNDEFINE_SNAPSHOTS_METADATA
        flags |= UNDEFINE_CHECKPOINTS_METADATA | UNDEFINE_NVRAM
        self._ignoring(lambda: self.client.undefine_domain(name, flags=flags))

    def _remove_network(self, name: str) -> None:
        """Stop and undefine a test network.

        :param name: the network name; must have the prefix.
        """
        self._check(name)
        self._ignoring(lambda: self.client.destroy_network(name))
        self._ignoring(lambda: self.client.undefine_network(name))

    def _remove_pool(self, name: str) -> None:
        """Delete the volumes of a test pool, then stop, delete and undefine it.

        :param name: the pool name; must have the prefix.
        """
        self._check(name)
        with contextlib.suppress(LibvirtError):
            self.client.refresh_pool(name)
            for volume in self.client.list_pool_volumes(name):
                self.client.delete_pool_volume(name, volume)
        self._ignoring(lambda: self.client.destroy_pool(name))
        self._ignoring(lambda: self.client.delete_pool(name))
        self._ignoring(lambda: self.client.undefine_pool(name))

    @staticmethod
    def _check(name: str) -> None:
        """Refuse to touch an object that is not a test object.

        :param name: the object name.
        :raises AssertionError: if it has no test prefix.
        """
        assert name.startswith(PREFIX), f"refusing to remove {name!r}"

    @staticmethod
    def _ignoring(action: object) -> None:
        """Run a cleanup step, ignoring libvirt's complaint that it is not needed.

        :param action: a function without arguments.
        """
        with contextlib.suppress(LibvirtError):
            action()  # type: ignore[operator]
