#!/usr/bin/env python3
"""
Quick Test - Verify Basic Functionality
"""

def test_imports():
    """Test basic imports"""
    try:
        import can
        print("✓ python-can imported")
        
        import tkinter as tk
        print("✓ tkinter imported")
        
        from ui_decode import CANDecoder, LINCANGateway
        print("✓ UI components imported")
        
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

def test_virtual_can():
    """Test virtual CAN"""
    try:
        import can
        bus = can.Bus(interface='virtual')
        
        # Send test message
        msg = can.Message(arbitration_id=0x123, data=[1, 2, 3])
        bus.send(msg)
        
        bus.shutdown()
        print("✓ Virtual CAN works")
        return True
    except Exception as e:
        print(f"✗ Virtual CAN failed: {e}")
        return False

def test_decoder():
    """Test decoder"""
    try:
        from ui_decode import CANDecoder
        decoder = CANDecoder()
        
        # Test decode
        result = decoder.decode_frame(0x711, [0x11, 0x22, 0x33])
        if result and 'description' in result[0]:
            print("✓ Decoder works")
            return True
        else:
            print("✗ Decoder failed")
            return False
    except Exception as e:
        print(f"✗ Decoder failed: {e}")
        return False

def test_csv_loading():
    """Test CSV loading"""
    try:
        from ui_decode import CANDecoder
        decoder = CANDecoder("sample_spn_data.csv")
        
        if decoder.spn_data:
            print("✓ CSV loading works")
            return True
        else:
            print("✗ CSV loading failed - no data")
            return False
    except Exception as e:
        print(f"✗ CSV loading failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Quick Test Suite")
    print("=" * 30)
    
    tests = [
        ("Imports", test_imports),
        ("Virtual CAN", test_virtual_can),
        ("Decoder", test_decoder),
        ("CSV Loading", test_csv_loading),
    ]
    
    passed = 0
    for name, test_func in tests:
        print(f"\n{name}:")
        if test_func():
            passed += 1
    
    print(f"\n📊 Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 All basic tests passed!")
    else:
        print("⚠️ Some tests failed - check dependencies")