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


@dataclass
class GestureOutput:
    active: bool
    detected_gesture: str
    stable_gesture: str
    confidence: float
    command: dict[str, Any] | None
    pan_dx: float = 0.0
    pan_dy: float = 0.0


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

        self._last_active_command_time = 0.0

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
            if active_command:
                output.command = active_command
            return output

        hand = hand_result.hands[0]

        detected_gesture = hand.gesture or "None"
        confidence = float(hand.gesture_confidence)

        if confidence < self.config.min_gesture_confidence:
            self._reset_pan()
            return self._build_output(
                detected_gesture="LowConfidence",
                confidence=confidence,
                command=active_command,
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
            )

        return self._build_output(
            detected_gesture=detected_gesture,
            confidence=confidence,
            command=command,
        )

    def _handle_keyboard(self, key: int | None) -> dict[str, Any] | None:
        if key not in (ord("a"), ord("A")):
            return None

        self.active = not self.active
        self._reset_pan()

        return {
            "type": "active",
            "value": self.active,
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
    ) -> dict[str, Any] | None:
        if not self.active:
            self._reset_pan()
            return None

        if stable_gesture == "Closed_Fist":
            self._reset_pan()
            return None

        if stable_gesture == "Open_Palm":
            return self._make_pan_command(
                hand=hand,
                frame_width=frame_width,
                frame_height=frame_height,
            )

        self._reset_pan()

        if stable_gesture == "Thumb_Up":
            return self._make_zoom_command(delta=1)

        if stable_gesture == "Thumb_Down":
            return self._make_zoom_command(delta=-1)

        if stable_gesture == "Victory":
            return self._make_zoom_command(delta=-1)

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
        }

    def _make_zoom_command(self, delta: int) -> dict[str, Any] | None:
        now = time.perf_counter()

        if now - self._last_zoom_time < self.config.zoom_cooldown_sec:
            return None

        self._last_zoom_time = now

        return {
            "type": "zoom",
            "delta": delta,
        }

    def _reset_pan(self) -> None:
        self._previous_center_px = None
        self._smoothed_dx = 0.0
        self._smoothed_dy = 0.0

    def _build_output(
        self,
        detected_gesture: str,
        confidence: float,
        command: dict[str, Any] | None,
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
        )

    def _clamp(self, value: float, min_value: float, max_value: float) -> float:
        return max(min_value, min(value, max_value))