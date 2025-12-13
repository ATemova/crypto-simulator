def proof_of_work(block, difficulty):
    required_prefix = "0" * difficulty

    while True:
        block.hash = block.calculate_hash()

        if block.hash.startswith(required_prefix):
            return block.hash

        block.nonce += 1