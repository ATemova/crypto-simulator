import argparse
import asyncio
import json
import sys
import threading
from datetime import datetime

from blockchain.blockchain import DEFAULT_DIFFICULTY, ValidationError
from blockchain.utils import shorten_key
from network.node import Node

HELP = """
Commands:
 connect <port> | <host:port>  - connect to a peer node
 send <recipient> <amount>     - sign, add to pool and broadcast a transaction
 sendraw <recipient> <amount>  - sign and add to local pool without broadcasting
 broadcast                     - broadcast all pending transactions to peers
 mine                          - mine a block with pending transactions
 balance [address]             - show confirmed and available balance
 chain                         - show chain height and validity
 blocks [n]                    - list the last n blocks (default 10)
 block <index>                 - show a block as JSON
 txpool                        - show pending transactions
 peers                         - show connected peers
 sync                          - request chains from all peers
 address                       - show your public key
 state                         - show node state summary
 validate                      - fully re-validate the chain
 help                          - show this list
 exit                          - quit
"""


def parse_peer(value: str, default_host: str):
    if ":" in value:
        host, port = value.replace("tcp://", "").rsplit(":", 1)
        return host, int(port)
    return default_host, int(value)


def print_blocks(node: Node, count: int) -> None:
    for block in node.blockchain.chain[-count:]:
        when = "genesis" if block.index == 0 else datetime.fromtimestamp(block.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        print(f"#{block.index:<4} {block.hash[:20]}...  txs={len(block.transactions):<3} nonce={block.nonce:<8} {when}")


def print_txpool(node: Node) -> None:
    pool = node.blockchain.pending_transactions
    if not pool:
        print("📭 Transaction pool is empty.")
        return
    for tx in pool:
        print(f"{tx.tx_id[:12]}  {shorten_key(tx.sender)} → {shorten_key(tx.recipient)}  {tx.amount}")


def print_peers(node: Node) -> None:
    peers = node.p2p.peer_list()
    if not peers:
        print("🕸 No peers connected.")
        return
    for peer in peers:
        print(f"[{peer['id']}] {peer['address']} ({peer['direction']})")


def print_state(node: Node) -> None:
    state = node.state()
    print(f"🔑 Address:    {shorten_key(state['address'])}")
    print(f"🔌 P2P port:   {state['p2p_port']}")
    print(f"⛓ Height:     {state['height']}  tip {state['tip_hash'][:16]}...")
    print(f"🎯 Difficulty: {state['difficulty']}  reward {state['mining_reward']}")
    print(f"💰 Balance:    {state['balance']['confirmed']} (available {state['balance']['available']})")
    print(f"📥 Pending:    {state['pending']}")
    print(f"🕸 Peers:      {state['peers']}")
    print(f"✔ Valid:      {state['valid']}")


async def handle(node: Node, cmd: list, default_host: str) -> bool:
    name, args = cmd[0].lower(), cmd[1:]

    if name == "connect" and len(args) == 1:
        host, port = parse_peer(args[0], default_host)
        await node.connect_to_peer(host, port)
    elif name == "send" and len(args) == 2:
        tx = await node.send_transaction(args[0], float(args[1]))
        print(f"📤 Sent {tx.amount} (tx {tx.tx_id[:12]})")
    elif name == "sendraw" and len(args) == 2:
        tx = node.create_transaction(args[0], float(args[1]))
        print("📦 Raw transaction created and added to local pool:")
        print(json.dumps(tx.to_dict(), indent=2))
    elif name == "broadcast" and not args:
        print(f"📤 Broadcast {await node.broadcast_pending()} pending transaction(s)")
    elif name == "mine" and not args:
        block = await node.mine()
        if block is None:
            print("⛏ No block mined.")
    elif name == "balance" and len(args) <= 1:
        balance = node.get_balance(args[0] if args else None)
        print(f"💰 Balance: {balance['confirmed']} (available {balance['available']})")
    elif name == "chain" and not args:
        print(f"⛓ Height: {node.blockchain.height}")
        print(f"✔ Valid: {node.blockchain.is_chain_valid()}")
    elif name == "blocks" and len(args) <= 1:
        print_blocks(node, int(args[0]) if args else 10)
    elif name == "block" and len(args) == 1:
        index = int(args[0])
        if not 0 <= index < node.blockchain.height:
            print("❌ No such block.")
        else:
            print(json.dumps(node.blockchain.chain[index].to_dict(), indent=2))
    elif name == "txpool" and not args:
        print_txpool(node)
    elif name == "peers" and not args:
        print_peers(node)
    elif name == "sync" and not args:
        await node.p2p.broadcast({"type": "get_chain"})
        print("🔄 Chain requested from all peers.")
    elif name == "address" and not args:
        print("🔑 Your address:")
        print(node.address)
    elif name == "state" and not args:
        print_state(node)
    elif name == "validate" and not args:
        print("✔ Chain valid:", node.blockchain.is_chain_valid())
    elif name == "help":
        print(HELP)
    elif name in ("exit", "quit"):
        return False
    else:
        print("❌ Unknown command or wrong arguments. Type 'help'.")
    return True


class ConsoleReader:
    def __init__(self):
        self._loop = asyncio.get_running_loop()
        self._queue = asyncio.Queue()
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        for line in sys.stdin:
            self._loop.call_soon_threadsafe(self._queue.put_nowait, line.rstrip("\n"))
        self._loop.call_soon_threadsafe(self._queue.put_nowait, None)

    async def readline(self, prompt: str):
        print(prompt, end="", flush=True)
        line = await self._queue.get()
        if line is None:
            raise EOFError
        return line


async def ask_port(console: ConsoleReader) -> int:
    while True:
        raw = await console.readline("Enter P2P port for this node: ")
        try:
            port = int(raw)
            if 0 < port < 65536:
                return port
        except ValueError:
            pass
        print("❌ Invalid port.")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Crypto Simulator node (CLI)")
    parser.add_argument("--port", type=int, help="P2P port to listen on")
    parser.add_argument("--host", default="127.0.0.1", help="interface to bind")
    parser.add_argument("--peer", action="append", default=[], help="peer to connect to (port or host:port)")
    parser.add_argument("--difficulty", type=int, default=DEFAULT_DIFFICULTY, help="PoW difficulty (leading hex zeros)")
    options = parser.parse_args()

    print("\nCrypto Simulator\n")
    console = ConsoleReader()
    port = options.port or await ask_port(console)

    node = Node(port, host=options.host, difficulty=options.difficulty)
    await node.start()
    for peer in options.peer:
        try:
            await node.connect_to_peer(*parse_peer(peer, options.host))
        except (OSError, ValueError) as exc:
            print(f"❌ Could not connect to {peer}: {exc}")

    print(HELP)
    try:
        while True:
            try:
                line = await console.readline("> ")
            except EOFError:
                break
            cmd = line.split()
            if not cmd:
                continue
            try:
                if not await handle(node, cmd, options.host):
                    break
            except ValidationError as exc:
                print(f"❌ {exc}")
            except (OSError, ValueError) as exc:
                print(f"❌ {exc}")
    finally:
        print("👋 Exiting...")
        await node.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
