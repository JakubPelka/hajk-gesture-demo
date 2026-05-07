import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import cv2


class VideoStreamServer:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8766,
        jpeg_quality: int = 80,
    ) -> None:
        self.host = host
        self.port = port
        self.jpeg_quality = jpeg_quality

        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

        self._condition = threading.Condition()
        self._jpeg_frame: bytes | None = None
        self._client_count = 0

        self.last_error: str | None = None

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}/video"

    @property
    def client_count(self) -> int:
        return self._client_count

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return

        handler_class = self._make_handler()

        try:
            self._server = ThreadingHTTPServer(
                (self.host, self.port),
                handler_class,
            )
        except Exception as error:
            self.last_error = f"Video stream server error: {error}"
            raise RuntimeError(self.last_error) from error

        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="VideoStreamServerThread",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None

        with self._condition:
            self._condition.notify_all()

        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def update_frame(self, frame_bgr: Any) -> None:
        encode_params = [
            int(cv2.IMWRITE_JPEG_QUALITY),
            int(self.jpeg_quality),
        ]

        ok, encoded = cv2.imencode(".jpg", frame_bgr, encode_params)

        if not ok:
            return

        jpeg_bytes = encoded.tobytes()

        with self._condition:
            self._jpeg_frame = jpeg_bytes
            self._condition.notify_all()

    def _make_handler(self):
        parent = self

        class VideoStreamHandler(BaseHTTPRequestHandler):
            server_version = "HajkGestureVideoStream/0.1"

            def do_GET(self) -> None:
                if self.path in ("/", "/index.html"):
                    self._send_info_page()
                    return

                if self.path == "/snapshot.jpg":
                    self._send_snapshot()
                    return

                if self.path == "/video":
                    self._send_mjpeg_stream()
                    return

                self.send_error(404, "Not found")

            def log_message(self, format: str, *args) -> None:
                return

            def _send_common_headers(self) -> None:
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
                self.send_header("Pragma", "no-cache")

            def _send_info_page(self) -> None:
                html = (
                    "<!doctype html>"
                    "<html><head><title>Hajk Gesture Video Stream</title></head>"
                    "<body>"
                    "<h1>Hajk Gesture Video Stream</h1>"
                    "<p>MJPEG stream:</p>"
                    "<p><a href='/video'>/video</a></p>"
                    "<p>Snapshot:</p>"
                    "<p><a href='/snapshot.jpg'>/snapshot.jpg</a></p>"
                    "</body></html>"
                ).encode("utf-8")

                self.send_response(200)
                self._send_common_headers()
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(html)))
                self.end_headers()
                self.wfile.write(html)

            def _send_snapshot(self) -> None:
                frame = parent._get_latest_frame()

                if frame is None:
                    self.send_error(503, "No frame available yet")
                    return

                self.send_response(200)
                self._send_common_headers()
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(frame)))
                self.end_headers()
                self.wfile.write(frame)

            def _send_mjpeg_stream(self) -> None:
                parent._client_count += 1

                try:
                    self.send_response(200)
                    self._send_common_headers()
                    self.send_header(
                        "Content-Type",
                        "multipart/x-mixed-replace; boundary=frame",
                    )
                    self.end_headers()

                    while True:
                        frame = parent._wait_for_frame()

                        if frame is None:
                            continue

                        self.wfile.write(b"--frame\r\n")
                        self.wfile.write(b"Content-Type: image/jpeg\r\n")
                        self.wfile.write(
                            f"Content-Length: {len(frame)}\r\n\r\n".encode("ascii")
                        )
                        self.wfile.write(frame)
                        self.wfile.write(b"\r\n")

                except (BrokenPipeError, ConnectionResetError):
                    pass

                finally:
                    parent._client_count = max(0, parent._client_count - 1)

        return VideoStreamHandler

    def _get_latest_frame(self) -> bytes | None:
        with self._condition:
            return self._jpeg_frame

    def _wait_for_frame(self) -> bytes | None:
        with self._condition:
            self._condition.wait(timeout=1.0)
            return self._jpeg_frame