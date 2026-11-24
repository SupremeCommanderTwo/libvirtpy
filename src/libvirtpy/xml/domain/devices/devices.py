"""``<devices>``: the container of all guest devices.

Device kinds not modelled yet are ignored on parsing; the corpus round-trip
report lists them.

See https://libvirt.org/formatdomain.html#devices
"""

from pydantic_xml import element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml.domain.devices.audio import Audio
from libvirtpy.xml.domain.devices.chardev import Channel, Console, Parallel, Serial
from libvirtpy.xml.domain.devices.controller import Controller
from libvirtpy.xml.domain.devices.disk import Disk
from libvirtpy.xml.domain.devices.filesystem import Filesystem
from libvirtpy.xml.domain.devices.graphics import Graphics
from libvirtpy.xml.domain.devices.hostdev import Hostdev
from libvirtpy.xml.domain.devices.input import Input
from libvirtpy.xml.domain.devices.interface import Interface
from libvirtpy.xml.domain.devices.iommu import Iommu
from libvirtpy.xml.domain.devices.memballoon import Memballoon
from libvirtpy.xml.domain.devices.memory_device import MemoryDevice
from libvirtpy.xml.domain.devices.misc import (
    Crypto,
    Lease,
    Panic,
    Pstore,
    Rng,
    Vsock,
    Watchdog,
)
from libvirtpy.xml.domain.devices.nvram import NvramDevice
from libvirtpy.xml.domain.devices.shmem import Shmem
from libvirtpy.xml.domain.devices.sound import Sound
from libvirtpy.xml.domain.devices.tpm import Tpm
from libvirtpy.xml.domain.devices.usb import Hub, Redirdev, RedirFilter, Smartcard
from libvirtpy.xml.domain.devices.video import Video

__all__ = ["Devices"]


class Devices(LibvirtXmlModel, tag="devices"):
    """``<devices>``: one list per device kind, in document order per kind."""

    emulator: str | None = element(
        tag="emulator", default=None, description="Path of the device model binary."
    )
    disks: list[Disk] = element(tag="disk", default_factory=list)
    audios: list[Audio] = element(tag="audio", default_factory=list)
    interfaces: list[Interface] = element(tag="interface", default_factory=list)
    graphics: list[Graphics] = element(tag="graphics", default_factory=list)
    serials: list[Serial] = element(tag="serial", default_factory=list)
    consoles: list[Console] = element(tag="console", default_factory=list)
    parallels: list[Parallel] = element(tag="parallel", default_factory=list)
    channels: list[Channel] = element(tag="channel", default_factory=list)
    rngs: list[Rng] = element(tag="rng", default_factory=list)
    watchdogs: list[Watchdog] = element(tag="watchdog", default_factory=list)
    panics: list[Panic] = element(tag="panic", default_factory=list)
    hostdevs: list[Hostdev] = element(tag="hostdev", default_factory=list)
    filesystems: list[Filesystem] = element(tag="filesystem", default_factory=list)
    sounds: list[Sound] = element(tag="sound", default_factory=list)
    smartcards: list[Smartcard] = element(tag="smartcard", default_factory=list)
    hubs: list[Hub] = element(tag="hub", default_factory=list)
    redirdevs: list[Redirdev] = element(tag="redirdev", default_factory=list)
    redirfilter: RedirFilter | None = element(tag="redirfilter", default=None)
    tpms: list[Tpm] = element(tag="tpm", default_factory=list)
    shmems: list[Shmem] = element(tag="shmem", default_factory=list)
    memories: list[MemoryDevice] = element(tag="memory", default_factory=list)
    crypto: Crypto | None = element(tag="crypto", default=None)
    leases: list[Lease] = element(tag="lease", default_factory=list)
    iommus: list[Iommu] = element(tag="iommu", default_factory=list)
    vsock: Vsock | None = element(tag="vsock", default=None)
    pstore: Pstore | None = element(tag="pstore", default=None)
    controllers: list[Controller] = element(tag="controller", default_factory=list)
    inputs: list[Input] = element(tag="input", default_factory=list)
    videos: list[Video] = element(tag="video", default_factory=list)
    memballoon: Memballoon | None = element(tag="memballoon", default=None)
    nvram: NvramDevice | None = element(tag="nvram", default=None)
