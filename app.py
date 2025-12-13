import asyncio
from network.node import Node


async def main():
    print("\n=== Crypto Simulator ===\n")

    # ask user for node port
    while True:
        try:
            port = int(input("Enter port for this node (e.g., 8000): "))
            break
        except ValueError:
            print("❌ Please enter a valid number.")

    node = Node(port)
    await node.start()

    print("\nCommands:")
    print(" connect <port>              - connect to peer node")
    print(" send <recipient> <amount>   - send coins")
    print(" mine                        - mine pending transactions")
    print(" balance                     - show your balance")
    print(" chain                       - show blockchain length")
    print(" exit                        - quit\n")

    # main command loop
    while True:
        cmd = input("> ").strip().split()

        if not cmd:
            continue

        # connect to peer
        if cmd[0] == "connect" and len(cmd) == 2:
            try:
                peer_port = int(cmd[1])
                print(f"🔌 Connecting to peer {peer_port} ...")
                asyncio.create_task(node.connect_to_peer(peer_port))

            except ValueError:
                print("❌ Invalid port number.")

        # send transaction
        elif cmd[0] == "send" and len(cmd) == 3:
            recipient = cmd[1]
            try:
                amount = float(cmd[2])
                asyncio.create_task(node.send_transaction(recipient, amount))
            except ValueError:
                print("❌ Amount must be numeric.")

        # mine block
        elif cmd[0] == "mine":
            print("⛏️ Mining started...")
            asyncio.create_task(node.mine())

        # balance
        elif cmd[0] == "balance":
            balance = 0
            pk = node.wallet.get_public_key_hex()

            for block in node.blockchain.chain:
                for tx in block.transactions:
                    if tx.recipient == pk:
                        balance += tx.amount
                    if tx.sender == pk:
                        balance -= tx.amount

            print(f"💰 Balance: {balance}")

        # show chain infro
        elif cmd[0] == "chain":
            print(f"⛓ Chain length: {len(node.blockchain.chain)}")
            print(f"✔ Valid: {node.blockchain.is_chain_valid()}")

        # exit
        elif cmd[0] == "exit":
            print("👋 Exiting node...")
            break

        else:
            print("❌ Unknown command.")


# Entry Point
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Program terminated.")