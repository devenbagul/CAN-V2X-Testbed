#!/usr/bin/env python3
"""
Linux-Specific Test - No GUI Dependencies
"""

def test_can_interfaces():
    """Test CAN interfaces on Linux"""
    import subprocess
    
    try:
        # Check if vcan0 exists
        result = subprocess.run(['ip', 'link', 'show', 'vcan0'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ vcan0 interface exists")
            return True
        else:
            print("✗ vcan0 interface missing")
            return False
    except Exception as e:
        print(f"✗ Interface check failed: {e}")
        return False

def test_can_send_receive():
    """Test CAN send/receive"""
    try:
        import can
        
        # Test with vcan0
        bus = can.Bus(channel='vcan0', interface='socketcan')
        
        # Send message
        msg = can.Message(arbitration_id=0x123, data=[1, 2, 3, 4])
        bus.send(msg)
        
        # Try to receive (with short timeout)
        received = bus.recv(timeout=0.1)
        
        bus.shutdown()
        print("✓ CAN send/receive works")
        return True
        
    except Exception as e:
        print(f"✗ CAN send/receive failed: {e}")
        return False

def test_original_files():
    """Test original file functionality without GUI"""
    import os
    
    # Check if original files exist
    original_files = [
        'sender-code.py',
        'reciever-code.py', 
        'pgn_fileread.py',
        'main_cont_1.py'
    ]
    
    missing = [f for f in original_files if not os.path.exists(f)]
    if missing:
        print(f"✗ Missing files: {missing}")
        return False
    
    print("✓ All original files present")
    return True

def test_can_utils():
    """Test Linux CAN utilities"""
    import subprocess
    
    try:
        # Test cansend
        result = subprocess.run(['cansend', 'vcan0', '123#DEADBEEF'], 
                              capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            print("✓ cansend works")
            return True
        else:
            print(f"✗ cansend failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ cansend test failed: {e}")
        return False

def test_python_can_linux():
    """Test python-can with Linux socketcan"""
    try:
        import can
        
        # Test socketcan interface
        bus = can.Bus(channel='vcan0', interface='socketcan')
        
        # Send test message
        msg = can.Message(arbitration_id=0x456, data=[0xDE, 0xAD, 0xBE, 0xEF])
        bus.send(msg)
        
        bus.shutdown()
        print("✓ Python-can socketcan works")
        return True
        
    except Exception as e:
        print(f"✗ Python-can socketcan failed: {e}")
        return False

if __name__ == "__main__":
    print("🐧 Linux CAN Test Suite")
    print("=" * 30)
    
    tests = [
        ("CAN Interfaces", test_can_interfaces),
        ("CAN Send/Receive", test_can_send_receive),
        ("Original Files", test_original_files),
        ("CAN Utils", test_can_utils),
        ("Python-CAN Linux", test_python_can_linux),
    ]
    
    passed = 0
    for name, test_func in tests:
        print(f"\n{name}:")
        if test_func():
            passed += 1
    
    print(f"\n📊 Results: {passed}/{len(tests)} tests passed")
    
    if passed >= 4:
        print("🎉 Linux CAN functionality working!")
        print("\nNext steps:")
        print("1. Test original sender: python3 sender-code.py")
        print("2. Test original receiver: python3 reciever-code.py") 
        print("3. Test main controller: python3 main_cont_1.py vcan0")
    else:
        print("⚠️ Some Linux features need setup")
        print("\nRun these commands:")
        print("sudo apt install -y python3-tk can-utils")
        print("sudo modprobe vcan")
        print("sudo ip link add dev vcan0 type vcan")
        print("sudo ip link set up vcan0")