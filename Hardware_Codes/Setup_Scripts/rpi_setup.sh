#!/bin/bash
# Raspberry Pi V2X System Setup Script
# Run this on both RPi boards

echo "🚗 Setting up Raspberry Pi for V2X CAN System..."

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install required packages
echo "🔧 Installing CAN utilities and Python packages..."
sudo apt install -y can-utils python3-pip git nano htop

# Install Python dependencies
echo "🐍 Installing Python CAN libraries..."
pip3 install python-can cantools RPi.GPIO

# Enable SPI interface
echo "⚡ Enabling SPI interface..."
sudo raspi-config nonint do_spi 0

# Configure CAN overlay in boot config
echo "🔌 Configuring CAN overlay..."
if ! grep -q "dtoverlay=mcp2515-can0" /boot/config.txt; then
    echo "dtparam=spi=on" | sudo tee -a /boot/config.txt
    echo "dtoverlay=mcp2515-can0,oscillator=16000000,interrupt=25" | sudo tee -a /boot/config.txt
    echo "dtoverlay=spi-bcm2835-overlay" | sudo tee -a /boot/config.txt
fi

# Create CAN network configuration
echo "🌐 Setting up CAN network configuration..."
sudo tee /etc/systemd/network/80-can.network > /dev/null <<EOF
[Match]
Name=can0

[CAN]
BitRate=500000
RestartSec=100ms
EOF

# Create CAN interface startup script
echo "🚀 Creating CAN startup script..."
sudo tee /usr/local/bin/setup-can.sh > /dev/null <<'EOF'
#!/bin/bash
# Setup CAN interface
sudo ip link set can0 down 2>/dev/null
sudo ip link set can0 up type can bitrate 500000
echo "CAN interface can0 is ready"
EOF

sudo chmod +x /usr/local/bin/setup-can.sh

# Create systemd service for CAN
echo "⚙️ Creating CAN systemd service..."
sudo tee /etc/systemd/system/can-setup.service > /dev/null <<EOF
[Unit]
Description=Setup CAN Interface
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/setup-can.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

# Enable CAN service
sudo systemctl enable can-setup.service

# Create V2X project directory
echo "📁 Creating V2X project directory..."
mkdir -p ~/v2x_project
cd ~/v2x_project

echo "✅ Setup complete! Please reboot the Raspberry Pi."
echo "After reboot, run: sudo systemctl start can-setup.service"
echo "Test CAN with: candump can0"