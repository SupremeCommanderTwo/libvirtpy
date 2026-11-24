"""``<graphics>``: how the guest display is exposed on the host.

One class per graphics ``type``; ``Graphics`` is their plain union (see
``libvirtpy.xml.domain.devices.address`` for why it is not a discriminated one).

See https://libvirt.org/formatdomain.html#graphical-framebuffers
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._types import YesNo

__all__ = [
    "AddressListen",
    "DbusGraphics",
    "DesktopGraphics",
    "EglHeadlessGraphics",
    "Graphics",
    "GraphicsAudio",
    "GraphicsGl",
    "Listen",
    "NetworkListen",
    "NoneListen",
    "RdpGraphics",
    "SdlGraphics",
    "SocketListen",
    "SpiceChannel",
    "SpiceGraphics",
    "VncGraphics",
]


class AddressListen(LibvirtXmlModel, tag="listen"):
    """``<listen type='address'>``: listen on an IP address or host name."""

    type: Literal["address"] = attr(name="type")
    address: str | None = attr(name="address", default=None)


class NetworkListen(LibvirtXmlModel, tag="listen"):
    """``<listen type='network'>``: listen on the address of a libvirt network."""

    type: Literal["network"] = attr(name="type")
    network: str = attr(name="network")
    address: str | None = attr(
        name="address", default=None, description="Filled in by libvirt."
    )


class SocketListen(LibvirtXmlModel, tag="listen"):
    """``<listen type='socket'>``: listen on a UNIX socket."""

    type: Literal["socket"] = attr(name="type")
    socket: str | None = attr(name="socket", default=None)


class NoneListen(LibvirtXmlModel, tag="listen"):
    """``<listen type='none'>``: do not listen on the host."""

    type: Literal["none"] = attr(name="type")


Listen = AddressListen | NetworkListen | SocketListen | NoneListen
"""Any ``<listen>``; the variant is chosen by its ``type`` attribute."""


class GraphicsGl(LibvirtXmlModel, tag="gl"):
    """``<gl>``: OpenGL acceleration."""

    enable: YesNo | None = attr(name="enable", default=None)
    rendernode: str | None = attr(name="rendernode", default=None)


class GraphicsAudio(LibvirtXmlModel, tag="audio"):
    """``<audio>``: the ``<audio>`` device (by ``id``) the display uses."""

    id: int = attr(name="id", ge=0, le=255)


class _GraphicsBase(LibvirtXmlModel, tag="graphics"):
    """Attributes and children every graphics type has."""

    listens: list[Listen] = element(tag="listen", default_factory=list)


class _NetworkGraphicsBase(_GraphicsBase):
    """Attributes of the graphics types that listen on a port."""

    port: int | None = attr(name="port", default=None, ge=-1, le=65535)
    autoport: YesNo | None = attr(name="autoport", default=None)
    listen: str | None = attr(
        name="listen", default=None, description="Shortcut of ``<listen>``."
    )
    passwd: str | None = attr(name="passwd", default=None)
    passwd_valid_to: str | None = attr(name="passwdValidTo", default=None)
    keymap: str | None = attr(name="keymap", default=None)
    connected: Literal["fail", "disconnect", "keep"] | None = attr(
        name="connected", default=None
    )


class SdlGraphics(_GraphicsBase, tag="graphics"):
    """``type='sdl'``: a window on the host display."""

    type: Literal["sdl"] = attr(name="type")
    display: str | None = attr(name="display", default=None)
    xauth: str | None = attr(name="xauth", default=None)
    fullscreen: YesNo | None = attr(name="fullscreen", default=None)
    gl: GraphicsGl | None = element(tag="gl", default=None)


class VncGraphics(_NetworkGraphicsBase, tag="graphics"):
    """``type='vnc'``: a VNC server."""

    type: Literal["vnc"] = attr(name="type")
    websocket: int | None = attr(name="websocket", default=None, ge=-1, le=65535)
    share_policy: Literal["allow-exclusive", "force-shared", "ignore"] | None = attr(
        name="sharePolicy", default=None
    )
    power_control: YesNo | None = attr(name="powerControl", default=None)
    wait: YesNo | None = attr(name="wait", default=None)
    socket: str | None = attr(name="socket", default=None)
    audio: GraphicsAudio | None = element(tag="audio", default=None)


class SpiceChannel(LibvirtXmlModel, tag="channel"):
    """``<channel>``: the security mode of one SPICE channel."""

    name: Literal[
        "main",
        "display",
        "inputs",
        "cursor",
        "playback",
        "record",
        "smartcard",
        "usbredir",
    ] = attr(name="name")
    mode: Literal["any", "secure", "insecure"] = attr(name="mode")


class SpiceImage(LibvirtXmlModel, tag="image"):
    compression: Literal["auto_glz", "auto_lz", "quic", "glz", "lz", "off"] = attr(
        name="compression"
    )


class SpiceJpeg(LibvirtXmlModel, tag="jpeg"):
    compression: Literal["auto", "never", "always"] = attr(name="compression")


class SpiceZlib(LibvirtXmlModel, tag="zlib"):
    compression: Literal["auto", "never", "always"] = attr(name="compression")


class SpicePlayback(LibvirtXmlModel, tag="playback"):
    compression: Literal["on", "off"] = attr(name="compression")


class SpiceStreaming(LibvirtXmlModel, tag="streaming"):
    mode: Literal["filter", "all", "off"] = attr(name="mode")


class SpiceClipboard(LibvirtXmlModel, tag="clipboard"):
    copypaste: YesNo = attr(name="copypaste")


class SpiceMouse(LibvirtXmlModel, tag="mouse"):
    mode: Literal["server", "client"] = attr(name="mode")


class SpiceFiletransfer(LibvirtXmlModel, tag="filetransfer"):
    enable: YesNo = attr(name="enable")


class SpiceGraphics(_NetworkGraphicsBase, tag="graphics"):
    """``type='spice'``: a SPICE server."""

    type: Literal["spice"] = attr(name="type")
    tls_port: int | None = attr(name="tlsPort", default=None, ge=-1, le=65535)
    default_mode: Literal["any", "secure", "insecure"] | None = attr(
        name="defaultMode", default=None
    )
    channels: list[SpiceChannel] = element(tag="channel", default_factory=list)
    image: SpiceImage | None = element(tag="image", default=None)
    jpeg: SpiceJpeg | None = element(tag="jpeg", default=None)
    zlib: SpiceZlib | None = element(tag="zlib", default=None)
    playback: SpicePlayback | None = element(tag="playback", default=None)
    streaming: SpiceStreaming | None = element(tag="streaming", default=None)
    clipboard: SpiceClipboard | None = element(tag="clipboard", default=None)
    mouse: SpiceMouse | None = element(tag="mouse", default=None)
    filetransfer: SpiceFiletransfer | None = element(tag="filetransfer", default=None)
    gl: GraphicsGl | None = element(tag="gl", default=None)


class DbusGraphics(_GraphicsBase, tag="graphics"):
    """``type='dbus'``: a D-Bus display."""

    type: Literal["dbus"] = attr(name="type")
    address: str | None = attr(name="address", default=None)
    p2p: YesNo | None = attr(name="p2p", default=None)
    gl: GraphicsGl | None = element(tag="gl", default=None)
    audio: GraphicsAudio | None = element(tag="audio", default=None)


class RdpGraphics(_GraphicsBase, tag="graphics"):
    """``type='rdp'``: an RDP server."""

    type: Literal["rdp"] = attr(name="type")
    port: int | None = attr(name="port", default=None, ge=-1, le=65535)
    autoport: YesNo | None = attr(name="autoport", default=None)
    replace_user: YesNo | None = attr(name="replaceUser", default=None)
    multi_user: YesNo | None = attr(name="multiUser", default=None)
    listen: str | None = attr(name="listen", default=None)
    username: str | None = attr(name="username", default=None)
    passwd: str | None = attr(name="passwd", default=None)


class DesktopGraphics(_GraphicsBase, tag="graphics"):
    """``type='desktop'``: a window on the host desktop (VirtualBox)."""

    type: Literal["desktop"] = attr(name="type")
    display: str | None = attr(name="display", default=None)


class EglHeadlessGraphics(_GraphicsBase, tag="graphics"):
    """``type='egl-headless'``: remote rendering without a display."""

    type: Literal["egl-headless"] = attr(name="type")
    gl: GraphicsGl | None = element(tag="gl", default=None)


Graphics = (
    SdlGraphics
    | VncGraphics
    | SpiceGraphics
    | DbusGraphics
    | RdpGraphics
    | DesktopGraphics
    | EglHeadlessGraphics
)
"""Any ``<graphics>``; the variant is chosen by its ``type`` attribute."""
