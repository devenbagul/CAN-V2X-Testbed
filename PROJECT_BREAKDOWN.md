# Automotive CAN-LIN Gateway & V2X Safety System: Technical Breakdown

This document provides a detailed breakdown of the architecture, protocol formats, safety algorithms, and code components in the repository.

---

## 1. System-Level Architecture

The repository represents a hierarchical automotive network simulation and hardware configuration suite. It acts on three distinct networking layers:
- **LIN (Local Interconnect Network) Bus**: Simulated sensors for low-cost, low-speed body electronics (e.g., doors, windows, climate control, seats).
- **CAN (Controller Area Network) / J1939 Bus**: High-speed backbone connecting simulated ECUs (Engine, Brakes, Airbags, Steering).
- **V2X (Vehicle-to-Everything) Wireless Alerting**: Simulated V2V (Vehicle-to-Vehicle) safety messaging using broadcast packets to prevent collisions and alert surrounding traffic.

### Communication Data Flow
1. **LIN Status Messages** $\rightarrow$ Encapsulated into CAN frames (`0x700–0x73F`) by the Gateway $\rightarrow$ Received and decoded by the dashboard UI.
2. **J1939 PGN Queries** $\rightarrow$ Request signals broadcasted on the CAN bus $\rightarrow$ Gateway captures queries, retrieves values from simulated LIN nodes, and transmits response frames.
3. **Simulated ECU Telemetry** $\rightarrow$ Simulator fires messages $\rightarrow$ Safety System scans parameters (Speed, Temperature, Brake Pressure) and triggers automated warnings or overrides (e.g., active braking).
4. **Physical HIL Deployment** $\rightarrow$ Dual Raspberry Pis communicate via socketcan interfaces over MCP2515 CAN transceivers.

---

## 2. File-by-File Technical Analysis

### Core Main Workspace (Root Directory)

#### `reciever-code.py`
- **Role**: The main LIN-CAN gateway translation daemon.
- **Key Logic**:
  - Sets up standard and virtual CAN connections.
  - Intercepts CAN frames with IDs in the `0x700–0x73F` range and parses them as LIN frames (subtracting `0x700` to yield the original 6-bit LIN ID).
  - Listens for 29-bit extended CAN arbitration IDs, extracts the SAE J1939 Parameter Group Number (PGN), and searches for SPN definitions.
  - Responds to specific queries (e.g. Engine Temperature PGN 65108) by querying virtual LIN sensors and transmitting response payloads.

#### `sender-code.py`
- **Role**: Test harness to verify the gateway.
- **Key Logic**:
  - Connects to the shared virtual interface.
  - Iterates through a scenario list to broadcast PGN requests and test LIN-over-CAN packets.
  - Listens for responses and verifies that translation logic correctly formats and returns parameters.

#### `shared_bus.py`
- **Role**: Software-defined mock CAN bus.
- **Key Logic**:
  - Implements a thread-safe, Singleton `SharedVirtualBus`.
  - Employs a publisher-subscriber model with a daemon message dispatcher thread.
  - Allows full software loopback testing without socketcan or root permissions, ensuring portability across Windows, macOS, and Linux.

#### `updated-lin-can-gateway-ui.py`
- **Role**: Integrated J1939 monitoring & controller GUI.
- **Key Logic**:
  - Implements a multi-tab Tkinter interface.
  - **Gateway Tab**: Visualizes real-time CAN/LIN traffic, lists packet counters, and handles socketcan interface initialization.
  - **Sender Tab**: Provides controls to manually dispatch PGN requests or LIN status packets.
  - **Decoder Tab**: Parses database CSV entries to display decoded parameter lists (showing Suspect Parameter Numbers, descriptions, values, and units).

#### `setup_vcan.py`
- **Role**: Linux kernel network configuration script.
- **Key Logic**:
  - Loads the kernel virtual CAN driver (`sudo modprobe vcan`).
  - Creates virtual network links (`vcan0`, `vcan1`) and brings them up via IP link tools.

#### `complete_test_suite.py`
- **Role**: Automated cross-platform unit and integration test runner.
- **Key Logic**:
  - Detects operating system configurations.
  - Executes a sequence of import validation checks, CSV load checks, virtual CAN tests, and parser runs, printing a final success rate report.

---

### V2X Simulation & Safety Workspace (`V2X/`)

#### `shared_can.py`
- **Role**: Inter-Process Communication (IPC) mock CAN interface.
- **Key Logic**:
  - Uses a shared JSON database file (`can_messages_shared.json`) as a persistent virtual bus.
  - When `send()` is invoked, it appends a message dictionary to the file, enforcing a sliding buffer limit of 100 entries.
  - Uses file monitoring threads to poll and deliver frames to callback functions, enabling concurrent process simulations.

