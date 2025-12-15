<p align="center">
  <img src="https://raw.githubusercontent.com/ATemova/crypto-simulator/3b71cc20169a9b4a278d8eed86ef7e622f53f8ba/crypto-simulator.png" 
       alt="Crypto Simulator Logo" 
       width="120">
</p>

<h1 align="center">🚀 Crypto Simulator</h1>

<p align="center">
A lightweight <b>Python blockchain simulator</b> for learning and experimentation.
</p>

## ⭐ Features

### Blockchain
- Genesis block creation  
- Signed transactions (ECDSA)  
- Proof-of-Work mining  
- Mining rewards  
- Adjustable difficulty  
- Full chain validation  

### Wallets
- Auto-generated ECDSA key pair  
- Digital signature support  

### Peer-to-Peer Network
- Asynchronous TCP communication  
- Manual peer connections  
- Broadcasts transactions + blocks  
- Handles multiple peers at once  


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
### Connect Node #2 → Node #1
```bash
connect 8000
```
### Send a transaction
```bash
send <recipient_public_key> 5
```

## ⚠️ Known Limitations (To Be Improved)
These will be added in future updates:

- No blockchain synchronization
- Blocks from peers not merged
- No UTXO/accounting model
- No persistent storage
- Mining reward simplified
- No automatic peer discovery

## 🛠 Technologies Used
- Python 3  
- asyncio  
- ecdsa (SECP256k1)  
- SHA-256 hashing  
- Proof-of-Work  

## 📌 Future Development
Planned improvements:

- Full node synchronization
- Web dashboard interface
- UTXO or account-based balances
- Mempool validation
- Peer discovery

- Database storage
