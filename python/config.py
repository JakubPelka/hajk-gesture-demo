from dataclasses import dataclass


@dataclass(frozen=True)
class CameraConfig:
    camera_index: int = 1
    width: int = 1280
    height: int = 720
    fps: int = 30
    window_name: str = "Hajk Gesture Demo - Camera Preview"
    mirror_preview: bool = True


@dataclass(frozen=True)
class OverlayConfig:
    font_scale: float = 0.7
    thickness: int = 2
    line_height: int = 28
    margin_x: int = 16
    margin_y: int = 32


CAMERA = CameraConfig()
OVERLAY = OverlayConfig()