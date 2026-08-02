# 🚗 V2X Hardware Deployment Guide

## 📋 Prerequisites
- 2x Raspberry Pi 4B with Raspberry Pi OS installed
- 2x MCP2515 CAN HAT modules properly connected
- CAN-H, CAN-L, GND wired between boards
- 120Ω termination resistors on CAN bus
- SSH access to both Raspberry Pi boards

## 🔧 Hardware Setup

### 1. Physical Connections
```
RPi 1 (Vehicle A) ←→ RPi 2 (Vehicle B)
CAN-H ←→ CAN-H
CAN-L ←→ CAN-L  
GND ←→ GND
```

### 2. CAN HAT Installation
- Mount MCP2515 CAN HAT on both Raspberry Pi boards
- Ensure proper GPIO connections
- Add 120Ω termination resistors at both ends of CAN bus

## 🚀 Software Deployment

### Step 1: Prepare Raspberry Pi Boards

**On both RPi boards:**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Enable SSH (if not already enabled)
sudo systemctl enable ssh
sudo systemctl start ssh
```

### Step 2: Deploy Code to Raspberry Pi Boards

**From your development machine:**

```bash
# Navigate to Hardware_Codes directory
cd "CAN-LIN Project/Hardware_Codes/Setup_Scripts"

# Deploy to Vehicle A (replace with actual IP)
./deploy_to_rpi.sh 192.168.1.100 A

# Deploy to Vehicle B (replace with actual IP)  
./deploy_to_rpi.sh 192.168.1.101 B
```

### Step 3: Setup CAN Interface on Both Boards

**SSH to each RPi and run:**
```bash
ssh pi@192.168.1.100  # Vehicle A
cd v2x_project
sudo bash rpi_setup.sh
sudo reboot
```

```bash
ssh pi@192.168.1.101  # Vehicle B
cd v2x_project  
sudo bash rpi_setup.sh
sudo reboot
```

### Step 4: Test CAN Communication

**After reboot, test on both boards:**

**Vehicle A (RPi 1):**
```bash
ssh pi@192.168.1.100
cd v2x_project
python3 test_can_connection.py A
```

**Vehicle B (RPi 2):**
```bash
ssh pi@192.168.1.101
cd v2x_project
python3 test_can_connection.py B
```

You should see messages being exchanged between the boards.

### Step 5: Run V2X System

**Vehicle A (Primary):**
```bash
ssh pi@192.168.1.100
cd v2x_project
python3 vehicle_a_main.py
```

**Vehicle B (Secondary):**
```bash
ssh pi@192.168.1.101
cd v2x_project
python3 vehicle_b_main.py
```

## 📊 Expected Results

### Successful Communication
- Both vehicles should detect each other
- Speed warnings when >80 km/h
- Emergency brake alerts
- Collision warnings
- V2X message exchanges

### Console Output Example
```
🚗 Vehicle A - V2X Primary Controller
=====================================
🚀 Starting Vehicle A V2X System...
✅ CAN interface can0 configured successfully
✅ Connected to CAN bus on can0
✅ Vehicle A system started successfully

📊 Vehicle A Status:
Speed: 65.3 km/h
Engine RPM: 3086
Engine Temp: 89°C
Brake Pressure: 0%
Emergency Mode: False
Pending Alerts: 0
```

## 🔍 Troubleshooting

### CAN Interface Issues
```bash
# Check if CAN interface exists
ip link show can0

# Manually setup CAN interface
sudo ip link set can0 down
sudo ip link set can0 up type can bitrate 500000

# Test with can-utils
candump can0        # In one terminal
cansend can0 123#DEADBEEF  # In another terminal
```

### Hardware Issues
- Check CAN HAT connections
- Verify 120Ω termination resistors
- Ensure CAN-H and CAN-L are not swapped
- Check power supply (5V, adequate current)

### Software Issues
```bash
# Check Python dependencies
pip3 list | grep can

# Check system logs
sudo journalctl -f

# Check CAN interface stats
cat /proc/net/can/stats
```

## 📈 Monitoring and Logging

### Real-time Monitoring
```bash
# Monitor CAN traffic
candump can0

# Monitor system resources
htop

# View application logs
tail -f vehicle_a.log
tail -f vehicle_b.log
```

### Performance Metrics
- CAN message rate: ~10-20 messages/second per vehicle
- Latency: <10ms for safety-critical messages
- CPU usage: <20% on Raspberry Pi 4B
- Memory usage: <100MB per vehicle application

## 🎯 Testing Scenarios

### 1. Basic Communication Test
- Start both vehicles
- Verify message exchange in logs
- Check CAN statistics

### 2. Speed Warning Test
- Increase Vehicle A speed >80 km/h
- Verify Vehicle B receives speed warning
- Check alert generation

### 3. Emergency Brake Test
- Trigger emergency brake on Vehicle A
- Verify Vehicle B receives alert and responds
- Check emergency response timing

### 4. Collision Avoidance Test
- Simulate collision scenario
- Verify both vehicles exchange warnings
- Check evasive action responses

## 🔧 Advanced Configuration

### Custom CAN Bitrates
```bash
# Change bitrate (both boards must match)
sudo ip link set can0 down
sudo ip link set can0 up type can bitrate 1000000  # 1Mbps
```

### Automatic Startup
```bash
# Create systemd service for auto-start
sudo nano /etc/systemd/system/v2x-vehicle-a.service

[Unit]
Description=V2X Vehicle A Controller
After=can-setup.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/v2x_project
ExecStart=/usr/bin/python3 vehicle_a_main.py
Restart=always

[Install]
WantedBy=multi-user.target

# Enable service
sudo systemctl enable v2x-vehicle-a.service
sudo systemctl start v2x-vehicle-a.service
```

## 📞 Support

If you encounter issues:
1. Check hardware connections
2. Verify CAN interface setup
3. Review application logs
4. Test with can-utils first
5. Check network connectivity between RPi boards