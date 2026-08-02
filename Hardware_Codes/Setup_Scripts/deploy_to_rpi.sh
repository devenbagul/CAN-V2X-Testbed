#!/bin/bash
# Deploy V2X code to Raspberry Pi boards
# Usage: ./deploy_to_rpi.sh <rpi_ip> <vehicle_type>
# Example: ./deploy_to_rpi.sh 192.168.1.100 A

if [ $# -ne 2 ]; then
    echo "Usage: $0 <rpi_ip> <vehicle_type>"
    echo "Example: $0 192.168.1.100 A"
    exit 1
fi

RPI_IP=$1
VEHICLE_TYPE=$2
RPI_USER="pi"
PROJECT_DIR="v2x_project"

echo "🚀 Deploying V2X code to Raspberry Pi..."
echo "Target: $RPI_IP (Vehicle $VEHICLE_TYPE)"

# Create project directory on RPi
echo "📁 Creating project directory..."
ssh $RPI_USER@$RPI_IP "mkdir -p ~/$PROJECT_DIR"

# Copy shared files
echo "📦 Copying shared files..."
scp -r ../Shared/* $RPI_USER@$RPI_IP:~/$PROJECT_DIR/

# Copy vehicle-specific files
if [ "$VEHICLE_TYPE" = "A" ]; then
    echo "🚗 Copying Vehicle A files..."
    scp -r ../Vehicle_A/* $RPI_USER@$RPI_IP:~/$PROJECT_DIR/
elif [ "$VEHICLE_TYPE" = "B" ]; then
    echo "🚗 Copying Vehicle B files..."
    scp -r ../Vehicle_B/* $RPI_USER@$RPI_IP:~/$PROJECT_DIR/
else
    echo "❌ Invalid vehicle type. Use 'A' or 'B'"
    exit 1
fi

# Copy setup scripts
echo "🔧 Copying setup scripts..."
scp *.sh *.py $RPI_USER@$RPI_IP:~/$PROJECT_DIR/

# Make scripts executable
echo "⚡ Making scripts executable..."
ssh $RPI_USER@$RPI_IP "chmod +x ~/$PROJECT_DIR/*.sh"
ssh $RPI_USER@$RPI_IP "chmod +x ~/$PROJECT_DIR/*.py"

# Install dependencies
echo "📦 Installing dependencies on RPi..."
ssh $RPI_USER@$RPI_IP "cd ~/$PROJECT_DIR && sudo bash install_dependencies.sh"

# Setup CAN interface
echo "🔌 Setting up CAN interface..."
ssh $RPI_USER@$RPI_IP "cd ~/$PROJECT_DIR && sudo bash rpi_setup.sh"

echo "✅ Deployment completed successfully!"
echo ""
echo "Next steps:"
echo "1. SSH to RPi: ssh $RPI_USER@$RPI_IP"
echo "2. Navigate to project: cd $PROJECT_DIR"
echo "3. Test CAN: python3 test_can_connection.py $VEHICLE_TYPE"
echo "4. Run vehicle: python3 vehicle_${VEHICLE_TYPE,,}_main.py"