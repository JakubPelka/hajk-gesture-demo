from dataclasses import dataclass

import cv2
import mediapipe as mp


@dataclass
class HandData:
    handedness: str
    confidence: float
    landmarks: list[tuple[float, float, float]]
    center_x: float
    center_y: float


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
        max_num_hands: int = 1,
        min_detection_confidence: float = 0.6,
        min_tracking_confidence: float = 0.5,
    ) -> None:
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_styles = mp.solutions.drawing_styles

        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_num_hands,
            model_complexity=1,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

    def process(self, frame_bgr, draw: bool = True) -> HandTrackingResult:
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        frame_rgb.flags.writeable = False

        result = self.hands.process(frame_rgb)

        frame_rgb.flags.writeable = True

        if not result.multi_hand_landmarks:
            return HandTrackingResult(hands=[])

        detected_hands: list[HandData] = []

        for index, hand_landmarks in enumerate(result.multi_hand_landmarks):
            handedness = "Unknown"
            confidence = 0.0

            if result.multi_handedness and index < len(result.multi_handedness):
                handedness_data = result.multi_handedness[index].classification[0]
                handedness = handedness_data.label
                confidence = handedness_data.score

            landmarks = [
                (landmark.x, landmark.y, landmark.z)
                for landmark in hand_landmarks.landmark
            ]

            center_x, center_y = self._calculate_hand_center(landmarks)

            detected_hands.append(
                HandData(
                    handedness=handedness,
                    confidence=confidence,
                    landmarks=landmarks,
                    center_x=center_x,
                    center_y=center_y,
                )
            )

            if draw:
                self._draw_landmarks(frame_bgr, hand_landmarks)
                self._draw_hand_label(
                    frame_bgr=frame_bgr,
                    hand_data=detected_hands[-1],
                )

        return HandTrackingResult(hands=detected_hands)

    def close(self) -> None:
        self.hands.close()

    def _calculate_hand_center(
        self,
        landmarks: list[tuple[float, float, float]],
    ) -> tuple[float, float]:
        if not landmarks:
            return 0.0, 0.0

        # Stable enough for Stage 1 and useful later for pan movement.
        # Uses wrist + main palm landmarks instead of all fingertips.
        palm_indices = [0, 5, 9, 13, 17]

        x_values = [landmarks[index][0] for index in palm_indices]
        y_values = [landmarks[index][1] for index in palm_indices]

        center_x = sum(x_values) / len(x_values)
        center_y = sum(y_values) / len(y_values)

        return center_x, center_y

    def _draw_landmarks(self, frame_bgr, hand_landmarks) -> None:
        self.mp_drawing.draw_landmarks(
            frame_bgr,
            hand_landmarks,
            self.mp_hands.HAND_CONNECTIONS,
            self.mp_styles.get_default_hand_landmarks_style(),
            self.mp_styles.get_default_hand_connections_style(),
        )

    def _draw_hand_label(self, frame_bgr, hand_data: HandData) -> None:
        height, width = frame_bgr.shape[:2]

        x = int(hand_data.center_x * width)
        y = int(hand_data.center_y * height)

        label = f"{hand_data.handedness} {hand_data.confidence:.2f}"

        cv2.circle(frame_bgr, (x, y), 6, (0, 255, 255), -1)

        cv2.putText(
            frame_bgr,
            label,
            (x + 12, y - 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 0, 0),
            4,
            cv2.LINE_AA,
        )

        cv2.putText(
            frame_bgr,
            label,
            (x + 12, y - 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )