from blockchain.block import Block
from blockchain.transaction import Transaction
from blockchain.pow import proof_of_work

class Blockchain:
    def __init__(self):
        self.chain = [self.create_genesis_block()]
        self.pending_transactions = []
        self.mining_reward = 10
        self.difficulty = 3

    def create_genesis_block(self):
        return Block(0, [], "0")

    def get_last_block(self):
        return self.chain[-1]

    # ---------------------------------------------------
    # TRANSACTIONS
    # ---------------------------------------------------
    def add_transaction(self, tx: Transaction):
        if tx.sender != "COINBASE" and not tx.is_valid():
            raise ValueError("Invalid transaction")
        self.pending_transactions.append(tx)

    # ---------------------------------------------------
    # MINING
    # ---------------------------------------------------
    def mine_pending_transactions(self, miner_address):
        reward_tx = Transaction(
            sender="COINBASE",
            recipient=miner_address,
            amount=self.mining_reward
        )
        self.pending_transactions.append(reward_tx)

        block = Block(
            index=len(self.chain),
            transactions=self.pending_transactions,
            previous_hash=self.get_last_block().hash
        )

        proof_of_work(block, self.difficulty)
        self.chain.append(block)

        # clear pool
        self.pending_transactions = []

        return block  # IMPORTANT FIX

    # ---------------------------------------------------
    # VALIDATION
    # ---------------------------------------------------
    def is_chain_valid(self):
        for i in range(1, len(self.chain)):
            curr = self.chain[i]
            prev = self.chain[i - 1]

            if curr.hash != curr.calculate_hash():
                return False
            if curr.previous_hash != prev.hash:
                return False

        return True