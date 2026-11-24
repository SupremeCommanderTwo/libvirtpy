from libvirtpy.xml.domain.devices import Video, VideoAcceleration, VideoModel


def test_video_model_with_acceleration() -> None:
    video = Video.from_xml(
        "<video><model type='virtio' heads='1' primary='yes'>"
        "<acceleration accel3d='yes'/></model></video>"
    )

    assert video.model == VideoModel(
        type="virtio",
        heads=1,
        primary=True,
        acceleration=VideoAcceleration(accel3d=True),
    )


def test_qxl_memory_sizes() -> None:
    video = Video.from_xml(
        "<video><model type='qxl' ram='65536' vram='65536' vgamem='16384'/></video>"
    )

    assert video.model == VideoModel(type="qxl", ram=65536, vram=65536, vgamem=16384)
