# Investigation_Messaging_SN

A hands-on investigation into **L1-L2 cross-chain messaging between Ethereum and Starknet**.

This repo is built on top of the smart contract examples by [Glihm](https://github.com/glihm/starknet-messaging-dev). The main original contribution here is the Python orchestration script (`l1_testing.py`) that automates the full local test environment from scratch — spinning up both nodes, deploying contracts on both layers, and executing an end-to-end messaging flow.

---

## What This Repo Investigates

Starknet communicates with Ethereum through a message-passing protocol mediated by the **Starknet Core contract** on L1. This repo explores:

- How to **send messages from L1 (Ethereum) to L2 (Starknet)**
- How to **send messages from L2 (Starknet) to L1 (Ethereum)** and consume them
- How data is **serialized/deserialized** across the two layers (`felt252` ↔ `uint256`, structs)
- How to **automate** a full local bidirectional messaging test with Python

---

## Repository Structure

```
Investigation_Messaging_SN/
├── README.md
└── Testing_L1L2_Com/
    ├── l1_testing.py           # <-- Main contribution: Python orchestration script
    ├── anvil.messaging.json    # Katana messaging config pointing to local Anvil node
    ├── cairo/                  # L2 Cairo contracts (Starknet)
    │   ├── src/
    │   │   └── contract_msg.cairo
    │   ├── Scarb.toml
    │   ├── Makefile
    │   └── katana.env
    └── solidity/               # L1 Solidity contracts (Ethereum)
        ├── src/
    │   │   ├── ContractMsg.sol
    │   │   └── StarknetMessagingLocal.sol
        ├── script/
        │   ├── LocalTesting.s.sol
        │   ├── SendMessage.s.sol
        │   └── ConsumeMessage.s.sol
        ├── foundry.toml
        └── anvil.env
```

---

## Tech Stack

| Layer | Language | Tooling |
|---|---|---|
| L1 – Ethereum | Solidity | Foundry (Forge + Anvil) |
| L2 – Starknet | Cairo 2 | Scarb, Starkli, Katana |
| Orchestration | Python 3 | subprocess, time |

---

## Smart Contracts

### L2 — `contract_msg.cairo` (Starknet)

Handles both sending and receiving messages.

**Sending to L1** (3 variants):
- `send_message_value(to_address, value)` — sends a single `felt252` value
- `send_message_struct(to_address, data)` — sends a serialized `MyData` struct `{ a, b }`
- `send_message_deposit(to_address, receiver, asset, shares, exchange_rate)` — sends a deposit-style payload (4 fields)

All three use the Cairo syscall `send_message_to_l1_syscall`.

**Receiving from L1** (via `#[l1_handler]`):
- `msg_handler_value(from_address, value)` — asserts `value == 123`, emits `ValueReceivedFromL1`
- `msg_handler_struct(from_address, data)` — asserts both `data.a` and `data.b` are non-zero, emits `StructReceivedFromL1`

Only functions annotated with `#[l1_handler]` can receive L1 messages, as the Starknet sequencer uses a special `L1HandlerTransaction` type exclusively for these endpoints.

---

### L1 — `ContractMsg.sol` (Ethereum)

Wraps the Starknet Core messaging contract.

**Sending to L2:**
- `sendMessage(contractAddress, selector, payload[])` — generic send with arbitrary payload
- `sendMessageValue(contractAddress, selector, value)` — convenience wrapper for a single value

**Consuming from L2:**
- `consumeMessage(fromAddress, payload[])` — generic consume
- `consumeMessageValue(fromAddress, payload[])` — validates payload is exactly 1 element > 0
- `consumeMessageStruct(fromAddress, payload[])` — validates payload has 2 elements (fields `a` and `b`)

### L1 — `StarknetMessagingLocal.sol`

A dev-only extension of the standard `StarknetMessaging` contract. Adds `addMessageHashesFromL2()` which lets you manually register message hashes without waiting for Starknet block proofs — essential for fast local testing.

---

## Data Serialization

Starknet's native type is `felt252` (a field element up to ~252 bits). On the Solidity side this maps to `uint256`.

| Cairo type | Solidity type | Notes |
|---|---|---|
| `felt252` | `uint256` | Direct mapping |
| `uint256` | two `uint256` | Must be split into low/high parts |
| struct | `uint256[]` | Cairo's `Serde` trait serializes fields in order |

---

## How the Messaging Flows Work

### L2 → L1

```
Cairo contract
  └─ send_message_to_l1_syscall(l1_address, payload)
       └─ Starknet sequencer includes message in block
            └─ [In local dev] StarknetMessagingLocal.addMessageHashesFromL2()
                 └─ ContractMsg.consumeMessage(fromAddress, payload)
                      └─ Starknet Core verifies hash → message consumed
```

### L1 → L2

```
ContractMsg.sendMessage(l2_address, selector, payload)
  └─ IStarknetMessaging.sendMessageToL2{value: fee}(...)
       └─ Starknet sequencer picks up message
            └─ L2 contract's #[l1_handler] function is called
```

---

## `l1_testing.py` — The Orchestration Script

This is the main original contribution of this repo. It automates the entire local test environment using Python's `subprocess` module, opening multiple `gnome-terminal` windows in sequence:

### What it does, step by step

**Step 1 — Start Anvil (local L1 node)**
```python
anvil --fork-url https://eth-mainnet.g.alchemy.com/v2/<KEY>
```
Forks Ethereum mainnet locally. Waits 3 seconds for initialization.

**Step 2 — Deploy L1 contracts**
```
cd solidity → forge install → source anvil.env
→ forge script script/LocalTesting.s.sol:LocalSetup --broadcast
```
Deploys `StarknetMessagingLocal` and `ContractMsg` on the local Anvil chain. Outputs contract addresses to a JSON file.

**Step 3 — Start Katana (local L2 node)**
```
starkliup → dojoup -v 1.0.0-alpha.0
→ katana --messaging anvil.messaging.json
```
Starts the Starknet local node and links it to Anvil for message bridging. Waits 26 seconds for full setup.

**Step 4 — Deploy L2 contract**
```
cd cairo → source katana.env → scarb build
→ starkli declare ... → starkli deploy ...
```
Builds and deploys the Cairo contract on Katana.

**Step 5 — Send a message from L2 to L1**
```
starkli invoke <L2_contract> send_message_value <L1_contract_address> 1
```
Triggers the L2 → L1 message with value `1`.

**Step 6 — Consume the message on L1**
```
forge script script/ConsumeMessage.s.sol:Value --broadcast
```
Reads the message on the L1 side, verifying the full cross-chain round trip.

---

## Prerequisites

- [Foundry](https://book.getfoundry.sh/) (forge, anvil, cast)
- [Scarb](https://docs.swmansion.com/scarb/) (Cairo package manager)
- [Starkli](https://github.com/xJonathanLEI/starkli) (Starknet CLI)
- [Dojo / Katana](https://book.dojoengine.org/) (local Starknet node)
- Python 3
- `gnome-terminal` (the script opens new terminal windows)
- An Alchemy API key for the Ethereum mainnet fork

---

## Running the Test

```bash
cd Testing_L1L2_Com
python3 l1_testing.py
```

This will open several terminal windows automatically and run the full L2 → L1 messaging flow.

---

## Credits

- Smart contracts and Cairo/Solidity messaging examples forked from [Glihm](https://github.com/glihm/starknet-messaging-dev)
- Python orchestration script (`l1_testing.py`) by [petarcalic99](https://github.com/petarcalic99)
