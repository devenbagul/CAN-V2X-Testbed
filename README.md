# Automotive CAN-LIN Gateway & V2X Safety System

An advanced, end-to-end automotive networking and safety application designed for virtual simulation and physical hardware deployment. The project implements a bidirectional **LIN-to-CAN Gateway**, **SAE J1939 (SPN/PGN) Parameter Decoder**, **V2X Safety Alerting Systems**, and **Hardware-in-the-Loop (HIL)** configuration scripts for Raspberry Pi nodes with MCP2515 CAN transceivers.

---

## 🚗 Main Features

- **LIN-to-CAN Gateway**: Real-time translation between LIN and CAN protocols. Capsules 6-bit LIN IDs (0–63) into a reserved CAN identifier space (`0x700–0x73F`) with automatic data padding and checksum generation.
- **SAE J1939 Decoder**: Parse 29-bit extended CAN arbitration IDs into Priority, Parameter Group Number (PGN), and Source/Destination addresses. Leverages a modular SPN database (`sample_spn_data.csv`) to decode bit-packed parameters using customizable resolution, offsets, and range checks.
- **V2X Safety System**: Simulates vehicle Electronic Control Units (ECUs) on a virtual CAN network. Triggers real-time alerts for speed limits, engine overheating, and brake line pressures, including active safety overrides (e.g., sending emergency braking packets).
- **Cross-Platform Mocking**: Includes an in-memory Pub/Sub mock bus and JSON file-based Inter-Process Communication (IPC) mock CAN interfaces. Enables seamless development and testing on Windows, macOS, and Linux without hardware.
- **Hardware-in-the-Loop Deployment**: Turnkey setup files, boot-up initialization scripts, and dedicated controller nodes for a dual-Raspberry Pi sender/receiver physical CAN network.

---

## 📁 Repository Structure

```
.
├── PROJECT_BREAKDOWN.md          # Comprehensive module & file-by-file guide
├── README.md                     # Root project documentation (this file)
├── .gitignore                    # Git ignore file (excludes Archive, Venv, etc.)
├── .gitattributes                # Enforces line endings configuration
│
├── V2X/                          # V2X simulation and safety dashboard
│   ├── shared_can.py             # File-based simulated CAN IPC interface
│   ├── v2x_safety.py             # Safety thresholds and override rules
│   ├── v2x_simulator.py          # Virtual vehicle ECU generator
│   ├── v2x_ui.py                 # Instrument cluster dashboard GUI
│   └── main.py                   # V2X entry point
│
├── Hardware_Codes/               # Raspberry Pi deployment codes
│   ├── Setup_Scripts/            # System configuration & loopback test scripts
│   ├── Shared/                   # Common CAN protocol & frame builders
│   ├── Vehicle_A/                # Sender controller & dashboard
│   └── Vehicle_B/                # Evasive action receiver & dashboard
│
├── shared_bus.py                 # In-memory pub/sub mock CAN bus
├── ui_decode.py                  # Main Tkinter J1939 decoder & monitor
├── updated-lin-can-gateway-ui.py # Integrated gateway control & log GUI
├── reciever-code.py              # Gateway translation & J1939 responder
├── sender-code.py                # CAN/LIN gateway test engine
├── pgn_fileread.py               # File-based PGN request sequence runner
├── setup_vcan.py                 # Linux virtual CAN interface setup utility
├── complete_test_suite.py        # Cross-platform automated test runner
└── requirements.txt              # Python packages list
```

---

## 🔧 Prerequisites & Setup

### 1. Installation
Install the necessary Python packages using pip:
```bash
pip install -r requirements.txt
```

### 2. Configure Virtual CAN Interfaces (Linux)
On Linux systems, you can instantiate a local kernel-based virtual CAN interface:
```bash
# Setup vcan0 and vcan1
python setup_vcan.py
```

---

## 🚀 Running the System

The project is structured with modular entry points. Here are the primary ways to run the systems:

### Option A: J1939 Decoder & Gateway GUI (Main Workspace)
Start the main gateway and decoding dashboard:
```bash
# Start the unified, updated UI
python main.py ui

# To run J1939/LIN tests in a terminal (Sender & Receiver)
python main.py receiver
python main.py sender
```

### Option B: V2X Safety Simulator & Instrument Dashboard
Launch the standalone V2X safety monitor and simulation tool:
```bash
# Start V2X Simulation GUI
python V2X/main.py ui

# Start V2X Safety Monitor terminal process
python V2X/main.py safety

# Start Simulated vehicle ECU broadcaster
python V2X/main.py simulator
```

### Option C: Physical Raspberry Pi Deployment
Consult the [Hardware Deployment Guide](Hardware_Codes/DEPLOYMENT_GUIDE.md) and run scripts directly on Pi nodes:
```bash
# Node A (Primary Sender)
python Hardware_Codes/Vehicle_A/vehicle_a_main.py

# Node B (Receiver & Collision Prevention Node)
python Hardware_Codes/Vehicle_B/vehicle_b_main.py
```

---

## 🧪 Testing

The repository includes a comprehensive, platform-aware validation script that checks all core components (cross-platform modules, CSV parsers, shared interfaces, and communication nodes):

```bash
python complete_test_suite.py
```

---

## 📝 Documentation
For a complete architecture, protocol, and code breakdown, please review the [PROJECT_BREAKDOWN.md](PROJECT_BREAKDOWN.md) file.
