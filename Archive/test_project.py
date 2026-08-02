#!/usr/bin/env python3
"""
Project Test Script
------------------
Tests all components of the LIN-CAN Gateway project
"""

import sys
import os
import time
import threading
import can

def test_imports():
    """Test if all required modules can be imported"""
    print("Testing imports...")
    
    try:
        import tkinter as tk
        print("✓ tkinter")
    except ImportError:
        print("✗ tkinter - GUI not available")
        
    try:
        import can
        print("✓ python-can")
    except ImportError:
        print("✗ python-can - Install with: pip install python-can")
        return False
        
    try:
        from ui_decode import CANDecoder, LINCANGateway, LINCANGatewayApp
        print("✓ UI components")
    except ImportError as e:
        print(f"✗ UI components - {e}")
        return False
        
    return True

def test_virtual_can():
    """Test virtual CAN interface"""
    print("\nTesting virtual CAN interface...")
    
    try:
        bus = can.interface.Bus(interface='virtual')
        print("✓ Virtual CAN interface created")
        
        # Test sending a message
        msg = can.Message(arbitration_id=0x123, data=[1, 2, 3, 4])
        bus.send(msg)
        print("✓ Message sent successfully")
        
        # Test receiving (with timeout)
        received = bus.recv(timeout=0.1)
        if received:
            print(f"✓ Message received: {received}")
        else:
            print("ℹ No message received (normal for virtual interface)")
            
        bus.shutdown()
        print("✓ Virtual CAN interface closed")
        return True
        
    except Exception as e:
        print(f"✗ Virtual CAN test failed: {e}")
        return False

def test_decoder():
    """Test CAN decoder functionality"""
    print("\nTesting CAN decoder...")
    
    try:
        from ui_decode import CANDecoder
        decoder = CANDecoder()
        print("✓ Decoder created")
        
        # Test J1939 field extraction
        test_id = 0x18FEF100  # Example J1939 ID
        fields = decoder.extract_j1939_fields(test_id)
        print(f"✓ J1939 fields extracted: PGN={fields['pgn']}")
        
        # Test frame decoding
        decoded = decoder.decode_frame(0x711, [0x11, 0x22, 0x33])  # LIN-over-CAN
        print(f"✓ Frame decoded: {decoded[0]['description']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Decoder test failed: {e}")
        return False

def test_gateway():
    """Test gateway functionality"""
    print("\nTesting LIN-CAN gateway...")
    
    try:
        from ui_decode import LINCANGateway
        gateway = LINCANGateway()
        print("✓ Gateway created")
        
        # Test connection to virtual interface
        if gateway.connect('virtual', interface_type='virtual'):
            print("✓ Gateway connected to virtual interface")
            
            # Test LIN message sending
            gateway.send_lin_as_can(0x12, [0x55, 0x66], "Test LIN message")
            print("✓ LIN message sent")
            
            gateway.cleanup()
            print("✓ Gateway cleaned up")
            return True
        else:
            print("✗ Gateway connection failed")
            return False
            
    except Exception as e:
        print(f"✗ Gateway test failed: {e}")
        return False

def test_csv_loading():
    """Test CSV file loading"""
    print("\nTesting CSV file loading...")
    
    try:
        from ui_decode import CANDecoder
        decoder = CANDecoder("sample_spn_data.csv")
        print("✓ Sample CSV loaded successfully")
        
        # Check if data was loaded
        if decoder.spn_data:
            pgn_count = len(decoder.spn_data)
            spn_count = sum(len(spns) for spns in decoder.spn_data.values())
            print(f"✓ Loaded {spn_count} SPNs from {pgn_count} PGNs")
        else:
            print("⚠ No SPN data loaded")
            
        return True
        
    except Exception as e:
        print(f"✗ CSV loading failed: {e}")
        return False

def test_ui_creation():
    """Test UI creation (without showing)"""
    print("\nTesting UI creation...")
    
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()  # Hide the window
        
        from ui_decode import LINCANGatewayApp
        app = LINCANGatewayApp(root)
        print("✓ UI application created")
        
        root.destroy()
        print("✓ UI cleaned up")
        return True
        
    except Exception as e:
        print(f"✗ UI creation failed: {e}")
        return False

def main():
    """Run all tests"""
    print("LIN-CAN Gateway Project Test Suite")
    print("=" * 40)
    
    tests = [
        ("Import Test", test_imports),
        ("Virtual CAN Test", test_virtual_can),
        ("Decoder Test", test_decoder),
        ("Gateway Test", test_gateway),
        ("CSV Loading Test", test_csv_loading),
        ("UI Creation Test", test_ui_creation),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * len(test_name))
        
        try:
            if test_func():
                passed += 1
                print(f"✓ {test_name} PASSED")
            else:
                print(f"✗ {test_name} FAILED")
        except Exception as e:
            print(f"✗ {test_name} ERROR: {e}")
    
    print(f"\n{'='*40}")
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Project is ready to use.")
        print("\nTo start the application:")
        print("python main.py ui")
    else:
        print("⚠ Some tests failed. Check the output above.")
        print("\nYou can still try running:")
        print("python main.py ui")

if __name__ == "__main__":
    main()