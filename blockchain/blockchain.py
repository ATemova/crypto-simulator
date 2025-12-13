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

    def add_transaction(self, transaction: Transaction):
        if transaction.sender != "MINING_REWARD":
            if not transaction.sender or not transaction.recipient:
                raise ValueError("Invalid transaction fields.")
            if not transaction.is_valid():
                raise ValueError("Invalid signature.")

        self.pending_transactions.append(transaction)

    def mine_pending_transactions(self, miner_address):
        reward_tx = Transaction(
            sender="MINING_REWARD",
            recipient=miner_address,
            amount=self.mining_reward,
            signature=""
        )
        self.pending_transactions.append(reward_tx)

        new_block = Block(
            index=len(self.chain),
            transactions=self.pending_transactions,
            previous_hash=self.get_last_block().hash
        )

        print("⛏ Mining block...")
        proof_of_work(new_block, self.difficulty)

        print(f"✔ Block mined: {new_block.hash}")
        self.chain.append(new_block)

        self.pending_transactions = []

    def is_chain_valid(self):
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            if current.hash != current.calculate_hash():
                print("❌ Block hash mismatch")
                return False

            if current.previous_hash != previous.hash:
                print("❌ Chain link broken")
                return False

            for tx in current.transactions:
                if tx.sender != "MINING_REWARD" and not tx.is_valid():
                    print("❌ Invalid transaction detected")
                    return False

        return True