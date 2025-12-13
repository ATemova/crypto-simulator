import hashlib
import json
from ecdsa import SigningKey, VerifyingKey, SECP256k1


class Transaction:
    def __init__(self, sender, recipient, amount, signature=None):
        self.sender = sender
        self.recipient = recipient
        self.amount = amount
        self.signature = signature

    def to_dict(self):
        return {
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "signature": self.signature
        }

    def calculate_hash(self):
        tx_string = json.dumps(self.to_dict(), sort_keys=True).encode()
        return hashlib.sha256(tx_string).hexdigest()

    def sign(self, private_key):
        if self.sender == "MINING_REWARD":
            return

        message = self.calculate_hash().encode()
        sk = SigningKey.from_string(bytes.fromhex(private_key), curve=SECP256k1)
        self.signature = sk.sign(message).hex()

    def is_valid(self):
        if self.sender == "MINING_REWARD":
            return True

        if not self.signature:
            return False

        try:
            vk = VerifyingKey.from_string(bytes.fromhex(self.sender), curve=SECP256k1)
            message = self.calculate_hash().encode()
            vk.verify(bytes.fromhex(self.signature), message)
            return True
        except:
            return False