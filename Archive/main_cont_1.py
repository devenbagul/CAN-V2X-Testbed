import can
import os
import time

# Cross-platform CAN setup
import platform
system = platform.system().lower()
print(f"Setting up CAN interface on {system}...")

class Main:
    def __init__(self, interface='auto'):
        self.bus = None
        self.connect_to_can(interface)
    
    def connect_to_can(self, interface='auto'):
        """Connect to CAN interface with auto-detection"""
        if interface == 'auto':
            # Auto-detect best interface
            if system == 'linux':
                interface = 'vcan0'  # Prefer Linux virtual CAN
            else:
                interface = 'virtual'  # Use python-can virtual on Windows
        
        try:
            if interface in ['can0', 'can1'] and system == 'linux':
                # Real CAN interface on Linux
                os.system(f"sudo ip link set {interface} down")
                os.system(f"sudo ip link set {interface} up type can bitrate 125000")
                self.bus = can.interface.Bus(channel=interface, interface='socketcan')
                print(f"Connected to real CAN interface: {interface}")
                
            elif interface in ['vcan0', 'vcan1'] and system == 'linux':
                # Linux virtual CAN
                os.system("sudo modprobe vcan")
                os.system(f"sudo ip link add dev {interface} type vcan 2>/dev/null")
                os.system(f"sudo ip link set up {interface}")
                self.bus = can.interface.Bus(channel=interface, interface='socketcan')
                print(f"Connected to Linux virtual CAN: {interface}")
                
            else:
                # Python-can virtual interface (cross-platform)
                self.bus = can.interface.Bus(interface='virtual')
                print(f"Connected to python-can virtual interface")
                
        except Exception as e:
            print(f"Failed to connect to {interface}: {e}")
            # Fallback to virtual interface
            try:
                self.bus = can.interface.Bus(interface='virtual')
                print("Connected using fallback virtual interface")
            except Exception as e2:
                print(f"All connection methods failed: {e2}")
                raise
        
    def send_lin_as_can(self, lin_id, lin_data):
        """Translate a LIN message to CAN format and send it"""
        # LIN to CAN translation logic
        # For a real implementation, you might need to:
        # 1. Map LIN IDs to appropriate CAN IDs
        # 2. Add necessary headers/metadata
        # 3. Handle checksum/parity differences
        
        arbitration_id = 0x300 + lin_id  # Example: Map LIN ID to CAN ID range starting at 0x300
        data = bytes(lin_data)
        
        try:
            msg = can.Message(arbitration_id=arbitration_id, data=data)
            self.bus.send(msg)
            print(f"LIN message translated and sent as CAN frame: ID {hex(arbitration_id)}, data {data.hex()}")
            return True
        except Exception as e:
            print(f"Error sending translated LIN message: {e}")
            return False

    def process_can_message(self, msg):
        pgn_mask = 0x1FFFFF
        source_mask = 0xFF
        
        request = msg.arbitration_id
        requested_pgn = (request >> 8) & pgn_mask
        source_address = request & source_mask
        
        print(f"Received message with PGN: {requested_pgn}, source: {source_address}")
        
        # Example: Process specific PGNs that might require LIN responses
        if requested_pgn == 0x1234:  # Example PGN
            # This might be a request that requires LIN data
            lin_id = 0x12
            lin_data = [0x11, 0x22, 0x33]  # In a real implementation, this would come from actual LIN data
            self.send_lin_as_can(lin_id, lin_data)
        
        # Then process your regular CAN response logic
        try:
            # Call your existing data processing functions
            xml_generator = CSVToXMLGenerator()
            xml_generator.generate_xml('FinalCSV.csv', 'updated_formula.xml')
            
            parser = DataParser()
            spn_data = parser.parse_xml('updated_formula.xml')
            json_data = parser.load_json('final_json.json')
            
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
                    print(f"Response sent for PGN: {pgn}")
        except Exception as e:
            print(f"Error processing message: {e}")

    def main(self):
        try:
            print("Waiting for CAN messages...")
            msg = self.bus.recv(1)  # 1 second timeout
            if msg:
                self.process_can_message(msg)
        except can.CanError as e:
            print(f"CAN error: {e}")
        except KeyboardInterrupt:
            print("Shutting down...")
            self.bus.shutdown()
        except Exception as e:
            print(f"Unexpected error: {e}")

    def cleanup(self):
        if hasattr(self, 'bus'):
            self.bus.shutdown()
        print("CAN bus interface shutdown")

if __name__ == "__main__":
    import sys
    
    # Allow interface selection via command line
    interface = 'auto'
    if len(sys.argv) > 1:
        interface = sys.argv[1]
    
    print(f"Starting with interface: {interface}")
    main_instance = Main(interface)
    
    try:
        while True:
            main_instance.main()
            time.sleep(0.01)  # Small delay to prevent CPU hogging
    except KeyboardInterrupt:
        print("Program terminated by user")
    finally:
        main_instance.cleanup()