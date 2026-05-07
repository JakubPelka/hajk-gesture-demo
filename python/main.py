import cv2

from camera import Camera, CameraFrame
from config import CAMERA, OVERLAY


def draw_overlay(data: CameraFrame) -> None:
    frame = data.frame

    lines = [
        f"FPS: {data.fps:.1f}",
        f"Camera: {CAMERA.camera_index}",
        f"Resolution: {data.frame_width} x {data.frame_height}",
        "Stage: 0 - camera preview",
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

    try:
        camera.open()
        cv2.namedWindow(CAMERA.window_name, cv2.WINDOW_NORMAL)

        while True:
            frame_data = camera.read()
            draw_overlay(frame_data)

            cv2.imshow(CAMERA.window_name, frame_data.frame)

            key = cv2.waitKey(1) & 0xFF

            if should_quit(key):
                break

    except RuntimeError as error:
        print(f"ERROR: {error}")

    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()