import asyncio
import json

class P2PNetwork:
    def __init__(self, node):
        self.node = node
        self.peers = set()

    async def start_server(self, host="127.0.0.1", port=8000):
        server = await asyncio.start_server(self.handle_connection, host, port)
        print(f"🔌 TCP server running on {host}:{port}")

        async with server:
            await server.serve_forever()

    async def handle_connection(self, reader, writer):
        addr = writer.get_extra_info("peername")
        print(f"🔗 Incoming connection from {addr}")
        self.peers.add((reader, writer))

        try:
            while True:
                data = await reader.readline()
                if not data:
                    break

                msg = json.loads(data.decode())
                await self.node.handle_network_message(msg)

        except Exception as e:
            print("⚠️ Peer error:", e)

        finally:
            self.peers.remove((reader, writer))
            writer.close()

    async def connect_to_peer(self, url):
        host, port = url.replace("tcp://", "").split(":")
        reader, writer = await asyncio.open_connection(host, int(port))

        self.peers.add((reader, writer))
        print(f"🔗 Connected to peer {url}")

        asyncio.create_task(self.listen_to_peer(reader, writer))

    async def listen_to_peer(self, reader, writer):
        try:
            while True:
                data = await reader.readline()
                if not data:
                    break

                msg = json.loads(data.decode())
                await self.node.handle_network_message(msg)

        except:
            pass

    async def broadcast(self, msg):
        data = (json.dumps(msg) + "\n").encode()

        remove = []
        for reader, writer in self.peers:
            try:
                writer.write(data)
                await writer.drain()
            except:
                remove.append((reader, writer))

        for peer in remove:
            self.peers.remove(peer)