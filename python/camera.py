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
    camera_index: int


class Camera:
    def __init__(self, camera_index: int = CAMERA.camera_index) -> None:
        self.camera_index = camera_index
        self.capture: cv2.VideoCapture | None = None
        self._last_time = time.perf_counter()
        self._fps = 0.0

    def open(self) -> None:
        self._open_index(self.camera_index)

    def switch_to_index(self, camera_index: int) -> None:
        previous_index = self.camera_index

        try:
            self.release()
            self.camera_index = camera_index
            self._open_index(camera_index)
            self._reset_fps()

        except RuntimeError:
            self.release()
            self.camera_index = previous_index
            self._open_index(previous_index)
            self._reset_fps()
            raise

    def switch_to_next(self, max_camera_index: int = 5) -> int:
        if max_camera_index < 0:
            raise RuntimeError("max_camera_index must be 0 or greater")

        start_index = self.camera_index

        for step in range(1, max_camera_index + 2):
            candidate_index = (start_index + step) % (max_camera_index + 1)

            try:
                self.switch_to_index(candidate_index)
                return self.camera_index

            except RuntimeError:
                continue

        raise RuntimeError(
            f"Could not find another working camera in range 0-{max_camera_index}"
        )

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
            camera_index=self.camera_index,
        )

    def release(self) -> None:
        if self.capture is not None:
            self.capture.release()
            self.capture = None

    def _open_index(self, camera_index: int) -> None:
        self.capture = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)

        if not self.capture.isOpened():
            self.capture = cv2.VideoCapture(camera_index)

        if not self.capture.isOpened():
            self.capture = None
            raise RuntimeError(f"Could not open camera with index {camera_index}")

        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA.width)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA.height)
        self.capture.set(cv2.CAP_PROP_FPS, CAMERA.fps)

        if not self._can_read_frame():
            self.release()
            raise RuntimeError(f"Camera index {camera_index} opened but did not return frames")

    def _can_read_frame(self) -> bool:
        if self.capture is None:
            return False

        for _ in range(5):
            ok, frame = self.capture.read()

            if ok and frame is not None:
                return True

        return False

    def _reset_fps(self) -> None:
        self._last_time = time.perf_counter()
        self._fps = 0.0