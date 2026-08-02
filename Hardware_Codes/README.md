# Hardware Implementation - Raspberry Pi V2X System

## 🚗 Project Overview
Real-world V2X automotive communication system using 2 Raspberry Pi boards with CAN modules.

## 📁 Folder Structure
```
Hardware_Codes/
├── Vehicle_A/          # Primary vehicle (sender) code
├── Vehicle_B/          # Secondary vehicle (receiver) code  
├── Shared/             # Common libraries and protocols
├── Setup_Scripts/      # Installation and configuration scripts
└── README.md          # This file
```

## 🔧 Hardware Requirements
- 2x Raspberry Pi 4B (with Raspberry Pi OS installed)
- 2x MCP2515 CAN HAT modules
- CAN-H, CAN-L, GND wiring between boards
- 120Ω termination resistors

## 🚀 Quick Start

### 1. Setup Both RPi Boards:
```bash
# Run on both RPi boards
cd Hardware_Codes/Setup_Scripts
sudo bash rpi_setup.sh
```

### 2. Deploy Vehicle A Code:
```bash
# On RPi 1
cd Hardware_Codes/Vehicle_A
python3 vehicle_a_main.py
```

### 3. Deploy Vehicle B Code:
```bash
# On RPi 2  
cd Hardware_Codes/Vehicle_B
python3 vehicle_b_main.py
```

## 📡 V2X Features
- Real-time vehicle-to-vehicle communication
- Speed limit warnings (>80 km/h)
- Emergency brake alerts
- Collision avoidance system
- Traffic management protocols
- Safety monitoring and logging

## 🔗 CAN Message Protocol
- 0x100-0x1FF: Engine Control Messages
- 0x200-0x2FF: Brake System Messages
- 0x300-0x3FF: Safety System Messages
- 0x400-0x4FF: V2X Communication Messages
- 0x500-0x5FF: Emergency Messages

## 📊 Monitoring
- Real-time CAN message logging
- V2X alert dashboard
- System health monitoring
- Performance analytics