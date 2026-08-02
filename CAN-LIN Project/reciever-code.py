#!/usr/bin/env python3
import can
import os
import time
import logging
# Helper modules are not required for core gateway functionality

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("lin_can_gateway.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('LIN-CAN-Gateway')

# Setup CAN interface (Windows compatible)
logger.info("Setting up CAN interface...")

class LINCANGateway:
    def __init__(self):
        """Initialize the LIN-CAN Gateway"""
        try:
            # Try virtual interface first (works on Windows)
            self.bus = can.interface.Bus(interface='virtual')
            logger.info("Connected to virtual CAN bus successfully")
            
            # LIN message ID to description mapping (for better logging)
            self.lin_id_descriptions = {
                0x11: "Door Lock Status",
                0x12: "Engine Temperature Sensor",
                0x13: "Light Status",
                0x14: "Window Position",
                0x22: "Climate Control",
                0x33: "Seat Position",
            }
            
            # PGN to description mapping
            self.pgn_descriptions = {
                65108: "Engine Temperature",
                61444: "Electronic Engine Controller",
                65267: "Vehicle Position",
                65262: "Engine Coolant Temperature",
                65269: "Ambient Conditions",
            }
            
            # Track LIN messages to properly respond with matching data
            self.lin_message_cache = {}
        except Exception as e:
            logger.error(f"Failed to initialize CAN bus: {e}")
            raise
    
    def send_lin_as_can(self, lin_id, lin_data, description=None):
        """
        Translate a LIN message to CAN format and send it
        
        Args:
            lin_id (int): LIN identifier (0-63)
            lin_data (list): Data bytes for the LIN message
            description (str, optional): Human-readable description of what this message represents
        """
        if lin_id > 63:
            logger.warning(f"Invalid LIN ID: {lin_id}. Must be 0-63.")
            return False
            
        # Calculate LIN checksum (simple sum for demonstration)
        checksum = sum(lin_data) & 0xFF
        
        # Map LIN ID to a reserved CAN ID range (0x700-0x73F for this example)
        lin_as_can_id = 0x700 + lin_id
        
        # Ensure data is maximum 7 bytes (leaving 1 byte for checksum in 8-byte CAN frame)
        if len(lin_data) > 7:
            lin_data = lin_data[:7]
            logger.warning(f"LIN data truncated to 7 bytes for ID 0x{lin_id:02X}")
        
        # Pad data to fill CAN frame
        padded_data = lin_data + [checksum] + [0x00] * (7 - len(lin_data))
        
        # Cache this LIN message for potential responses
        self.lin_message_cache[lin_id] = {
            'data': lin_data,
            'timestamp': time.time()
        }
        
        try:
            msg = can.Message(arbitration_id=lin_as_can_id, data=padded_data, is_extended_id=False)
            self.bus.send(msg)
            msg_desc = description or self.lin_id_descriptions.get(lin_id, "Unknown LIN message")
            logger.info(f"Sent LIN message as CAN: ID=0x{lin_id:02X} ({msg_desc}), Data={[hex(b)[2:].zfill(2) for b in lin_data]}, Checksum={hex(checksum)}")
            return True
        except can.CanError as e:
            logger.error(f"Error sending LIN message: {e}")
            return False

    def process_can_message(self, msg):
        """Process incoming CAN messages and translate to LIN when appropriate"""
        # Check if this is a LIN-as-CAN message (in the reserved ID range)
        if 0x700 <= msg.arbitration_id <= 0x73F:
            # This is a LIN message sent as CAN
            lin_id = msg.arbitration_id - 0x700
            # Extract data (excluding checksum and padding)
            data_length = 7  # Maximum LIN data length in our implementation
            for i in range(7, 0, -1):
                if msg.data[i] != 0:
                    data_length = i
                    break
            lin_data = list(msg.data[:data_length])
            
            msg_desc = self.lin_id_descriptions.get(lin_id, "Unknown LIN message")
            logger.info(f"Received LIN-over-CAN: ID=0x{lin_id:02X} ({msg_desc}), Data={[hex(b)[2:].zfill(2) for b in lin_data]}")
            
            # Process the LIN message based on its ID
            self.process_lin_message(lin_id, lin_data)
            return

        # If not a LIN message, process as regular CAN
        pgn_mask = 0x1FFFFF
        source_mask = 0xFF
        
        request = msg.arbitration_id
        requested_pgn = (request >> 8) & pgn_mask
        source_address = request & source_mask
        
        pgn_desc = self.pgn_descriptions.get(requested_pgn, "Unknown PGN")
        logger.info(f"Received CAN message: PGN={requested_pgn} ({pgn_desc}), Source={source_address}, Data={[hex(b)[2:].zfill(2) for b in msg.data]}")
        
        # Special handling for specific PGNs that require LIN data
        self.process_pgn_request(requested_pgn, source_address)
        
        # Process standard PGN response
        try:
            # Generate XML from CSV for parameter lookup
            xml_generator = CSVToXMLGenerator()
            xml_generator.generate_xml('FinalCSV.csv', 'updated_formula.xml')
            
            # Parse XML and JSON data
            parser = DataParser()
            spn_data = parser.parse_xml('updated_formula.xml')
            json_data = parser.load_json('final_json.json')
            
            # Generate data frames
            Data_frame_generator = DataFrameGenerator()
            Data_frames = Data_frame_generator.get_data_frame(spn_data, json_data, requested_pgn)
            
            # Send appropriate CAN responses
            for frame in Data_frames:
                pgn, frame_num, data_frame = frame
                if str(pgn) == str(requested_pgn):
                    byte_array = bytes.fromhex(data_frame)
                    generatecanid = CANFrameGenerator()
                    can_id = generatecanid.calculate_can_id(pgn, 6, source_address)
                    response_msg = can.Message(arbitration_id=can_id, data=byte_array)
                    self.bus.send(response_msg)
                    logger.info(f"Sent CAN response for PGN: {pgn}")
        except Exception as e:
            logger.error(f"Error processing PGN {requested_pgn}: {e}")

    def process_lin_message(self, lin_id, lin_data):
        """Process incoming LIN messages received over CAN"""
        # Example: Process LIN messages based on ID
        if lin_id == 0x11:  # Door lock status
            lock_status = "Locked" if lin_data[0] > 0 else "Unlocked"
            logger.info(f"Door status updated: {lock_status}")
            
            # You might want to forward this status to other systems via CAN
            # self.send_door_status_as_can(lock_status)
        
        elif lin_id == 0x12:  # Engine temperature sensor
            temp = lin_data[0] - 40  # Example conversion
            logger.info(f"Engine temperature received via LIN: {temp}°C")
        
        elif lin_id == 0x22:  # Climate control
            ac_on = bool(lin_data[0] & 0x01)
            fan_speed = (lin_data[0] >> 1) & 0x07
            temperature = lin_data[1]
            logger.info(f"Climate control: AC={'ON' if ac_on else 'OFF'}, Fan={fan_speed}, Temp={temperature}")

    def process_pgn_request(self, pgn, source_address):
        """Handle specific PGN requests that might need LIN data"""
        pgn_desc = self.pgn_descriptions.get(pgn, "Unknown PGN")
        logger.info(f"Processing PGN request: {pgn} ({pgn_desc})")
        
        # Map specific PGNs to LIN responses
        if pgn == 65108:  # Engine Temperature 
            # Simulate getting engine temperature from LIN sensor
            self.send_lin_as_can(0x12, [0x55, 0x23], "Engine Temperature Sensor Response")
            logger.info("Sent engine temperature data from LIN sensor")
            
        elif pgn == 61444:  # Electronic Engine Controller
            # Simulate getting engine controller data from LIN
            self.send_lin_as_can(0x13, [0x12, 0x34, 0x56, 0x78], "Engine Controller Status")
            logger.info("Sent engine controller data from LIN network")
            
        elif pgn == 65267:  # Vehicle Position
            # Simulate getting vehicle position data
            self.send_lin_as_can(0x33, [0x42, 0x17, 0x80], "Seat Position Sensor")
            logger.info("Sent vehicle position data from LIN sensors")

    def main_loop(self):
        """Main processing loop"""
        try:
            logger.info("Waiting for CAN messages...")
            msg = self.bus.recv(1)  # 1 second timeout
            if msg:
                self.process_can_message(msg)
                
            # Periodic tasks - simulate some regular LIN sensor updates
            current_time = time.time()
            if not hasattr(self, 'last_lin_update') or current_time - self.last_lin_update > 5:
                # Every 5 seconds, simulate a LIN sensor update
                self.send_lin_as_can(0x14, [0x30], "Window Position Periodic Update")
                self.last_lin_update = current_time
                
        except can.CanError as e:
            logger.error(f"CAN error: {e}")
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            self.cleanup()
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            
        return True

    def cleanup(self):
        """Clean up resources when shutting down"""
        if hasattr(self, 'bus'):
            self.bus.shutdown()
        logger.info("CAN bus interface shutdown")

if __name__ == "__main__":
    gateway = LINCANGateway()
    try:
        logger.info("Starting LIN-CAN Gateway")
        while True:
            if not gateway.main_loop():
                break
            time.sleep(0.01)  # Small delay to prevent CPU hogging
    except KeyboardInterrupt:
        logger.info("Program terminated by user")
    finally:
        gateway.cleanup()