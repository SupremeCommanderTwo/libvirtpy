"""Exceptions raised by libvirtpy."""

__all__ = ["LibvirtPyError"]


class LibvirtPyError(Exception):
    """Base class for every error raised on purpose by libvirtpy."""
