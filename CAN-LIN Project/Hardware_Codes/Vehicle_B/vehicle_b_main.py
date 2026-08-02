#!/usr/bin/env python3
"""
Vehicle B - Secondary Vehicle Controller
Raspberry Pi implementation for V2X receiver vehicle
"""

import sys
import os
import time
import threading
import logging
from datetime import datetime
from collections import deque

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Shared'))

from can_protocol import CANMessageIDs, V2XProtocol, SafetyThresholds, get_message_description
from rpi_can_interface import RPiCANInterface, CANLogger

class VehicleBController:
    """Main controller for Vehicle B (Secondary/Receiver)"""
    
    def __init__(self):
        self.can_interface = RPiCANInterface('can0')
        self.can_logger = CANLogger("vehicle_b.log")
        self.running = False
        
        # Vehicle state
        self.vehicle_state = {
            'speed': 0.0,
            'engine_rpm': 800,
            'engine_temp': 85,
            'brake_pressure': 0,
            'fuel_level': 80,
            'steering_angle': 0,
            'abs_active': False,
            'emergency_brake': False
        }
        
        # V2X monitoring
        self.other_vehicles = {}  # Track other vehicles
        self.safety_alerts = deque(maxlen=50)
        self.collision_warnings = deque(maxlen=20)
        
        # Safety thresholds
        self.safety_distance = 50  # meters
        self.speed_warning_sent = False
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("VehicleB")
        
        print("🚗 Vehicle B Controller Initialized")
    
    def start_system(self):
        """Start the V2X system"""
        print("🚀 Starting Vehicle B V2X System...")
        
        # Connect to CAN bus
        if not self.can_interface.connect():
            print("❌ Failed to connect to CAN interface")
            return False
        
        self.running = True
        
        # Start monitoring incoming messages
        self.can_interface.start_monitoring(self.handle_incoming_message)
        
        # Start vehicle simulation and safety threads
        threading.Thread(target=self.vehicle_simulation, daemon=True).start()
        threading.Thread(target=self.safety_processor, daemon=True).start()
        threading.Thread(target=self.collision_detector, daemon=True).start()
        threading.Thread(target=self.v2x_responder, daemon=True).start()
        
        print("✅ Vehicle B system started successfully")
        self.can_logger.log_event("SYSTEM", "Vehicle B started")
        return True
    
    def stop_system(self):
        """Stop the V2X system"""
        print("🛑 Stopping Vehicle B system...")
        self.running = False
        self.can_interface.disconnect()
        self.can_logger.log_event("SYSTEM", "Vehicle B stopped")
    
    def handle_incoming_message(self, msg):
        """Handle incoming CAN messages"""
        try:
            self.can_logger.log_message(msg, "RX")
            
            # Parse and process different message types
            if msg.arbitration_id == CANMessageIDs.VEHICLE_SPEED:
                self.process_speed_message(msg)
            elif msg.arbitration_id == CANMessageIDs.ENGINE_RPM:
                self.process_engine_message(msg)
            elif msg.arbitration_id == CANMessageIDs.BRAKE_PRESSURE:
                self.process_brake_message(msg)
            elif msg.arbitration_id == CANMessageIDs.COLLISION_WARNING:
                self.process_collision_warning(msg)
            elif msg.arbitration_id == CANMessageIDs.EMERGENCY_VEHICLE:
                self.process_emergency_vehicle(msg)
            elif msg.arbitration_id == CANMessageIDs.SPEED_WARNING:
                self.process_speed_warning(msg)
            
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
    
    def process_speed_message(self, msg):
        """Process vehicle speed message from other vehicle"""
        speed = V2XProtocol.parse_speed_message(msg)
        if speed is not None:
            vehicle_id = "VehicleA"  # In real implementation, extract from message
            self.other_vehicles[vehicle_id] = {
                'speed': speed,
                'last_seen': datetime.now(),
                'distance': 30  # Simulated distance
            }
            
            # Check for speed-based safety concerns
            if speed > SafetyThresholds.MAX_SPEED:
                self.add_safety_alert("SPEED_VIOLATION", f"Vehicle {vehicle_id} exceeding speed limit: {speed:.1f} km/h")
    
    def process_engine_message(self, msg):
        """Process engine data from other vehicle"""
        engine_data = V2XProtocol.parse_engine_message(msg)
        if engine_data:
            if engine_data['temperature'] > SafetyThresholds.MAX_ENGINE_TEMP:
                self.add_safety_alert("ENGINE_OVERHEAT", f"Vehicle engine overheating: {engine_data['temperature']}°C")
    
    def process_brake_message(self, msg):
        """Process brake data from other vehicle"""
        brake_data = V2XProtocol.parse_brake_message(msg)
        if brake_data:
            if brake_data['pressure'] > 80:  # High brake pressure
                self.add_safety_alert("HARD_BRAKING", "Vehicle ahead braking hard!")
                self.initiate_emergency_response()
    
    def process_collision_warning(self, msg):
        """Process collision warning from other vehicle"""
        self.collision_warnings.append({
            'timestamp': datetime.now(),
            'severity': msg.data[1] if len(msg.data) > 1 else 0x80,
            'message': "Collision warning received"
        })
        
        print("🚨 COLLISION WARNING RECEIVED!")
        self.add_safety_alert("COLLISION_WARNING", "Immediate collision risk detected")
        self.initiate_emergency_response()
    
    def process_emergency_vehicle(self, msg):
        """Process emergency vehicle alert"""
        print("🚨 Emergency vehicle approaching!")
        self.add_safety_alert("EMERGENCY_VEHICLE", "Emergency vehicle in area - yield right of way")
        self.initiate_lane_change()
    
    def process_speed_warning(self, msg):
        """Process speed warning from other vehicle"""
        if len(msg.data) >= 5:
            current_speed = int.from_bytes(msg.data[:2], 'big')
            speed_limit = int.from_bytes(msg.data[2:4], 'big')
            
            print(f"⚠️ Speed warning: {current_speed} km/h in {speed_limit} km/h zone")
            self.add_safety_alert("SPEED_WARNING", f"Speed limit violation detected: {current_speed}/{speed_limit} km/h")
    
    def vehicle_simulation(self):
        """Simulate Vehicle B's own movement and systems"""
        import random
        
        while self.running:
            try:
                # Simulate speed changes (more conservative than Vehicle A)
                if random.random() < 0.2:  # 20% chance to change speed
                    if self.vehicle_state['speed'] < 5:
                        self.vehicle_state['speed'] += random.uniform(2, 8)
                    elif self.vehicle_state['speed'] > 90:
                        self.vehicle_state['speed'] -= random.uniform(3, 12)
                    else:
                        self.vehicle_state['speed'] += random.uniform(-5, 8)
                
                # Keep speed in range
                self.vehicle_state['speed'] = max(0, min(self.vehicle_state['speed'], 100))
                
                # Update engine parameters
                if self.vehicle_state['speed'] > 0:
                    self.vehicle_state['engine_rpm'] = 800 + (self.vehicle_state['speed'] * 30)
                else:
                    self.vehicle_state['engine_rpm'] = 800
                
                # Broadcast own status
                self.broadcast_status()
                
                time.sleep(0.3)  # ~3Hz update rate
                
            except Exception as e:
                self.logger.error(f"Vehicle simulation error: {e}")
                time.sleep(1)
    
    def safety_processor(self):
        """Process safety conditions and generate responses"""
        while self.running:
            try:
                # Check distance to other vehicles
                for vehicle_id, data in self.other_vehicles.items():
                    # Remove stale vehicle data
                    if (datetime.now() - data['last_seen']).seconds > 5:
                        del self.other_vehicles[vehicle_id]
                        continue
                    
                    # Check collision risk
                    if data['distance'] < self.safety_distance and data['speed'] > self.vehicle_state['speed']:
                        self.add_safety_alert("COLLISION_RISK", f"Vehicle {vehicle_id} approaching too fast")
                        self.send_collision_warning()
                
                # Monitor own vehicle safety
                if self.vehicle_state['speed'] > SafetyThresholds.MAX_SPEED and not self.speed_warning_sent:
                    self.send_speed_warning()
                    self.speed_warning_sent = True
                elif self.vehicle_state['speed'] <= SafetyThresholds.MAX_SPEED:
                    self.speed_warning_sent = False
                
                time.sleep(1.0)  # 1Hz safety processing
                
            except Exception as e:
                self.logger.error(f"Safety processor error: {e}")
                time.sleep(1)
    
    def collision_detector(self):
        """Advanced collision detection and avoidance"""
        while self.running:
            try:
                # Analyze collision warnings
                recent_warnings = [w for w in self.collision_warnings 
                                 if (datetime.now() - w['timestamp']).seconds < 10]
                
                if len(recent_warnings) > 2:  # Multiple warnings in short time
                    print("🚨 MULTIPLE COLLISION WARNINGS - TAKING EVASIVE ACTION!")
                    self.initiate_emergency_response()
                
                time.sleep(0.5)  # 2Hz collision detection
                
            except Exception as e:
                self.logger.error(f"Collision detector error: {e}")
                time.sleep(1)
    
    def v2x_responder(self):
        """Respond to V2X messages from other vehicles"""
        while self.running:
            try:
                # Send acknowledgments for critical messages
                if self.collision_warnings:
                    # Send collision acknowledgment
                    ack_msg = V2XProtocol.create_emergency_message(0x03, 0x01, b'ACK_OK')
                    self.send_can_message(ack_msg)
                
                time.sleep(2.0)  # Send responses every 2 seconds
                
            except Exception as e:
                self.logger.error(f"V2X responder error: {e}")
                time.sleep(1)
    
    def add_safety_alert(self, alert_type, message):
        """Add safety alert to queue"""
        alert = {
            'type': alert_type,
            'message': message,
            'timestamp': datetime.now(),
            'processed': False
        }
        self.safety_alerts.append(alert)
        
        print(f"⚠️ Safety Alert: {message}")
        self.can_logger.log_event("SAFETY", f"{alert_type}: {message}")
    
    def initiate_emergency_response(self):
        """Initiate emergency response procedures"""
        print("🚨 INITIATING EMERGENCY RESPONSE!")
        
        # Activate emergency braking
        self.vehicle_state['emergency_brake'] = True
        self.vehicle_state['brake_pressure'] = 100
        self.vehicle_state['abs_active'] = True
        
        # Send emergency brake message
        brake_msg = V2XProtocol.create_brake_message(100, abs_active=True)
        self.send_can_message(brake_msg)
        
        # Reduce speed
        self.vehicle_state['speed'] = max(0, self.vehicle_state['speed'] - 20)
        
        self.can_logger.log_event("EMERGENCY", "Emergency response activated")
        
        # Reset emergency state after 5 seconds
        threading.Timer(5.0, self.reset_emergency_state).start()
    
    def initiate_lane_change(self):
        """Simulate lane change for emergency vehicle"""
        print("🚗 Changing lanes for emergency vehicle...")
        self.vehicle_state['steering_angle'] = 15  # Simulate steering
        
        # Reset steering after 3 seconds
        threading.Timer(3.0, lambda: setattr(self.vehicle_state, 'steering_angle', 0)).start()
        
        self.can_logger.log_event("MANEUVER", "Lane change for emergency vehicle")
    
    def send_collision_warning(self):
        """Send collision warning to other vehicles"""
        warning_msg = V2XProtocol.create_emergency_message(0x01, 0xFF, b'DANGER')
        self.send_can_message(warning_msg)
        
        print("📡 Collision warning sent to other vehicles")
        self.can_logger.log_event("V2X", "Collision warning transmitted")
    
    def send_speed_warning(self):
        """Send speed warning"""
        speed_msg = V2XProtocol.create_speed_warning(
            self.vehicle_state['speed'],
            SafetyThresholds.MAX_SPEED
        )
        self.send_can_message(speed_msg)
        
        print(f"📡 Speed warning sent: {self.vehicle_state['speed']:.1f} km/h")
    
    def broadcast_status(self):
        """Broadcast vehicle status"""
        # Send speed
        speed_msg = V2XProtocol.create_speed_message(self.vehicle_state['speed'])
        self.send_can_message(speed_msg)
        
        # Send engine data occasionally
        if int(time.time()) % 5 == 0:  # Every 5 seconds
            engine_msg = V2XProtocol.create_engine_message(
                self.vehicle_state['engine_rpm'],
                self.vehicle_state['engine_temp']
            )
            self.send_can_message(engine_msg)
    
    def reset_emergency_state(self):
        """Reset emergency state"""
        self.vehicle_state['emergency_brake'] = False
        self.vehicle_state['brake_pressure'] = 0
        self.vehicle_state['abs_active'] = False
        print("✅ Emergency state reset")
    
    def send_can_message(self, msg):
        """Send CAN message and log it"""
        if self.can_interface.send_message(msg.arbitration_id, msg.data):
            self.can_logger.log_message(msg, "TX")
    
    def get_system_status(self):
        """Get current system status"""
        stats = self.can_interface.get_interface_stats()
        return {
            'vehicle_state': self.vehicle_state,
            'other_vehicles': dict(self.other_vehicles),
            'safety_alerts': len(self.safety_alerts),
            'collision_warnings': len(self.collision_warnings),
            'can_stats': stats,
            'running': self.running
        }
    
    def print_status(self):
        """Print current vehicle status"""
        print(f"\n📊 Vehicle B Status:")
        print(f"Speed: {self.vehicle_state['speed']:.1f} km/h")
        print(f"Engine RPM: {self.vehicle_state['engine_rpm']}")
        print(f"Emergency Brake: {self.vehicle_state['emergency_brake']}")
        print(f"Other Vehicles: {len(self.other_vehicles)}")
        print(f"Safety Alerts: {len(self.safety_alerts)}")
        print(f"Collision Warnings: {len(self.collision_warnings)}")
        
        # Show recent alerts
        recent_alerts = list(self.safety_alerts)[-3:]
        if recent_alerts:
            print("Recent Alerts:")
            for alert in recent_alerts:
                print(f"  - {alert['type']}: {alert['message']}")

def main():
    """Main function"""
    print("🚗 Vehicle B - V2X Secondary Controller")
    print("=======================================")
    
    vehicle_b = VehicleBController()
    
    try:
        if vehicle_b.start_system():
            print("\n🎮 Vehicle B is running. Press Ctrl+C to stop.")
            print("📊 Status updates every 10 seconds...\n")
            
            while True:
                time.sleep(10)
                vehicle_b.print_status()
                
    except KeyboardInterrupt:
        print("\n🛑 Shutting down Vehicle B...")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        vehicle_b.stop_system()
        print("✅ Vehicle B stopped successfully")

if __name__ == "__main__":
    main()