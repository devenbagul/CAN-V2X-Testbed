#!/usr/bin/env python3
"""
Test Shared Virtual CAN Bus
---------------------------
Tests that messages flow between sender and receiver via shared bus
"""

import time
import can
import threading
from shared_bus import SharedCANInterface

def test_shared_bus():
    """Test shared bus message passing"""
    print("Testing shared virtual CAN bus...")
    
    received_messages = []
    
    def message_handler(msg):
        received_messages.append(msg)
        print(f"Received: ID=0x{msg.arbitration_id:X}, Data={list(msg.data)}")
    
    # Create sender and receiver
    sender = SharedCANInterface()
    receiver = SharedCANInterface()
    
    # Set up receiver callback
    receiver.set_callback(message_handler)
    
    # Send test messages
    test_messages = [
        can.Message(arbitration_id=0x711, data=[0x11, 0x22, 0x33]),  # LIN message
        can.Message(arbitration_id=0x18FEF100, data=[0x55, 0x66, 0x77, 0x88]),  # J1939 message
    ]
    
    print("Sending test messages...")
    for msg in test_messages:
        sender.send(msg)
        time.sleep(0.1)
    
    # Wait for messages to be processed
    time.sleep(0.5)
    
    print(f"Sent {len(test_messages)} messages, received {len(received_messages)} messages")
    
    # Cleanup
    sender.shutdown()
    receiver.shutdown()
    
    return len(received_messages) == len(test_messages)

if __name__ == "__main__":
    if test_shared_bus():
        print("✓ Shared bus test PASSED")
        print("\nNow you can:")
        print("1. Run: python main.py ui")
        print("2. Connect to 'virtual' interface")
        print("3. Start gateway")
        print("4. In another terminal: python main.py sender")
        print("5. Watch messages appear in UI!")
    else:
        print("✗ Shared bus test FAILED")