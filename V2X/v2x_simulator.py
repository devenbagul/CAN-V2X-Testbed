#!/usr/bin/env python3
"""
V2X CAN Message Simulator
Simulates automotive CAN messages for testing
"""

import can
import time
import threading
import random
from datetime import datetime

class CANMsg:
    def __init__(self, arb_id, data):
        self.arbitration_id = arb_id
        self.data = data

class V2XSimulator:
    def __init__(self, interface='vcan0'):
        self.interface = interface
        self.bus = None
        self.running = False
        self.speed = 0
        self.engine_rpm = 800
        self.brake_pressure = 0
        
        # CAN Message IDs
        self.CAN_IDS = {
            'ENGINE_RPM': 0x0CF00400,
            'VEHICLE_SPEED': 0x0CF00503,
            'BRAKE_PRESSURE': 0x0CF00300,
            'STEERING_ANGLE': 0x0CF00200,
            'AIRBAG_STATUS': 0x0CF00100,
            'V2X_SPEED_WARNING': 0x0CF00600,
            'V2X_EMERGENCY': 0x0CF00700,
            'ENGINE_TEMP': 0x0CF00401,
            'FUEL_LEVEL': 0x0CF00402
        }
        
    def connect(self):
        """Connect to CAN bus"""
        try:
            # Try file-based shared CAN for Windows
            from shared_can import SharedCANBus
            self.bus = SharedCANBus('v2x')
            print(f"Connected to shared file CAN interface")
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
    
    def send_engine_data(self):
        """Send engine RPM and temperature"""
        # Engine RPM (0-8000 RPM)
        rpm = int(self.engine_rpm)
        rpm_data = rpm.to_bytes(2, 'big') + b'\x00' * 6
        msg = CANMsg(self.CAN_IDS['ENGINE_RPM'], rpm_data)
        self.bus.send(msg)
        
        # Engine Temperature (60-120°C)
        temp = random.randint(60, 120)
        temp_data = temp.to_bytes(1, 'big') + b'\x00' * 7
        msg = CANMsg(self.CAN_IDS['ENGINE_TEMP'], temp_data)
        self.bus.send(msg)
    
    def send_vehicle_speed(self):
        """Send vehicle speed and check V2X warnings"""
        speed = int(self.speed * 100)
        speed_data = speed.to_bytes(2, 'big') + b'\x00' * 6
        msg = CANMsg(self.CAN_IDS['VEHICLE_SPEED'], speed_data)
        self.bus.send(msg)
        
        # V2X Speed Warning (>80 km/h)
        if self.speed > 80:
            warning_data = b'\x01\x50\x00\x00\x00\x00\x00\x00'  # Warning + 80 km/h threshold
            msg = CANMsg(self.CAN_IDS['V2X_SPEED_WARNING'], warning_data)
            self.bus.send(msg)
    
    def send_brake_data(self):
        """Send brake pressure"""
        pressure = int(self.brake_pressure)
        pressure_data = pressure.to_bytes(2, 'big') + b'\x00' * 6
        msg = CANMsg(self.CAN_IDS['BRAKE_PRESSURE'], pressure_data)
        self.bus.send(msg)
    
    def send_steering_data(self):
        """Send steering angle"""
        angle = random.randint(-540, 540)  # -540° to +540°
        angle_data = angle.to_bytes(2, 'big', signed=True) + b'\x00' * 6
        msg = CANMsg(self.CAN_IDS['STEERING_ANGLE'], angle_data)
        self.bus.send(msg)
    
    def send_airbag_status(self):
        """Send airbag system status"""
        status = 0x00  # All airbags OK
        if random.random() < 0.01:  # 1% chance of fault
            status = 0x01  # Fault detected
        
        status_data = status.to_bytes(1, 'big') + b'\x00' * 7
        msg = CANMsg(self.CAN_IDS['AIRBAG_STATUS'], status_data)
        self.bus.send(msg)
    
    def simulate_driving(self):
        """Simulate realistic driving patterns"""
        while self.running:
            # Simulate speed changes
            if random.random() < 0.3:  # 30% chance to change speed
                if self.speed < 5:
                    self.speed += random.uniform(0, 10)
                elif self.speed > 100:
                    self.speed -= random.uniform(0, 15)
                else:
                    self.speed += random.uniform(-5, 10)
                self.speed = max(0, min(120, self.speed))
            
            # Simulate engine RPM based on speed
            if self.speed > 0:
                self.engine_rpm = 800 + (self.speed * 40)
            else:
                self.engine_rpm = 800
            
            # Simulate braking
            if random.random() < 0.2:  # 20% chance of braking
                self.brake_pressure = random.uniform(0, 100)
            else:
                self.brake_pressure = 0
            
            time.sleep(0.1)
    
    def start_simulation(self):
        """Start the simulation"""
        if not self.connect():
            return False
        
        self.running = True
        
        # Start driving simulation thread
        driving_thread = threading.Thread(target=self.simulate_driving)
        driving_thread.daemon = True
        driving_thread.start()
        
        print("🚗 V2X Simulation started...")
        
        try:
            while self.running:
                self.send_engine_data()
                self.send_vehicle_speed()
                self.send_brake_data()
                self.send_steering_data()
                self.send_airbag_status()
                
                time.sleep(0.1)  # 10Hz update rate
                
        except KeyboardInterrupt:
            self.stop_simulation()
        
        return True
    
    def stop_simulation(self):
        """Stop the simulation"""
        self.running = False
        if self.bus:
            self.bus.shutdown()
        print("🛑 V2X Simulation stopped")

if __name__ == "__main__":
    simulator = V2XSimulator()
    simulator.start_simulation()