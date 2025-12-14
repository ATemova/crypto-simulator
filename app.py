import asyncio
from network.node import Node

async def main():
    print("\nCrypto Simulator\n")

    # Ask for port
    while True:
        try:
            port = int(input("Enter port for this node: "))
            break
        except ValueError:
            print("❌ Invalid port.")

    node = Node(port)
    await node.start()

    # COMMAND LIST
    print("\nCommands:")
    print(" connect <port>              - connect to peer node")
    print(" send <recipient> <amount>   - send coins")
    print(" sendraw <recipient> <amount>- create tx without broadcast")
    print(" mine                        - mine pending transactions")
    print(" balance                     - show your balance")
    print(" chain                       - show blockchain length + validity")
    print(" blocks                      - list all blocks")
    print(" txpool                      - show pending transactions")
    print(" peers                       - show connected peers")
    print(" address                     - show your public key")
    print(" state                       - show node state summary")
    print(" validate                    - full chain validation")
    print(" exit                        - quit\n")

    # MAIN LOOP
    while True:
        cmd = input("> ").split()

        if not cmd:
            continue

        # CONNECT
        if cmd[0] == "connect" and len(cmd) == 2:
            peer_port = cmd[1]
            await node.connect_to_peer(f"tcp://127.0.0.1:{peer_port}")

        # SEND TRANSACTION
        elif cmd[0] == "send" and len(cmd) == 3:
            await node.send_transaction(cmd[1], float(cmd[2]))

        # SEND RAW (no broadcast)
        elif cmd[0] == "sendraw" and len(cmd) == 3:
            tx = node.create_transaction(cmd[1], float(cmd[2]))
            print("📦 Raw transaction created:")
            print(tx.to_dict())

        # MINING
        elif cmd[0] == "mine":
            await node.mine()

        # BALANCE
        elif cmd[0] == "balance":
            print("💰 Balance:", node.get_balance())

        # CHAIN STATS
        elif cmd[0] == "chain":
            print(f"⛓ Length: {len(node.blockchain.chain)}")
            print("✔ Valid:", node.blockchain.is_chain_valid())

        # LIST BLOCKS
        elif cmd[0] == "blocks":
            node.print_blocks()

        # TX POOL
        elif cmd[0] == "txpool":
            node.print_txpool()

        # PEERS
        elif cmd[0] == "peers":
            node.print_peers()

        # ADDRESS
        elif cmd[0] == "address":
            print("🔑 Your address:")
            print(node.wallet.get_public_key_hex())

        # NODE STATE
        elif cmd[0] == "state":
            node.print_state()

        # VALIDATE
        elif cmd[0] == "validate":
            print("✔ Chain valid:", node.blockchain.is_chain_valid())

        # EXIT
        elif cmd[0] == "exit":
            print("👋 Exiting...")
            break

        else:
            print("❌ Unknown command.")


if __name__ == "__main__":
    asyncio.run(main())