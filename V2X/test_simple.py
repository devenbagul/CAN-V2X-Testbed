#!/usr/bin/env python3
"""
Simple test to verify CAN communication
"""

import can
import time
import threading

def sender():
    """Send test messages"""
    try:
        from shared_can import SharedCANBus
        bus = SharedCANBus('test')
        print("Sender connected")
        
        for i in range(10):
            # Send speed message
            speed = 50 + i * 5  # 50, 55, 60... km/h
            speed_data = (speed * 100).to_bytes(2, 'big') + b'\x00' * 6
            msg = can.Message(arbitration_id=0x0CF00503, data=speed_data)
            bus.send(msg)
            print(f"Sent speed: {speed} km/h")
            
            # Send RPM message
            rpm = 1000 + i * 200  # 1000, 1200, 1400... RPM
            rpm_data = rpm.to_bytes(2, 'big') + b'\x00' * 6
            msg = can.Message(arbitration_id=0x0CF00400, data=rpm_data)
            bus.send(msg)
            print(f"Sent RPM: {rpm}")
            
            time.sleep(1)
            
    except Exception as e:
        print(f"Sender error: {e}")

def receiver():
    """Receive test messages"""
    try:
        from shared_can import SharedCANBus
        bus = SharedCANBus('test')
        print("Receiver connected")
        
        while True:
            msg = bus.recv(timeout=1.0)
            if msg:
                if msg.arbitration_id == 0x0CF00503:  # Speed
                    speed = ((msg.data[0] << 8) | msg.data[1]) / 100
                    print(f"Received speed: {speed} km/h")
                elif msg.arbitration_id == 0x0CF00400:  # RPM
                    rpm = (msg.data[0] << 8) | msg.data[1]
                    print(f"Received RPM: {rpm}")
                    
    except Exception as e:
        print(f"Receiver error: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "send":
        sender()
    else:
        receiver()