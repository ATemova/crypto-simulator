<p align="center">
  <img src="https://raw.githubusercontent.com/ATemova/crypto-simulator/main/crypto-simulator.png"
       alt="Crypto Simulator Logo"
       width="120">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python" />
  <img src="https://img.shields.io/badge/Cryptography-ECDSA-purple?style=flat-square" />
  <img src="https://img.shields.io/badge/Consensus-Proof--of--Work-orange?style=flat-square" />
  <img src="https://img.shields.io/badge/Networking-P2P-informational?style=flat-square" />
  <img src="https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi" />
  <img src="https://img.shields.io/badge/Communication-WebSockets-darkgreen?style=flat-square" />
  <img src="https://img.shields.io/badge/Blockchain-Distributed%20Ledger-success?style=flat-square" />
  <img src="https://img.shields.io/badge/Status-Completed-brightgreen?style=flat-square" />
</p>

# 🚀 Crypto Simulator

A blockchain simulator implemented in **Python** that demonstrates the core principles of distributed ledger technologies, including transaction signing, Proof-of-Work consensus, peer-to-peer networking, and block validation.

The project provides both a command-line interface and an optional web dashboard, allowing multiple nodes to communicate over a lightweight peer-to-peer network while maintaining a shared blockchain.

## 🎥 Demonstration

![Crypto Simulator](crypto-simulator.gif)

## 🧠 Motivation

Blockchain systems combine cryptography, distributed networking, and consensus algorithms to maintain a secure, decentralized ledger without relying on a trusted third party.

This project explores these concepts by implementing the essential components of a blockchain from first principles, focusing on correctness, modularity, and educational value.

## ⚙️ System Overview

The simulator consists of the following components:

- Blockchain ledger
- Wallet and digital signatures
- Proof-of-Work mining
- Peer-to-peer networking
- Web dashboard
- Block validation engine

Multiple nodes can operate simultaneously, exchange transactions, propagate newly mined blocks, and independently validate the integrity of the blockchain.

## 🏗 Architecture

```text
Wallet
   │
   ▼
Signed Transaction
   │
   ▼
Peer-to-Peer Network
   │
   ▼
Mempool
   │
   ▼
Proof-of-Work Miner
   │
   ▼
New Block
   │
   ▼
Blockchain
   │
   ▼
FastAPI Dashboard
```

## 🚀 Core Features

### 🔗 Blockchain

- Genesis block creation
- Block hashing using SHA-256
- Blockchain validation
- Immutable block structure
- Transaction storage

### ⛏ Consensus

- Proof-of-Work mining
- Configurable mining difficulty
- Mining rewards
- Block verification

### 💼 Wallet

- ECDSA key pair generation
- Digital transaction signing
- Signature verification
- Secure public/private key management

### 🌐 Peer-to-Peer Networking

- Asynchronous TCP communication
- Manual peer discovery
- Transaction broadcasting
- Block propagation

### 🖥 Web Dashboard

- Live blockchain statistics
- Block explorer
- One-click mining
- WebSocket updates
- FastAPI backend

## 📊 Technologies

| Layer | Technologies |
||-|
| Language | Python |
| Cryptography | ECDSA (SECP256k1) |
| Consensus | Proof-of-Work |
| Hashing | SHA-256 |
| Networking | asyncio TCP |
| Backend | FastAPI |
| Communication | WebSockets |

## ▶️ Quick Start

### Install dependencies

```bash
pip install -r requirements.txt
```

### Start the first node

```bash
python app.py
```

Enter:

```text
8000
```

### Start another node

```bash
python app.py
```

Enter:

```text
8001
```

### Connect nodes

```bash
connect 8000
```

### Create a transaction

```bash
send <recipient_public_key> 5
```

## 🔬 Engineering Focus

The project demonstrates practical implementation of:

- Distributed ledger architecture
- Cryptographic signatures
- Peer-to-peer communication
- Consensus algorithms
- Blockchain validation
- Event-driven networking

## 🚧 Current Limitations

The simulator intentionally focuses on blockchain fundamentals and does not yet implement:

- Full blockchain synchronization
- UTXO-based balance management
- Automatic peer discovery
- Persistent storage
- Advanced networking protocols
- Byzantine fault tolerance
- Smart contracts

## 🎯 Outcome

Crypto Simulator provides a compact yet complete implementation of the core mechanisms behind blockchain systems, illustrating how cryptographic security, distributed networking, and Proof-of-Work consensus interact to maintain a decentralized ledger.
