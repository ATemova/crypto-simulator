import hashlib
import json
from ecdsa import SigningKey, VerifyingKey, SECP256k1

class Transaction:
    def __init__(self, sender, recipient, amount, signature=None):
        self.sender = sender        # public key hex OR "MINING_REWARD"
        self.recipient = recipient  # public key hex
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
        tx_str = json.dumps({
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount
        }, sort_keys=True).encode()

        return hashlib.sha256(tx_str).hexdigest()

    def sign(self, private_key_hex):
        if self.sender == "MINING_REWARD":
            return  # no signature needed
        
        sk = SigningKey.from_string(bytes.fromhex(private_key_hex), curve=SECP256k1)
        message = self.calculate_hash().encode()
        self.signature = sk.sign(message).hex()

    def is_valid(self):
        if self.sender == "MINING_REWARD":
            return True

        if not self.signature:
            return False

        try:
            vk = VerifyingKey.from_string(bytes.fromhex(self.sender), curve=SECP256k1)
            vk.verify(bytes.fromhex(self.signature), self.calculate_hash().encode())
            return True
        except:
            return False