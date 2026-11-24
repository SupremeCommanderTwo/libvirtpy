"""``<audio>``: host audio backends for the guest's sound devices.

One class per backend ``type``; ``Audio`` is their plain union. Each backend
has an ``<input>`` and an ``<output>`` stream with the same attributes, so the
stream models are shared by both elements (the field gives the tag).

See https://libvirt.org/formatdomain.html#audio-backends
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._types import YesNo

__all__ = [
    "AlsaAudio",
    "AlsaStream",
    "Audio",
    "AudioSettings",
    "AudioStream",
    "CoreaudioAudio",
    "CoreaudioStream",
    "DbusAudio",
    "FileAudio",
    "JackAudio",
    "JackStream",
    "NoneAudio",
    "OssAudio",
    "OssStream",
    "PipewireAudio",
    "PipewireStream",
    "PulseaudioAudio",
    "PulseaudioStream",
    "SdlAudio",
    "SdlStream",
    "SpiceAudio",
]


class AudioSettings(LibvirtXmlModel, tag="settings"):
    """``<settings>``: the fixed format of a stream."""

    frequency: int | None = attr(name="frequency", default=None, ge=0)
    channels: int | None = attr(name="channels", default=None, ge=0)
    format: Literal["s8", "u8", "s16", "u16", "s32", "u32", "f32"] | None = attr(
        name="format", default=None
    )


class AudioStream(LibvirtXmlModel):
    """An ``<input>`` or ``<output>`` stream: the attributes every backend has."""

    mixing_engine: YesNo | None = attr(name="mixingEngine", default=None)
    fixed_settings: YesNo | None = attr(name="fixedSettings", default=None)
    voices: int | None = attr(name="voices", default=None, ge=0)
    buffer_length: int | None = attr(name="bufferLength", default=None, ge=0)
    settings: AudioSettings | None = element(tag="settings", default=None)


class AlsaStream(AudioStream):
    dev: str | None = attr(name="dev", default=None)


class CoreaudioStream(AudioStream):
    buffer_count: int | None = attr(name="bufferCount", default=None, ge=0)


class JackStream(AudioStream):
    server_name: str | None = attr(name="serverName", default=None)
    client_name: str | None = attr(name="clientName", default=None)
    connect_ports: str | None = attr(name="connectPorts", default=None)
    exact_name: YesNo | None = attr(name="exactName", default=None)


class OssStream(AudioStream):
    dev: str | None = attr(name="dev", default=None)
    buffer_count: int | None = attr(name="bufferCount", default=None, ge=0)
    try_poll: YesNo | None = attr(name="tryPoll", default=None)


class PipewireStream(AudioStream):
    name: str | None = attr(name="name", default=None)
    stream_name: str | None = attr(name="streamName", default=None)
    latency: int | None = attr(name="latency", default=None, ge=0)


class PulseaudioStream(AudioStream):
    name: str | None = attr(name="name", default=None)
    stream_name: str | None = attr(name="streamName", default=None)
    latency: int | None = attr(name="latency", default=None, ge=0)


class SdlStream(AudioStream):
    buffer_count: int | None = attr(name="bufferCount", default=None, ge=0)


class _AudioBase(LibvirtXmlModel, tag="audio"):
    """Attributes every ``<audio>`` has."""

    id: int = attr(name="id", ge=0, le=255)
    timer_period: int | None = attr(
        name="timerPeriod", default=None, ge=0, description="Microseconds."
    )


class NoneAudio(_AudioBase, tag="audio"):
    """``type='none'``: audio is discarded."""

    type: Literal["none"] = attr(name="type")
    input: AudioStream | None = element(tag="input", default=None)
    output: AudioStream | None = element(tag="output", default=None)


class DbusAudio(_AudioBase, tag="audio"):
    """``type='dbus'``. Since 8.4.0."""

    type: Literal["dbus"] = attr(name="type")
    input: AudioStream | None = element(tag="input", default=None)
    output: AudioStream | None = element(tag="output", default=None)


class AlsaAudio(_AudioBase, tag="audio"):
    type: Literal["alsa"] = attr(name="type")
    input: AlsaStream | None = element(tag="input", default=None)
    output: AlsaStream | None = element(tag="output", default=None)


class CoreaudioAudio(_AudioBase, tag="audio"):
    type: Literal["coreaudio"] = attr(name="type")
    input: CoreaudioStream | None = element(tag="input", default=None)
    output: CoreaudioStream | None = element(tag="output", default=None)


class JackAudio(_AudioBase, tag="audio"):
    type: Literal["jack"] = attr(name="type")
    input: JackStream | None = element(tag="input", default=None)
    output: JackStream | None = element(tag="output", default=None)


class OssAudio(_AudioBase, tag="audio"):
    type: Literal["oss"] = attr(name="type")
    try_mmap: YesNo | None = attr(name="tryMMap", default=None)
    exclusive: YesNo | None = attr(name="exclusive", default=None)
    dsp_policy: int | None = attr(name="dspPolicy", default=None)
    input: OssStream | None = element(tag="input", default=None)
    output: OssStream | None = element(tag="output", default=None)


class PipewireAudio(_AudioBase, tag="audio"):
    type: Literal["pipewire"] = attr(name="type")
    runtime_dir: str | None = attr(name="runtimeDir", default=None)
    input: PipewireStream | None = element(tag="input", default=None)
    output: PipewireStream | None = element(tag="output", default=None)


class PulseaudioAudio(_AudioBase, tag="audio"):
    type: Literal["pulseaudio"] = attr(name="type")
    server_name: str | None = attr(name="serverName", default=None)
    input: PulseaudioStream | None = element(tag="input", default=None)
    output: PulseaudioStream | None = element(tag="output", default=None)


class SdlAudio(_AudioBase, tag="audio"):
    type: Literal["sdl"] = attr(name="type")
    driver: Literal["esd", "alsa", "arts", "pulseaudio"] | None = attr(
        name="driver", default=None
    )
    input: SdlStream | None = element(tag="input", default=None)
    output: SdlStream | None = element(tag="output", default=None)


class SpiceAudio(_AudioBase, tag="audio"):
    """``type='spice'``: audio goes through the SPICE channel."""

    type: Literal["spice"] = attr(name="type")
    input: AudioStream | None = element(tag="input", default=None)
    output: AudioStream | None = element(tag="output", default=None)


class FileAudio(_AudioBase, tag="audio"):
    """``type='file'``: audio is written to a file. Since 7.2.0."""

    type: Literal["file"] = attr(name="type")
    path: str | None = attr(name="path", default=None)
    input: AudioStream | None = element(tag="input", default=None)
    output: AudioStream | None = element(tag="output", default=None)


Audio = (
    NoneAudio
    | DbusAudio
    | AlsaAudio
    | CoreaudioAudio
    | JackAudio
    | OssAudio
    | PipewireAudio
    | PulseaudioAudio
    | SdlAudio
    | SpiceAudio
    | FileAudio
)
"""Any ``<audio>``; the variant is chosen by its ``type`` attribute."""
