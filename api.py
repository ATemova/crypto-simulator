import os
import asyncio
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from network.node import Node

# ---------------------------------------------------
# FASTAPI APP
# ---------------------------------------------------
app = FastAPI(title="Crypto Simulator API")

# Enable dashboard access from browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------
# SERVE DASHBOARD STATIC FILES
# ---------------------------------------------------
dashboard_path = os.path.join(os.getcwd(), "dashboard")
app.mount("/dashboard", StaticFiles(directory=dashboard_path), name="dashboard")

@app.get("/")
def root():
    """Opens the dashboard automatically."""
    return FileResponse("dashboard/index.html")

@app.get("/dashboard")
def dashboard_home():
    return FileResponse("dashboard/index.html")


# ---------------------------------------------------
# CREATE NODE (running internally on port 8000)
# ---------------------------------------------------
node = Node(8000)

@app.on_event("startup")
async def start_node():
    """Start blockchain node when API boots"""
    await node.start()


# ---------------------------------------------------
# MODELS
# ---------------------------------------------------
class TxRequest(BaseModel):
    recipient: str
    amount: float


# ---------------------------------------------------
# REST API ENDPOINTS
# ---------------------------------------------------

@app.get("/chain")
def get_chain():
    return {
        "length": len(node.blockchain.chain),
        "valid": node.blockchain.is_chain_valid(),
        "chain": [b.to_dict() for b in node.blockchain.chain]
    }


@app.get("/balance")
def get_balance():
    pk = node.wallet.get_public_key_hex()

    balance = 0
    for block in node.blockchain.chain:
        for tx in block.transactions:
            if tx.recipient == pk:
                balance += tx.amount
            if tx.sender == pk:
                balance -= tx.amount

    return {"balance": balance}


@app.get("/pending")
def get_pending():
    return {
        "pending": [tx.to_dict() for tx in node.blockchain.pending_transactions]
    }


@app.get("/peers")
def get_peers():
    return {"peers": node.p2p.peers}


@app.post("/mine")
async def mine_block():
    """Trigger mining and return newly mined block."""
    await node.mine()
    block = node.blockchain.get_last_block()
    return {"status": "success", "block": block.to_dict()}


# ---------------------------------------------------
# WEBSOCKET FEED FOR LIVE DASHBOARD UPDATES
# ---------------------------------------------------
@app.websocket("/ws")
async def dashboard_feed(ws: WebSocket):
    await ws.accept()

    while True:
        data = {
            "chain_length": len(node.blockchain.chain),
            "balance": get_balance()["balance"],
            "pending": len(node.blockchain.pending_transactions),
            "peers": node.p2p.peers,
            "chain": [b.to_dict() for b in node.blockchain.chain]
        }

        await ws.send_json(data)
        await asyncio.sleep(1)  # update every second