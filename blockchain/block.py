import hashlib
import json
import time

from blockchain.transaction import Transaction


class Block:
    def __init__(self, index, transactions, previous_hash, nonce=0, timestamp=None, difficulty=0, block_hash=None):
        self.index = index
        self.timestamp = timestamp if timestamp is not None else time.time()
        self.transactions = list(transactions)
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.difficulty = difficulty
        self.hash = block_hash if block_hash is not None else self.calculate_hash()

    def header(self) -> dict:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "difficulty": self.difficulty,
        }

    def calculate_hash(self) -> str:
        block_string = json.dumps(self.header(), sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def meets_difficulty(self) -> bool:
        return self.hash.startswith("0" * self.difficulty)

    def to_dict(self) -> dict:
        data = self.header()
        data["hash"] = self.hash
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Block":
        return cls(
            index=data["index"],
            transactions=[Transaction.from_dict(tx) for tx in data["transactions"]],
            previous_hash=data["previous_hash"],
            nonce=data["nonce"],
            timestamp=data["timestamp"],
            difficulty=data["difficulty"],
            block_hash=data["hash"],
        )
