"""Errors raised by the client.

A libvirt daemon reports a failure as a numeric ``code`` (``virErrorNumber``) and
a ``domain`` (the part of libvirt that failed). ``LibvirtError`` carries both,
and the common codes have their own subclass so callers can write
``except NoDomainError``.

``ErrorNumber`` lists the codes the prototype knows; the full list will be
generated from ``include/libvirt/virterror.h``.
"""

from enum import IntEnum

from libvirtpy.errors import LibvirtPyError

__all__ = [
    "AuthFailedError",
    "ErrorNumber",
    "ExistsError",
    "InvalidArgumentError",
    "LibvirtError",
    "NoCheckpointError",
    "NoDomainError",
    "NoFilterBindingError",
    "NoFilterError",
    "NoInterfaceError",
    "NoNetworkError",
    "NoNetworkPortError",
    "NoNodeDeviceError",
    "NoSecretError",
    "NoSnapshotError",
    "NoStoragePoolError",
    "NoStorageVolumeError",
    "NotSupportedError",
    "OperationInvalidError",
    "error_class_for",
]


class ErrorNumber(IntEnum):
    """The libvirt error codes (``virErrorNumber``) that have a dedicated class."""

    OK = 0
    INTERNAL_ERROR = 1
    NO_SUPPORT = 3
    INVALID_ARG = 8
    OPERATION_FAILED = 9
    XML_ERROR = 27
    DOM_EXIST = 28
    OPERATION_DENIED = 29
    NETWORK_EXIST = 37
    NO_DOMAIN = 42
    NO_NETWORK = 43
    AUTH_FAILED = 45
    NO_STORAGE_POOL = 49
    NO_STORAGE_VOL = 50
    NO_NODE_DEVICE = 53
    OPERATION_INVALID = 55
    NO_INTERFACE = 57
    NO_NWFILTER = 62
    NO_SECRET = 66
    NO_DOMAIN_SNAPSHOT = 72
    NO_NWFILTER_BINDING = 101
    NO_DOMAIN_CHECKPOINT = 103
    NO_NETWORK_PORT = 107


class LibvirtError(LibvirtPyError):
    """A libvirt daemon reported an error."""

    def __init__(
        self,
        message: str,
        *,
        code: int = ErrorNumber.INTERNAL_ERROR,
        domain: int = 0,
    ) -> None:
        """Create the error.

        :param message: the daemon's description of the failure.
        :param code: the ``virErrorNumber`` of the failure.
        :param domain: the ``virErrorDomain``: the part of libvirt that failed.
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.domain = domain


class NoDomainError(LibvirtError):
    """The domain does not exist."""


class NoNetworkError(LibvirtError):
    """The network does not exist."""


class NoStoragePoolError(LibvirtError):
    """The storage pool does not exist."""


class NoStorageVolumeError(LibvirtError):
    """The storage volume does not exist."""


class NoSecretError(LibvirtError):
    """The secret does not exist."""


class NoNodeDeviceError(LibvirtError):
    """The host device does not exist."""


class NoInterfaceError(LibvirtError):
    """The host interface does not exist."""


class NoFilterError(LibvirtError):
    """The network filter does not exist."""


class NoSnapshotError(LibvirtError):
    """The domain snapshot does not exist."""


class NoCheckpointError(LibvirtError):
    """The domain checkpoint does not exist."""


class NoNetworkPortError(LibvirtError):
    """The network port does not exist."""


class NoFilterBindingError(LibvirtError):
    """The network filter binding does not exist."""


class OperationInvalidError(LibvirtError):
    """The operation does not apply in the object's current state."""


class ExistsError(LibvirtError):
    """An object with that name or UUID already exists."""


class InvalidArgumentError(LibvirtError):
    """An argument is invalid."""


class NotSupportedError(LibvirtError):
    """The hypervisor does not support the operation."""


class AuthFailedError(LibvirtError):
    """Authentication failed."""


_CLASSES: dict[int, type[LibvirtError]] = {
    ErrorNumber.NO_DOMAIN: NoDomainError,
    ErrorNumber.NO_NETWORK: NoNetworkError,
    ErrorNumber.NO_STORAGE_POOL: NoStoragePoolError,
    ErrorNumber.NO_STORAGE_VOL: NoStorageVolumeError,
    ErrorNumber.NO_SECRET: NoSecretError,
    ErrorNumber.NO_NODE_DEVICE: NoNodeDeviceError,
    ErrorNumber.NO_INTERFACE: NoInterfaceError,
    ErrorNumber.NO_NWFILTER: NoFilterError,
    ErrorNumber.NO_DOMAIN_SNAPSHOT: NoSnapshotError,
    ErrorNumber.NO_DOMAIN_CHECKPOINT: NoCheckpointError,
    ErrorNumber.NO_NETWORK_PORT: NoNetworkPortError,
    ErrorNumber.NO_NWFILTER_BINDING: NoFilterBindingError,
    ErrorNumber.OPERATION_INVALID: OperationInvalidError,
    ErrorNumber.DOM_EXIST: ExistsError,
    ErrorNumber.NETWORK_EXIST: ExistsError,
    ErrorNumber.INVALID_ARG: InvalidArgumentError,
    ErrorNumber.NO_SUPPORT: NotSupportedError,
    ErrorNumber.AUTH_FAILED: AuthFailedError,
}


def error_class_for(code: int) -> type[LibvirtError]:
    """Return the exception class for a ``virErrorNumber``.

    :param code: the error code reported by the daemon.
    :returns: the dedicated subclass, or ``LibvirtError`` for other codes.
    """
    return _CLASSES.get(code, LibvirtError)
