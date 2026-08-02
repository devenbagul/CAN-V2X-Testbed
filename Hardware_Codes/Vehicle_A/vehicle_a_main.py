#!/usr/bin/env python3
"""
Vehicle A - Primary Vehicle Controller
Raspberry Pi implementation for V2X sender vehicle
"""

import sys
import os
import time
import threading
import logging
from datetime import datetime

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Shared'))

from can_protocol import CANMessageIDs, V2XProtocol, SafetyThresholds
from rpi_can_interface import RPiCANInterface, CANLogger

class VehicleAController:
    """Main controller for Vehicle A (Primary/Sender)"""
    
    def __init__(self):
        self.can_interface = RPiCANInterface('can0')
        self.can_logger = CANLogger("vehicle_a.log")
        self.running = False
        
        # Vehicle state
        self.vehicle_state = {
            'speed': 0.0,           # km/h
            'engine_rpm': 800,      # RPM
            'engine_temp': 85,      # °C
            'brake_pressure': 0,    # %
            'fuel_level': 75,       # %
            'steering_angle': 0,    # degrees
            'abs_active': False,
            'emergency_brake': False
        }
        
        # V2X state
        self.v2x_alerts = []
        self.emergency_mode = False
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("VehicleA")
        
        print("🚗 Vehicle A Controller Initialized")
    
    def start_system(self):
        """Start the V2X system"""
        print("🚀 Starting Vehicle A V2X System...")
        
        # Connect to CAN bus
        if not self.can_interface.connect():
            print("❌ Failed to connect to CAN interface")
            return False
        
        self.running = True
        
        # Start monitoring incoming messages
        self.can_interface.start_monitoring(self.handle_incoming_message)
        
        # Start vehicle simulation threads
        threading.Thread(target=self.engine_simulation, daemon=True).start()
        threading.Thread(target=self.speed_simulation, daemon=True).start()
        threading.Thread(target=self.safety_monitoring, daemon=True).start()
        threading.Thread(target=self.v2x_broadcaster, daemon=True).start()
        
        print("✅ Vehicle A system started successfully")
        self.can_logger.log_event("SYSTEM", "Vehicle A started")
        return True
    
    def stop_system(self):
        """Stop the V2X system"""
        print("🛑 Stopping Vehicle A system...")
        self.running = False
        self.can_interface.disconnect()
        self.can_logger.log_event("SYSTEM", "Vehicle A stopped")
    
    def handle_incoming_message(self, msg):
        """Handle incoming CAN messages"""
        try:
            self.can_logger.log_message(msg, "RX")
            
            # Process V2X messages from other vehicles
            if msg.arbitration_id == CANMessageIDs.COLLISION_WARNING:
                self.handle_collision_warning(msg)
            elif msg.arbitration_id == CANMessageIDs.EMERGENCY_VEHICLE:
                self.handle_emergency_vehicle(msg)
            elif msg.arbitration_id == CANMessageIDs.TRAFFIC_ALERT:
                self.handle_traffic_alert(msg)
            
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
    
    def engine_simulation(self):
        """Simulate engine parameters"""
        while self.running:
            try:
                # Simulate engine RPM based on speed
                if self.vehicle_state['speed'] > 0:
                    base_rpm = 800 + (self.vehicle_state['speed'] * 35)
                    self.vehicle_state['engine_rpm'] = min(base_rpm, 6000)
                else:
                    self.vehicle_state['engine_rpm'] = 800
                
                # Simulate engine temperature
                if self.vehicle_state['engine_rpm'] > 3000:
                    self.vehicle_state['engine_temp'] = min(self.vehicle_state['engine_temp'] + 1, 120)
                else:
                    self.vehicle_state['engine_temp'] = max(self.vehicle_state['engine_temp'] - 0.5, 85)
                
                # Send engine data
                msg = V2XProtocol.create_engine_message(
                    self.vehicle_state['engine_rpm'],
                    self.vehicle_state['engine_temp']
                )
                self.send_can_message(msg)
                
                time.sleep(0.5)  # 2Hz update rate
                
            except Exception as e:
                self.logger.error(f"Engine simulation error: {e}")
                time.sleep(1)
    
    def speed_simulation(self):
        """Simulate vehicle speed changes"""
        import random
        
        while self.running:
            try:
                # Simulate realistic speed changes
                if random.random() < 0.3:  # 30% chance to change speed
                    if self.vehicle_state['speed'] < 10:
                        # Accelerate from low speed
                        self.vehicle_state['speed'] += random.uniform(5, 15)
                    elif self.vehicle_state['speed'] > 100:
                        # Decelerate from high speed
                        self.vehicle_state['speed'] -= random.uniform(5, 20)
                    else:
                        # Normal speed variation
                        self.vehicle_state['speed'] += random.uniform(-10, 15)
                
                # Keep speed in realistic range
                self.vehicle_state['speed'] = max(0, min(self.vehicle_state['speed'], 120))
                
                # Send speed data
                msg = V2XProtocol.create_speed_message(self.vehicle_state['speed'])
                self.send_can_message(msg)
                
                time.sleep(0.2)  # 5Hz update rate
                
            except Exception as e:
                self.logger.error(f"Speed simulation error: {e}")
                time.sleep(1)
    
    def safety_monitoring(self):
        """Monitor safety conditions and generate alerts"""
        while self.running:
            try:
                # Check speed limit
                if self.vehicle_state['speed'] > SafetyThresholds.MAX_SPEED:
                    self.generate_speed_warning()
                
                # Check engine temperature
                if self.vehicle_state['engine_temp'] > SafetyThresholds.MAX_ENGINE_TEMP:
                    self.generate_engine_warning()
                
                # Simulate emergency braking scenario
                if random.random() < 0.01:  # 1% chance per cycle
                    self.simulate_emergency_brake()
                
                time.sleep(1.0)  # 1Hz monitoring
                
            except Exception as e:
                self.logger.error(f"Safety monitoring error: {e}")
                time.sleep(1)
    
    def v2x_broadcaster(self):
        """Broadcast V2X messages to other vehicles"""
        while self.running:
            try:
                # Broadcast vehicle status every 100ms
                self.broadcast_vehicle_status()
                
                # Process and send any pending alerts
                if self.v2x_alerts:
                    alert = self.v2x_alerts.pop(0)
                    self.send_v2x_alert(alert)
                
                time.sleep(0.1)  # 10Hz broadcast rate
                
            except Exception as e:
                self.logger.error(f"V2X broadcaster error: {e}")
                time.sleep(1)
    
    def generate_speed_warning(self):
        """Generate speed limit warning"""
        msg = V2XProtocol.create_speed_warning(
            self.vehicle_state['speed'],
            SafetyThresholds.MAX_SPEED
        )
        self.send_can_message(msg)
        
        alert = {
            'type': 'SPEED_WARNING',
            'message': f"Speed {self.vehicle_state['speed']:.1f} km/h exceeds limit {SafetyThresholds.MAX_SPEED} km/h",
            'severity': 'HIGH',
            'timestamp': datetime.now()
        }
        self.v2x_alerts.append(alert)
        
        print(f"⚠️ Speed Warning: {alert['message']}")
        self.can_logger.log_event("SAFETY", alert['message'])
    
    def generate_engine_warning(self):
        """Generate engine overheat warning"""
        alert = {
            'type': 'ENGINE_WARNING',
            'message': f"Engine temperature {self.vehicle_state['engine_temp']}°C is critical",
            'severity': 'CRITICAL',
            'timestamp': datetime.now()
        }
        self.v2x_alerts.append(alert)
        
        print(f"🔥 Engine Warning: {alert['message']}")
        self.can_logger.log_event("SAFETY", alert['message'])
    
    def simulate_emergency_brake(self):
        """Simulate emergency braking scenario"""
        self.vehicle_state['emergency_brake'] = True
        self.vehicle_state['brake_pressure'] = 100
        
        # Send emergency brake message
        msg = V2XProtocol.create_brake_message(100, abs_active=True)
        self.send_can_message(msg)
        
        # Send emergency alert to other vehicles
        emergency_msg = V2XProtocol.create_emergency_message(0x02, 0xFF, b'BRAKE!')
        self.send_can_message(emergency_msg)
        
        print("🚨 EMERGENCY BRAKE ACTIVATED!")
        self.can_logger.log_event("EMERGENCY", "Emergency brake activated")
        
        # Reset after 3 seconds
        threading.Timer(3.0, self.reset_emergency_brake).start()
    
    def reset_emergency_brake(self):
        """Reset emergency brake state"""
        self.vehicle_state['emergency_brake'] = False
        self.vehicle_state['brake_pressure'] = 0
        print("✅ Emergency brake reset")
    
    def broadcast_vehicle_status(self):
        """Broadcast current vehicle status"""
        # Send basic vehicle data
        speed_msg = V2XProtocol.create_speed_message(self.vehicle_state['speed'])
        self.send_can_message(speed_msg)
    
    def send_v2x_alert(self, alert):
        """Send V2X alert message"""
        msg_type = 0x01 if alert['severity'] == 'HIGH' else 0x02
        severity = 0xFF if alert['severity'] == 'CRITICAL' else 0x80
        
        emergency_msg = V2XProtocol.create_emergency_message(msg_type, severity)
        self.send_can_message(emergency_msg)
    
    def send_can_message(self, msg):
        """Send CAN message and log it"""
        if self.can_interface.send_message(msg.arbitration_id, msg.data):
            self.can_logger.log_message(msg, "TX")
    
    def handle_collision_warning(self, msg):
        """Handle collision warning from other vehicle"""
        print("⚠️ Collision warning received from other vehicle!")
        self.can_logger.log_event("V2X", "Collision warning received")
        
        # Activate emergency braking
        self.simulate_emergency_brake()
    
    def handle_emergency_vehicle(self, msg):
        """Handle emergency vehicle alert"""
        print("🚨 Emergency vehicle approaching - moving to side!")
        self.can_logger.log_event("V2X", "Emergency vehicle alert received")
    
    def handle_traffic_alert(self, msg):
        """Handle traffic information"""
        print("🚦 Traffic alert received")
        self.can_logger.log_event("V2X", "Traffic alert received")
    
    def get_system_status(self):
        """Get current system status"""
        stats = self.can_interface.get_interface_stats()
        return {
            'vehicle_state': self.vehicle_state,
            'can_stats': stats,
            'running': self.running,
            'emergency_mode': self.emergency_mode,
            'alerts_pending': len(self.v2x_alerts)
        }
    
    def print_status(self):
        """Print current vehicle status"""
        print(f"\n📊 Vehicle A Status:")
        print(f"Speed: {self.vehicle_state['speed']:.1f} km/h")
        print(f"Engine RPM: {self.vehicle_state['engine_rpm']}")
        print(f"Engine Temp: {self.vehicle_state['engine_temp']}°C")
        print(f"Brake Pressure: {self.vehicle_state['brake_pressure']}%")
        print(f"Emergency Mode: {self.emergency_mode}")
        print(f"Pending Alerts: {len(self.v2x_alerts)}")

def main():
    """Main function"""
    print("🚗 Vehicle A - V2X Primary Controller")
    print("=====================================")
    
    vehicle_a = VehicleAController()
    
    try:
        if vehicle_a.start_system():
            print("\n🎮 Vehicle A is running. Press Ctrl+C to stop.")
            print("📊 Status updates every 10 seconds...\n")
            
            while True:
                time.sleep(10)
                vehicle_a.print_status()
                
    except KeyboardInterrupt:
        print("\n🛑 Shutting down Vehicle A...")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        vehicle_a.stop_system()
        print("✅ Vehicle A stopped successfully")

if __name__ == "__main__":
    main()