import copy

import pytest

from blockchain.block import Block
from blockchain.blockchain import GENESIS_HASH, Blockchain, ValidationError
from blockchain.pow import _header_parts, proof_of_work
from blockchain.transaction import COINBASE, Transaction
from blockchain.wallet import Wallet

DIFF = 2


@pytest.fixture
def chain():
    return Blockchain(difficulty=DIFF)


@pytest.fixture
def alice():
    return Wallet()


@pytest.fixture
def bob():
    return Wallet()


def signed(sender: Wallet, recipient: Wallet, amount):
    tx = Transaction(sender.get_public_key_hex(), recipient.get_public_key_hex(), amount)
    tx.sign(sender.get_private_key_hex())
    return tx


def test_genesis_is_deterministic():
    assert Blockchain().chain[0].hash == Blockchain().chain[0].hash == GENESIS_HASH


def test_block_roundtrip(chain, alice):
    block = chain.mine_pending_transactions(alice.get_public_key_hex())
    clone = Block.from_dict(block.to_dict())
    assert clone.hash == block.hash == clone.calculate_hash()


def test_fast_pow_matches_block_hash(alice):
    block = Block(1, [Transaction(COINBASE, alice.get_public_key_hex(), 10)], "ab", difficulty=DIFF)
    head, tail = _header_parts(block)
    import hashlib, json
    assert hashlib.sha256(head + b"0" + tail).hexdigest() == hashlib.sha256(
        json.dumps({**block.header(), "nonce": 0}, sort_keys=True).encode()
    ).hexdigest()
    proof_of_work(block, DIFF)
    assert block.hash == block.calculate_hash() and block.meets_difficulty()


def test_mining_rewards_miner(chain, alice):
    chain.mine_pending_transactions(alice.get_public_key_hex())
    assert chain.get_balance(alice.get_public_key_hex()) == chain.mining_reward
    assert chain.is_chain_valid()


def test_transfer_updates_balances(chain, alice, bob):
    chain.mine_pending_transactions(alice.get_public_key_hex())
    chain.add_transaction(signed(alice, bob, 4))
    assert chain.get_available_balance(alice.get_public_key_hex()) == 6
    chain.mine_pending_transactions(bob.get_public_key_hex())
    assert chain.get_balance(alice.get_public_key_hex()) == 6
    assert chain.get_balance(bob.get_public_key_hex()) == 14
    assert chain.pending_transactions == []


def test_rejects_forged_coinbase(chain, alice):
    with pytest.raises(ValidationError):
        chain.add_transaction(Transaction(COINBASE, alice.get_public_key_hex(), 1_000_000))


@pytest.mark.parametrize("amount", [0, -5, float("inf"), float("nan")])
def test_rejects_bad_amounts(chain, alice, bob, amount):
    chain.mine_pending_transactions(alice.get_public_key_hex())
    tx = Transaction(alice.get_public_key_hex(), bob.get_public_key_hex(), amount)
    tx.sign(alice.get_private_key_hex())
    with pytest.raises(ValidationError):
        chain.add_transaction(tx)


def test_rejects_overspend_including_pending(chain, alice, bob):
    chain.mine_pending_transactions(alice.get_public_key_hex())
    chain.add_transaction(signed(alice, bob, 7))
    with pytest.raises(ValidationError, match="Insufficient"):
        chain.add_transaction(signed(alice, bob, 7))


def test_rejects_bad_signature(chain, alice, bob):
    chain.mine_pending_transactions(alice.get_public_key_hex())
    tx = signed(alice, bob, 1)
    tx.amount = 2
    with pytest.raises(ValidationError, match="signature"):
        chain.add_transaction(tx)


def test_cannot_sign_for_someone_else(alice, bob):
    tx = Transaction(alice.get_public_key_hex(), bob.get_public_key_hex(), 1)
    with pytest.raises(ValueError):
        tx.sign(bob.get_private_key_hex())


