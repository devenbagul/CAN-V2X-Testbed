#!/bin/bash
# Complete Linux CAN Setup Script
# Run this on Ubuntu/Linux to set up original CAN interfaces

echo "🐧 Setting up Complete Linux CAN Environment"
echo "============================================"

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install CAN utilities
echo "🔧 Installing CAN utilities..."
sudo apt install -y can-utils python3-pip python3-venv git

# Install Python CAN library
echo "🐍 Installing Python CAN library..."
pip3 install python-can

# Setup virtual CAN interfaces (your original)
echo "🚗 Setting up virtual CAN interfaces..."
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0
sudo ip link add dev vcan1 type vcan  
sudo ip link set up vcan1

# Setup real CAN interfaces (if hardware exists)
echo "🔌 Attempting to setup real CAN interfaces..."
sudo ip link set can0 down 2>/dev/null || echo "can0 not available (no hardware)"
sudo ip link set can0 up type can bitrate 500000 2>/dev/null || echo "can0 setup skipped"
sudo ip link set can1 down 2>/dev/null || echo "can1 not available (no hardware)" 
sudo ip link set can1 up type can bitrate 500000 2>/dev/null || echo "can1 setup skipped"

# Make interfaces persistent
echo "💾 Making CAN interfaces persistent..."
sudo tee /etc/systemd/system/setup-vcan.service > /dev/null <<EOF
[Unit]
Description=Setup Virtual CAN interfaces
After=network.target

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'modprobe vcan && ip link add dev vcan0 type vcan && ip link set up vcan0 && ip link add dev vcan1 type vcan && ip link set up vcan1'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable setup-vcan.service
sudo systemctl start setup-vcan.service

# Test interfaces
echo "🧪 Testing CAN interfaces..."
echo "Available CAN interfaces:"
ip link show | grep can

echo ""
echo "✅ Linux CAN setup complete!"
echo ""
echo "🚀 Now you can test:"
echo "   cansend vcan0 123#DEADBEEF"
echo "   candump vcan0"
echo "   python3 main.py ui"
echo ""