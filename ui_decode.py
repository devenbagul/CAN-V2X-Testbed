#!/usr/bin/env python3
"""
LIN-CAN Gateway UI Application
------------------------------
Complete implementation with decoder, gateway, and UI components
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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class UILogHandler(logging.Handler):
    """Custom log handler to display logs in UI"""
    def __init__(self, log_widget):
        super().__init__()
        self.log_widget = log_widget
        self.formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

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
        
        self.lin_id_descriptions = {
            0x11: "Door Lock Status",
            0x12: "Engine Temperature Sensor",
            0x13: "Light Status",
            0x14: "Window Position",
            0x22: "Climate Control",
            0x33: "Seat Position",
        }
        
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
                        'is_signed': float(row['Min']) < 0
                    }
            logging.info(f"Loaded {sum(len(spns) for spns in self.spn_data.values())} SPNs")
        except Exception as e:
            logging.error(f"Failed to load CSV: {e}")
            raise

    def extract_j1939_fields(self, arbitration_id):
        """Extract J1939 fields from CAN arbitration ID"""
        # Handle both extended and standard CAN IDs
        if arbitration_id > 0x7FF:  # Extended ID
            priority = (arbitration_id >> 26) & 0x7
            extended_data_page = (arbitration_id >> 25) & 0x1
            data_page = (arbitration_id >> 24) & 0x1
            pdu_format = (arbitration_id >> 16) & 0xFF
            pdu_specific = (arbitration_id >> 8) & 0xFF
            source_address = arbitration_id & 0xFF
            
            if pdu_format < 240:
                pgn = (extended_data_page << 17) | (data_page << 16) | (pdu_format << 8)
                dest_address = pdu_specific
            else:
                pgn = (extended_data_page << 17) | (data_page << 16) | (pdu_format << 8) | pdu_specific
                dest_address = 0xFF
        else:
            # For standard IDs, treat as simple PGN
            pgn = arbitration_id
            priority = 6
            source_address = 0
            dest_address = 0xFF
        
        return {
            'pgn': pgn,
            'priority': priority,
            'source_address': source_address,
            'destination_address': dest_address
        }

    def decode_frame(self, can_id, data):
        """Decode a CAN frame"""
        fields = self.extract_j1939_fields(can_id)
        pgn = fields['pgn']
        
        # Check for LIN-over-CAN message
        if 0x700 <= can_id <= 0x73F and not can_id & 0x80000000:
            lin_id = can_id - 0x700
            msg_desc = self.lin_id_descriptions.get(lin_id, "Unknown LIN message")
            
            # Decode LIN message data based on ID
            decoded_value = "Raw Data"
            unit = ""
            
            if lin_id == 0x11:  # Door Lock Status
                decoded_value = "Locked" if data[0] > 0 else "Unlocked"
                unit = "Status"
            elif lin_id == 0x12:  # Engine Temperature
                decoded_value = f"{data[0] - 40}" if len(data) > 0 else "N/A"
                unit = "°C"
            elif lin_id == 0x14:  # Window Position
                decoded_value = f"{(data[0] * 100) // 255}" if len(data) > 0 else "N/A"
                unit = "% Open"
            elif lin_id == 0x22:  # Climate Control
                decoded_value = f"AC: {'ON' if data[0] & 1 else 'OFF'}" if len(data) > 0 else "N/A"
                unit = "Status"
            else:
                decoded_value = " ".join(f"{b:02X}" for b in data[:4])
                unit = "Hex"
            
            return [{
                'type': 'LIN',
                'id': lin_id,
                'description': msg_desc,
                'data': list(data),
                'raw_value': data[0] if len(data) > 0 else 0,
                'value': decoded_value,
                'unit': unit
            }]
        
        # Try to decode using SPN data if available
        if pgn in self.spn_data:
            decoded = []
            for spn, info in self.spn_data[pgn].items():
                try:
                    # Simple decoding for demonstration
                    if len(data) >= 2:
                        raw_value = data[0] + (data[1] << 8)
                        scaled_value = raw_value * info['resolution'] + info['offset']
                        
                        if info['min'] <= scaled_value <= info['max']:
                            decoded.append({
                                'type': 'J1939',
                                'pgn': pgn,
                                'spn': spn,
                                'description': info['description'],
                                'raw_value': raw_value,
                                'value': scaled_value,
                                'unit': ''
                            })
                except Exception:
                    continue
            
            if decoded:
                return decoded
        
        # Regular J1939 message
        pgn_desc = self.pgn_descriptions.get(pgn, f"Unknown PGN {pgn}")
        return [{
            'type': 'J1939',
            'pgn': pgn,
            'description': pgn_desc,
            'raw_value': None,
            'value': None,
            'unit': None
        }]

class LINCANGateway:
    """LIN-CAN Gateway class"""
    def __init__(self, decoder=None, message_callback=None):
        self.decoder = decoder
        self.message_callback = message_callback
        self.bus = None
        self.running = False
        self.processing_thread = None
        self.message_queue = queue.Queue()
        
        self.lin_id_descriptions = {
            0x11: "Door Lock Status",
            0x12: "Engine Temperature Sensor",
            0x13: "Light Status",
            0x14: "Window Position",
            0x22: "Climate Control",
            0x33: "Seat Position",
        }
        
        self.pgn_descriptions = {
            65108: "Engine Temperature",
            61444: "Electronic Engine Controller",
            65267: "Vehicle Position",
            65262: "Engine Coolant Temperature",
            65269: "Ambient Conditions",
        }

    def connect(self, interface='vcan0', bitrate=500000, interface_type='socketcan'):
        """Connect to CAN bus with full Linux and Windows support"""
        import platform
        system = platform.system().lower()
        
        try:
            # Method 1: Try original Linux interfaces first
            if interface in ['can0', 'can1'] and system == 'linux':
                # Setup real CAN interface on Linux
                os.system(f"sudo ip link set {interface} down")
                os.system(f"sudo ip link set {interface} up type can bitrate {bitrate}")
                self.bus = can.interface.Bus(channel=interface, interface='socketcan')
                logging.info(f"Connected to real CAN interface: {interface}")
                return True
                
            elif interface in ['vcan0', 'vcan1'] and system == 'linux':
                # Setup Linux virtual CAN
                os.system("sudo modprobe vcan")
                os.system(f"sudo ip link add dev {interface} type vcan")
                os.system(f"sudo ip link set up {interface}")
                self.bus = can.interface.Bus(channel=interface, interface='socketcan')
                logging.info(f"Connected to Linux virtual CAN: {interface}")
                return True
                
            elif interface == 'virtual' or interface_type == 'virtual':
                # Use shared virtual bus for cross-platform compatibility
                try:
                    from shared_bus import SharedCANInterface
                    self.bus = SharedCANInterface()
                    self.bus.set_callback(self._handle_shared_message)
                    logging.info(f"Connected to shared virtual CAN interface")
                    return True
                except ImportError:
                    # Fallback to regular virtual interface
                    self.bus = can.interface.Bus(interface='virtual')
                    logging.info(f"Connected to python-can virtual interface")
                    return True
            else:
                # Try as regular socketcan interface
                self.bus = can.interface.Bus(channel=interface, interface='socketcan')
                logging.info(f"Connected to CAN interface: {interface}")
                return True
                
        except Exception as e:
            logging.error(f"Failed to connect to {interface}: {e}")
            
            # Fallback chain
            fallbacks = [
                ('shared virtual', lambda: self._try_shared_virtual()),
                ('python-can virtual', lambda: can.interface.Bus(interface='virtual')),
            ]
            
            for name, method in fallbacks:
                try:
                    self.bus = method()
                    logging.info(f"Connected using fallback: {name}")
                    return True
                except Exception as e2:
                    logging.debug(f"Fallback {name} failed: {e2}")
                    continue
            
            logging.error("All connection methods failed")
            return False
    
    def _try_shared_virtual(self):
        """Try to connect to shared virtual bus"""
        from shared_bus import SharedCANInterface
        bus = SharedCANInterface()
        bus.set_callback(self._handle_shared_message)
        return bus

    def start_gateway(self):
        """Start the gateway processing"""
        if not self.bus:
            logging.error("No CAN bus connection")
            return False
        
        self.running = True
        self.processing_thread = threading.Thread(target=self.main_loop, daemon=True)
        self.processing_thread.start()
        logging.info("Gateway started")
        return True

    def stop_gateway(self):
        """Stop the gateway processing"""
        self.running = False
        if self.processing_thread:
            self.processing_thread.join(timeout=2)
        logging.info("Gateway stopped")

    def send_lin_as_can(self, lin_id, data, description=""):
        """Send LIN message as CAN"""
        if not self.bus:
            return
        
        can_id = 0x700 + lin_id
        padded_data = data + [0] * (8 - len(data))
        
        try:
            msg = can.Message(arbitration_id=can_id, data=padded_data[:8], is_extended_id=False)
            self.bus.send(msg)
            logging.info(f"Sent LIN as CAN: ID={lin_id:02X}, Data={data}, {description}")
        except Exception as e:
            logging.error(f"Error sending LIN as CAN: {e}")

    def process_can_message(self, msg):
        """Process incoming CAN message"""
        if self.message_callback:
            self.message_callback(msg)
        
        if self.decoder:
            decoded = self.decoder.decode_frame(msg.arbitration_id, msg.data)
            for item in decoded:
                logging.info(f"Decoded: {item['description']}")

    def _handle_shared_message(self, msg):
        """Handle messages from shared bus"""
        if self.running:
            self.process_can_message(msg)
    
    def main_loop(self):
        """Main processing loop"""
        last_lin_update = time.time()
        
        while self.running:
            try:
                # For shared bus, messages come via callback
                if hasattr(self.bus, 'recv'):
                    msg = self.bus.recv(timeout=0.1)
                    if msg:
                        self.process_can_message(msg)
                
                current_time = time.time()
                if current_time - last_lin_update > 30:  # Reduced frequency to every 30 seconds
                    self.send_lin_as_can(0x14, [0x30], "Window Position Periodic Update")
                    last_lin_update = current_time
                    
            except can.CanError as e:
                logging.error(f"CAN error: {e}")
            except Exception as e:
                logging.error(f"Unexpected error: {e}")
                
            time.sleep(0.01)

    def cleanup(self):
        """Clean up resources"""
        if self.bus:
            self.bus.shutdown()
            self.bus = None
        logging.info("CAN bus interface shutdown")

class LINCANGatewayApp:
    """Main application class for the LIN-CAN Gateway UI"""
    def __init__(self, root):
        self.root = root
        self.root.title("LIN-CAN Gateway")
        self.root.geometry("1000x700")
        
        # Initialize variables
        self.decoder = None
        self.gateway = None
        self.csv_path_var = tk.StringVar()
        self.interface_var = tk.StringVar(value="vcan0")
        self.bitrate_var = tk.StringVar(value="500000")
        self.can_status_var = tk.StringVar(value="Disconnected")
        self.status_var = tk.StringVar(value="Ready")
        self.can_id_var = tk.StringVar()
        self.can_data_var = tk.StringVar()
        
        # Create UI
        self.create_ui()
        
        # Start message processing
        self.process_message_queue()

    def create_ui(self):
        """Create the main UI"""
        # Create notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Gateway tab
        self.create_gateway_tab(notebook)
        
        # Decoder tab
        self.create_decoder_tab(notebook)
        
        # Log tab
        self.create_log_tab(notebook)
        
        # Status bar
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(status_frame, text="CAN Status:").pack(side=tk.LEFT)
        ttk.Label(status_frame, textvariable=self.can_status_var).pack(side=tk.LEFT, padx=5)
        ttk.Label(status_frame, textvariable=self.status_var).pack(side=tk.LEFT, padx=20)

    def create_gateway_tab(self, notebook):
        """Create the Gateway Control tab"""
        gateway_frame = ttk.Frame(notebook)
        notebook.add(gateway_frame, text="Gateway")
        
        # Control frame
        control_frame = ttk.LabelFrame(gateway_frame, text="Gateway Control")
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Interface selection
        ttk.Label(control_frame, text="Interface:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        interface_combo = ttk.Combobox(control_frame, textvariable=self.interface_var, 
                                     values=self.get_available_interfaces())
        interface_combo.grid(row=0, column=1, padx=5, pady=2)
        
        # Bitrate
        ttk.Label(control_frame, text="Bitrate:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(control_frame, textvariable=self.bitrate_var, width=10).grid(row=0, column=3, padx=5, pady=2)
        
        # Control buttons
        ttk.Button(control_frame, text="Connect", command=self.connect_gateway).grid(row=1, column=0, padx=5, pady=5)
        ttk.Button(control_frame, text="Start Gateway", command=self.start_gateway).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(control_frame, text="Stop Gateway", command=self.stop_gateway).grid(row=1, column=2, padx=5, pady=5)
        
        # Message display
        msg_frame = ttk.LabelFrame(gateway_frame, text="Messages")
        msg_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Treeview for messages
        columns = ('Time', 'ID', 'Type', 'Data', 'Description')
        self.msg_tree = ttk.Treeview(msg_frame, columns=columns, show='headings', height=15)
        
        for col in columns:
            self.msg_tree.heading(col, text=col)
            self.msg_tree.column(col, width=100)
        
        scrollbar = ttk.Scrollbar(msg_frame, orient=tk.VERTICAL, command=self.msg_tree.yview)
        self.msg_tree.configure(yscrollcommand=scrollbar.set)
        
        self.msg_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def create_decoder_tab(self, notebook):
        """Create the Decoder tab"""
        decoder_frame = ttk.Frame(notebook)
        notebook.add(decoder_frame, text="Decoder")
        
        # CSV file selection
        csv_frame = ttk.LabelFrame(decoder_frame, text="SPN Database")
        csv_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Entry(csv_frame, textvariable=self.csv_path_var, width=50).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(csv_frame, text="Browse", command=self.select_csv_file).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Manual decode
        decode_frame = ttk.LabelFrame(decoder_frame, text="Manual Decode")
        decode_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(decode_frame, text="CAN ID (hex):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(decode_frame, textvariable=self.can_id_var, width=15).grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(decode_frame, text="Data (hex):").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(decode_frame, textvariable=self.can_data_var, width=25).grid(row=0, column=3, padx=5, pady=2)
        
        ttk.Button(decode_frame, text="Decode", command=self.decode_message).grid(row=0, column=4, padx=5, pady=2)
        
        # Decode results
        result_frame = ttk.LabelFrame(decoder_frame, text="Decode Results")
        result_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ('SPN', 'Description', 'Value', 'Unit')
        self.decoder_tree = ttk.Treeview(result_frame, columns=columns, show='headings')
        
        for col in columns:
            self.decoder_tree.heading(col, text=col)
            self.decoder_tree.column(col, width=150)
        
        self.decoder_tree.pack(fill=tk.BOTH, expand=True)

    def create_log_tab(self, notebook):
        """Create the Log tab"""
        log_frame = ttk.Frame(notebook)
        notebook.add(log_frame, text="Logs")
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=20)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Add log handler
        log_handler = UILogHandler(self.log_text)
        logging.getLogger().addHandler(log_handler)

    def get_available_interfaces(self):
        """Get available CAN interfaces"""
        interfaces = ["virtual", "vcan0", "vcan1", "can0", "can1"]
        return interfaces

    def select_csv_file(self):
        """Handle CSV file selection"""
        file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if file_path:
            self.csv_path_var.set(file_path)
            try:
                self.decoder = CANDecoder(file_path)
                logging.info(f"SPN definitions loaded from {file_path}")
            except Exception as e:
                messagebox.showerror("CSV Error", f"Failed to load CSV: {str(e)}")

    def connect_gateway(self):
        """Connect to CAN gateway"""
        interface = self.interface_var.get()
        
        self.gateway = LINCANGateway(decoder=self.decoder, message_callback=self.handle_can_message)
        
        # Try different interface types for Windows compatibility
        if self.gateway.connect(interface):
            self.can_status_var.set("Connected")
            self.status_var.set(f"Connected to {interface}")
        elif interface.startswith('vcan') and self.gateway.connect(interface, interface_type='virtual'):
            self.can_status_var.set("Connected")
            self.status_var.set(f"Connected to {interface} (virtual)")
        else:
            self.can_status_var.set("Error")
            self.status_var.set("Connection failed")

    def start_gateway(self):
        """Start the gateway"""
        if self.gateway and self.gateway.start_gateway():
            self.status_var.set("Gateway running")
        else:
            self.status_var.set("Failed to start gateway")

    def stop_gateway(self):
        """Stop the gateway"""
        if self.gateway:
            self.gateway.stop_gateway()
            self.status_var.set("Gateway stopped")

    def handle_can_message(self, msg):
        """Handle incoming CAN message"""
        timestamp = time.strftime("%H:%M:%S")
        can_id = f"0x{msg.arbitration_id:08X}"
        data_str = " ".join(f"{b:02X}" for b in msg.data)
        
        # Determine message type
        if 0x700 <= msg.arbitration_id <= 0x73F:
            msg_type = "LIN"
            description = "LIN over CAN"
        else:
            msg_type = "J1939"
            description = "J1939 message"
        
        # Add to tree
        self.msg_tree.insert('', 0, values=(timestamp, can_id, msg_type, data_str, description))
        
        # Keep only last 100 messages
        children = self.msg_tree.get_children()
        if len(children) > 100:
            self.msg_tree.delete(children[-1])

    def decode_message(self):
        """Decode manual CAN message input"""
        if not self.decoder:
            messagebox.showwarning("Decoder Error", "Load SPN CSV first")
            return
            
        try:
            can_id_str = self.can_id_var.get().strip()
            data_str = self.can_data_var.get().strip()
            
            if not can_id_str or not data_str:
                raise ValueError("CAN ID and Data fields are required")
            
            can_id = int(can_id_str, 16)
            data = bytes.fromhex(data_str.replace(' ', ''))
            
            decoded = self.decoder.decode_frame(can_id, data)
            
            self.decoder_tree.delete(*self.decoder_tree.get_children())
            for item in decoded:
                value_str = f"{item['value']:.2f}" if item['value'] is not None else 'N/A'
                self.decoder_tree.insert('', tk.END, values=(
                    item.get('spn', 'N/A'),
                    item['description'],
                    value_str,
                    item['unit'] or ''
                ))
        except ValueError as ve:
            messagebox.showerror("Input Error", f"Invalid input: {str(ve)}")
        except Exception as e:
            messagebox.showerror("Decode Error", f"Decoding failed: {str(e)}")

    def process_message_queue(self):
        """Process message queue"""
        self.root.after(100, self.process_message_queue)

    def on_closing(self):
        """Handle application closing"""
        if self.gateway:
            self.gateway.stop_gateway()
            self.gateway.cleanup()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = LINCANGatewayApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()