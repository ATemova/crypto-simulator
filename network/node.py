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

    # network callbacks
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

    # local operations
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
        miner_addr = self.wallet.get_public_key_hex()
        self.blockchain.mine_pending_transactions(miner_addr)

        block = self.blockchain.get_last_block()
        await self.p2p.broadcast({
            "type": "new_block",
            "data": {
                "index": block.index,
                "hash": block.hash,
                "transactions": [t.to_dict() for t in block.transactions]
            }
        })

        print(f"⛏ Mining complete. Block #{block.index}")

    # utility commands for CLI
    def get_balance(self):
        pk = self.wallet.get_public_key_hex()
        balance = 0

        for block in self.blockchain.chain:
            for tx in block.transactions:
                if tx.recipient == pk:
                    balance += tx.amount
                if tx.sender == pk:
                    balance -= tx.amount
        return balance

    def print_blocks(self):
        for block in self.blockchain.chain:
            print(f"\nBlock #{block.index}")
            print("Hash:", block.hash[:20], "...")
            print("Prev:", block.previous_hash[:20], "...")
            print("Tx count:", len(block.transactions))

            for tx in block.transactions:
                print(" -", tx.to_dict())

    def print_txpool(self):
        pool = self.blockchain.pending_transactions
        if not pool:
            print("🕳 Pending transaction pool empty.")
            return

        print(f"🧾 {len(pool)} pending transactions:")
        for tx in pool:
            print(" -", tx.to_dict())

    def print_peers(self):
        if not self.p2p.peers:
            print("🌐 No connected peers.")
            return

        print("🌐 Connected peers:")
        for _, writer in self.p2p.peers:
            addr = writer.get_extra_info("peername")
            print(" -", addr)

    def print_state(self):
        print("\nNode State")
        print("Balance:", self.get_balance())
        print("Blockchain height:", len(self.blockchain.chain))
        print("Pending transactions:", len(self.blockchain.pending_transactions))
        print("Peers:", len(self.p2p.peers))