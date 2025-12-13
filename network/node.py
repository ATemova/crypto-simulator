import asyncio
from blockchain.blockchain import Blockchain
from blockchain.transaction import Transaction
from blockchain.wallet import Wallet
from network.p2p import P2PNetwork


class Node:
    def __init__(self, port):
        self.port = port
        self.blockchain = Blockchain()
        self.wallet = Wallet()
        self.p2p = P2PNetwork(self)

        print(f"🟢 Node started on port {port}")
        print(f"🔑 Public Key: {self.wallet.get_public_key_hex()[:20]}...")

    # start node
    async def start(self):
        asyncio.create_task(self.p2p.start_server(port=self.port))
        await asyncio.sleep(0.2)  # allow server to bind

    async def connect_to_peer(self, peer_port):
        url = f"tcp://127.0.0.1:{peer_port}"
        print(f"🔌 Connecting to peer {url} ...")
        await self.p2p.connect_to_peer(url)

    # broadcasting
    async def broadcast_transaction(self, tx: Transaction):
        await self.p2p.broadcast({
            "type": "transaction",
            "data": tx.to_dict()
        })

    async def broadcast_block(self, block):
        await self.p2p.broadcast({
            "type": "new_block",
            "data": {
                "index": block.index,
                "hash": block.hash,
                "nonce": block.nonce,
                "previous_hash": block.previous_hash,
                "transactions": [tx.to_dict() for tx in block.transactions]
            }
        })

    # incoming network messages
    async def handle_network_message(self, msg):
        msg_type = msg.get("type")

        if msg_type == "transaction":
            await self.handle_incoming_transaction(msg["data"])
        elif msg_type == "new_block":
            await self.handle_incoming_block(msg["data"])

    async def handle_incoming_transaction(self, tx_data):
        """Receive and add a transaction from a peer."""
        tx = Transaction(
            sender=tx_data["sender"],
            recipient=tx_data["recipient"],
            amount=tx_data["amount"],
            signature=tx_data.get("signature")
        )

        try:
            self.blockchain.add_transaction(tx)
            print("💬 Transaction added to pending pool.")
        except Exception as e:
            print("❌ Invalid incoming transaction:", e)

    async def handle_incoming_block(self, block_data):
        """Receive a mined block from a peer."""
        print(f"📦 Received block #{block_data['index']} from peer.")

        incoming_index = block_data["index"]
        local_index = len(self.blockchain.chain) - 1

        if incoming_index > local_index:
            print("🔄 Peer has a longer chain. Sync not implemented yet.")
        else:
            print("ℹ Ignoring block (local chain already up-to-date).")

    # local operations
    def create_transaction(self, recipient, amount):
        """Create + sign + locally add a new transaction."""
        tx = Transaction(
            sender=self.wallet.get_public_key_hex(),
            recipient=recipient,
            amount=amount
        )
        tx.sign(self.wallet.get_private_key_hex())
        self.blockchain.add_transaction(tx)
        return tx

    async def send_transaction(self, recipient, amount):
        tx = self.create_transaction(recipient, amount)
        await self.broadcast_transaction(tx)
        print("📤 Transaction broadcasted.")

    async def mine(self):
        """Mine pending transactions."""
        miner_address = self.wallet.get_public_key_hex()

        print("⛏ Mining started...")

        self.blockchain.mine_pending_transactions(miner_address)

        new_block = self.blockchain.get_last_block()
        print(f"🏆 Mined block #{new_block.index} → {new_block.hash[:16]}...")

        await self.broadcast_block(new_block)