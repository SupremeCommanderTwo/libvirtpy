import pytest
from pydantic import ValidationError

from libvirtpy.xml.domain.devices import (
    AudioSettings,
    AudioStream,
    Devices,
    NoneAudio,
    PulseaudioAudio,
    PulseaudioStream,
)


def test_audio_type_selects_the_variant() -> None:
    devices = Devices.from_xml(
        "<devices><audio id='1' type='none'/>"
        "<audio id='2' type='pulseaudio' serverName='/run/pulse'>"
        "<output name='out' latency='20'/></audio></devices>"
    )

    assert devices.audios == [
        NoneAudio(id=1, type="none"),
        PulseaudioAudio(
            id=2,
            type="pulseaudio",
            server_name="/run/pulse",
            output=PulseaudioStream(name="out", latency=20),
        ),
    ]


def test_input_and_output_streams_use_their_own_tags() -> None:
    audio = NoneAudio(
        id=1, type="none", input=AudioStream(voices=1), output=AudioStream()
    )

    assert (
        audio.to_xml()
        == b'<audio id="1" type="none"><input voices="1"/><output/></audio>'
    )


def test_stream_settings() -> None:
    devices = Devices.from_xml(
        "<devices><audio id='1' type='none'><output><settings frequency='44100' "
        "channels='2' format='s16'/></output></audio></devices>"
    )

    output = devices.audios[0].output
    assert output is not None
    assert output.settings == AudioSettings(frequency=44100, channels=2, format="s16")


def test_audio_requires_id() -> None:
    with pytest.raises(ValidationError):
        Devices.from_xml("<devices><audio type='none'/></devices>")


def test_audio_rejects_unknown_type() -> None:
    with pytest.raises(ValidationError):
        Devices.from_xml("<devices><audio id='1' type='telepathy'/></devices>")