#### `v2x_safety.py`
- **Role**: Automated safety supervisor.
- **Key Logic**:
  - Continuously reads the IPC CAN bus.
  - Decodes vehicle speed, engine temp, brake pressure, airbag health, and V2X warning flags.
  - Monitors parameters against predefined safety thresholds and transmits command overrides to mitigate risks.

#### `v2x_simulator.py`
- **Role**: Vehicle sensor emulator.
- **Key Logic**:
  - Runs a background loop generating simulated ECU data (Engine, Brakes, Airbag, GPS coordinates, ESC status).
  - Transmits data frames to the virtual bus.

#### `v2x_ui.py`
- **Role**: Virtual vehicle diagnostic dashboard.
- **Key Logic**:
  - A Tkinter application rendering safety alerts, active CAN logs, and real-time visual dials for Speed, Engine RPM, Coolant Temp, and Airbag deployment status.

---

### Physical Hardware Workspace (`Hardware_Codes/`)

#### `Shared/can_protocol.py`
- **Role**: Unified message protocol catalog.
- **Key Logic**:
  - Maps standard message types to specific 11-bit standard CAN arbitration IDs.
  - Contains helper functions to pack and unpack integer values (such as velocity or temperature) into standard 8-byte bytearrays.

#### `Vehicle_A/vehicle_a_main.py`
- **Role**: Sender vehicle controller daemon.
- **Key Logic**:
  - Connects to the physical SPI-based `can0` interface on a Raspberry Pi.
  - Runs parallel simulation threads modeling engine heat, speed fluctuations, and brake pressure.
  - Periodically broadcasts vehicle status and broadcasts emergency V2X warning packets if safety conditions are violated.

#### `Vehicle_B/vehicle_b_main.py`
- **Role**: Receiver/Evasive safety controller daemon.
- **Key Logic**:
  - Listens to the CAN bus for telemetry broadcasted by Vehicle A.
  - Analyzes safety parameters (relative speed, simulated follow distance).
  - If a collision warning packet is received or the follow distance drops below limits, it automatically fires an override sequence (activating emergency braking and adjusting steering angles to simulate a lane-yield maneuver).

---

## 3. Protocol Definitions

### LIN-over-CAN Encapsulation Format
The gateway encapsulates 6-bit LIN frames into standard 11-bit CAN frames to leverage the high-speed backbone.

- **CAN Arbitration ID**: `0x700` + `LIN ID` (e.g. LIN ID `0x12` maps to CAN ID `0x712`).
- **Data Payload Layout (8 Bytes)**:
  - **Bytes 0–6**: LIN Frame Data (up to 7 bytes). If the LIN frame is shorter, bytes are padded with `0x00`.
  - **Byte 7**: Simple arithmetic checksum ($Checksum = \sum Data \pmod{256}$).

### J1939 Arbitration ID Structure
29-bit extended CAN arbitration IDs are partitioned into J1939 header fields:

$$\text{Arbitration ID (29 bits)} = \text{Priority (3 bits)} \mid \text{Data Page (1 bit)} \mid \text{PDU Format (8 bits)} \mid \text{PDU Specific (8 bits)} \mid \text{Source Address (8 bits)}$$

- **Parameter Group Number (PGN)**:
  - If **PDU Format** $< 240$: The message is destination-specific (PDU1 format). The PGN is defined by the PDU Format byte, with PDU Specific containing the Destination Address.
  - If **PDU Format** $\ge 240$: The message is a broadcast (PDU2 format). The PGN combines both PDU Format and PDU Specific bytes.

---

## 4. Safety Logic & Action Matrix

The safety systems (`v2x_safety.py` and `Vehicle_B/vehicle_b_main.py`) continuously evaluate inputs against safety thresholds to perform actions:

| Input Signal | Warning Threshold | Safety Action | Override Payload |
| :--- | :--- | :--- | :--- |
| **Vehicle Speed** | $> 80$ km/h | Triggers Speed Warning Alert; transmits Emergency Braking request. | `0x0CF00301`: `FF 64 00 00 00 00 00 00` (100% Brake Pressure) |
| **Engine Coolant Temp** | $> 110$ °C | Triggers Engine Overheat Alert; transmits Engine Protection command. | `0x0CF00403`: `0x01 00 00 00 00 00 00 00` (Power Derate Active) |
| **Brake Pressure** | $> 90$ % | Triggers Brake Overload Alert. | None |
| **Airbag Fault Status** | `data[0] != 0` | Triggers Critical Airbag System Fault Alert. | None |
| **V2X Proximity Distance** | $< 50$ meters | Triggers Collision Risk Alert; initiates evasive steering maneuvers. | None (Adjusts local vehicle steer variables to 15 degrees) |