def test_rejects_invalid_recipient(chain, alice):
    chain.mine_pending_transactions(alice.get_public_key_hex())
    tx = Transaction(alice.get_public_key_hex(), "not-an-address", 1)
    tx.sign(alice.get_private_key_hex())
    with pytest.raises(ValidationError):
        chain.add_transaction(tx)


def test_rejects_replay(chain, alice, bob):
    chain.mine_pending_transactions(alice.get_public_key_hex())
    tx = signed(alice, bob, 1)
    chain.add_transaction(tx)
    with pytest.raises(ValidationError, match="already pending"):
        chain.add_transaction(copy.deepcopy(tx))
    chain.mine_pending_transactions(alice.get_public_key_hex())
    with pytest.raises(ValidationError, match="already confirmed"):
        chain.add_transaction(copy.deepcopy(tx))


def test_identical_payments_get_distinct_ids(alice, bob):
    assert signed(alice, bob, 1).tx_id != signed(alice, bob, 1).tx_id


def test_detects_tampering(chain, alice, bob):
    chain.mine_pending_transactions(alice.get_public_key_hex())
    chain.add_transaction(signed(alice, bob, 3))
    chain.mine_pending_transactions(alice.get_public_key_hex())
    assert chain.is_chain_valid()
    chain.chain[2].transactions[1].amount = 9
    assert not chain.is_chain_valid()


def test_rejects_block_without_pow(chain, alice):
    block = chain.build_candidate_block(alice.get_public_key_hex())
    block.hash = block.calculate_hash()
    while block.meets_difficulty():
        block.nonce += 1
        block.hash = block.calculate_hash()
    with pytest.raises(ValidationError, match="Proof-of-Work"):
        chain.add_block(block)


def test_rejects_wrong_reward(chain, alice):
    block = Block(1, [Transaction(COINBASE, alice.get_public_key_hex(), 999)], chain.get_last_block().hash)
    proof_of_work(block, DIFF)
    with pytest.raises(ValidationError, match="reward"):
        chain.add_block(block)


def test_rejects_double_coinbase(chain, alice):
    addr = alice.get_public_key_hex()
    block = Block(
        1,
        [Transaction(COINBASE, addr, chain.mining_reward), Transaction(COINBASE, addr, chain.mining_reward)],
        chain.get_last_block().hash,
    )
    proof_of_work(block, DIFF)
    with pytest.raises(ValidationError, match="Multiple coinbase"):
        chain.add_block(block)


def test_longest_valid_chain_wins_and_orphans_return_to_pool(alice, bob):
    a = Blockchain(difficulty=DIFF)
    b = Blockchain(difficulty=DIFF)

    a.mine_pending_transactions(alice.get_public_key_hex())
    b.replace_chain(a.chain)

    tx = signed(alice, bob, 2)
    a.add_transaction(tx)
    a.mine_pending_transactions(alice.get_public_key_hex())

    b.mine_pending_transactions(bob.get_public_key_hex())
    b.mine_pending_transactions(bob.get_public_key_hex())

    assert a.replace_chain(b.chain)
    assert a.chain[-1].hash == b.chain[-1].hash
    assert [p.tx_id for p in a.pending_transactions] == [tx.tx_id]
    assert not a.replace_chain(b.chain)


def test_replace_chain_rejects_invalid(alice):
    a = Blockchain(difficulty=DIFF)
    b = Blockchain(difficulty=DIFF)
    for _ in range(2):
        b.mine_pending_transactions(alice.get_public_key_hex())
    forged = [Block.from_dict(x) for x in b.to_list()]
    forged[1].transactions[0].amount = 500
    with pytest.raises(ValidationError):
        a.replace_chain(forged)
    assert a.height == 1


def test_rejects_wrong_genesis(alice):
    a = Blockchain(difficulty=DIFF)
    fake = [Block(0, [], "0", timestamp=123, difficulty=0)]
    with pytest.raises(ValidationError, match="Genesis"):
        a._replay(fake)
