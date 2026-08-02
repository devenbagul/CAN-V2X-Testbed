#!/usr/bin/env python3
"""
V2X CAN Protocol Definitions
Shared message formats and IDs for vehicle communication
"""

# CAN Message ID Ranges
class CANMessageIDs:
    # Engine Control Messages (0x100-0x1FF)
    ENGINE_RPM = 0x100
    ENGINE_TEMP = 0x101
    ENGINE_LOAD = 0x102
    FUEL_LEVEL = 0x103
    
    # Brake System Messages (0x200-0x2FF)
    BRAKE_PRESSURE = 0x200
    ABS_STATUS = 0x201
    BRAKE_TEMP = 0x202
    EMERGENCY_BRAKE = 0x203
    
    # Safety System Messages (0x300-0x3FF)
    AIRBAG_STATUS = 0x300
    SEATBELT_STATUS = 0x301
    DOOR_STATUS = 0x302
    STEERING_ANGLE = 0x303
    
    # V2X Communication Messages (0x400-0x4FF)
    VEHICLE_SPEED = 0x400
    VEHICLE_POSITION = 0x401
    VEHICLE_HEADING = 0x402
    VEHICLE_ID = 0x403
    
    # Emergency Messages (0x500-0x5FF)
    COLLISION_WARNING = 0x500
    EMERGENCY_VEHICLE = 0x501
    SPEED_WARNING = 0x502
    TRAFFIC_ALERT = 0x503
    WEATHER_WARNING = 0x504

# V2X Message Types
class V2XMessageTypes:
    BASIC_SAFETY = 0x01
    EMERGENCY_WARNING = 0x02
    TRAFFIC_INFO = 0x03
    WEATHER_INFO = 0x04
    ROAD_HAZARD = 0x05

# Safety Thresholds
class SafetyThresholds:
    MAX_SPEED = 80  # km/h
    MAX_ENGINE_TEMP = 110  # °C
    MAX_BRAKE_TEMP = 200  # °C
    COLLISION_DISTANCE = 50  # meters
    EMERGENCY_BRAKE_PRESSURE = 90  # %

# Vehicle States
class VehicleStates:
    NORMAL = 0x00
    WARNING = 0x01
    EMERGENCY = 0x02
    FAULT = 0x03

class CANMessage:
    """Standard CAN message format"""
    def __init__(self, arbitration_id, data, timestamp=None):
        self.arbitration_id = arbitration_id
        self.data = data if isinstance(data, bytes) else bytes(data)
        self.timestamp = timestamp
        self.dlc = len(self.data)
    
    def __str__(self):
        return f"CAN ID: 0x{self.arbitration_id:03X}, Data: {self.data.hex().upper()}"

class V2XProtocol:
    """V2X message protocol handler"""
    
    @staticmethod
    def create_speed_message(speed_kmh):
        """Create vehicle speed message"""
        speed_data = int(speed_kmh * 100).to_bytes(2, 'big') + b'\x00' * 6
        return CANMessage(CANMessageIDs.VEHICLE_SPEED, speed_data)
    
    @staticmethod
    def create_engine_message(rpm, temp):
        """Create engine status message"""
        rpm_bytes = int(rpm).to_bytes(2, 'big')
        temp_bytes = int(temp).to_bytes(1, 'big')
        data = rpm_bytes + temp_bytes + b'\x00' * 5
        return CANMessage(CANMessageIDs.ENGINE_RPM, data)
    
    @staticmethod
    def create_brake_message(pressure, abs_active=False):
        """Create brake system message"""
        pressure_bytes = int(pressure).to_bytes(2, 'big')
        abs_byte = b'\x01' if abs_active else b'\x00'
        data = pressure_bytes + abs_byte + b'\x00' * 5
        return CANMessage(CANMessageIDs.BRAKE_PRESSURE, data)
    
    @staticmethod
    def create_emergency_message(msg_type, severity, data_payload=None):
        """Create emergency V2X message"""
        header = bytes([msg_type, severity])
        payload = data_payload if data_payload else b'\x00' * 6
        data = header + payload[:6]
        return CANMessage(CANMessageIDs.COLLISION_WARNING, data)
    
    @staticmethod
    def create_speed_warning(current_speed, speed_limit):
        """Create speed limit warning message"""
        speed_bytes = int(current_speed).to_bytes(2, 'big')
        limit_bytes = int(speed_limit).to_bytes(2, 'big')
        warning_byte = b'\x01'  # Warning active
        data = speed_bytes + limit_bytes + warning_byte + b'\x00' * 3
        return CANMessage(CANMessageIDs.SPEED_WARNING, data)
    
    @staticmethod
    def parse_speed_message(msg):
        """Parse vehicle speed from CAN message"""
        if msg.arbitration_id == CANMessageIDs.VEHICLE_SPEED and len(msg.data) >= 2:
            speed = int.from_bytes(msg.data[:2], 'big') / 100
            return speed
        return None
    
    @staticmethod
    def parse_engine_message(msg):
        """Parse engine data from CAN message"""
        if msg.arbitration_id == CANMessageIDs.ENGINE_RPM and len(msg.data) >= 3:
            rpm = int.from_bytes(msg.data[:2], 'big')
            temp = msg.data[2]
            return {'rpm': rpm, 'temperature': temp}
        return None
    
    @staticmethod
    def parse_brake_message(msg):
        """Parse brake data from CAN message"""
        if msg.arbitration_id == CANMessageIDs.BRAKE_PRESSURE and len(msg.data) >= 3:
            pressure = int.from_bytes(msg.data[:2], 'big')
            abs_active = msg.data[2] == 0x01
            return {'pressure': pressure, 'abs_active': abs_active}
        return None

# Message descriptions for logging
MESSAGE_DESCRIPTIONS = {
    CANMessageIDs.ENGINE_RPM: "Engine RPM & Temperature",
    CANMessageIDs.ENGINE_TEMP: "Engine Temperature",
    CANMessageIDs.BRAKE_PRESSURE: "Brake Pressure & ABS",
    CANMessageIDs.ABS_STATUS: "ABS System Status",
    CANMessageIDs.EMERGENCY_BRAKE: "Emergency Brake Signal",
    CANMessageIDs.AIRBAG_STATUS: "Airbag System Status",
    CANMessageIDs.STEERING_ANGLE: "Steering Wheel Angle",
    CANMessageIDs.VEHICLE_SPEED: "Vehicle Speed",
    CANMessageIDs.VEHICLE_POSITION: "Vehicle GPS Position",
    CANMessageIDs.COLLISION_WARNING: "Collision Warning",
    CANMessageIDs.EMERGENCY_VEHICLE: "Emergency Vehicle Alert",
    CANMessageIDs.SPEED_WARNING: "Speed Limit Warning",
    CANMessageIDs.TRAFFIC_ALERT: "Traffic Information"
}

def get_message_description(can_id):
    """Get human-readable description of CAN message"""
    return MESSAGE_DESCRIPTIONS.get(can_id, f"Unknown Message (0x{can_id:03X})")