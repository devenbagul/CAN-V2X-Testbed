#!/usr/bin/env python3
"""
Test CAN Connection Between Two Raspberry Pi Boards
Run this script on both boards to verify communication
"""

import sys
import os
import time
import threading
import can
from datetime import datetime

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Shared'))

try:
    from rpi_can_interface import RPiCANInterface
    from can_protocol import CANMessageIDs
except ImportError:
    print("❌ Error: Cannot import shared modules. Make sure you're in the correct directory.")
    sys.exit(1)

class CANTester:
    def __init__(self, board_id):
        self.board_id = board_id  # 'A' or 'B'
        self.can_interface = RPiCANInterface('can0')
        self.running = False
        self.messages_sent = 0
        self.messages_received = 0
        self.test_results = []
        
    def start_test(self):
        """Start the CAN communication test"""
        print(f"🧪 Starting CAN test for Board {self.board_id}")
        
        # Connect to CAN
        if not self.can_interface.connect():
            print("❌ Failed to connect to CAN interface")
            return False
        
        self.running = True
        
        # Start message receiver
        self.can_interface.start_monitoring(self.handle_message)
        
        # Start sender thread
        threading.Thread(target=self.sender_loop, daemon=True).start()
        
        return True
    
    def stop_test(self):
        """Stop the test"""
        self.running = False
        self.can_interface.disconnect()
    
    def handle_message(self, msg):
        """Handle received CAN messages"""
        self.messages_received += 1
        
        # Check if it's a test message
        if msg.arbitration_id == 0x123:
            sender_board = chr(msg.data[0]) if len(msg.data) > 0 else '?'
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            
            if sender_board != self.board_id:
                result = f"✅ [{timestamp}] Received test message from Board {sender_board}"
                print(result)
                self.test_results.append(result)
                
                # Send acknowledgment
                self.send_ack_message(sender_board)
        
        elif msg.arbitration_id == 0x124:  # Acknowledgment message
            sender_board = chr(msg.data[0]) if len(msg.data) > 0 else '?'
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            
            if sender_board != self.board_id:
                result = f"📨 [{timestamp}] Received ACK from Board {sender_board}"
                print(result)
                self.test_results.append(result)
    
    def sender_loop(self):
        """Send test messages periodically"""
        while self.running:
            try:
                # Send test message
                test_data = [ord(self.board_id), self.messages_sent & 0xFF, 0x00, 0x00]
                
                if self.can_interface.send_message(0x123, test_data):
                    self.messages_sent += 1
                    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    print(f"📡 [{timestamp}] Sent test message #{self.messages_sent}")
                
                time.sleep(2)  # Send every 2 seconds
                
            except Exception as e:
                print(f"❌ Sender error: {e}")
                time.sleep(1)
    
    def send_ack_message(self, to_board):
        """Send acknowledgment message"""
        ack_data = [ord(self.board_id), 0xAC, 0xK0, ord(to_board)]
        self.can_interface.send_message(0x124, ack_data)
    
    def print_statistics(self):
        """Print test statistics"""
        print(f"\n📊 Test Statistics for Board {self.board_id}:")
        print(f"Messages Sent: {self.messages_sent}")
        print(f"Messages Received: {self.messages_received}")
        print(f"Test Results: {len(self.test_results)} successful exchanges")
        
        if self.test_results:
            print("\nRecent Results:")
            for result in self.test_results[-5:]:  # Show last 5 results
                print(f"  {result}")

def test_can_interface():
    """Test basic CAN interface functionality"""
    print("🔧 Testing CAN Interface Setup...")
    
    # Test if CAN interface exists
    result = os.system("ip link show can0 > /dev/null 2>&1")
    if result != 0:
        print("❌ CAN interface 'can0' not found")
        print("💡 Run: sudo ip link set can0 up type can bitrate 500000")
        return False
    
    # Test CAN utilities
    print("✅ CAN interface found")
    
    # Test python-can
    try:
        import can
        print("✅ python-can library available")
    except ImportError:
        print("❌ python-can not installed")
        print("💡 Run: pip3 install python-can")
        return False
    
    return True

def main():
    """Main test function"""
    print("🚗 V2X CAN Communication Test")
    print("=============================")
    
    # Get board ID
    if len(sys.argv) > 1:
        board_id = sys.argv[1].upper()
    else:
        board_id = input("Enter board ID (A or B): ").upper()
    
    if board_id not in ['A', 'B']:
        print("❌ Invalid board ID. Use 'A' or 'B'")
        return
    
    # Test CAN interface
    if not test_can_interface():
        print("❌ CAN interface test failed")
        return
    
    # Start communication test
    tester = CANTester(board_id)
    
    try:
        if tester.start_test():
            print(f"\n🎮 Board {board_id} test running. Press Ctrl+C to stop.")
            print("📊 Statistics will be shown every 10 seconds...\n")
            
            while True:
                time.sleep(10)
                tester.print_statistics()
                
    except KeyboardInterrupt:
        print(f"\n🛑 Stopping Board {board_id} test...")
    except Exception as e:
        print(f"❌ Test error: {e}")
    finally:
        tester.stop_test()
        print("✅ Test completed")

if __name__ == "__main__":
    main()