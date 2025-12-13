# 🚀 Crypto Simulator

A lightweight **Python blockchain simulator** featuring:
- A custom blockchain  
- Transaction signing (ECDSA)  
- Proof-of-Work mining  
- Wallet key pairs  
- Peer-to-peer TCP communication  
- Multiple interactive CLI nodes  

This project is for **learning & experimentation**, not production use.

## ⭐ Features

### Blockchain
- Genesis block creation
- Transactions with digital signatures
- Proof-of-Work mining algorithm
- Mining rewards
- Adjustable difficulty
- Full blockchain validation

### Wallets
- Each node generates its own ECDSA key pair
- Supports signing + verifying transactions

### Peer-to-Peer Network
- Fully asynchronous TCP networking
- Nodes can connect to each other manually
- Broadcasting:
  - New transactions
  - Newly mined blocks
- Incoming & outgoing connections handled simultaneously

## ▶ How to Run

### Install dependencies
```bash
pip install -r requirements.txt
```
### Start Node #1
```bash
python app.py
Enter: 8000
```
### Start Node #2 (new terminal)
```bash
python app.py
Enter: 8001
```
### Connect nodes
```bash
In Node #2: connect 8000
```
### Send a transaction
```bash
send <recipient_public_key> 5
```

## ⚠️ Known Limitations (To Be Improved)
These will be added in future updates:

- No full blockchain synchronization yet  
- Blocks from peers not merged into local chain  
- No UTXO model or balances verification  
- No persistent storage  
- Mining rewards simplified  
- No automatic peer discovery  


## 🛠 Technologies Used
- Python 3  
- asyncio  
- ecdsa (SECP256k1)  
- SHA-256 hashing  
- Proof-of-Work  


## 📌 Future Development
Planned improvements:

- Full chain download + sync between nodes  
- Web interface for monitoring the chain  
- UTXO or account-based balance tracking  
- Transaction mempool validation  
- Networking with peer discovery  
- Persistent DB storage
