import asyncio
import itertools
import json

MAX_MESSAGE_BYTES = 32 * 1024 * 1024


class Peer:
    _ids = itertools.count(1)

    def __init__(self, reader, writer, direction, address=None):
        self.id = next(Peer._ids)
        self.reader = reader
        self.writer = writer
        self.direction = direction
        host, port = writer.get_extra_info("peername")[:2]
        self.remote = f"{host}:{port}"
        self.address = address
        self.listen_port = None
        self._send_lock = asyncio.Lock()

    @property
    def label(self) -> str:
        if self.address:
            return self.address
        if self.listen_port:
            return f"{self.remote.rsplit(':', 1)[0]}:{self.listen_port}"
        return self.remote

    def to_dict(self) -> dict:
        return {"id": self.id, "address": self.label, "direction": self.direction}

    async def send(self, msg: dict) -> None:
        data = (json.dumps(msg) + "\n").encode()
        async with self._send_lock:
            self.writer.write(data)
            await self.writer.drain()

    async def close(self) -> None:
        self.writer.close()
        try:
            await self.writer.wait_closed()
        except (ConnectionError, OSError):
            pass


class P2PNetwork:
    def __init__(self, node, host="127.0.0.1", port=6000):
        self.node = node
        self.host = host
        self.port = port
        self.peers = {}
        self._server = None
        self._tasks = set()

    # ---------------------------------------------------
    # LIFECYCLE
    # ---------------------------------------------------
    async def start_server(self) -> None:
        self._server = await asyncio.start_server(
            self._handle_inbound, self.host, self.port, limit=MAX_MESSAGE_BYTES
        )
        self.port = self._server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
        tasks = list(self._tasks)
        for task in tasks:
            task.cancel()
        for peer in list(self.peers.values()):
            peer.writer.close()
        await asyncio.gather(*tasks, return_exceptions=True)
        self.peers.clear()
        if self._server is not None:
            try:
                await asyncio.wait_for(self._server.wait_closed(), timeout=2)
            except asyncio.TimeoutError:
                pass
            self._server = None

    # ---------------------------------------------------
    # CONNECTIONS
    # ---------------------------------------------------
    def peer_list(self) -> list:
        return [peer.to_dict() for peer in self.peers.values()]

    def _is_connected_to(self, address: str) -> bool:
        return any(peer.label == address for peer in self.peers.values())

    async def connect_to_peer(self, host: str, port: int) -> Peer:
        address = f"{host}:{port}"
        if int(port) == self.port and host in ("127.0.0.1", "localhost", self.host):
            raise ValueError("Cannot connect to self")
        if self._is_connected_to(address):
            raise ValueError(f"Already connected to {address}")

        reader, writer = await asyncio.open_connection(host, int(port), limit=MAX_MESSAGE_BYTES)
        peer = Peer(reader, writer, "outbound", address=address)
        self._register(peer)
        return peer

    async def _handle_inbound(self, reader, writer) -> None:
        peer = Peer(reader, writer, "inbound")
        self._register(peer)

    def _register(self, peer: Peer) -> None:
        self.peers[peer.id] = peer
        task = asyncio.create_task(self._listen(peer))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _listen(self, peer: Peer) -> None:
        try:
            await self.node.on_peer_connected(peer)
            while True:
                line = await peer.reader.readline()
                if not line:
                    break
                try:
                    msg = json.loads(line.decode())
                except (json.JSONDecodeError, UnicodeDecodeError):
                    self.node.log(f"Dropped malformed message from {peer.label}")
                    continue
                if not isinstance(msg, dict) or "type" not in msg:
                    continue
                try:
                    await self.node.handle_network_message(msg, peer)
                except Exception as exc:
                    self.node.log(f"Error handling '{msg.get('type')}' from {peer.label}: {exc}")
        except (ConnectionError, OSError, asyncio.IncompleteReadError, asyncio.LimitOverrunError, ValueError):
            pass
        except asyncio.CancelledError:
            raise
        finally:
            self.peers.pop(peer.id, None)
            await peer.close()
            self.node.log(f"Peer disconnected: {peer.label}")

    # ---------------------------------------------------
    # MESSAGING
    # ---------------------------------------------------
    async def send(self, peer: Peer, msg: dict) -> None:
        try:
            await peer.send(msg)
        except (ConnectionError, OSError):
            self.peers.pop(peer.id, None)

    async def broadcast(self, msg: dict, exclude: Peer = None) -> None:
        targets = [p for p in self.peers.values() if exclude is None or p.id != exclude.id]
        await asyncio.gather(*(self.send(peer, msg) for peer in targets))
