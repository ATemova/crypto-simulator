import hashlib
import json


class MiningCancelled(Exception):
    pass


def _header_parts(block):
    header = block.header()
    head = json.dumps({"difficulty": header["difficulty"], "index": header["index"]}, sort_keys=True)
    tail = json.dumps(
        {
            "previous_hash": header["previous_hash"],
            "timestamp": header["timestamp"],
            "transactions": header["transactions"],
        },
        sort_keys=True,
    )
    return (head[:-1] + ', "nonce": ').encode(), (", " + tail[1:]).encode()


def proof_of_work(block, difficulty, should_stop=None, check_every=5000):
    block.difficulty = difficulty
    prefix = "0" * difficulty
    head, tail = _header_parts(block)

    nonce = 0
    while True:
        digest = hashlib.sha256(head + str(nonce).encode() + tail).hexdigest()
        if digest.startswith(prefix):
            block.nonce = nonce
            block.hash = block.calculate_hash()
            if block.hash != digest:
                raise RuntimeError("Fast PoW hash diverged from Block.calculate_hash")
            return block.hash
        nonce += 1
        if should_stop is not None and nonce % check_every == 0 and should_stop():
            raise MiningCancelled()
