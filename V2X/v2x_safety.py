#!/usr/bin/env python3
"""
V2X Safety System
Monitors CAN messages and triggers safety responses
"""

import can
import threading
import time
from datetime import datetime

class V2XSafetySystem:
    def __init__(self, interface='vcan0'):
        self.interface = interface
        self.bus = None
        self.running = False
        
        # Safety thresholds
        self.SPEED_LIMIT = 80  # km/h
        self.MAX_ENGINE_TEMP = 110  # °C
        self.MAX_BRAKE_PRESSURE = 90  # %
        
        # Current vehicle state
        self.current_speed = 0
        self.engine_temp = 0
        self.brake_pressure = 0
        self.airbag_fault = False
        
        # Safety alerts
        self.alerts = []
        
    def connect(self):
        """Connect to CAN bus"""
        try:
            # Try virtual interface first (Windows compatible)
            self.bus = can.interface.Bus(interface='virtual')
            print(f"Connected to virtual CAN interface")
            return True
        except:
            try:
                # Try socketcan for Linux
                self.bus = can.interface.Bus(channel=self.interface, interface='socketcan')
                print(f"Connected to socketcan: {self.interface}")
                return True
            except Exception as e:
                print(f"CAN connection failed: {e}")
                return False
    
    def decode_message(self, msg):
        """Decode incoming CAN messages"""
        msg_id = msg.arbitration_id
        data = msg.data
        
        if msg_id == 0x0CF00503:  # Vehicle Speed
            self.current_speed = int.from_bytes(data[:2], 'big') / 100
            self.check_speed_safety()
            
        elif msg_id == 0x0CF00401:  # Engine Temperature
            self.engine_temp = data[0]
            self.check_engine_safety()
            
        elif msg_id == 0x0CF00300:  # Brake Pressure
            self.brake_pressure = int.from_bytes(data[:2], 'big')
            self.check_brake_safety()
            
        elif msg_id == 0x0CF00100:  # Airbag Status
            self.airbag_fault = data[0] != 0
            self.check_airbag_safety()
            
        elif msg_id == 0x0CF00600:  # V2X Speed Warning
            self.handle_v2x_warning(data)
    
    def check_speed_safety(self):
        """Check speed-related safety"""
        if self.current_speed > self.SPEED_LIMIT:
            alert = {
                'type': 'SPEED_WARNING',
                'message': f'Speed {self.current_speed:.1f} km/h exceeds limit {self.SPEED_LIMIT} km/h',
                'severity': 'HIGH',
                'timestamp': datetime.now()
            }
            self.add_alert(alert)
            self.send_emergency_brake_request()
    
    def check_engine_safety(self):
        """Check engine temperature safety"""
        if self.engine_temp > self.MAX_ENGINE_TEMP:
            alert = {
                'type': 'ENGINE_OVERHEAT',
                'message': f'Engine temperature {self.engine_temp}°C is critical',
                'severity': 'CRITICAL',
                'timestamp': datetime.now()
            }
            self.add_alert(alert)
            self.send_engine_protection()
    
    def check_brake_safety(self):
        """Check brake system safety"""
        if self.brake_pressure > self.MAX_BRAKE_PRESSURE:
            alert = {
                'type': 'BRAKE_OVERLOAD',
                'message': f'Brake pressure {self.brake_pressure}% is excessive',
                'severity': 'HIGH',
                'timestamp': datetime.now()
            }
            self.add_alert(alert)
    
    def check_airbag_safety(self):
        """Check airbag system safety"""
        if self.airbag_fault:
            alert = {
                'type': 'AIRBAG_FAULT',
                'message': 'Airbag system fault detected',
                'severity': 'CRITICAL',
                'timestamp': datetime.now()
            }
            self.add_alert(alert)
    
    def handle_v2x_warning(self, data):
        """Handle V2X communication warnings"""
        warning_type = data[0]
        if warning_type == 0x01:  # Speed warning
            alert = {
                'type': 'V2X_SPEED_WARNING',
                'message': 'V2X: Speed limit exceeded - reduce speed immediately',
                'severity': 'HIGH',
                'timestamp': datetime.now()
            }
            self.add_alert(alert)
    
    def send_emergency_brake_request(self):
        """Send emergency brake activation"""
        brake_data = b'\xFF\x64\x00\x00\x00\x00\x00\x00'  # 100% brake request
        msg = can.Message(arbitration_id=0x0CF00301, data=brake_data)
        if self.bus:
            self.bus.send(msg)
    
    def send_engine_protection(self):
        """Send engine protection command"""
        protection_data = b'\x01\x00\x00\x00\x00\x00\x00\x00'  # Reduce power
        msg = can.Message(arbitration_id=0x0CF00403, data=protection_data)
        if self.bus:
            self.bus.send(msg)
    
    def add_alert(self, alert):
        """Add safety alert"""
        self.alerts.append(alert)
        print(f"🚨 {alert['severity']}: {alert['message']}")
        
        # Keep only last 100 alerts
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]
    
    def get_recent_alerts(self, count=10):
        """Get recent safety alerts"""
        return self.alerts[-count:] if self.alerts else []
    
    def monitor_messages(self):
        """Monitor CAN messages for safety"""
        if not self.connect():
            return False
        
        self.running = True
        print("🛡️ V2X Safety System active...")
        
        try:
            while self.running:
                msg = self.bus.recv(timeout=1.0)
                if msg:
                    self.decode_message(msg)
                    
        except KeyboardInterrupt:
            self.stop_monitoring()
        
        return True
    
    def stop_monitoring(self):
        """Stop safety monitoring"""
        self.running = False
        if self.bus:
            self.bus.shutdown()
        print("🛑 V2X Safety System stopped")

if __name__ == "__main__":
    safety_system = V2XSafetySystem()
    safety_system.monitor_messages()