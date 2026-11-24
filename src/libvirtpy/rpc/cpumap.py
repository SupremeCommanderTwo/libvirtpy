"""CPU bitmaps: the wire form of "these host CPUs" (bit ``n`` of byte ``n // 8``)."""

from collections.abc import Iterable

__all__ = ["from_cpumap", "map_length", "to_cpumap"]


def to_cpumap(cpus: Iterable[int], length: int = 0) -> bytes:
    """Make the bitmap of a set of CPU numbers.

    :param cpus: the CPU numbers.
    :param length: the least number of bytes of the bitmap; it grows to hold the
        highest CPU.
    :returns: the bitmap.
    :raises ValueError: if a CPU number is negative.
    """
    wanted = sorted(set(cpus))
    if wanted and wanted[0] < 0:
        raise ValueError(f"CPU numbers are not negative: {wanted[0]}")

    size = max(length, (wanted[-1] // 8 + 1) if wanted else 1)
    bitmap = bytearray(size)
    for cpu in wanted:
        bitmap[cpu // 8] |= 1 << (cpu % 8)
    return bytes(bitmap)


def from_cpumap(bitmap: bytes) -> list[int]:
    """List the CPU numbers of a bitmap.

    :param bitmap: the bitmap.
    :returns: the CPU numbers that are set, ascending.
    """
    return [
        index * 8 + bit
        for index, byte in enumerate(bitmap)
        for bit in range(8)
        if byte >> bit & 1
    ]


def map_length(cpu_count: int) -> int:
    """Return the bytes needed for a bitmap of ``cpu_count`` CPUs.

    :param cpu_count: the number of CPUs of the host.
    :returns: ``ceil(cpu_count / 8)``, at least 1.
    """
    return max(1, (cpu_count + 7) // 8)
