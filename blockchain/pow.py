def proof_of_work(block, difficulty):
    prefix = "0" * difficulty

    while True:
        block.hash = block.calculate_hash()
        if block.hash.startswith(prefix):
            return block.hash
        
        block.nonce += 1