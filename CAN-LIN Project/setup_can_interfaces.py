#!/usr/bin/env python3
"""
CAN Interface Setup Script
--------------------------
Sets up both original Linux interfaces and new virtual interfaces
"""

import os
import sys
import platform
import subprocess

def setup_linux_can():
    """Setup original Linux CAN interfaces"""
    print("Setting up Linux CAN interfaces...")
    
    commands = [
        # Virtual CAN interfaces (original)
        "sudo modprobe vcan",
        "sudo ip link add dev vcan0 type vcan",
        "sudo ip link set up vcan0",
        "sudo ip link add dev vcan1 type vcan", 
        "sudo ip link set up vcan1",
        
        # Real CAN interfaces (if hardware exists)
        "sudo ip link set can0 down 2>/dev/null || true",
        "sudo ip link set can0 up type can bitrate 500000 2>/dev/null || true",
        "sudo ip link set can1 down 2>/dev/null || true", 
        "sudo ip link set can1 up type can bitrate 500000 2>/dev/null || true",
    ]
    
    for cmd in commands:
        try:
            result = subprocess.run(cmd.split(), capture_output=True, text=True)
            if "vcan" in cmd or "modprobe" in cmd:
                print(f"✓ {cmd}")
            elif result.returncode == 0:
                print(f"✓ {cmd}")
        except Exception as e:
            if "vcan" in cmd:
                print(f"✗ {cmd} - {e}")

def test_interfaces():
    """Test all available interfaces"""
    print("\nTesting available CAN interfaces...")
    
    import can
    
    interfaces_to_test = [
        ('virtual', 'Python-can virtual (cross-platform)'),
        ('vcan0', 'Linux virtual CAN 0'),
        ('vcan1', 'Linux virtual CAN 1'),
        ('can0', 'Real CAN interface 0'),
        ('can1', 'Real CAN interface 1'),
    ]
    
    working_interfaces = []
    
    for interface, description in interfaces_to_test:
        try:
            if interface == 'virtual':
                bus = can.interface.Bus(interface='virtual')
            else:
                bus = can.interface.Bus(channel=interface, interface='socketcan')
            
            # Test sending a message
            msg = can.Message(arbitration_id=0x123, data=[1, 2, 3])
            bus.send(msg)
            bus.shutdown()
            
            print(f"✓ {interface}: {description}")
            working_interfaces.append(interface)
            
        except Exception as e:
            print(f"✗ {interface}: {description} - {e}")
    
    return working_interfaces

def show_usage_examples(working_interfaces):
    """Show how to use different interfaces"""
    print(f"\n{'='*50}")
    print("USAGE EXAMPLES")
    print(f"{'='*50}")
    
    print("\n1. GUI Application (auto-detects best interface):")
    print("   python main.py ui")
    
    print("\n2. Specify interface in GUI:")
    print("   - Select from dropdown in Gateway tab")
    for interface in working_interfaces:
        print(f"   - {interface}")
    
    print("\n3. Command line with specific interface:")
    for interface in working_interfaces:
        print(f"   python main_cont_1.py {interface}")
    
    print("\n4. Original Linux commands (if on Linux):")
    if platform.system().lower() == 'linux':
        print("   sudo ip link show | grep can")
        print("   cansend vcan0 123#DEADBEEF")
        print("   candump vcan0")

def main():
    """Main setup function"""
    system = platform.system().lower()
    
    print("CAN Interface Setup")
    print("=" * 30)
    print(f"Operating System: {system}")
    
    if system == 'linux':
        print("\n🐧 Linux detected - Setting up original + virtual interfaces")
        setup_linux_can()
    else:
        print(f"\n🪟 {system} detected - Virtual interfaces only")
        print("Note: Real CAN hardware requires Linux or special drivers")
    
    # Test all interfaces
    working_interfaces = test_interfaces()
    
    if working_interfaces:
        print(f"\n🎉 Found {len(working_interfaces)} working interface(s)!")
        show_usage_examples(working_interfaces)
    else:
        print("\n❌ No working interfaces found!")
        print("Try: pip install python-can")
    
    print(f"\n{'='*50}")
    print("Setup complete! You can now run:")
    print("python main.py ui")

if __name__ == "__main__":
    main()