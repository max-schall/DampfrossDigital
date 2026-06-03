"""
NetworkBridge — QThread that runs an asyncio event loop for WebSocket
host/client communication.

Role "host":
  - Starts a local WebSocket server on self._port
  - Starts a pyngrok tunnel (falls back to local IP if unavailable)
  - Emits tunnel_url_ready(str) once the public URL is known
  - Clients that connect send join_lobby and action messages
  - Emits player_joined(slot, name, color) and action_received(slot, dict)
  - Call broadcast_state(dict), broadcast_map(bytes), broadcast_game_start(list)
    to push messages to all connected clients

Role "client":
  - Connects to host_url
  - Sends join_lobby automatically with (name, color) passed at construction
  - Emits state_received(dict), map_received(bytes), player_joined, game_started, …
  - Call send_action(dict) to send an action to the host

Qt ↔ asyncio:
  Qt thread → async: asyncio.run_coroutine_threadsafe() enqueues to the loop
  Async thread → Qt: pyqtSignal emission is thread-safe in PyQt6
"""
from __future__ import annotations
import asyncio
import base64
import json

from PyQt6.QtCore import QThread, pyqtSignal


_STOP_SENTINEL = object()


class NetworkBridge(QThread):
    # ── Signals (async thread → Qt main thread, thread-safe) ─────────────── #
    state_received   = pyqtSignal(dict)         # full serialized GameState
    map_received     = pyqtSignal(bytes)         # raw .dmpfmap bytes
    player_joined    = pyqtSignal(int, str, str) # slot, name, color
    game_started     = pyqtSignal(list)          # player_configs list
    player_left      = pyqtSignal(int)           # slot
    error_received   = pyqtSignal(str)
    tunnel_url_ready = pyqtSignal(str)           # host only: public WSS URL
    action_received  = pyqtSignal(int, dict)     # host only: slot, payload
    my_slot_assigned = pyqtSignal(int)           # client only: confirmed slot idx

    def __init__(self, role: str, host_url: str = "",
                 port: int = 8765,
                 name: str = "Player",
                 color: str = "#1f6fd9",
                 parent=None):
        super().__init__(parent)
        self._role     = role       # "host" or "client"
        self._host_url = host_url   # client: URL to connect to
        self._port     = port       # host: local port
        self._name     = name       # client: own name
        self._color    = color      # client: own color
        self._loop: asyncio.AbstractEventLoop | None = None
        self._outbound: asyncio.Queue | None = None   # host: msgs to broadcast
        self._actions:  asyncio.Queue | None = None   # client: msgs to send
        self._tunnel    = None       # pyngrok tunnel object (host only)
        # Tracks all joined players for host: {slot: {name, color}}
        self._player_info: dict = {}
        # Confirmed slot for this client (-1 until join_ack received)
        self._my_slot: int = -1
        if role == "host":
            self._player_info[0] = {"name": name, "color": color}

    # ── Public thread-safe API ────────────────────────────────────────────── #

    def broadcast_state(self, state_dict: dict) -> None:
        """Host: push serialized state to all connected clients."""
        self._enqueue_outbound({"type": "state_update", "state": state_dict})

    def broadcast_map(self, map_bytes: bytes) -> None:
        """Host: send raw map bytes (base64) to all connected clients."""
        self._enqueue_outbound({
            "type": "map_data",
            "data": base64.b64encode(map_bytes).decode("ascii"),
        })

    def broadcast_game_start(self, player_configs: list) -> None:
        """Host: tell all clients the game is starting."""
        self._enqueue_outbound({"type": "game_start", "player_configs": player_configs})

    def send_action(self, action_dict: dict) -> None:
        """Client: send an action to the host."""
        if self._loop and self._actions:
            asyncio.run_coroutine_threadsafe(
                self._actions.put({"type": "action", "payload": action_dict}),
                self._loop,
            )

    def stop(self) -> None:
        """Request clean shutdown from any thread."""
        try:
            if self._loop and self._outbound:
                asyncio.run_coroutine_threadsafe(
                    self._outbound.put(_STOP_SENTINEL), self._loop
                )
            if self._loop and self._actions:
                asyncio.run_coroutine_threadsafe(
                    self._actions.put(_STOP_SENTINEL), self._loop
                )
        except RuntimeError:
            pass  # loop already closed — nothing to signal

    # ── QThread.run() ────────────────────────────────────────────────────── #

    def run(self) -> None:
        self._loop    = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._outbound = asyncio.Queue()
        self._actions  = asyncio.Queue()
        try:
            if self._role == "host":
                self._loop.run_until_complete(self._host_main())
            else:
                self._loop.run_until_complete(self._client_main())
        except (asyncio.CancelledError, KeyboardInterrupt):
            pass
        except Exception as exc:
            self.error_received.emit(str(exc))
        finally:
            self._cleanup()
            self._loop.close()

    # ── Host implementation ───────────────────────────────────────────────── #

    async def _host_main(self) -> None:
        import websockets
        self._clients: dict = {}   # ws → slot
        self._next_slot = 1        # host is always slot 0

        server = await websockets.serve(
            self._handle_client, "localhost", self._port,
            max_size=None,
        )

        url = await self._start_tunnel()
        self.tunnel_url_ready.emit(url)

        # Broadcast loop — exits when STOP_SENTINEL arrives
        while True:
            msg = await self._outbound.get()
            if msg is _STOP_SENTINEL:
                break
            raw = json.dumps(msg)
            dead = set()
            for ws in list(self._clients):
                try:
                    await ws.send(raw)
                except Exception:
                    dead.add(ws)
            for ws in dead:
                slot = self._clients.pop(ws, None)
                if slot is not None:
                    self.player_left.emit(slot)
                    await self._broadcast_raw(json.dumps(
                        {"type": "player_disconnected", "slot": slot}
                    ))

        server.close()
        await server.wait_closed()

    async def _handle_client(self, ws) -> None:
        slot = self._next_slot
        self._next_slot += 1
        self._clients[ws] = slot
        try:
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                except Exception:
                    continue
                t = msg.get("type")
                if t == "join_lobby":
                    name  = msg.get("name",  f"Player {slot}")
                    color = msg.get("color", "#888888")
                    # Resolve color conflict: pick next free color if taken
                    used = {v["color"] for v in self._player_info.values()}
                    if color in used:
                        _fallbacks = [
                            "#e23b3b","#1f6fd9","#1f7a4a","#e8a915",
                            "#e76018","#7a4dd0","#0a9aa1","#d3398a",
                        ]
                        color = next((c for c in _fallbacks if c not in used), color)
                    self._player_info[slot] = {"name": name, "color": color}
                    # Send the new client their confirmed slot + full current roster
                    roster = [
                        {"slot": s, "name": v["name"], "color": v["color"]}
                        for s, v in sorted(self._player_info.items())
                    ]
                    await ws.send(json.dumps({
                        "type": "join_ack",
                        "slot":  slot,
                        "name":  name,
                        "color": color,
                        "roster": roster,
                    }))
                    self.player_joined.emit(slot, name, color)
                    await self._broadcast_raw(json.dumps(
                        {"type": "player_joined", "slot": slot,
                         "name": name, "color": color}
                    ))
                elif t == "action":
                    self.action_received.emit(slot, msg.get("payload", {}))
        except Exception:
            pass
        finally:
            self._clients.pop(ws, None)
            self.player_left.emit(slot)
            await self._broadcast_raw(json.dumps(
                {"type": "player_disconnected", "slot": slot}
            ))

    async def _broadcast_raw(self, raw: str) -> None:
        dead = set()
        for ws in list(self._clients):
            try:
                await ws.send(raw)
            except Exception:
                dead.add(ws)
        for ws in dead:
            slot = self._clients.pop(ws, None)
            if slot is not None:
                self.player_left.emit(slot)

    async def _start_tunnel(self) -> str:
        """Start a pyngrok tunnel and return the public WSS URL."""
        try:
            from pyngrok import ngrok
            tunnel = ngrok.connect(self._port, "http")
            self._tunnel = tunnel
            url = tunnel.public_url
            return url.replace("http://", "ws://").replace("https://", "wss://")
        except ImportError:
            pass
        except Exception as exc:
            self.error_received.emit(f"ngrok: {exc}")
        return self._local_url()

    def _local_url(self) -> str:
        import socket
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            ip = "127.0.0.1"
        return f"ws://{ip}:{self._port}"

    # ── Client implementation ─────────────────────────────────────────────── #

    async def _client_main(self) -> None:
        import websockets
        try:
            async with websockets.connect(self._host_url, max_size=None) as ws:
                # Announce ourselves
                await ws.send(json.dumps({
                    "type": "join_lobby",
                    "name":  self._name,
                    "color": self._color,
                }))
                recv_task = asyncio.ensure_future(self._client_recv(ws))
                send_task = asyncio.ensure_future(self._client_send(ws))
                done, pending = await asyncio.wait(
                    [recv_task, send_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for t in pending:
                    t.cancel()
        except Exception as exc:
            self.error_received.emit(str(exc))

    async def _client_recv(self, ws) -> None:
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except Exception:
                continue
            t = msg.get("type")
            if t == "join_ack":
                # Confirmed slot assignment + full current roster
                self._my_slot = msg["slot"]
                self.my_slot_assigned.emit(self._my_slot)
                for p in msg.get("roster", []):
                    self.player_joined.emit(p["slot"], p["name"], p["color"])
            elif t == "state_update":
                self.state_received.emit(msg["state"])
            elif t == "map_data":
                self.map_received.emit(base64.b64decode(msg["data"]))
            elif t == "player_joined":
                self.player_joined.emit(msg["slot"], msg["name"], msg["color"])
            elif t == "game_start":
                self.game_started.emit(msg.get("player_configs", []))
            elif t == "player_disconnected":
                self.player_left.emit(msg["slot"])
            elif t == "error":
                self.error_received.emit(msg["text"])

    async def _client_send(self, ws) -> None:
        while True:
            msg = await self._actions.get()
            if msg is _STOP_SENTINEL:
                break
            try:
                await ws.send(json.dumps(msg))
            except Exception as exc:
                self.error_received.emit(str(exc))
                break

    # ── Helpers ───────────────────────────────────────────────────────────── #

    def _enqueue_outbound(self, msg: dict) -> None:
        if self._loop and self._outbound and not self._loop.is_closed():
            asyncio.run_coroutine_threadsafe(
                self._outbound.put(msg), self._loop
            )

    def _cleanup(self) -> None:
        if self._tunnel is not None:
            try:
                from pyngrok import ngrok
                ngrok.disconnect(self._tunnel.public_url)
            except Exception:
                pass
            self._tunnel = None
