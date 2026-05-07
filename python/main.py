import time

import cv2

from camera import Camera, CameraFrame
from command_server import CommandServer
from config import CAMERA, OVERLAY
from gesture_state import GestureEngine, GestureOutput
from hand_tracker import HandTracker, HandTrackingResult
from video_stream_server import VideoStreamServer


SHOW_OPENCV_WINDOW = False


def draw_overlay(
    data: CameraFrame,
    hand_result: HandTrackingResult,
    gesture_output: GestureOutput,
    command_server: CommandServer,
    video_server: VideoStreamServer,
) -> None:
    frame = data.frame

    hand_text = "None"

    if hand_result.detected:
        first_hand = hand_result.hands[0]
        hand_text = (
            f"{first_hand.handedness} "
            f"{first_hand.gesture} "
            f"{first_hand.gesture_confidence:.2f}"
        )

    mode_text = "ACTIVE" if gesture_output.active else "INACTIVE"
    command_text = format_command(gesture_output.command)
    pinch_text = format_pinch(gesture_output.pinch_ratio)
    pointer_text = format_pointer(gesture_output)

    lines = [
        f"FPS: {data.fps:.1f}",
        f"Camera: {CAMERA.camera_index}",
        f"Resolution: {data.frame_width} x {data.frame_height}",
        "Stage: 4.7 - gesture-only activation",
        f"Mode: {mode_text}",
        f"Hands: {hand_result.hand_count}",
        f"Hand: {hand_text}",
        f"Detected: {gesture_output.detected_gesture} {gesture_output.confidence:.2f}",
        f"Stable: {gesture_output.stable_gesture}",
        f"Pinch distance: {pinch_text}",
        f"Pointer: {pointer_text}",
        f"Command: {command_text}",
        f"WebSocket: {command_server.url}",
        f"WebSocket clients: {command_server.client_count}",
        f"Video stream: {video_server.url}",
        f"Video clients: {video_server.client_count}",
        "Gestures: Thumb_Up active | Thumb_Down inactive | ILoveYou reset",
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


def format_command(command: dict | None) -> str:
    if command is None:
        return "None"

    command_type = command.get("type", "unknown")
    source = command.get("source", "")

    if command_type == "active":
        return f"active={command.get('value')} source={source}"

    if command_type == "pan":
        dx = command.get("dx", 0)
        dy = command.get("dy", 0)
        strength = command.get("strength", 0)

        return f"pan dx={dx} dy={dy} strength={strength} source={source}"

    if command_type == "zoom":
        return f"zoom delta={command.get('delta')} source={source}"

    if command_type == "pointer":
        visible = command.get("visible", False)
        x = command.get("x", "-")
        y = command.get("y", "-")
        return f"pointer visible={visible} x={x} y={y} source={source}"

    if command_type == "click":
        x = command.get("x", "-")
        y = command.get("y", "-")
        return f"click x={x} y={y} source={source}"

    if command_type == "reset":
        return f"reset source={source}"

    if command_type == "status":
        return "status"

    return str(command)


def format_pinch(pinch_ratio: float | None) -> str:
    if pinch_ratio is None:
        return "None"

    return f"{pinch_ratio:.1f}"


def format_pointer(gesture_output: GestureOutput) -> str:
    if not gesture_output.pointer_visible:
        return "hidden"

    if gesture_output.pointer_x is None or gesture_output.pointer_y is None:
        return "hidden"

    return f"x={gesture_output.pointer_x:.2f} y={gesture_output.pointer_y:.2f}"


def make_status_command(
    data: CameraFrame,
    hand_result: HandTrackingResult,
    gesture_output: GestureOutput,
    command_server: CommandServer,
    video_server: VideoStreamServer,
) -> dict:
    return {
        "type": "status",
        "active": gesture_output.active,
        "detected_gesture": gesture_output.detected_gesture,
        "stable_gesture": gesture_output.stable_gesture,
        "confidence": round(gesture_output.confidence, 2),
        "pinch_ratio": (
            round(gesture_output.pinch_ratio, 2)
            if gesture_output.pinch_ratio is not None
            else None
        ),
        "pointer_visible": gesture_output.pointer_visible,
        "pointer_x": (
            round(gesture_output.pointer_x, 4)
            if gesture_output.pointer_x is not None
            else None
        ),
        "pointer_y": (
            round(gesture_output.pointer_y, 4)
            if gesture_output.pointer_y is not None
            else None
        ),
        "hands": hand_result.hand_count,
        "fps": round(data.fps, 1),
        "clients": command_server.client_count,
        "video_clients": video_server.client_count,
    }


def get_control_key_and_quit(command_server: CommandServer) -> tuple[int | None, bool]:
    control_key = None
    should_quit_app = False

    for message in command_server.get_incoming_messages():
        if message.get("type") != "control":
            continue

        action = message.get("action")

        if action == "toggle_active":
            control_key = ord("A")

        elif action == "quit":
            should_quit_app = True

    return control_key, should_quit_app


def should_quit(key: int | None) -> bool:
    if key is None:
        return False

    if key == 27:
        return True

    if key in (ord("q"), ord("Q")):
        return True

    return False


def normalize_key(raw_key: int) -> int | None:
    key = raw_key & 0xFF

    if key == 255:
        return None

    return key


def main() -> None:
    camera = Camera()
    hand_tracker = HandTracker()
    gesture_engine = GestureEngine()
    command_server = CommandServer()
    video_server = VideoStreamServer()

    previous_key: int | None = None
    last_status_time = 0.0

    try:
        command_server.start()
        print(f"WebSocket server started: {command_server.url}")

        video_server.start()
        print(f"Video stream started: {video_server.url}")

        camera.open()

        if SHOW_OPENCV_WINDOW:
            cv2.namedWindow(CAMERA.window_name, cv2.WINDOW_NORMAL)

        while True:
            control_key, browser_quit = get_control_key_and_quit(command_server)

            if browser_quit:
                break

            key_for_engine = control_key if control_key is not None else previous_key

            frame_data = camera.read()

            hand_result = hand_tracker.process(
                frame_bgr=frame_data.frame,
                draw=True,
            )

            gesture_output = gesture_engine.update(
                hand_result=hand_result,
                frame_width=frame_data.frame_width,
                frame_height=frame_data.frame_height,
                key=key_for_engine,
            )

            if gesture_output.command is not None:
                command_server.send_command(gesture_output.command)

            now = time.perf_counter()

            if now - last_status_time >= 0.5:
                command_server.send_command(
                    make_status_command(
                        data=frame_data,
                        hand_result=hand_result,
                        gesture_output=gesture_output,
                        command_server=command_server,
                        video_server=video_server,
                    )
                )
                last_status_time = now

            draw_overlay(
                data=frame_data,
                hand_result=hand_result,
                gesture_output=gesture_output,
                command_server=command_server,
                video_server=video_server,
            )

            video_server.update_frame(frame_data.frame)

            if SHOW_OPENCV_WINDOW:
                cv2.imshow(CAMERA.window_name, frame_data.frame)
                current_key = normalize_key(cv2.waitKey(1))

                if should_quit(current_key):
                    break

                previous_key = current_key
            else:
                previous_key = None

    except RuntimeError as error:
        print(f"ERROR: {error}")

    except KeyboardInterrupt:
        print("Interrupted by user.")

    finally:
        video_server.stop()
        command_server.stop()
        hand_tracker.close()
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()