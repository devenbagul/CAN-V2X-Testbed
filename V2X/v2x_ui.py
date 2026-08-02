#!/usr/bin/env python3
"""
V2X System Professional UI
--------------------------
Complete automotive CAN monitoring and V2X communication interface
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import can
import os
import time
import threading
import logging
import platform
from collections import defaultdict
import queue

class V2XCANInterface:
    """Professional CAN interface for V2X system"""
    def __init__(self, message_callback=None):
        self.bus = None
        self.running = False
        self.processing_thread = None
        self.message_callback = message_callback
        
    def connect(self, interface='vcan0'):
        """Connect to CAN interface"""
        system = platform.system().lower()
        
        try:
            if system == 'linux' and interface.startswith('vcan'):
                # Setup Linux virtual CAN
                os.system("sudo modprobe vcan 2>/dev/null")
                os.system(f"sudo ip link add dev {interface} type vcan 2>/dev/null")
                os.system(f"sudo ip link set up {interface}")
                self.bus = can.interface.Bus(channel=interface, interface='socketcan')
                logging.info(f"Connected to Linux CAN: {interface}")
            elif system == 'linux' and interface.startswith('can'):
                # Real CAN interface
                os.system(f"sudo ip link set {interface} down")
                os.system(f"sudo ip link set {interface} up type can bitrate 500000")
                self.bus = can.interface.Bus(channel=interface, interface='socketcan')
                logging.info(f"Connected to real CAN: {interface}")
            else:
                # File-based shared CAN for Windows
                from shared_can import SharedCANBus
                self.bus = SharedCANBus('v2x')
                logging.info("Connected to shared file CAN interface")
            
            return True
        except Exception as e:
            logging.error(f"CAN connection failed: {e}")
            return False
    
    def start_monitoring(self):
        """Start CAN message monitoring"""
        if not self.bus:
            return False
        
        self.running = True
        self.processing_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.processing_thread.start()
        return True
    
    def stop_monitoring(self):
        """Stop CAN message monitoring"""
        self.running = False
        if self.processing_thread:
            self.processing_thread.join(timeout=2)
    
    def send_message(self, can_id, data):
        """Send CAN message"""
        if not self.bus:
            return False
        
        try:
            msg = can.Message(arbitration_id=can_id, data=data, is_extended_id=False)
            self.bus.send(msg)
            return True
        except Exception as e:
            logging.error(f"Send failed: {e}")
            return False
    
    def _monitor_loop(self):
        """CAN monitoring loop"""
        while self.running:
            try:
                msg = self.bus.recv(timeout=0.1)
                if msg and self.message_callback:
                    self.message_callback(msg)
            except Exception as e:
                logging.error(f"Monitor error: {e}")
            time.sleep(0.001)
    
    def cleanup(self):
        """Cleanup CAN interface"""
        self.stop_monitoring()
        if self.bus:
            self.bus.shutdown()

class V2XSystemApp:
    """Main V2X System Application"""
    def __init__(self, root):
        self.root = root
        self.root.title("V2X Automotive CAN System")
        self.root.geometry("1200x800")
        
        # Initialize system components
        self.can_interface = V2XCANInterface(message_callback=self.handle_can_message)
        self.message_queue = queue.Queue()
        
        # System state variables
        self.interface_var = tk.StringVar(value="shared")
        self.connection_status = tk.StringVar(value="Disconnected")
        self.system_status = tk.StringVar(value="Ready")
        
        # Vehicle state tracking
        self.vehicle_state = {
            'speed': 0,
            'engine_rpm': 0,
            'brake_pressure': 0,
            'steering_angle': 0,
            'airbag_status': 'OK',
            'abs_active': False,
            'esc_active': False
        }
        
        # V2X alerts
        self.v2x_alerts = []
        
        # Create UI
        self.create_ui()
        self.setup_logging()
        
        # Start message processing
        self.process_message_queue()
    
    def create_ui(self):
        """Create the main user interface"""
        # Create notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        self.create_dashboard_tab(notebook)
        self.create_vehicle_systems_tab(notebook)
        self.create_v2x_tab(notebook)
        self.create_can_monitor_tab(notebook)
        self.create_logs_tab(notebook)
        
        # Status bar
        self.create_status_bar()
    
    def create_dashboard_tab(self, notebook):
        """Create main dashboard tab"""
        dashboard_frame = ttk.Frame(notebook)
        notebook.add(dashboard_frame, text="Dashboard")
        
        # Connection control
        control_frame = ttk.LabelFrame(dashboard_frame, text="System Control")
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(control_frame, text="CAN Interface:").grid(row=0, column=0, padx=5, pady=5)
        interface_combo = ttk.Combobox(control_frame, textvariable=self.interface_var,
                                     values=["shared", "vcan0", "vcan1", "can0", "can1"])
        interface_combo.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Button(control_frame, text="Connect", command=self.connect_can).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(control_frame, text="Start Monitoring", command=self.start_monitoring).grid(row=0, column=3, padx=5, pady=5)
        ttk.Button(control_frame, text="Stop", command=self.stop_monitoring).grid(row=0, column=4, padx=5, pady=5)
        
        # Vehicle status display
        status_frame = ttk.LabelFrame(dashboard_frame, text="Vehicle Status")
        status_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Speed gauge
        speed_frame = ttk.Frame(status_frame)
        speed_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ttk.Label(speed_frame, text="Speed (km/h)", font=("Arial", 12, "bold")).pack()
        self.speed_label = ttk.Label(speed_frame, text="0", font=("Arial", 24, "bold"))
        self.speed_label.pack()
        
        # RPM gauge
        rpm_frame = ttk.Frame(status_frame)
        rpm_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ttk.Label(rpm_frame, text="Engine RPM", font=("Arial", 12, "bold")).pack()
        self.rpm_label = ttk.Label(rpm_frame, text="0", font=("Arial", 24, "bold"))
        self.rpm_label.pack()
        
        # System indicators
        indicators_frame = ttk.Frame(status_frame)
        indicators_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)
        
        ttk.Label(indicators_frame, text="System Status", font=("Arial", 12, "bold")).pack()
        
        self.abs_indicator = ttk.Label(indicators_frame, text="ABS: OFF", background="lightgray")
        self.abs_indicator.pack(pady=2)
        
        self.esc_indicator = ttk.Label(indicators_frame, text="ESC: OFF", background="lightgray")
        self.esc_indicator.pack(pady=2)
        
        self.airbag_indicator = ttk.Label(indicators_frame, text="Airbag: OK", background="lightgreen")
        self.airbag_indicator.pack(pady=2)
    
    def create_vehicle_systems_tab(self, notebook):
        """Create vehicle systems monitoring tab"""
        systems_frame = ttk.Frame(notebook)
        notebook.add(systems_frame, text="Vehicle Systems")
        
        # Engine control
        engine_frame = ttk.LabelFrame(systems_frame, text="Engine Control Unit (ECU)")
        engine_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(engine_frame, text="Send Engine Data", command=self.send_engine_data).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(engine_frame, text="Engine Warning", command=self.send_engine_warning).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Braking system
        brake_frame = ttk.LabelFrame(systems_frame, text="Anti-lock Braking System (ABS)")
        brake_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(brake_frame, text="Normal Braking", command=self.send_brake_normal).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(brake_frame, text="ABS Activation", command=self.send_abs_activation).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(brake_frame, text="Emergency Brake", command=self.send_emergency_brake).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Airbag system
        airbag_frame = ttk.LabelFrame(systems_frame, text="Airbag Control Module")
        airbag_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(airbag_frame, text="System Check", command=self.send_airbag_check).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(airbag_frame, text="Deployment Ready", command=self.send_airbag_ready).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(airbag_frame, text="Fault Detected", command=self.send_airbag_fault).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Steering system
        steering_frame = ttk.LabelFrame(systems_frame, text="Electronic Stability Control (ESC)")
        steering_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(steering_frame, text="Normal Steering", command=self.send_steering_normal).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(steering_frame, text="ESC Intervention", command=self.send_esc_intervention).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(steering_frame, text="Stability Warning", command=self.send_stability_warning).pack(side=tk.LEFT, padx=5, pady=5)
    
    def create_v2x_tab(self, notebook):
        """Create V2X communication tab"""
        v2x_frame = ttk.Frame(notebook)
        notebook.add(v2x_frame, text="V2X Communication")
        
        # V2X controls
        control_frame = ttk.LabelFrame(v2x_frame, text="V2X Safety Features")
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(control_frame, text="Speed Limit Warning", command=self.send_speed_warning).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(control_frame, text="Collision Alert", command=self.send_collision_alert).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(control_frame, text="Emergency Vehicle", command=self.send_emergency_vehicle).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(control_frame, text="Traffic Light Info", command=self.send_traffic_light).pack(side=tk.LEFT, padx=5, pady=5)
        
        # V2X alerts display
        alerts_frame = ttk.LabelFrame(v2x_frame, text="Active V2X Alerts")
        alerts_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Treeview for alerts
        columns = ('Time', 'Type', 'Message', 'Priority')
        self.v2x_tree = ttk.Treeview(alerts_frame, columns=columns, show='headings', height=15)
        
        for col in columns:
            self.v2x_tree.heading(col, text=col)
            self.v2x_tree.column(col, width=150)
        
        scrollbar_v2x = ttk.Scrollbar(alerts_frame, orient=tk.VERTICAL, command=self.v2x_tree.yview)
        self.v2x_tree.configure(yscrollcommand=scrollbar_v2x.set)
        
        self.v2x_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_v2x.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_can_monitor_tab(self, notebook):
        """Create CAN message monitoring tab"""
        monitor_frame = ttk.Frame(notebook)
        notebook.add(monitor_frame, text="CAN Monitor")
        
        # Message display
        msg_frame = ttk.LabelFrame(monitor_frame, text="CAN Messages")
        msg_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Treeview for messages
        columns = ('Time', 'ID', 'DLC', 'Data', 'Description')
        self.msg_tree = ttk.Treeview(msg_frame, columns=columns, show='headings', height=20)
        
        for col in columns:
            self.msg_tree.heading(col, text=col)
            self.msg_tree.column(col, width=120)
        
        scrollbar_msg = ttk.Scrollbar(msg_frame, orient=tk.VERTICAL, command=self.msg_tree.yview)
        self.msg_tree.configure(yscrollcommand=scrollbar_msg.set)
        
        self.msg_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_msg.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_logs_tab(self, notebook):
        """Create system logs tab"""
        log_frame = ttk.Frame(notebook)
        notebook.add(log_frame, text="System Logs")
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=25)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def create_status_bar(self):
        """Create status bar"""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(status_frame, text="Connection:").pack(side=tk.LEFT)
        ttk.Label(status_frame, textvariable=self.connection_status).pack(side=tk.LEFT, padx=5)
        ttk.Label(status_frame, textvariable=self.system_status).pack(side=tk.LEFT, padx=20)
    
    def setup_logging(self):
        """Setup logging to display in UI"""
        class UILogHandler(logging.Handler):
            def __init__(self, log_widget):
                super().__init__()
                self.log_widget = log_widget
                
            def emit(self, record):
                log_entry = self.format(record)
                self.log_widget.after(0, self._append_log, log_entry)
                
            def _append_log(self, message):
                self.log_widget.configure(state='normal')
                self.log_widget.insert(tk.END, message + '\n')
                self.log_widget.see(tk.END)
                self.log_widget.configure(state='disabled')
        
        handler = UILogHandler(self.log_text)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(handler)
    
    # CAN Interface Methods
    def connect_can(self):
        """Connect to CAN interface"""
        interface = self.interface_var.get()
        if self.can_interface.connect(interface):
            self.connection_status.set("Connected")
            self.system_status.set(f"Connected to {interface}")
            logging.info(f"Connected to CAN interface: {interface}")
        else:
            self.connection_status.set("Error")
            self.system_status.set("Connection failed")
            messagebox.showerror("Connection Error", "Failed to connect to CAN interface")
    
    def start_monitoring(self):
        """Start CAN monitoring"""
        if self.can_interface.start_monitoring():
            self.system_status.set("Monitoring active")
            logging.info("CAN monitoring started")
        else:
            messagebox.showerror("Monitor Error", "Failed to start CAN monitoring")
    
    def stop_monitoring(self):
        """Stop CAN monitoring"""
        self.can_interface.stop_monitoring()
        self.system_status.set("Monitoring stopped")
        logging.info("CAN monitoring stopped")
    
    # Vehicle System Methods
    def send_engine_data(self):
        """Send engine control data"""
        rpm = 2500
        temp = 85
        data = [
            (rpm >> 8) & 0xFF, rpm & 0xFF,  # RPM
            temp,  # Temperature
            0x80,  # Throttle position
            0x00, 0x00, 0x00, 0x00
        ]
        self.can_interface.send_message(0x100, data)
        logging.info("Sent engine control data")
    
    def send_engine_warning(self):
        """Send engine warning"""
        data = [0xFF, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]  # Warning code
        self.can_interface.send_message(0x101, data)
        logging.warning("Engine warning sent")
    
    def send_brake_normal(self):
        """Send normal braking data"""
        data = [0x00, 0x50, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]  # Normal pressure
        self.can_interface.send_message(0x200, data)
        logging.info("Normal braking data sent")
    
    def send_abs_activation(self):
        """Send ABS activation"""
        data = [0x01, 0xFF, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00]  # ABS active
        self.can_interface.send_message(0x201, data)
        self.abs_indicator.configure(text="ABS: ACTIVE", background="orange")
        logging.warning("ABS activation sent")
    
    def send_emergency_brake(self):
        """Send emergency brake signal"""
        data = [0xFF, 0xFF, 0xFF, 0x01, 0x00, 0x00, 0x00, 0x00]  # Emergency
        self.can_interface.send_message(0x202, data)
        logging.critical("Emergency brake signal sent")
    
    def send_airbag_check(self):
        """Send airbag system check"""
        data = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]  # All OK
        self.can_interface.send_message(0x300, data)
        self.airbag_indicator.configure(text="Airbag: OK", background="lightgreen")
        logging.info("Airbag system check sent")
    
    def send_airbag_ready(self):
        """Send airbag deployment ready"""
        data = [0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00]  # Ready
        self.can_interface.send_message(0x301, data)
        self.airbag_indicator.configure(text="Airbag: READY", background="yellow")
        logging.warning("Airbag deployment ready")
    
    def send_airbag_fault(self):
        """Send airbag fault"""
        data = [0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]  # Fault
        self.can_interface.send_message(0x302, data)
        self.airbag_indicator.configure(text="Airbag: FAULT", background="red")
        logging.error("Airbag fault detected")
    
    def send_steering_normal(self):
        """Send normal steering data"""
        data = [0x00, 0x00, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00]  # Center position
        self.can_interface.send_message(0x400, data)
        self.esc_indicator.configure(text="ESC: OFF", background="lightgray")
        logging.info("Normal steering data sent")
    
    def send_esc_intervention(self):
        """Send ESC intervention"""
        data = [0x01, 0xFF, 0x90, 0x01, 0x00, 0x00, 0x00, 0x00]  # ESC active
        self.can_interface.send_message(0x401, data)
        self.esc_indicator.configure(text="ESC: ACTIVE", background="orange")
        logging.warning("ESC intervention active")
    
    def send_stability_warning(self):
        """Send stability warning"""
        data = [0xFF, 0x01, 0xA0, 0xFF, 0x00, 0x00, 0x00, 0x00]  # Warning
        self.can_interface.send_message(0x402, data)
        logging.warning("Vehicle stability warning")
    
    # V2X Methods
    def send_speed_warning(self):
        """Send V2X speed limit warning"""
        speed = 85  # Current speed > 80 km/h limit
        data = [speed, 0x50, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00]  # Speed, limit, warning
        self.can_interface.send_message(0x500, data)
        self.add_v2x_alert("Speed Warning", f"Speed {speed} km/h exceeds limit 80 km/h", "HIGH")
        logging.warning(f"V2X Speed warning: {speed} km/h > 80 km/h")
    
    def send_collision_alert(self):
        """Send collision alert"""
        data = [0xFF, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]  # Collision imminent
        self.can_interface.send_message(0x501, data)
        self.add_v2x_alert("Collision Alert", "Forward collision warning", "CRITICAL")
        logging.critical("V2X Collision alert sent")
    
    def send_emergency_vehicle(self):
        """Send emergency vehicle alert"""
        data = [0x01, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00]  # Emergency vehicle
        self.can_interface.send_message(0x502, data)
        self.add_v2x_alert("Emergency Vehicle", "Emergency vehicle approaching", "HIGH")
        logging.warning("V2X Emergency vehicle alert")
    
    def send_traffic_light(self):
        """Send traffic light information"""
        data = [0x02, 0x0A, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]  # Red light, 10s remaining
        self.can_interface.send_message(0x503, data)
        self.add_v2x_alert("Traffic Light", "Red light ahead - 10s remaining", "MEDIUM")
        logging.info("V2X Traffic light information sent")
    
    def add_v2x_alert(self, alert_type, message, priority):
        """Add V2X alert to display"""
        timestamp = time.strftime("%H:%M:%S")
        self.v2x_tree.insert('', 0, values=(timestamp, alert_type, message, priority))
        
        # Keep only last 50 alerts
        children = self.v2x_tree.get_children()
        if len(children) > 50:
            self.v2x_tree.delete(children[-1])
    
    def handle_can_message(self, msg):
        """Handle incoming CAN message"""
        try:
            timestamp = time.strftime("%H:%M:%S")
            can_id = f"0x{msg.arbitration_id:03X}"
            dlc = len(msg.data)
            data_str = " ".join(f"{b:02X}" for b in msg.data)
            
            # Determine message description
            description = self.get_message_description(msg.arbitration_id, msg.data)
            
            # Update vehicle state
            self.update_vehicle_state(msg.arbitration_id, msg.data)
            
            # Add to message display using after() for thread safety
            self.root.after(0, self._add_message_to_tree, timestamp, can_id, dlc, data_str, description)
        except Exception as e:
            logging.error(f"Error handling CAN message: {e}")
    
    def _add_message_to_tree(self, timestamp, can_id, dlc, data_str, description):
        """Add message to tree view (called from main thread)"""
        try:
            self.msg_tree.insert('', 0, values=(timestamp, can_id, dlc, data_str, description))
            
            # Keep only last 100 messages
            children = self.msg_tree.get_children()
            if len(children) > 100:
                self.msg_tree.delete(children[-1])
        except Exception as e:
            logging.error(f"Error adding message to tree: {e}")
    
    def get_message_description(self, can_id, data):
        """Get description for CAN message"""
        descriptions = {
            # Simulator messages
            0x0CF00400: "Engine RPM",
            0x0CF00503: "Vehicle Speed",
            0x0CF00300: "Brake Pressure",
            0x0CF00200: "Steering Angle",
            0x0CF00100: "Airbag Status",
            0x0CF00600: "V2X Speed Warning",
            0x0CF00700: "V2X Emergency",
            0x0CF00401: "Engine Temperature",
            0x0CF00402: "Fuel Level",
            # Manual UI messages
            0x100: "Engine Control Data",
            0x101: "Engine Warning",
            0x200: "Brake System Data",
            0x201: "ABS Status",
            0x202: "Emergency Brake",
            0x300: "Airbag System Check",
            0x301: "Airbag Ready",
            0x302: "Airbag Fault",
            0x400: "Steering Data",
            0x401: "ESC Intervention",
            0x402: "Stability Warning",
            0x500: "V2X Speed Warning",
            0x501: "V2X Collision Alert",
            0x502: "V2X Emergency Vehicle",
            0x503: "V2X Traffic Light"
        }
        return descriptions.get(can_id, f"Unknown Message (0x{can_id:X})")
    
    def update_vehicle_state(self, can_id, data):
        """Update vehicle state from CAN messages"""
        try:
            # Engine RPM from simulator
            if can_id == 0x0CF00400 and len(data) >= 2:  # ENGINE_RPM
                rpm = (data[0] << 8) | data[1]
                self.vehicle_state['engine_rpm'] = rpm
                self.root.after(0, lambda: self.rpm_label.configure(text=str(rpm)))
            
            # Vehicle speed from simulator
            elif can_id == 0x0CF00503 and len(data) >= 2:  # VEHICLE_SPEED
                speed = ((data[0] << 8) | data[1]) / 100  # Convert back from simulator format
                self.vehicle_state['speed'] = speed
                self.root.after(0, self._update_speed_display, speed)
            
            # Manual button presses
            elif can_id == 0x100 and len(data) >= 3:  # Manual engine data
                rpm = (data[0] << 8) | data[1]
                self.vehicle_state['engine_rpm'] = rpm
                self.root.after(0, lambda: self.rpm_label.configure(text=str(rpm)))
            
            elif can_id == 0x500 and len(data) >= 1:  # Manual speed data
                speed = data[0]
                self.vehicle_state['speed'] = speed
                self.root.after(0, self._update_speed_display, speed)
        except Exception as e:
            logging.error(f"Error updating vehicle state: {e}")
    
    def _update_speed_display(self, speed):
        """Update speed display (called from main thread)"""
        try:
            self.speed_label.configure(text=str(int(speed)))
            # Check for speed warnings
            if speed > 80:
                self.speed_label.configure(foreground="red")
            else:
                self.speed_label.configure(foreground="black")
        except Exception as e:
            logging.error(f"Error updating speed display: {e}")
    
    def process_message_queue(self):
        """Process message queue"""
        self.root.after(100, self.process_message_queue)
    
    def on_closing(self):
        """Handle application closing"""
        self.can_interface.cleanup()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = V2XSystemApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()