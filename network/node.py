import asyncio
from blockchain.blockchain import Blockchain
from blockchain.transaction import Transaction
from blockchain.wallet import Wallet
from network.p2p import P2PNetwork

class Node:
    def __init__(self, port):
        self.port = port
        self.wallet = Wallet()
        self.blockchain = Blockchain()
        self.p2p = P2PNetwork(self)

        print(f"🟢 Node started on port {port}")
        print(f"🔑 Public Key: {self.wallet.get_public_key_hex()[:20]}...")

    async def start(self):
        asyncio.create_task(self.p2p.start_server(port=self.port))
        await asyncio.sleep(0.3)

    async def connect_to_peer(self, url):
        await self.p2p.connect_to_peer(url)

    # ---------------------------------------------------
    # INCOMING NETWORK MESSAGES
    # ---------------------------------------------------

    async def handle_network_message(self, msg):
        if msg["type"] == "transaction":
            await self.handle_incoming_transaction(msg["data"])

        elif msg["type"] == "new_block":
            await self.handle_incoming_block(msg["data"])

    async def handle_incoming_transaction(self, data):
        tx = Transaction(
            sender=data["sender"],
            recipient=data["recipient"],
            amount=data["amount"],
            signature=data["signature"]
        )

        try:
            self.blockchain.add_transaction(tx)
            print("💬 Received transaction added to pool.")
        except Exception as e:
            print("❌ Invalid transaction:", e)

    async def handle_incoming_block(self, block_data):
        print(f"📦 Received block #{block_data['index']} (sync not implemented).")

    # ---------------------------------------------------
    # LOCAL ACTIONS
    # ---------------------------------------------------

    def create_transaction(self, recipient, amount):
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
        await self.p2p.broadcast({"type": "transaction", "data": tx.to_dict()})
        print("📤 Transaction broadcasted.")

    async def mine(self):
        """Perform mining, return the mined block."""
        miner_addr = self.wallet.get_public_key_hex()

        print("⛏ Mining started...")
        block = self.blockchain.mine_pending_transactions(miner_addr)
        print(f"⛏ Block #{block.index} mined!")

        # Broadcast block
        await self.p2p.broadcast({
            "type": "new_block",
            "data": block.to_dict()
        })

        return block