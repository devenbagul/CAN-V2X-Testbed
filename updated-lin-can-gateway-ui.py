#!/usr/bin/env python3
"""
LIN-CAN Gateway UI Application
------------------------------
Integrates the LIN-CAN gateway, sender, and J1939 decoder capabilities
into a single graphical user interface.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import can
import os
import time
import threading
import csv
import logging
from collections import defaultdict
import sys
import traceback
import queue

# Configure logging to display in UI as well as files
class UILogHandler(logging.Handler):
    def __init__(self, log_widget):
        super().__init__()
        self.log_widget = log_widget
        self.formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    def emit(self, record):
        log_entry = self.formatter.format(record)
        self.log_widget.after(0, self._append_log, log_entry)

    def _append_log(self, message):
        self.log_widget.configure(state='normal')
        self.log_widget.insert(tk.END, message + '\n')
        self.log_widget.see(tk.END)
        self.log_widget.configure(state='disabled')

class CANDecoder:
    """J1939 CAN message decoder class"""
    def __init__(self, csv_path=None):
        self.spn_data = defaultdict(dict)
        if csv_path:
            self.load_csv(csv_path)
        
        # LIN message ID to description mapping
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

    def load_csv(self, csv_path):
        """Load SPN definitions from CSV file"""
        try:
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    pgn = int(row['PGN'])
                    spn = int(row['SPN'])
                    self.spn_data[pgn][spn] = {
                        'start_bit': float(row['Start Bit']),
                        'length': int(row['Length']),
                        'resolution': float(row['Resolution']),
                        'offset': float(row['Offset']),
                        'min': float(row['Min']),
                        'max': float(row['Max']),
                        'description': row['Description'],
                        'is_signed': float(row['Min']) < 0  # Determine if signed
                    }
            logging.info(f"Loaded {sum(len(spns) for spns in self.spn_data.values())} SPNs from {csv_path}")
        except Exception as e:
            logging.error(f"Failed to load CSV: {e}")
            raise

    def extract_j1939_fields(self, arbitration_id):
        """Extract J1939 fields from CAN arbitration ID"""
        priority = (arbitration_id >> 26) & 0x7
        extended_data_page = (arbitration_id >> 25) & 0x1
        data_page = (arbitration_id >> 24) & 0x1
        pdu_format = (arbitration_id >> 16) & 0xFF
        pdu_specific = (arbitration_id >> 8) & 0xFF
        source_address = arbitration_id & 0xFF
        
        if pdu_format < 240:
            # PDU1 format - destination specific
            pgn = (extended_data_page << 17) | (data_page << 16) | (pdu_format << 8)
            dest_address = pdu_specific
        else:
            # PDU2 format - broadcast message
            pgn = (extended_data_page << 17) | (data_page << 16) | (pdu_format << 8) | pdu_specific
            dest_address = 0xFF  # Broadcast
        
        return {
            'pgn': pgn,
            'priority': priority,
            'source_address': source_address,
            'destination_address': dest_address
        }

    def decode_frame(self, can_id, data):
        """Decode a CAN frame using loaded SPN definitions"""
        fields = self.extract_j1939_fields(can_id)
        pgn = fields['pgn']
        
        # Check if this is a LIN-over-CAN message (in the reserved ID range)
        if 0x700 <= can_id <= 0x73F and not can_id & 0x80000000:  # Non-extended IDs
            lin_id = can_id - 0x700
            # Extract data (excluding checksum and padding)
            data_length = min(7, len(data))  # Maximum LIN data length
            for i in range(min(7, len(data)-1), 0, -1):
                if data[i] != 0:
                    data_length = i + 1  # Fixed: add +1 to include the non-zero byte
                    break
            lin_data = list(data[:data_length])
            
            msg_desc = self.lin_id_descriptions.get(lin_id, "Unknown LIN message")
            return [{
                'type': 'LIN',
                'id': lin_id,
                'description': msg_desc,
                'data': lin_data,
                'raw_value': None,
                'value': None,
                'unit': None
            }]
        
        # Regular J1939 message
        if pgn not in self.spn_data:
            pgn_desc = self.pgn_descriptions.get(pgn, "Unknown PGN")
            return [{
                'type': 'J1939',
                'pgn': pgn,
                'description': pgn_desc,
                'raw_value': None,
                'value': None,
                'unit': None
            }]
        
        # Convert bytes to binary string (little-endian within byte, big-endian byte order)
        if isinstance(data, str):
            # If data is a hex string
            data_bytes = bytes.fromhex(data)
        else:
            # If data is already bytes
            data_bytes = data
            
        binary_str = ''.join(f"{byte:08b}" for byte in data_bytes)
        
        decoded = []
        for spn, info in self.spn_data[pgn].items():
            try:
                # Convert start bit notation (e.g., 1.1 to byte 0, bit 0)
                byte_pos = int(info['start_bit']) // 8
                bit_pos = int(info['start_bit'] % 8)
                start_bit = byte_pos * 8 + (7 - bit_pos)  # Big-endian bit order
                
                # Extract bits
                bits = binary_str[start_bit:start_bit + info['length']]
                if len(bits) < info['length']:
                    continue
                
                # Convert to integer (handle signed)
                raw_value = int(bits, 2)
                if info['is_signed']:
                    max_val = (1 << (info['length'] - 1)) - 1
                    if raw_value > max_val:
                        raw_value -= (1 << info['length'])
                
                # Apply scaling and offset
                scaled_value = raw_value * info['resolution'] + info['offset']
                
                # Validate range
                if not (info['min'] <= scaled_value <= info['max']):
                    continue
                
                # Extract unit from description if available
                parts = info['description'].split()
                unit = parts[-1] if len(parts) > 1 and parts[-1].startswith('(') and parts[-1].endswith(')') else ''
                
                decoded.append({
                    'type': 'J1939',
                    'pgn': pgn,
                    'spn': spn,
                    'description': info['description'],
                    'raw_value': raw_value,
                    'value': scaled_value,
                    'unit': unit
                })
            except Exception as e:
                logging.debug(f"Error decoding SPN {spn}: {e}")
                continue
                
        return decoded if decoded else [{
            'type': 'J1939',
            'pgn': pgn,
            'description': self.pgn_descriptions.get(pgn, "Unknown PGN"),
            'raw_value': None,
            'value': None,
            'unit': None
        }]


class LINCANGateway:
    """LIN-CAN Gateway class - handles translation between LIN and CAN protocols"""
    def __init__(self, decoder=None, message_callback=None):
        """Initialize the LIN-CAN Gateway"""
        self.decoder = decoder
        self.message_callback = message_callback
        self.bus = None
        self.running = False
        self.processing_thread = None
        self.message_queue = queue.Queue()  # Added message queue for thread safety
            
        # LIN message ID to description mapping
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
    
    def start(self, interface='can0', bitrate=125000):
        """Start the LIN-CAN Gateway on specified interface"""
        if self.running:
            return False
            
        try:
            # Setup CAN interface using a background thread to avoid UI freezing
            threading.Thread(target=self._setup_can_interface, 
                            args=(interface, bitrate), 
                            daemon=True).start()
            return True
        except Exception as e:
            logging.error(f"Failed to initialize CAN bus: {e}")
            return False
    
    def _setup_can_interface(self, interface, bitrate):
        """Setup CAN interface in a background thread"""
        try:
            # Setup CAN interface
            os.system(f"sudo ip link set {interface} down")
            os.system(f"sudo ip link set {interface} up type can bitrate {bitrate}")
            logging.info(f"CAN interface {interface} configured at {bitrate}bps")
            
            self.bus = can.interface.Bus(channel=interface, interface='socketcan')
            logging.info("Connected to CAN bus successfully")
            
            self.running = True
            self.processing_thread = threading.Thread(target=self.main_loop, daemon=True)
            self.processing_thread.start()
        except Exception as e:
            logging.error(f"Failed to initialize CAN bus: {e}")
            # Update status in UI thread
            if self.message_callback:
                self.message_queue.put({
                    'type': 'status',
                    'status': 'error',
                    'message': f"Failed to initialize CAN bus: {e}",
                    'timestamp': time.time()
                })
    
    def stop(self):
        """Stop the LIN-CAN Gateway"""
        self.running = False
        if self.processing_thread:
            self.processing_thread.join(timeout=1.0)
        self.cleanup()
    
    def send_lin_as_can(self, lin_id, lin_data, description=None):
        """
        Translate a LIN message to CAN format and send it
        
        Args:
            lin_id (int): LIN identifier (0-63)
            lin_data (list): Data bytes for the LIN message
            description (str, optional): Human-readable description of what this message represents
        """
        if not self.running or not self.bus:
            logging.warning("Cannot send LIN message: Gateway not running")
            return False
            
        if lin_id > 63:
            logging.warning(f"Invalid LIN ID: {lin_id}. Must be 0-63.")
            return False
            
        # Calculate LIN checksum (simple sum for demonstration)
        checksum = sum(lin_data) & 0xFF
        
        # Map LIN ID to a reserved CAN ID range (0x700-0x73F for this example)
        lin_as_can_id = 0x700 + lin_id
        
        # Ensure data is maximum 7 bytes (leaving 1 byte for checksum in 8-byte CAN frame)
        if len(lin_data) > 7:
            lin_data = lin_data[:7]
            logging.warning(f"LIN data truncated to 7 bytes for ID 0x{lin_id:02X}")
        
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
            logging.info(f"Sent LIN message as CAN: ID=0x{lin_id:02X} ({msg_desc}), Data={[hex(b)[2:].zfill(2) for b in lin_data]}, Checksum={hex(checksum)}")
            
            # Notify via callback - using message queue for thread safety
            if self.message_callback:
                self.message_queue.put({
                    'direction': 'TX',
                    'type': 'LIN',
                    'id': lin_id,
                    'description': msg_desc,
                    'data': lin_data.copy(),
                    'timestamp': time.time()
                })
            return True
        except can.CanError as e:
            logging.error(f"Error sending LIN message: {e}")
            return False

    def send_pgn_request(self, pgn, source_address=0xFE, destination=0xFF):
        """
        Send a J1939 PGN request
        
        Args:
            pgn (int): Parameter Group Number to request
            source_address (int): Source address for this request
            destination (int): Destination address or 0xFF for broadcast
        """
        if not self.running or not self.bus:
            logging.warning("Cannot send PGN request: Gateway not running")
            return False
            
        priority = 6  # Default priority for requests
        
        # Check if this is PDU1 or PDU2 format
        pdu_format = (pgn >> 8) & 0xFF
        
        if pdu_format < 240:
            # PDU1 format - destination specific
            pdu_specific = destination
            can_id = (priority << 26) | (pgn << 8) | source_address
        else:
            # PDU2 format - broadcast
            pdu_specific = pgn & 0xFF
            can_id = (priority << 26) | (pgn << 8) | source_address
        
        try:
            # Request message with standard data
            msg = can.Message(arbitration_id=can_id, data=[0xFF, 0xFF, 0xFF], is_extended_id=True)
            self.bus.send(msg)
            
            pgn_desc = self.pgn_descriptions.get(pgn, "Unknown PGN")
            logging.info(f"Sent J1939 PGN request: PGN={pgn} ({pgn_desc}), Source={source_address}")
            
            # Notify via callback - using message queue for thread safety
            if self.message_callback:
                self.message_queue.put({
                    'direction': 'TX',
                    'type': 'J1939',
                    'pgn': pgn,
                    'priority': priority,
                    'source': source_address,
                    'destination': destination,
                    'description': f"Request for {pgn_desc}",
                    'data': [0xFF, 0xFF, 0xFF],
                    'timestamp': time.time()
                })
            return True
        except can.CanError as e:
            logging.error(f"Error sending PGN request: {e}")
            return False

    def process_can_message(self, msg):
        """Process incoming CAN messages and translate to LIN when appropriate"""
        # Check if this is a LIN-as-CAN message (in the reserved ID range)
        if 0x700 <= msg.arbitration_id <= 0x73F and not msg.is_extended_id:
            # This is a LIN message sent as CAN
            lin_id = msg.arbitration_id - 0x700
            # Extract data (excluding checksum and padding)
            data_length = 7  # Maximum LIN data length in our implementation
            for i in range(7, 0, -1):
                if i < len(msg.data) and msg.data[i] != 0:
                    data_length = i + 1  # Fixed: add +1 to include the non-zero byte
                    break
            lin_data = list(msg.data[:data_length])
            
            msg_desc = self.lin_id_descriptions.get(lin_id, "Unknown LIN message")
            logging.info(f"Received LIN-over-CAN: ID=0x{lin_id:02X} ({msg_desc}), Data={[hex(b)[2:].zfill(2) for b in lin_data]}")
            
            # Notify via callback - using message queue for thread safety
            if self.message_callback:
                self.message_queue.put({
                    'direction': 'RX',
                    'type': 'LIN',
                    'id': lin_id,
                    'description': msg_desc,
                    'data': lin_data.copy(),
                    'timestamp': msg.timestamp if hasattr(msg, 'timestamp') else time.time()
                })
            
            # Process the LIN message based on its ID
            self.process_lin_message(lin_id, lin_data)
            return

        # If not a LIN message, process as regular CAN/J1939
        if self.decoder:
            fields = self.decoder.extract_j1939_fields(msg.arbitration_id)
            pgn = fields['pgn']
            source_address = fields['source_address']
            
            pgn_desc = self.pgn_descriptions.get(pgn, "Unknown PGN")
            logging.info(f"Received CAN message: PGN={pgn} ({pgn_desc}), Source={source_address}, Data={[hex(b)[2:].zfill(2) for b in msg.data]}")
            
            # Decode the message
            decoded = self.decoder.decode_frame(msg.arbitration_id, msg.data)
            
            # Notify via callback - using message queue for thread safety
            if self.message_callback:
                self.message_queue.put({
                    'direction': 'RX',
                    'type': 'J1939',
                    'pgn': pgn,
                    'priority': fields['priority'],
                    'source': source_address,
                    'destination': fields['destination_address'],
                    'description': pgn_desc,
                    'data': list(msg.data),
                    'decoded': decoded,
                    'timestamp': msg.timestamp if hasattr(msg, 'timestamp') else time.time()
                })
            
            # Special handling for specific PGNs that require LIN data
            self.process_pgn_request(pgn, source_address)

    def process_lin_message(self, lin_id, lin_data):
        """Process incoming LIN messages received over CAN"""
        # Example: Process LIN messages based on ID
        if lin_id == 0x11:  # Door lock status
            lock_status = "Locked" if lin_data[0] > 0 else "Unlocked"
            logging.info(f"Door status updated: {lock_status}")
            
            # You might want to forward this status to other systems via CAN
            # Example: Translate to J1939 message
            self.send_door_status_as_j1939(lock_status == "Locked")
        
        elif lin_id == 0x12:  # Engine temperature sensor
            temp = lin_data[0] - 40  # Example conversion
            logging.info(f"Engine temperature received via LIN: {temp}°C")
            
            # Forward to J1939 bus with proper PGN
            self.send_engine_temp_as_j1939(temp)
        
        elif lin_id == 0x22:  # Climate control
            ac_on = bool(lin_data[0] & 0x01)
            fan_speed = (lin_data[0] >> 1) & 0x07
            temperature = lin_data[1]
            logging.info(f"Climate control: AC={'ON' if ac_on else 'OFF'}, Fan={fan_speed}, Temp={temperature}")

    def send_door_status_as_j1939(self, is_locked):
        """Example: Convert door lock status from LIN to J1939"""
        if not self.bus:
            return
            
        # Example PGN for door status (made up for demonstration)
        pgn = 65280  # Proprietary PGN
        priority = 6
        source_address = 0x10  # Example source address
        
        can_id = (priority << 26) | (pgn << 8) | source_address
        data = [0x01 if is_locked else 0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]
        
        try:
            msg = can.Message(arbitration_id=can_id, data=data, is_extended_id=True)
            self.bus.send(msg)
            logging.info(f"Sent door status as J1939: {'Locked' if is_locked else 'Unlocked'}")
        except can.CanError as e:
            logging.error(f"Error sending door status: {e}")

    def send_engine_temp_as_j1939(self, temperature):
        """Example: Convert engine temperature from LIN to J1939"""
        if not self.bus:
            return
            
        # PGN for engine temperature
        pgn = 65262  # Engine coolant temperature
        priority = 6
        source_address = 0x10  # Example source address
        
        can_id = (priority << 26) | (pgn << 8) | source_address
        
        # J1939 format: Engine coolant temp in first byte with 1C resolution, -40C offset
        temp_value = int(temperature + 40) & 0xFF
        data = [temp_value, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]
        
        try:
            msg = can.Message(arbitration_id=can_id, data=data, is_extended_id=True)
            self.bus.send(msg)
            logging.info(f"Sent engine temperature as J1939: {temperature}°C")
        except can.CanError as e:
            logging.error(f"Error sending engine temperature: {e}")

    def process_pgn_request(self, pgn, source_address):
        """Handle specific PGN requests that might need LIN data"""
        pgn_desc = self.pgn_descriptions.get(pgn, "Unknown PGN")
        logging.info(f"Processing PGN request: {pgn} ({pgn_desc})")
        
        # Map specific PGNs to LIN responses
        if pgn == 65108:  # Engine Temperature
            # Simulate getting engine temperature from LIN sensor
            self.send_lin_as_can(0x12, [0x55, 0x23], "Engine Temperature Sensor Response")
            logging.info("Sent engine temperature data from LIN sensor")
            
        elif pgn == 61444:  # Electronic Engine Controller
            # Simulate getting engine controller data from LIN
            self.send_lin_as_can(0x13, [0x12, 0x34, 0x56, 0x78], "Engine Controller Status")
            logging.info("Sent engine controller data from LIN network")
            
        elif pgn == 65267:  # Vehicle Position
            # Simulate getting vehicle position data
            self.send_lin_as_can(0x33, [0x42, 0x17, 0x80], "Seat Position Sensor")
            logging.info("Sent vehicle position data from LIN sensors")

    def main_loop(self):
        """Main processing loop"""
        last_lin_update = 0
        message_processing_time = 0
        error_count = 0
        error_threshold = 5  # Maximum consecutive errors before recovery
        
        while self.running:
            try:
                # Process messages from the queue for UI updates (non-blocking)
                while not self.message_queue.empty() and self.message_callback:
                    msg = self.message_queue.get_nowait()
                    if msg:
                        self.message_callback(msg)
                
                # Receive CAN messages
                msg = self.bus.recv(timeout=0.5)  # 0.5 second timeout
                if msg:
                    self.process_can_message(msg)
                    message_processing_time = time.time()
                    error_count = 0  # Reset error counter on successful message
                    
                # Periodic tasks - simulate some regular LIN sensor updates
                current_time = time.time()
                if current_time - last_lin_update > 5:
                    # Every 5 seconds, simulate a LIN sensor update
                    self.send_lin_as_can(0x14, [0x30], "Window Position Periodic Update")
                    last_lin_update = current_time
                    
                # Check if we haven't processed a message in a while
                if current_time - message_processing_time > 30:
                    logging.warning("No CAN messages received for 30 seconds")
                    
            except can.CanError as e:
                logging.error(f"CAN error: {e}")
                error_count += 1
                if error_count > error_threshold:
                    logging.error("Too many consecutive CAN errors, attempting recovery")
                    try:
                        self.cleanup()
                        time.sleep(1)
                        # Try to reestablish the bus
                        interface = self.bus.channel
                        self.bus = can.interface.Bus(channel=interface, interface='socketcan')
                        logging.info(f"CAN interface {interface} recovered")
                        error_count = 0
                    except Exception as recovery_error:
                        logging.error(f"Recovery failed: {recovery_error}")
            except Exception as e:
                logging.error(f"Unexpected error in main loop: {e}")
                logging.error(traceback.format_exc())
                error_count += 1
                
            time.sleep(0.01)  # Small delay to prevent CPU hogging

    def cleanup(self):
        """Clean up resources when shutting down"""
        if hasattr(self, 'bus') and self.bus:
            try:
                self.bus.shutdown()
            except:
                pass
            self.bus = None
        logging.info("CAN bus interface shutdown")


class LINCANGatewayApp:
    """Main application class for the LIN-CAN Gateway UI"""
    def __init__(self, root):
        self.root = root
        self.root.title("LIN-CAN Gateway Interface")
        self.root.geometry("1280x800")
        
        # Setup member variables
        self.gateway = None
        self.decoder = None
        self.pgn_list = []
        self.lin_messages = {}
        
        # Set up UI refresh timer
        self.message_queue = queue.Queue()
        
        # Configure logging
        self.setup_logging()
        
        # Create the UI
        self.create_widgets()
        
        # Configure application shutdown handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Start the UI update timer
        self.root.after(100, self.process_message_queue)
        
        # Load configuration if available
        self.load_config()
    
    def setup_logging(self):
        """Set up the logging handlers for the application"""
        # Configure root logger
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler("lin_can_gateway_ui.log"),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def create_widgets(self):
        """Create all the UI widgets"""
        # Create notebook for tabbed interface
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create tabs
        self.gateway_tab = ttk.Frame(self.notebook)
        self.sender_tab = ttk.Frame(self.notebook)
        self.decoder_tab = ttk.Frame(self.notebook)
        self.log_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.gateway_tab, text="Gateway Control")
        self.notebook.add(self.sender_tab, text="Send Messages")
        self.notebook.add(self.decoder_tab, text="J1939 Decoder")
        self.notebook.add(self.log_tab, text="Logs")
        
        # Create widgets for each tab
        self.create_gateway_tab()
        self.create_sender_tab()
        self.create_decoder_tab()
        self.create_log_tab()
        
        # Bottom status bar
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN).pack(fill=tk.X, padx=5, pady=2)
    
    def create_gateway_tab(self):
        """Create widgets for the Gateway Control tab"""
        # Top control frame
        control_frame = ttk.LabelFrame(self.gateway_tab, text="Gateway Configuration", padding=10)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # CAN interface selection
        ttk.Label(control_frame, text="CAN Interface:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.interface_var = tk.StringVar(value="can0")
        
        # Check for available interfaces
        # Check for available interfaces
        interfaces = self.get_available_interfaces()
        if interfaces:
            self.interface_combo = ttk.Combobox(control_frame, textvariable=self.interface_var, values=interfaces)
        else:
            self.interface_combo = ttk.Combobox(control_frame, textvariable=self.interface_var, values=["can0", "can1", "vcan0"])
        self.interface_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Bitrate selection
        ttk.Label(control_frame, text="Bitrate:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        self.bitrate_var = tk.IntVar(value=125000)
        bitrate_combo = ttk.Combobox(control_frame, textvariable=self.bitrate_var, 
                                      values=[125000, 250000, 500000, 1000000])
        bitrate_combo.grid(row=0, column=3, sticky=tk.W, padx=5, pady=5)
        
        # CSV file for SPN definitions
        ttk.Label(control_frame, text="SPN Definitions:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.csv_path_var = tk.StringVar()
        ttk.Entry(control_frame, textvariable=self.csv_path_var, width=40).grid(row=1, column=1, columnspan=2, sticky=tk.W+tk.E, padx=5, pady=5)
        ttk.Button(control_frame, text="Browse...", command=self.select_csv_file).grid(row=1, column=3, sticky=tk.W, padx=5, pady=5)
        
        # Start/Stop buttons
        button_frame = ttk.Frame(control_frame)
        button_frame.grid(row=2, column=0, columnspan=4, pady=10)
        
        self.start_button = ttk.Button(button_frame, text="Start Gateway", command=self.start_gateway)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="Stop Gateway", command=self.stop_gateway, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # Gateway status
        self.status_frame = ttk.LabelFrame(self.gateway_tab, text="Gateway Status", padding=10)
        self.status_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Status indicators
        ttk.Label(self.status_frame, text="CAN Bus:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.can_status_var = tk.StringVar(value="Disconnected")
        ttk.Label(self.status_frame, textvariable=self.can_status_var).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(self.status_frame, text="Messages Received:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        self.rx_count_var = tk.IntVar(value=0)
        ttk.Label(self.status_frame, textvariable=self.rx_count_var).grid(row=0, column=3, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(self.status_frame, text="Messages Sent:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.tx_count_var = tk.IntVar(value=0)
        ttk.Label(self.status_frame, textvariable=self.tx_count_var).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(self.status_frame, text="Last Message:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        self.last_msg_var = tk.StringVar(value="None")
        ttk.Label(self.status_frame, textvariable=self.last_msg_var).grid(row=1, column=3, sticky=tk.W, padx=5, pady=5)
        
        # Message view with tree
        msg_frame = ttk.LabelFrame(self.gateway_tab, text="Message Traffic", padding=10)
        msg_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create tree view for messages
        cols = ("Direction", "Type", "ID", "Description", "Data", "Timestamp")
        self.msg_tree = ttk.Treeview(msg_frame, columns=cols, show="headings")
        
        # Configure columns
        for col in cols:
            self.msg_tree.heading(col, text=col)
            if col == "Data":
                self.msg_tree.column(col, width=250)
            elif col == "Description":
                self.msg_tree.column(col, width=200)
            else:
                self.msg_tree.column(col, width=100)
        
        # Add scrollbars
        vsb = ttk.Scrollbar(msg_frame, orient="vertical", command=self.msg_tree.yview)
        hsb = ttk.Scrollbar(msg_frame, orient="horizontal", command=self.msg_tree.xview)
        self.msg_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Pack scrollbars and tree
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.msg_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Add a simple context menu for tree items
        self.create_tree_context_menu(self.msg_tree)

    def get_available_interfaces(self):
        """Get list of available CAN interfaces on the system"""
        interfaces = []
        try:
            # Check for standard CAN interfaces
            with open('/proc/net/can/dev_list', 'r') as f:
                for line in f:
                    if 'can' in line:
                        interface = line.split()[0]
                        interfaces.append(interface)
        except FileNotFoundError:
            # Try another method for listing interfaces
            try:
                import subprocess
                output = subprocess.check_output(['ip', '-details', 'link', 'show']).decode('utf-8')
                for line in output.split('\n'):
                    if 'can' in line and '<' in line and '>' in line:
                        interface = line.split(':')[1].strip()
                        interfaces.append(interface)
            except:
                logging.warning("Could not detect CAN interfaces automatically")
                pass
        
        return interfaces

    def create_tree_context_menu(self, tree):
        """Create context menu for tree views"""
        self.context_menu = tk.Menu(tree, tearoff=0)
        self.context_menu.add_command(label="Copy Selected", command=self.copy_selected_message)
        self.context_menu.add_command(label="Export Selected...", command=self.export_selected_messages)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Clear All", command=self.clear_tree)
        
        tree.bind("<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        """Show context menu on right-click"""
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def copy_selected_message(self):
        """Copy selected message to clipboard"""
        selected = self.msg_tree.selection()
        if selected:
            values = self.msg_tree.item(selected[0], 'values')
            text = "\t".join(str(v) for v in values)
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.status_var.set("Copied message to clipboard")

    def export_selected_messages(self):
        """Export selected messages to a CSV file"""
        selected = self.msg_tree.selection()
        if not selected:
            messagebox.showinfo("Export", "No messages selected")
            return
            
        filename = filedialog.asksaveasfilename(defaultextension=".csv",
                                                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not filename:
            return
            
        try:
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                # Write header
                cols = self.msg_tree.configure()['columns'][-1]
                writer.writerow(cols)
                
                # Write selected rows
                for item in selected:
                    values = self.msg_tree.item(item, 'values')
                    writer.writerow(values)
                
            self.status_var.set(f"Exported {len(selected)} messages to {filename}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Error exporting messages: {e}")

    def clear_tree(self):
        """Clear all messages from the tree view"""
        for item in self.msg_tree.get_children():
            self.msg_tree.delete(item)
        self.status_var.set("Message view cleared")

class LINCANGatewayUI:
    """Main UI Application"""
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("LIN-CAN Gateway")
        self.root.geometry("800x600")
        
        # Create main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Gateway tab
        gateway_frame = ttk.Frame(notebook)
        notebook.add(gateway_frame, text="Gateway")
        
        # Add some basic controls
        ttk.Label(gateway_frame, text="LIN-CAN Gateway Interface").pack(pady=10)
        ttk.Button(gateway_frame, text="Start Gateway").pack(pady=5)
        ttk.Button(gateway_frame, text="Stop Gateway").pack(pady=5)
        
        # Message display
        ttk.Label(gateway_frame, text="Messages:").pack(anchor=tk.W, pady=(20,5))
        self.message_text = scrolledtext.ScrolledText(gateway_frame, height=15)
        self.message_text.pack(fill=tk.BOTH, expand=True)
        
    def run(self):
        """Start the UI application"""
        self.root.mainloop()

if __name__ == "__main__":
    app = LINCANGatewayUI()
    app.run()