import hashlib
import json
import math
import time
import uuid

from ecdsa import BadSignatureError, SECP256k1, SigningKey, VerifyingKey

COINBASE = "COINBASE"
AMOUNT_DECIMALS = 8


def normalize_amount(amount) -> float:
    return round(float(amount), AMOUNT_DECIMALS)


def is_valid_address(address) -> bool:
    if not isinstance(address, str) or len(address) != 128:
        return False
    try:
        VerifyingKey.from_string(bytes.fromhex(address), curve=SECP256k1)
        return True
    except (ValueError, AssertionError):
        return False


class Transaction:
    def __init__(self, sender, recipient, amount, signature=None, timestamp=None, nonce=None):
        self.sender = sender
        self.recipient = recipient
        self.amount = normalize_amount(amount)
        self.timestamp = timestamp if timestamp is not None else time.time()
        self.nonce = nonce if nonce is not None else uuid.uuid4().hex
        self.signature = signature

    @property
    def is_coinbase(self) -> bool:
        return self.sender == COINBASE

    @property
    def tx_id(self) -> str:
        return self.calculate_hash()

    def payload(self) -> dict:
        return {
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
        }

    def to_dict(self) -> dict:
        data = self.payload()
        data["signature"] = self.signature
        data["id"] = self.tx_id
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Transaction":
        return cls(
            sender=data["sender"],
            recipient=data["recipient"],
            amount=data["amount"],
            signature=data.get("signature"),
            timestamp=data["timestamp"],
            nonce=data["nonce"],
        )

    def calculate_hash(self) -> str:
        tx_str = json.dumps(self.payload(), sort_keys=True).encode()
        return hashlib.sha256(tx_str).hexdigest()

    def sign(self, private_key_hex: str) -> None:
        if self.is_coinbase:
            return
        sk = SigningKey.from_string(bytes.fromhex(private_key_hex), curve=SECP256k1)
        if sk.get_verifying_key().to_string().hex() != self.sender:
            raise ValueError("Private key does not match sender address")
        self.signature = sk.sign(self.calculate_hash().encode()).hex()

    def has_valid_structure(self) -> bool:
        if not is_valid_address(self.recipient):
            return False
        if not self.is_coinbase and not is_valid_address(self.sender):
            return False
        if not math.isfinite(self.amount) or self.amount <= 0:
            return False
        if self.sender == self.recipient:
            return False
        return True

    def has_valid_signature(self) -> bool:
        if self.is_coinbase:
            return self.signature is None
        if not self.signature:
            return False
        try:
            vk = VerifyingKey.from_string(bytes.fromhex(self.sender), curve=SECP256k1)
            vk.verify(bytes.fromhex(self.signature), self.calculate_hash().encode())
            return True
        except (BadSignatureError, ValueError, AssertionError):
            return False

    def is_valid(self) -> bool:
        return self.has_valid_structure() and self.has_valid_signature()

    def __eq__(self, other):
        return isinstance(other, Transaction) and self.tx_id == other.tx_id

    def __hash__(self):
        return hash(self.tx_id)
