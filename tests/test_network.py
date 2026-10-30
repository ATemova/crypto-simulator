import asyncio

import pytest

from network.node import Node

DIFF = 2


async def wait_for(predicate, timeout=5.0):
    deadline = asyncio.get_running_loop().time() + timeout
    while not predicate():
        if asyncio.get_running_loop().time() > deadline:
            raise AssertionError("condition not met in time")
        await asyncio.sleep(0.02)


async def start_nodes(count):
    nodes = [Node(0, difficulty=DIFF, verbose=False) for _ in range(count)]
    for node in nodes:
        await node.start()
    return nodes


def run(coro):
    asyncio.run(coro)


def test_new_node_syncs_existing_chain():
    async def scenario():
        a, b = await start_nodes(2)
        try:
            for _ in range(3):
                await a.mine()
            await b.connect_to_peer("127.0.0.1", a.port)
            await wait_for(lambda: b.blockchain.height == 4)
            assert b.blockchain.get_last_block().hash == a.blockchain.get_last_block().hash
            assert b.get_balance(a.address)["confirmed"] == 30
        finally:
            await a.stop()
            await b.stop()

    run(scenario())


def test_transaction_and_block_propagate_through_relay():
    async def scenario():
        a, b, c = await start_nodes(3)
        try:
            await b.connect_to_peer("127.0.0.1", a.port)
            await c.connect_to_peer("127.0.0.1", b.port)
            await a.mine()
            await wait_for(lambda: c.blockchain.height == 2)

            tx = await a.send_transaction(c.address, 4)
            await wait_for(lambda: any(p.tx_id == tx.tx_id for p in c.blockchain.pending_transactions))

            block = await c.mine()
            assert block is not None
            await wait_for(lambda: a.blockchain.height == 3 and b.blockchain.height == 3)
            assert a.get_balance()["confirmed"] == 6
            assert a.get_balance(c.address)["confirmed"] == 14
            assert a.blockchain.pending_transactions == []
        finally:
            for node in (a, b, c):
                await node.stop()

    run(scenario())


def test_forged_coinbase_from_peer_is_rejected():
    async def scenario():
        a, b = await start_nodes(2)
        try:
            await b.connect_to_peer("127.0.0.1", a.port)
            await wait_for(lambda: len(a.p2p.peers) == 1)
            forged = {
                "sender": "COINBASE",
                "recipient": b.address,
                "amount": 1_000_000,
                "timestamp": 0,
                "nonce": "x",
                "signature": None,
            }
            await b.p2p.broadcast({"type": "transaction", "data": forged})
            await asyncio.sleep(0.2)
            assert a.blockchain.pending_transactions == []
        finally:
            await a.stop()
            await b.stop()

    run(scenario())


def test_fork_resolves_to_longest_chain():
    async def scenario():
        a, b = await start_nodes(2)
        try:
            await a.mine()
            await b.mine()
            await b.mine()
            await a.connect_to_peer("127.0.0.1", b.port)
            await wait_for(lambda: a.blockchain.height == 3)
            assert a.blockchain.get_last_block().hash == b.blockchain.get_last_block().hash
            assert a.get_balance()["confirmed"] == 0
        finally:
            await a.stop()
            await b.stop()

    run(scenario())


def test_peer_list_is_serializable_and_self_connect_refused():
    async def scenario():
        a, b = await start_nodes(2)
        try:
            await a.connect_to_peer("127.0.0.1", b.port)
            await wait_for(lambda: len(b.p2p.peers) == 1)
            assert a.p2p.peer_list()[0]["address"] == f"127.0.0.1:{b.port}"
            with pytest.raises(ValueError):
                await a.connect_to_peer("127.0.0.1", a.port)
            with pytest.raises(ValueError):
                await a.connect_to_peer("127.0.0.1", b.port)
        finally:
            await a.stop()
            await b.stop()

    run(scenario())
