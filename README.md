<p align="center">
  <img src="https://raw.githubusercontent.com/ATemova/crypto-simulator/main/crypto-simulator.png"
       alt="Crypto Simulator Logo"
       width="120">
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge">
  <img alt="Status" src="https://img.shields.io/badge/Status-Active-brightgreen?style=for-the-badge">
  <img alt="License" src="https://img.shields.io/badge/License-MIT-orange?style=for-the-badge">
</p>

<h1 align="center">🚀 Crypto Simulator</h1>

<p align="center">
A simple <b>Python blockchain simulator</b> featuring mining, transactions, wallets, peer-to-peer networking, and an optional web dashboard.
</p>

---

## ⭐ Features

### 🔗 Blockchain
- Genesis block  
- Signed transactions (ECDSA)  
- Proof-of-Work mining  
- Mining rewards  
- Full chain integrity validation  

### 💼 Wallet
- ECDSA keypair generation  
- Transaction signing & verification  

### 🌐 Peer-to-Peer Network
- Async TCP nodes  
- Manual peer connections  
- Broadcast of transactions & blocks  

### 🖥 Web Dashboard (Optional)
- Live blockchain stats (via WebSocket)  
- Block explorer  
- One-click mining  
- Works through FastAPI  

---

## ▶ Running the Simulator (CLI)

### Install dependencies
```bash
pip install -r requirements.txt
```
### Start node #1
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
connect 8000
```

### Send a transaction
```bash
send <recipient_public_key> 5
```

⚠️ Current Limitations
- Full blockchain synchronization
- Proper balance tracking / UTXO
- Automatic peer discovery
- Persistent database
- Better networking protocol
- Improved dashboard UI

🛠 Technologies
- Python
- FastAPI + WebSockets
- asyncio networking
- ECDSA (SECP256k1)
- SHA-256 hashing
- Proof-of-Work

📄 License
- This project is released under the MIT License