#!/usr/bin/env python3
"""
Raspberry Pi CAN Interface
Hardware-specific CAN communication for RPi with MCP2515
"""

import can
import time
import threading
import logging
import os
from datetime import datetime

class RPiCANInterface:
    """Raspberry Pi CAN interface using socketcan"""
    
    def __init__(self, interface='can0', bitrate=500000):
        self.interface = interface
        self.bitrate = bitrate
        self.bus = None
        self.running = False
        self.message_callback = None
        self.monitor_thread = None
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def setup_interface(self):
        """Setup CAN interface on Raspberry Pi"""
        try:
            # Bring down interface first
            os.system(f"sudo ip link set {self.interface} down 2>/dev/null")
            
            # Configure and bring up interface
            cmd = f"sudo ip link set {self.interface} up type can bitrate {self.bitrate}"
            result = os.system(cmd)
            
            if result == 0:
                self.logger.info(f"CAN interface {self.interface} configured successfully")
                return True
            else:
                self.logger.error(f"Failed to configure CAN interface {self.interface}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error setting up CAN interface: {e}")
            return False
    
    def connect(self):
        """Connect to CAN bus"""
        try:
            # Setup interface first
            if not self.setup_interface():
                return False
            
            # Create CAN bus connection
            self.bus = can.interface.Bus(channel=self.interface, interface='socketcan')
            self.logger.info(f"Connected to CAN bus on {self.interface}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to CAN bus: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from CAN bus"""
        try:
            self.stop_monitoring()
            
            if self.bus:
                self.bus.shutdown()
                self.bus = None
            
            # Bring down interface
            os.system(f"sudo ip link set {self.interface} down 2>/dev/null")
            self.logger.info("Disconnected from CAN bus")
            
        except Exception as e:
            self.logger.error(f"Error disconnecting from CAN bus: {e}")
    
    def send_message(self, arbitration_id, data):
        """Send CAN message"""
        if not self.bus:
            self.logger.error("CAN bus not connected")
            return False
        
        try:
            # Ensure data is bytes
            if isinstance(data, list):
                data = bytes(data)
            elif isinstance(data, str):
                data = bytes.fromhex(data)
            
            # Create and send message
            msg = can.Message(arbitration_id=arbitration_id, data=data)
            self.bus.send(msg)
            
            self.logger.debug(f"Sent: ID=0x{arbitration_id:03X}, Data={data.hex().upper()}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            return False
    
    def receive_message(self, timeout=1.0):
        """Receive single CAN message"""
        if not self.bus:
            return None
        
        try:
            msg = self.bus.recv(timeout=timeout)
            if msg:
                self.logger.debug(f"Received: ID=0x{msg.arbitration_id:03X}, Data={msg.data.hex().upper()}")
            return msg
            
        except Exception as e:
            self.logger.error(f"Error receiving message: {e}")
            return None
    
    def start_monitoring(self, callback=None):
        """Start continuous message monitoring"""
        if not self.bus:
            self.logger.error("CAN bus not connected")
            return False
        
        self.message_callback = callback
        self.running = True
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        self.logger.info("Started CAN message monitoring")
        return True
    
    def stop_monitoring(self):
        """Stop message monitoring"""
        self.running = False
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)
        
        self.logger.info("Stopped CAN message monitoring")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                msg = self.bus.recv(timeout=0.1)
                if msg and self.message_callback:
                    self.message_callback(msg)
                    
            except Exception as e:
                if self.running:  # Only log if we're supposed to be running
                    self.logger.error(f"Error in monitor loop: {e}")
                time.sleep(0.1)
    
    def get_interface_stats(self):
        """Get CAN interface statistics"""
        try:
            # Read interface statistics
            with open(f"/sys/class/net/{self.interface}/statistics/rx_packets", 'r') as f:
                rx_packets = int(f.read().strip())
            
            with open(f"/sys/class/net/{self.interface}/statistics/tx_packets", 'r') as f:
                tx_packets = int(f.read().strip())
            
            with open(f"/sys/class/net/{self.interface}/statistics/rx_errors", 'r') as f:
                rx_errors = int(f.read().strip())
            
            with open(f"/sys/class/net/{self.interface}/statistics/tx_errors", 'r') as f:
                tx_errors = int(f.read().strip())
            
            return {
                'rx_packets': rx_packets,
                'tx_packets': tx_packets,
                'rx_errors': rx_errors,
                'tx_errors': tx_errors,
                'interface': self.interface,
                'bitrate': self.bitrate
            }
            
        except Exception as e:
            self.logger.error(f"Error reading interface stats: {e}")
            return None
    
    def is_connected(self):
        """Check if CAN interface is connected and active"""
        try:
            # Check if interface exists and is up
            result = os.system(f"ip link show {self.interface} | grep -q UP")
            return result == 0 and self.bus is not None
            
        except Exception:
            return False

class CANLogger:
    """CAN message logger for debugging and analysis"""
    
    def __init__(self, log_file="can_messages.log"):
        self.log_file = log_file
        self.logger = logging.getLogger("CANLogger")
        
        # Setup file handler
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def log_message(self, msg, direction="RX"):
        """Log CAN message with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_entry = f"{direction} - ID:0x{msg.arbitration_id:03X} Data:{msg.data.hex().upper()} DLC:{len(msg.data)}"
        self.logger.info(log_entry)
    
    def log_event(self, event_type, description):
        """Log system events"""
        self.logger.info(f"EVENT - {event_type}: {description}")

# Test functions
def test_can_interface():
    """Test CAN interface functionality"""
    print("🧪 Testing Raspberry Pi CAN Interface...")
    
    can_interface = RPiCANInterface()
    
    # Test connection
    if can_interface.connect():
        print("✅ CAN interface connected successfully")
        
        # Test sending a message
        test_data = [0x01, 0x02, 0x03, 0x04]
        if can_interface.send_message(0x123, test_data):
            print("✅ Test message sent successfully")
        
        # Test receiving (with timeout)
        print("🔍 Listening for messages (5 seconds)...")
        start_time = time.time()
        while time.time() - start_time < 5:
            msg = can_interface.receive_message(timeout=1.0)
            if msg:
                print(f"📨 Received: ID=0x{msg.arbitration_id:03X}, Data={msg.data.hex().upper()}")
        
        # Get stats
        stats = can_interface.get_interface_stats()
        if stats:
            print(f"📊 Interface Stats: RX={stats['rx_packets']}, TX={stats['tx_packets']}")
        
        can_interface.disconnect()
        print("✅ Test completed successfully")
    else:
        print("❌ Failed to connect to CAN interface")

if __name__ == "__main__":
    test_can_interface()