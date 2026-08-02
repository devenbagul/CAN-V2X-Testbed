#!/bin/bash
# Install all required dependencies for V2X system

echo "🔧 Installing V2X System Dependencies..."

# Update package list
sudo apt update

# Install system packages
echo "📦 Installing system packages..."
sudo apt install -y \
    can-utils \
    python3-pip \
    python3-dev \
    git \
    nano \
    htop \
    screen \
    build-essential \
    cmake

# Install Python packages
echo "🐍 Installing Python packages..."
pip3 install --upgrade pip
pip3 install \
    python-can \
    cantools \
    RPi.GPIO \
    numpy \
    matplotlib \
    flask \
    requests

echo "✅ Dependencies installed successfully!"