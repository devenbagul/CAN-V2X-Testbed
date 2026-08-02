#!/usr/bin/env python3
"""
Virtual CAN Setup Script
------------------------
Sets up virtual CAN interfaces for testing on Windows/Linux
"""

import os
import sys
import subprocess
import platform

def setup_vcan_linux():
    """Setup virtual CAN interface on Linux"""
    commands = [
        "sudo modprobe vcan",
        "sudo ip link add dev vcan0 type vcan",
        "sudo ip link set up vcan0",
        "sudo ip link add dev vcan1 type vcan", 
        "sudo ip link set up vcan1"
    ]
    
    print("Setting up virtual CAN interfaces on Linux...")
    for cmd in commands:
        try:
            result = subprocess.run(cmd.split(), capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✓ {cmd}")
            else:
                print(f"✗ {cmd} - {result.stderr}")
        except Exception as e:
            print(f"✗ {cmd} - {e}")

def setup_vcan_windows():
    """Setup instructions for Windows"""
    print("Virtual CAN setup for Windows:")
    print("1. Install PCAN-View or similar CAN simulator")
    print("2. Or use python-can with 'virtual' interface")
    print("3. The UI will work with 'virtual' interface for testing")

def main():
    system = platform.system().lower()
    
    if system == "linux":
        setup_vcan_linux()
    elif system == "windows":
        setup_vcan_windows()
    else:
        print(f"Unsupported system: {system}")
        
    print("\nVirtual CAN setup complete!")
    print("You can now run the LIN-CAN Gateway UI")

if __name__ == "__main__":
    main()