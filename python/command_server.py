import asyncio
import json
import queue
import threading
from typing import Any

import websockets


class CommandServer:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
    ) -> None:
        self.host = host
        self.port = port

        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._server = None
        self._clients: set[Any] = set()
        self._started = threading.Event()
        self._incoming_messages: queue.Queue[dict[str, Any]] = queue.Queue()

        self.last_error: str | None = None

    @property
    def url(self) -> str:
        return f"ws://{self.host}:{self.port}"

    @property
    def client_count(self) -> int:
        return len(self._clients)

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return

        self._thread = threading.Thread(
            target=self._run_loop,
            name="CommandServerThread",
            daemon=True,
        )
        self._thread.start()
        self._started.wait(timeout=3.0)

        if self.last_error:
            raise RuntimeError(self.last_error)

    def stop(self) -> None:
        if self._loop is None:
            return

        self._loop.call_soon_threadsafe(self._loop.stop)

        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def send_command(self, command: dict[str, Any] | None) -> None:
        if command is None:
            return

        if self._loop is None or not self._loop.is_running():
            return

        if not self._clients:
            return

        payload = json.dumps(command, ensure_ascii=False)

        asyncio.run_coroutine_threadsafe(
            self._broadcast(payload),
            self._loop,
        )

    def get_incoming_messages(self) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []

        while True:
            try:
                messages.append(self._incoming_messages.get_nowait())
            except queue.Empty:
                break

        return messages

    def _run_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        try:
            self._loop.run_until_complete(self._start_server())
            self._started.set()
            self._loop.run_forever()

        except Exception as error:
            self.last_error = f"WebSocket server error: {error}"
            self._started.set()

        finally:
            self._loop.run_until_complete(self._shutdown())
            self._loop.close()

    async def _start_server(self) -> None:
        self._server = await websockets.serve(
            self._handle_client,
            self.host,
            self.port,
        )

    async def _handle_client(self, websocket, *args) -> None:
        self._clients.add(websocket)

        try:
            await websocket.send(
                json.dumps(
                    {
                        "type": "status",
                        "message": "connected",
                        "server": self.url,
                    }
                )
            )

            async for raw_message in websocket:
                self._handle_incoming_message(raw_message)

        finally:
            self._clients.discard(websocket)

    def _handle_incoming_message(self, raw_message: str) -> None:
        try:
            message = json.loads(raw_message)
        except json.JSONDecodeError:
            message = {
                "type": "invalid",
                "raw": raw_message,
            }

        self._incoming_messages.put(message)

    async def _broadcast(self, payload: str) -> None:
        if not self._clients:
            return

        disconnected_clients = []

        for client in list(self._clients):
            try:
                await client.send(payload)
            except Exception:
                disconnected_clients.append(client)

        for client in disconnected_clients:
            self._clients.discard(client)

    async def _shutdown(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()

        for client in list(self._clients):
            try:
                await client.close()
            except Exception:
                pass

        self._clients.clear()