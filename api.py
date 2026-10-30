import argparse
import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from blockchain.blockchain import DEFAULT_DIFFICULTY, ValidationError
from network.node import Node

DASHBOARD_DIR = Path(__file__).resolve().parent / "dashboard"
EXPLORER_BLOCKS = 100


class TxRequest(BaseModel):
    recipient: str = Field(min_length=128, max_length=128)
    amount: float = Field(gt=0)


class PeerRequest(BaseModel):
    host: str = "127.0.0.1"
    port: int = Field(gt=0, lt=65536)


def parse_peer(value: str, default_host: str):
    if ":" in value:
        host, port = value.replace("tcp://", "").rsplit(":", 1)
        return host, int(port)
    return default_host, int(value)


def create_app(p2p_port=None, p2p_host=None, peers=None, difficulty=None) -> FastAPI:
    p2p_port = p2p_port if p2p_port is not None else int(os.getenv("P2P_PORT", "6000"))
    p2p_host = p2p_host or os.getenv("P2P_HOST", "127.0.0.1")
    difficulty = difficulty if difficulty is not None else int(os.getenv("DIFFICULTY", str(DEFAULT_DIFFICULTY)))
    if peers is None:
        peers = [p for p in os.getenv("PEERS", "").split(",") if p.strip()]

    node = Node(p2p_port, host=p2p_host, difficulty=difficulty)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await node.start()
        for peer in peers:
            try:
                await node.connect_to_peer(*parse_peer(peer.strip(), p2p_host))
            except (OSError, ValueError) as exc:
                node.log(f"❌ Could not connect to {peer}: {exc}")
        yield
        await node.stop()

    app = FastAPI(title="Crypto Simulator API", lifespan=lifespan)
    app.state.node = node
    app.mount("/dashboard", StaticFiles(directory=DASHBOARD_DIR, html=True), name="dashboard")

    @app.get("/", include_in_schema=False)
    async def root():
        return RedirectResponse("/dashboard/")

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        return FileResponse(Path(__file__).resolve().parent / "crypto-simulator.png")

    # ---------------------------------------------------
    # READ ENDPOINTS
    # ---------------------------------------------------
    @app.get("/state")
    async def get_state():
        return node.state()

    @app.get("/chain")
    async def get_chain():
        return {
            "length": node.blockchain.height,
            "valid": node.blockchain.is_chain_valid(),
            "chain": node.blockchain.to_list(),
        }

    @app.get("/blocks/{index}")
    async def get_block(index: int):
        if not 0 <= index < node.blockchain.height:
            raise HTTPException(404, "Block not found")
        return node.blockchain.chain[index].to_dict()

    @app.get("/transactions/{tx_id}")
    async def get_transaction(tx_id: str):
        found = node.blockchain.find_transaction(tx_id)
        if found is not None:
            index, tx = found
            return {"status": "confirmed", "block": index, "transaction": tx.to_dict()}
        for tx in node.blockchain.pending_transactions:
            if tx.tx_id == tx_id:
                return {"status": "pending", "block": None, "transaction": tx.to_dict()}
        raise HTTPException(404, "Transaction not found")

    @app.get("/address")
    async def get_address():
        return {"address": node.address}

    @app.get("/balance")
    async def get_balance(address: str = None):
        return node.get_balance(address)

    @app.get("/pending")
    async def get_pending():
        return {"pending": [tx.to_dict() for tx in node.blockchain.pending_transactions]}

    @app.get("/peers")
    async def get_peers():
        return {"peers": node.p2p.peer_list()}

    @app.get("/events")
    async def get_events():
        return {"events": node.events[-50:]}

    # ---------------------------------------------------
    # WRITE ENDPOINTS
    # ---------------------------------------------------
    @app.post("/mine")
    async def mine_block():
        if node.mining:
            raise HTTPException(409, "Already mining")
        block = await node.mine()
        if block is None:
            raise HTTPException(409, "Mining was aborted because a competing block arrived")
        return {"status": "success", "block": block.to_dict()}

    @app.post("/transactions", status_code=201)
    async def create_transaction(req: TxRequest):
        try:
            tx = await node.send_transaction(req.recipient, req.amount)
        except ValidationError as exc:
            raise HTTPException(400, str(exc))
        return {"status": "pending", "transaction": tx.to_dict()}

    @app.post("/peers", status_code=201)
    async def add_peer(req: PeerRequest):
        try:
            await node.connect_to_peer(req.host, req.port)
        except (OSError, ValueError) as exc:
            raise HTTPException(400, f"Could not connect: {exc}")
        return {"peers": node.p2p.peer_list()}

    # ---------------------------------------------------
    # WEBSOCKET FEED FOR LIVE DASHBOARD UPDATES
    # ---------------------------------------------------
    @app.websocket("/ws")
    async def dashboard_feed(ws: WebSocket):
        await ws.accept()
        last_tip = None
        try:
            while True:
                state = node.state()
                payload = {
                    "state": state,
                    "peers": node.p2p.peer_list(),
                    "pending": [tx.to_dict() for tx in node.blockchain.pending_transactions],
                    "events": node.events[-30:],
                }
                if state["tip_hash"] != last_tip:
                    last_tip = state["tip_hash"]
                    payload["blocks"] = [b.to_dict() for b in node.blockchain.chain[-EXPLORER_BLOCKS:]]
                await ws.send_json(payload)
                await asyncio.sleep(1)
        except (WebSocketDisconnect, RuntimeError):
            pass

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser(description="Crypto Simulator node with web dashboard")
    parser.add_argument("--api-port", type=int, default=5000, help="HTTP port for API and dashboard")
    parser.add_argument("--p2p-port", type=int, default=6000, help="TCP port for peer-to-peer traffic")
    parser.add_argument("--host", default="127.0.0.1", help="interface to bind")
    parser.add_argument("--peer", action="append", default=[], help="peer to connect to (port or host:port)")
    parser.add_argument("--difficulty", type=int, default=DEFAULT_DIFFICULTY, help="PoW difficulty")
    options = parser.parse_args()

    uvicorn.run(
        create_app(options.p2p_port, options.host, options.peer, options.difficulty),
        host=options.host,
        port=options.api_port,
    )
