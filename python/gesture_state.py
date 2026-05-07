import math
import time
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GestureConfig:
    stable_frames: int = 5
    min_gesture_confidence: float = 0.55

    pan_smoothing: float = 0.35
    pan_deadzone_px: float = 4.0
    pan_max_step_px: float = 60.0

    zoom_cooldown_sec: float = 0.7
    gesture_lost_timeout_sec: float = 0.5

    pinch_zoom_in_threshold: float = 0.35
    pinch_zoom_out_threshold: float = 1.30
    pinch_min_hand_scale: float = 0.03


@dataclass
class GestureOutput:
    active: bool
    detected_gesture: str
    stable_gesture: str
    confidence: float
    command: dict[str, Any] | None
    pan_dx: float = 0.0
    pan_dy: float = 0.0
    pinch_ratio: float | None = None


class GestureEngine:
    def __init__(self, config: GestureConfig | None = None) -> None:
        self.config = config or GestureConfig()

        self.active = False

        self._pending_gesture = "None"
        self._stable_gesture = "None"
        self._stable_count = 0

        self._last_seen_time = time.perf_counter()
        self._last_zoom_time = 0.0

        self._previous_center_px: tuple[float, float] | None = None
        self._smoothed_dx = 0.0
        self._smoothed_dy = 0.0

    def update(
        self,
        hand_result,
        frame_width: int,
        frame_height: int,
        key: int | None = None,
    ) -> GestureOutput:
        active_command = self._handle_keyboard(key)

        if not hand_result.detected:
            output = self._handle_no_hand()

            if active_command is not None:
                output.command = active_command

            return output

        hand = hand_result.hands[0]

        detected_gesture = hand.gesture or "None"
        confidence = float(hand.gesture_confidence)
        pinch_ratio = self._calculate_pinch_ratio(hand.landmarks)

        if confidence < self.config.min_gesture_confidence:
            self._reset_pan()

            return self._build_output(
                detected_gesture="LowConfidence",
                confidence=confidence,
                command=active_command,
                pinch_ratio=pinch_ratio,
            )

        self._last_seen_time = time.perf_counter()

        stable_gesture = self._update_stability(detected_gesture)

        command = active_command

        if command is None:
            command = self._make_command(
                hand=hand,
                stable_gesture=stable_gesture,
                frame_width=frame_width,
                frame_height=frame_height,
                pinch_ratio=pinch_ratio,
            )

        return self._build_output(
            detected_gesture=detected_gesture,
            confidence=confidence,
            command=command,
            pinch_ratio=pinch_ratio,
        )

    def _handle_keyboard(self, key: int | None) -> dict[str, Any] | None:
        if key not in (ord("a"), ord("A")):
            return None

        self.active = not self.active
        self._reset_pan()

        return {
            "type": "active",
            "value": self.active,
            "source": "keyboard",
        }

    def _handle_no_hand(self) -> GestureOutput:
        now = time.perf_counter()

        if now - self._last_seen_time > self.config.gesture_lost_timeout_sec:
            self._pending_gesture = "None"
            self._stable_gesture = "None"
            self._stable_count = 0
            self._reset_pan()

        return self._build_output(
            detected_gesture="None",
            confidence=0.0,
            command=None,
            pinch_ratio=None,
        )

    def _update_stability(self, detected_gesture: str) -> str:
        if detected_gesture == self._pending_gesture:
            self._stable_count += 1
        else:
            self._pending_gesture = detected_gesture
            self._stable_count = 1

        if self._stable_count >= self.config.stable_frames:
            self._stable_gesture = detected_gesture

        return self._stable_gesture

    def _make_command(
        self,
        hand,
        stable_gesture: str,
        frame_width: int,
        frame_height: int,
        pinch_ratio: float | None,
    ) -> dict[str, Any] | None:
        if not self.active:
            self._reset_pan()
            return None

        if stable_gesture == "Closed_Fist":
            self._reset_pan()
            return None

        pinch_command = self._make_pinch_zoom_command(
            stable_gesture=stable_gesture,
            pinch_ratio=pinch_ratio,
        )

        if pinch_command is not None:
            self._reset_pan()
            return pinch_command

        if stable_gesture == "Open_Palm":
            return self._make_pan_command(
                hand=hand,
                frame_width=frame_width,
                frame_height=frame_height,
            )

        self._reset_pan()

        if stable_gesture == "Thumb_Up":
            return self._make_zoom_command(delta=1, source="thumb_up")

        if stable_gesture == "Thumb_Down":
            return self._make_zoom_command(delta=-1, source="thumb_down")

        if stable_gesture == "Victory":
            return self._make_zoom_command(delta=-1, source="victory_fallback")

        return None

    def _make_pinch_zoom_command(
        self,
        stable_gesture: str,
        pinch_ratio: float | None,
    ) -> dict[str, Any] | None:
        if pinch_ratio is None:
            return None

        if stable_gesture == "Closed_Fist":
            return None

        if pinch_ratio <= self.config.pinch_zoom_in_threshold:
            return self._make_zoom_command(delta=1, source="pinch_close")

        # Avoid accidental zoom-out during normal Open_Palm panning.
        if stable_gesture != "Open_Palm" and pinch_ratio >= self.config.pinch_zoom_out_threshold:
            return self._make_zoom_command(delta=-1, source="pinch_spread")

        return None

    def _make_pan_command(
        self,
        hand,
        frame_width: int,
        frame_height: int,
    ) -> dict[str, Any] | None:
        center_x = hand.center_x * frame_width
        center_y = hand.center_y * frame_height

        if self._previous_center_px is None:
            self._previous_center_px = (center_x, center_y)
            return None

        previous_x, previous_y = self._previous_center_px
        self._previous_center_px = (center_x, center_y)

        raw_dx = center_x - previous_x
        raw_dy = center_y - previous_y

        alpha = self.config.pan_smoothing

        self._smoothed_dx = self._smoothed_dx * (1.0 - alpha) + raw_dx * alpha
        self._smoothed_dy = self._smoothed_dy * (1.0 - alpha) + raw_dy * alpha

        dx = self._clamp(
            self._smoothed_dx,
            -self.config.pan_max_step_px,
            self.config.pan_max_step_px,
        )

        dy = self._clamp(
            self._smoothed_dy,
            -self.config.pan_max_step_px,
            self.config.pan_max_step_px,
        )

        if abs(dx) < self.config.pan_deadzone_px and abs(dy) < self.config.pan_deadzone_px:
            return None

        return {
            "type": "pan",
            "dx": round(dx, 2),
            "dy": round(dy, 2),
            "strength": round(
                min(1.0, max(abs(dx), abs(dy)) / self.config.pan_max_step_px),
                2,
            ),
            "source": "open_palm",
        }

    def _make_zoom_command(
        self,
        delta: int,
        source: str,
    ) -> dict[str, Any] | None:
        now = time.perf_counter()

        if now - self._last_zoom_time < self.config.zoom_cooldown_sec:
            return None

        self._last_zoom_time = now

        return {
            "type": "zoom",
            "delta": delta,
            "source": source,
        }

    def _calculate_pinch_ratio(
        self,
        landmarks: list[tuple[float, float, float]],
    ) -> float | None:
        if len(landmarks) < 21:
            return None

        thumb_tip = landmarks[4]
        index_tip = landmarks[8]

        wrist = landmarks[0]
        middle_mcp = landmarks[9]
        index_mcp = landmarks[5]
        pinky_mcp = landmarks[17]

        pinch_distance = self._distance_2d(thumb_tip, index_tip)
        palm_depth = self._distance_2d(wrist, middle_mcp)
        palm_width = self._distance_2d(index_mcp, pinky_mcp)

        hand_scale = max(palm_depth, palm_width)

        if hand_scale < self.config.pinch_min_hand_scale:
            return None

        return pinch_distance / hand_scale

    def _distance_2d(
        self,
        point_a: tuple[float, float, float],
        point_b: tuple[float, float, float],
    ) -> float:
        dx = point_a[0] - point_b[0]
        dy = point_a[1] - point_b[1]

        return math.sqrt(dx * dx + dy * dy)

    def _reset_pan(self) -> None:
        self._previous_center_px = None
        self._smoothed_dx = 0.0
        self._smoothed_dy = 0.0

    def _build_output(
        self,
        detected_gesture: str,
        confidence: float,
        command: dict[str, Any] | None,
        pinch_ratio: float | None,
    ) -> GestureOutput:
        pan_dx = 0.0
        pan_dy = 0.0

        if command and command.get("type") == "pan":
            pan_dx = float(command.get("dx", 0.0))
            pan_dy = float(command.get("dy", 0.0))

        return GestureOutput(
            active=self.active,
            detected_gesture=detected_gesture,
            stable_gesture=self._stable_gesture,
            confidence=confidence,
            command=command,
            pan_dx=pan_dx,
            pan_dy=pan_dy,
            pinch_ratio=pinch_ratio,
        )

    def _clamp(
        self,
        value: float,
        min_value: float,
        max_value: float,
    ) -> float:
        return max(min_value, min(value, max_value))