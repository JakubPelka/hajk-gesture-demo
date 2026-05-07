import time
from dataclasses import dataclass

import cv2

from config import CAMERA


@dataclass
class CameraFrame:
    frame: object
    fps: float
    frame_width: int
    frame_height: int


class Camera:
    def __init__(self, camera_index: int = CAMERA.camera_index) -> None:
        self.camera_index = camera_index
        self.capture: cv2.VideoCapture | None = None
        self._last_time = time.perf_counter()
        self._fps = 0.0

    def open(self) -> None:
        self.capture = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)

        if not self.capture.isOpened():
            self.capture = cv2.VideoCapture(self.camera_index)

        if not self.capture.isOpened():
            raise RuntimeError(f"Could not open camera with index {self.camera_index}")

        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA.width)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA.height)
        self.capture.set(cv2.CAP_PROP_FPS, CAMERA.fps)

    def read(self) -> CameraFrame:
        if self.capture is None:
            raise RuntimeError("Camera is not opened")

        ok, frame = self.capture.read()

        if not ok or frame is None:
            raise RuntimeError("Could not read frame from camera")

        if CAMERA.mirror_preview:
            frame = cv2.flip(frame, 1)

        now = time.perf_counter()
        delta = now - self._last_time
        self._last_time = now

        if delta > 0:
            current_fps = 1.0 / delta
            if self._fps:
                self._fps = self._fps * 0.85 + current_fps * 0.15
            else:
                self._fps = current_fps

        height, width = frame.shape[:2]

        return CameraFrame(
            frame=frame,
            fps=self._fps,
            frame_width=width,
            frame_height=height,
        )

    def release(self) -> None:
        if self.capture is not None:
            self.capture.release()
            self.capture = None