import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17),
]


@dataclass
class HandData:
    handedness: str
    handedness_confidence: float
    gesture: str
    gesture_confidence: float
    landmarks: list[tuple[float, float, float]]
    center_x: float
    center_y: float

    @property
    def confidence(self) -> float:
        return max(self.handedness_confidence, self.gesture_confidence)


@dataclass
class HandTrackingResult:
    hands: list[HandData]

    @property
    def detected(self) -> bool:
        return len(self.hands) > 0

    @property
    def hand_count(self) -> int:
        return len(self.hands)


class HandTracker:
    def __init__(
        self,
        model_path: str = "models/gesture_recognizer.task",
        max_num_hands: int = 1,
        min_hand_detection_confidence: float = 0.6,
        min_hand_presence_confidence: float = 0.6,
        min_tracking_confidence: float = 0.5,
    ) -> None:
        self.model_path = Path(model_path)

        if not self.model_path.exists():
            raise RuntimeError(
                "Gesture recognizer model not found: "
                f"{self.model_path}. "
                "Download it to models/gesture_recognizer.task."
            )

        base_options = python.BaseOptions(
            model_asset_path=str(self.model_path)
        )

        options = vision.GestureRecognizerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_hands=max_num_hands,
            min_hand_detection_confidence=min_hand_detection_confidence,
            min_hand_presence_confidence=min_hand_presence_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

        self.recognizer = vision.GestureRecognizer.create_from_options(options)
        self._last_timestamp_ms = 0

    def process(self, frame_bgr, draw: bool = True) -> HandTrackingResult:
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        frame_rgb = np.ascontiguousarray(frame_rgb)

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=frame_rgb,
        )

        timestamp_ms = self._get_timestamp_ms()
        result = self.recognizer.recognize_for_video(mp_image, timestamp_ms)

        if not result.hand_landmarks:
            return HandTrackingResult(hands=[])

        detected_hands: list[HandData] = []

        for index, hand_landmarks in enumerate(result.hand_landmarks):
            handedness = "Unknown"
            handedness_confidence = 0.0
            gesture = "None"
            gesture_confidence = 0.0

            if result.handedness and index < len(result.handedness):
                if result.handedness[index]:
                    handedness_category = result.handedness[index][0]
                    handedness = handedness_category.category_name
                    handedness_confidence = handedness_category.score

            if result.gestures and index < len(result.gestures):
                if result.gestures[index]:
                    gesture_category = result.gestures[index][0]
                    gesture = gesture_category.category_name
                    gesture_confidence = gesture_category.score

            landmarks = [
                (landmark.x, landmark.y, landmark.z)
                for landmark in hand_landmarks
            ]

            center_x, center_y = self._calculate_hand_center(landmarks)

            hand_data = HandData(
                handedness=handedness,
                handedness_confidence=handedness_confidence,
                gesture=gesture,
                gesture_confidence=gesture_confidence,
                landmarks=landmarks,
                center_x=center_x,
                center_y=center_y,
            )

            detected_hands.append(hand_data)

            if draw:
                self._draw_landmarks(frame_bgr, hand_data)

        return HandTrackingResult(hands=detected_hands)

    def close(self) -> None:
        self.recognizer.close()

    def _get_timestamp_ms(self) -> int:
        timestamp_ms = int(time.perf_counter() * 1000)

        if timestamp_ms <= self._last_timestamp_ms:
            timestamp_ms = self._last_timestamp_ms + 1

        self._last_timestamp_ms = timestamp_ms
        return timestamp_ms

    def _calculate_hand_center(
        self,
        landmarks: list[tuple[float, float, float]],
    ) -> tuple[float, float]:
        if not landmarks:
            return 0.0, 0.0

        palm_indices = [0, 5, 9, 13, 17]

        x_values = [landmarks[index][0] for index in palm_indices]
        y_values = [landmarks[index][1] for index in palm_indices]

        center_x = sum(x_values) / len(x_values)
        center_y = sum(y_values) / len(y_values)

        return center_x, center_y

    def _draw_landmarks(self, frame_bgr, hand_data: HandData) -> None:
        height, width = frame_bgr.shape[:2]

        for start_index, end_index in HAND_CONNECTIONS:
            start = hand_data.landmarks[start_index]
            end = hand_data.landmarks[end_index]

            start_point = (
                int(start[0] * width),
                int(start[1] * height),
            )
            end_point = (
                int(end[0] * width),
                int(end[1] * height),
            )

            cv2.line(
                frame_bgr,
                start_point,
                end_point,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )

        for landmark in hand_data.landmarks:
            point = (
                int(landmark[0] * width),
                int(landmark[1] * height),
            )

            cv2.circle(
                frame_bgr,
                point,
                4,
                (0, 255, 255),
                -1,
                cv2.LINE_AA,
            )

        center = (
            int(hand_data.center_x * width),
            int(hand_data.center_y * height),
        )

        cv2.circle(
            frame_bgr,
            center,
            8,
            (255, 0, 255),
            -1,
            cv2.LINE_AA,
        )

        label = (
            f"{hand_data.handedness} "
            f"{hand_data.gesture} "
            f"{hand_data.gesture_confidence:.2f}"
        )

        cv2.putText(
            frame_bgr,
            label,
            (center[0] + 12, center[1] - 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 0, 0),
            4,
            cv2.LINE_AA,
        )

        cv2.putText(
            frame_bgr,
            label,
            (center[0] + 12, center[1] - 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )