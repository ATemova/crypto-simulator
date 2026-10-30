from collections import defaultdict

from blockchain.block import Block
from blockchain.pow import proof_of_work
from blockchain.transaction import COINBASE, Transaction, normalize_amount

DEFAULT_DIFFICULTY = 5
DEFAULT_MINING_REWARD = 10.0
MAX_TXS_PER_BLOCK = 500


class ValidationError(ValueError):
    pass


def create_genesis_block() -> Block:
    return Block(index=0, transactions=[], previous_hash="0", nonce=0, timestamp=0, difficulty=0)


GENESIS_HASH = create_genesis_block().hash


class Blockchain:
    def __init__(self, difficulty=DEFAULT_DIFFICULTY, mining_reward=DEFAULT_MINING_REWARD):
        self.difficulty = difficulty
        self.mining_reward = normalize_amount(mining_reward)
        self.chain = [create_genesis_block()]
        self.pending_transactions = []
        self._balances = defaultdict(float)
        self._confirmed_ids = set()

    # ---------------------------------------------------
    # STATE
    # ---------------------------------------------------
    def get_last_block(self) -> Block:
        return self.chain[-1]

    @property
    def height(self) -> int:
        return len(self.chain)

    def get_balance(self, address: str) -> float:
        return normalize_amount(self._balances.get(address, 0.0))

    def get_available_balance(self, address: str) -> float:
        outgoing = sum(tx.amount for tx in self.pending_transactions if tx.sender == address)
        return normalize_amount(self.get_balance(address) - outgoing)

    def to_list(self) -> list:
        return [block.to_dict() for block in self.chain]

    def find_transaction(self, tx_id: str):
        for block in self.chain:
            for tx in block.transactions:
                if tx.tx_id == tx_id:
                    return block.index, tx
        return None

    # ---------------------------------------------------
    # TRANSACTIONS
    # ---------------------------------------------------
    def validate_pending_transaction(self, tx: Transaction) -> None:
        if tx.is_coinbase:
            raise ValidationError("Coinbase transactions can only be created by miners")
        if not tx.has_valid_structure():
            raise ValidationError("Malformed transaction (check address and amount)")
        if not tx.has_valid_signature():
            raise ValidationError("Invalid signature")
        if tx.tx_id in self._confirmed_ids:
            raise ValidationError("Transaction already confirmed")
        if any(p.tx_id == tx.tx_id for p in self.pending_transactions):
            raise ValidationError("Transaction already pending")
        if tx.amount > self.get_available_balance(tx.sender) + 1e-9:
            raise ValidationError("Insufficient funds")

    def add_transaction(self, tx: Transaction) -> None:
        self.validate_pending_transaction(tx)
        self.pending_transactions.append(tx)

    # ---------------------------------------------------
    # MINING
    # ---------------------------------------------------
    def build_candidate_block(self, miner_address: str) -> Block:
        coinbase = Transaction(sender=COINBASE, recipient=miner_address, amount=self.mining_reward)
        if not coinbase.has_valid_structure():
            raise ValidationError("Invalid miner address")

        balances = defaultdict(float, self._balances)
        selected = []
        for tx in self.pending_transactions[:MAX_TXS_PER_BLOCK]:
            if tx.tx_id in self._confirmed_ids or not tx.is_valid():
                continue
            if balances[tx.sender] + 1e-9 < tx.amount:
                continue
            balances[tx.sender] -= tx.amount
            balances[tx.recipient] += tx.amount
            selected.append(tx)

        last = self.get_last_block()
        return Block(
            index=last.index + 1,
            transactions=[coinbase] + selected,
            previous_hash=last.hash,
            difficulty=self.difficulty,
        )

    def mine_pending_transactions(self, miner_address: str) -> Block:
        block = self.build_candidate_block(miner_address)
        proof_of_work(block, self.difficulty)
        self.add_block(block)
        return block

    # ---------------------------------------------------
    # VALIDATION
    # ---------------------------------------------------
    def _validate_block(self, block: Block, previous: Block, balances, seen_ids) -> None:
        if block.index != previous.index + 1:
            raise ValidationError(f"Bad index {block.index}, expected {previous.index + 1}")
        if block.previous_hash != previous.hash:
            raise ValidationError("previous_hash does not match")
        if block.difficulty != self.difficulty:
            raise ValidationError("Wrong difficulty")
        if block.hash != block.calculate_hash():
            raise ValidationError("Block hash mismatch")
        if not block.meets_difficulty():
            raise ValidationError("Proof-of-Work not satisfied")
        if not block.transactions:
            raise ValidationError("Block has no coinbase")

        coinbase = block.transactions[0]
        if not coinbase.is_coinbase:
            raise ValidationError("First transaction must be coinbase")
        if abs(coinbase.amount - self.mining_reward) > 1e-9:
            raise ValidationError("Wrong mining reward")

        for position, tx in enumerate(block.transactions):
            if position > 0 and tx.is_coinbase:
                raise ValidationError("Multiple coinbase transactions")
            if not tx.is_valid():
                raise ValidationError(f"Invalid transaction {tx.tx_id[:12]}")
            if tx.tx_id in seen_ids:
                raise ValidationError(f"Duplicate transaction {tx.tx_id[:12]}")
            if not tx.is_coinbase:
                if balances[tx.sender] + 1e-9 < tx.amount:
                    raise ValidationError(f"Insufficient funds in {tx.tx_id[:12]}")
                balances[tx.sender] -= tx.amount
            balances[tx.recipient] += tx.amount
            seen_ids.add(tx.tx_id)

    def _replay(self, chain):
        if not chain or chain[0].hash != GENESIS_HASH or chain[0].hash != chain[0].calculate_hash():
            raise ValidationError("Genesis block mismatch")
        balances = defaultdict(float)
        seen_ids = set()
        for previous, block in zip(chain, chain[1:]):
            self._validate_block(block, previous, balances, seen_ids)
        return balances, seen_ids

    def is_chain_valid(self, chain=None) -> bool:
        try:
            self._replay(self.chain if chain is None else chain)
            return True
        except ValidationError:
            return False

    # ---------------------------------------------------
    # CHAIN UPDATES
    # ---------------------------------------------------
    def add_block(self, block: Block) -> None:
        balances = defaultdict(float, self._balances)
        seen_ids = set(self._confirmed_ids)
        self._validate_block(block, self.get_last_block(), balances, seen_ids)
        self.chain.append(block)
        self._balances = balances
        self._confirmed_ids = seen_ids
        self._rebuild_pool(self.pending_transactions)

    def replace_chain(self, new_chain) -> bool:
        if len(new_chain) <= len(self.chain):
            return False
        balances, seen_ids = self._replay(new_chain)

        new_hashes = {block.hash for block in new_chain}
        orphaned = [
            tx
            for block in self.chain
            if block.hash not in new_hashes
            for tx in block.transactions
            if not tx.is_coinbase
        ]

        candidates = orphaned + self.pending_transactions
        self.chain = list(new_chain)
        self._balances = balances
        self._confirmed_ids = seen_ids
        self._rebuild_pool(candidates)
        return True

    def replace_chain_from_dicts(self, chain_data) -> bool:
        try:
            blocks = [Block.from_dict(item) for item in chain_data]
        except (KeyError, TypeError, ValueError) as exc:
            raise ValidationError(f"Malformed chain: {exc}") from exc
        return self.replace_chain(blocks)

    def _rebuild_pool(self, candidates) -> None:
        self.pending_transactions = []
        for tx in candidates:
            try:
                self.add_transaction(tx)
            except ValidationError:
                pass
