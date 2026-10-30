import asyncio
import time

from blockchain.block import Block
from blockchain.blockchain import DEFAULT_DIFFICULTY, Blockchain, ValidationError
from blockchain.pow import MiningCancelled, proof_of_work
from blockchain.transaction import Transaction
from blockchain.utils import shorten_key
from blockchain.wallet import Wallet
from network.p2p import P2PNetwork


class Node:
    def __init__(self, port, host="127.0.0.1", difficulty=DEFAULT_DIFFICULTY, verbose=True):
        self.wallet = Wallet()
        self.blockchain = Blockchain(difficulty=difficulty)
        self.p2p = P2PNetwork(self, host=host, port=port)
        self.verbose = verbose
        self.events = []
        self._mining_lock = asyncio.Lock()
        self.mining = False

    @property
    def port(self) -> int:
        return self.p2p.port

    @property
    def address(self) -> str:
        return self.wallet.get_public_key_hex()

    def log(self, message: str) -> None:
        self.events.append({"time": time.time(), "message": message})
        del self.events[:-200]
        if self.verbose:
            print(message, flush=True)

    # ---------------------------------------------------
    # LIFECYCLE
    # ---------------------------------------------------
    async def start(self) -> None:
        await self.p2p.start_server()
        self.log(f"🟢 Node listening on {self.p2p.host}:{self.port}")
        self.log(f"🔑 Address: {shorten_key(self.address)}")

    async def stop(self) -> None:
        await self.p2p.stop()

    async def connect_to_peer(self, host: str, port: int) -> None:
        peer = await self.p2p.connect_to_peer(host, port)
        self.log(f"🔗 Connected to peer {peer.label}")

    async def on_peer_connected(self, peer) -> None:
        if peer.direction == "inbound":
            self.log(f"🔗 Incoming connection from {peer.remote}")
        await self.p2p.send(peer, {"type": "hello", "data": {"port": self.port}})
        await self.p2p.send(peer, {"type": "get_chain"})

    # ---------------------------------------------------
    # INCOMING NETWORK MESSAGES
    # ---------------------------------------------------
    async def handle_network_message(self, msg: dict, peer=None) -> None:
        handler = {
            "hello": self._on_hello,
            "transaction": self._on_transaction,
            "new_block": self._on_new_block,
            "get_chain": self._on_get_chain,
            "chain": self._on_chain,
        }.get(msg["type"])
        if handler is not None:
            await handler(msg.get("data"), peer)

    async def _on_hello(self, data, peer) -> None:
        if peer is not None and isinstance(data, dict) and isinstance(data.get("port"), int):
            peer.listen_port = data["port"]

    async def _on_transaction(self, data, peer) -> None:
        try:
            tx = Transaction.from_dict(data)
            self.blockchain.add_transaction(tx)
        except (KeyError, TypeError, ValueError) as exc:
            if "already" not in str(exc):
                self.log(f"❌ Rejected transaction: {exc}")
            return
        self.log(f"💬 Transaction {tx.tx_id[:12]} added to pool")
        await self.p2p.broadcast({"type": "transaction", "data": tx.to_dict()}, exclude=peer)

    async def _on_new_block(self, data, peer) -> None:
        try:
            block = Block.from_dict(data)
        except (KeyError, TypeError, ValueError) as exc:
            self.log(f"❌ Malformed block: {exc}")
            return

        height = self.blockchain.height
        if block.index < height:
            return
        if block.index > height:
            self.log(f"📦 Block #{block.index} is ahead of us, requesting chain")
            await self.p2p.send(peer, {"type": "get_chain"})
            return
        if block.previous_hash != self.blockchain.get_last_block().hash:
            self.log(f"📦 Block #{block.index} is on a fork, requesting chain")
            await self.p2p.send(peer, {"type": "get_chain"})
            return

        try:
            self.blockchain.add_block(block)
        except ValidationError as exc:
            self.log(f"❌ Rejected block #{block.index}: {exc}")
            return
        self.log(f"📦 Accepted block #{block.index} from {peer.label}")
        await self.p2p.broadcast({"type": "new_block", "data": block.to_dict()}, exclude=peer)

    async def _on_get_chain(self, data, peer) -> None:
        await self.p2p.send(peer, {"type": "chain", "data": self.blockchain.to_list()})

    async def _on_chain(self, data, peer) -> None:
        if not isinstance(data, list) or len(data) <= self.blockchain.height:
            return
        try:
            replaced = self.blockchain.replace_chain_from_dicts(data)
        except ValidationError as exc:
            self.log(f"❌ Rejected chain from {peer.label}: {exc}")
            return
        if replaced:
            self.log(f"🔄 Synced to longer chain from {peer.label} (height {self.blockchain.height})")
            tip = self.blockchain.get_last_block()
            await self.p2p.broadcast({"type": "new_block", "data": tip.to_dict()}, exclude=peer)

    # ---------------------------------------------------
    # LOCAL ACTIONS
    # ---------------------------------------------------
    def get_balance(self, address: str = None) -> dict:
        address = address or self.address
        return {
            "confirmed": self.blockchain.get_balance(address),
            "available": self.blockchain.get_available_balance(address),
        }

    def create_transaction(self, recipient: str, amount: float) -> Transaction:
        tx = Transaction(sender=self.address, recipient=recipient, amount=amount)
        tx.sign(self.wallet.get_private_key_hex())
        self.blockchain.add_transaction(tx)
        return tx

    async def send_transaction(self, recipient: str, amount: float) -> Transaction:
        tx = self.create_transaction(recipient, amount)
        await self.p2p.broadcast({"type": "transaction", "data": tx.to_dict()})
        self.log(f"📤 Transaction {tx.tx_id[:12]} broadcast")
        return tx

    async def broadcast_pending(self) -> int:
        for tx in self.blockchain.pending_transactions:
            await self.p2p.broadcast({"type": "transaction", "data": tx.to_dict()})
        return len(self.blockchain.pending_transactions)

    async def mine(self):
        async with self._mining_lock:
            self.mining = True
            try:
                candidate = self.blockchain.build_candidate_block(self.address)
                tip_hash = candidate.previous_hash
                self.log(f"⛏ Mining block #{candidate.index} ({len(candidate.transactions)} txs)...")

                def stale() -> bool:
                    return self.blockchain.get_last_block().hash != tip_hash

                started = time.perf_counter()
                try:
                    await asyncio.to_thread(proof_of_work, candidate, self.blockchain.difficulty, stale)
                except MiningCancelled:
                    self.log("⛏ Mining aborted: a new block arrived first")
                    return None

                try:
                    self.blockchain.add_block(candidate)
                except ValidationError as exc:
                    self.log(f"⛏ Mined block discarded: {exc}")
                    return None

                elapsed = time.perf_counter() - started
                self.log(f"⛏ Block #{candidate.index} mined in {elapsed:.2f}s (nonce {candidate.nonce})")
                await self.p2p.broadcast({"type": "new_block", "data": candidate.to_dict()})
                return candidate
            finally:
                self.mining = False

    def state(self) -> dict:
        tip = self.blockchain.get_last_block()
        return {
            "address": self.address,
            "p2p_port": self.port,
            "height": self.blockchain.height,
            "tip_hash": tip.hash,
            "difficulty": self.blockchain.difficulty,
            "mining_reward": self.blockchain.mining_reward,
            "pending": len(self.blockchain.pending_transactions),
            "peers": len(self.p2p.peers),
            "valid": self.blockchain.is_chain_valid(),
            "mining": self.mining,
            "balance": self.get_balance(),
        }
