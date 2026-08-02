#!/usr/bin/env python3
"""
Virtual CAN Setup for V2X System
Sets up vcan0 interface for testing on Linux/Windows
"""

import subprocess
import sys
import platform

def setup_vcan():
    """Setup virtual CAN interface"""
    system = platform.system()
    
    if system == "Linux":
        try:
            # Load vcan module
            subprocess.run(["sudo", "modprobe", "vcan"], check=True)
            print("✓ Loaded vcan kernel module")
            
            # Create vcan0 interface
            subprocess.run(["sudo", "ip", "link", "add", "dev", "vcan0", "type", "vcan"], check=True)
            print("✓ Created vcan0 interface")
            
            # Bring interface up
            subprocess.run(["sudo", "ip", "link", "set", "up", "vcan0"], check=True)
            print("✓ Activated vcan0 interface")
            
            # Verify interface
            result = subprocess.run(["ip", "link", "show", "vcan0"], capture_output=True, text=True)
            if "UP" in result.stdout:
                print("✓ vcan0 is UP and ready")
                return True
            else:
                print("✗ vcan0 setup failed")
                return False
                
        except subprocess.CalledProcessError as e:
            print(f"✗ Error setting up vcan0: {e}")
            return False
    else:
        print(f"✓ Virtual CAN will be used on {system}")
        return True

if __name__ == "__main__":
    if setup_vcan():
        print("\n🚗 V2X CAN system ready!")
        print("Run: python main.py ui")
    else:
        print("\n❌ Setup failed. Check permissions.")
        sys.exit(1)