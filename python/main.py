import cv2

from camera import Camera, CameraFrame
from config import CAMERA, OVERLAY
from hand_tracker import HandTracker, HandTrackingResult


def draw_overlay(data: CameraFrame, hand_result: HandTrackingResult) -> None:
    frame = data.frame

    hand_text = "None"
    if hand_result.detected:
        first_hand = hand_result.hands[0]
        hand_text = f"{first_hand.handedness} {first_hand.confidence:.2f}"

    lines = [
        f"FPS: {data.fps:.1f}",
        f"Camera: {CAMERA.camera_index}",
        f"Resolution: {data.frame_width} x {data.frame_height}",
        "Stage: 1 - MediaPipe hand landmarks",
        f"Hands: {hand_result.hand_count}",
        f"Hand: {hand_text}",
        "ESC / Q: quit",
    ]

    x = OVERLAY.margin_x
    y = OVERLAY.margin_y

    for index, text in enumerate(lines):
        line_y = y + index * OVERLAY.line_height

        cv2.putText(
            frame,
            text,
            (x, line_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            OVERLAY.font_scale,
            (0, 0, 0),
            OVERLAY.thickness + 2,
            cv2.LINE_AA,
        )

        cv2.putText(
            frame,
            text,
            (x, line_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            OVERLAY.font_scale,
            (255, 255, 255),
            OVERLAY.thickness,
            cv2.LINE_AA,
        )


def should_quit(key: int) -> bool:
    if key == 27:
        return True

    if key in (ord("q"), ord("Q")):
        return True

    return False


def main() -> None:
    camera = Camera()
    hand_tracker = HandTracker()

    try:
        camera.open()
        cv2.namedWindow(CAMERA.window_name, cv2.WINDOW_NORMAL)

        while True:
            frame_data = camera.read()

            hand_result = hand_tracker.process(
                frame_bgr=frame_data.frame,
                draw=True,
            )

            draw_overlay(frame_data, hand_result)

            cv2.imshow(CAMERA.window_name, frame_data.frame)

            key = cv2.waitKey(1) & 0xFF

            if should_quit(key):
                break

    except RuntimeError as error:
        print(f"ERROR: {error}")

    finally:
        hand_tracker.close()
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()