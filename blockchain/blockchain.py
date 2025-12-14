from blockchain.block import Block
from blockchain.transaction import Transaction
from blockchain.pow import proof_of_work

class Blockchain:
    def __init__(self):
        self.chain = [self.create_genesis_block()]
        self.difficulty = 4
        self.pending_transactions = []
        self.mining_reward = 10

    def create_genesis_block(self):
        return Block(0, [], "0")

    def get_last_block(self):
        return self.chain[-1]

    # add transaction
    def add_transaction(self, tx: Transaction):
        """Add a transaction to the pool, validate if needed."""
        if tx.sender != "MINING_REWARD":
            if not tx.sender or not tx.recipient:
                raise ValueError("Transactions must include sender & recipient.")

            if not tx.is_valid():
                raise ValueError("Invalid transaction signature.")

        self.pending_transactions.append(tx)

    # mining
    def mine_pending_transactions(self, miner_address):
        """Mine pending transactions and add block to chain."""

        # Create reward transaction
        reward_tx = Transaction(
            sender="MINING_REWARD",
            recipient=miner_address,
            amount=self.mining_reward,
            signature=None
        )
        self.pending_transactions.append(reward_tx)

        # Build new block
        new_block = Block(
            index=len(self.chain),
            transactions=self.pending_transactions,
            previous_hash=self.get_last_block().hash
        )

        print("⛏ Mining block with", len(self.pending_transactions), "transactions...")

        # Proof of Work
        proof_of_work(new_block, self.difficulty)

        print(f"✔ Block mined: {new_block.hash[:12]}...")
        self.chain.append(new_block)

        # Clear tx pool
        self.pending_transactions = []

    # validation
    def is_chain_valid(self):
        """Verify entire blockchain integrity."""
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            if current.hash != current.calculate_hash():
                print("❌ Block hash mismatch.")
                return False

            if current.previous_hash != previous.hash:
                print("❌ Chain linkage broken.")
                return False

            for tx in current.transactions:
                if tx.sender != "MINING_REWARD":
                    if not tx.is_valid():
                        print("❌ Invalid transaction detected.")
                        return False

        return True