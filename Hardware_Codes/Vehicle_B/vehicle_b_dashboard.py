#!/usr/bin/env python3
"""
Vehicle B Dashboard - Professional UI for V2X Secondary Vehicle
Real-time visualization of received CAN messages and safety responses
"""

import sys
import os
import time
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext
from datetime import datetime
import queue
from collections import deque
import math

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Shared'))

from can_protocol import CANMessageIDs, V2XProtocol, SafetyThresholds, get_message_description
from rpi_can_interface import RPiCANInterface, CANLogger

class VehicleBDashboard:
    """Professional Dashboard for Vehicle B"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("🚗 Vehicle B - V2X Secondary Controller Dashboard")
        self.root.geometry("1200x800")
        self.root.configure(bg='#34495e')
        
        # Initialize CAN interface
        self.can_interface = RPiCANInterface('can0')
        self.can_logger = CANLogger("vehicle_b_dashboard.log")
        self.running = False
        
        # Vehicle state
        self.vehicle_state = {
            'speed': tk.DoubleVar(value=0.0),
            'engine_rpm': tk.IntVar(value=800),
            'engine_temp': tk.IntVar(value=85),
            'brake_pressure': tk.IntVar(value=0),
            'fuel_level': tk.IntVar(value=80),
            'abs_active': tk.BooleanVar(value=False),
            'emergency_brake': tk.BooleanVar(value=False),
            'collision_risk': tk.BooleanVar(value=False)
        }
        
        # Other vehicles tracking
        self.other_vehicles = {}
        self.safety_alerts = deque(maxlen=50)
        self.collision_warnings = deque(maxlen=20)
        
        # UI queues for thread safety
        self.message_queue = queue.Queue()
        self.alert_queue = queue.Queue()
        self.safety_queue = queue.Queue()
        
        # Message counters
        self.messages_sent = 0
        self.messages_received = 0
        
        # Create UI
        self.create_ui()
        self.setup_simulation()
        
        # Start UI update loop
        self.update_ui()
    
    def create_ui(self):
        """Create the main dashboard UI"""
        # Main container
        main_frame = tk.Frame(self.root, bg='#34495e')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        title_label = tk.Label(main_frame, text="🚗 Vehicle B - V2X Secondary Controller", 
                              font=('Arial', 18, 'bold'), fg='white', bg='#34495e')
        title_label.pack(pady=(0, 20))
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create tabs
        self.create_dashboard_tab()
        self.create_safety_tab()
        self.create_v2x_monitor_tab()
        self.create_other_vehicles_tab()
        self.create_logs_tab()
    
    def create_dashboard_tab(self):
        """Create main dashboard tab"""
        dashboard_frame = ttk.Frame(self.notebook)
        self.notebook.add(dashboard_frame, text="📊 Dashboard")
        
        # Connection status
        status_frame = ttk.LabelFrame(dashboard_frame, text="System Status")
        status_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.connection_status = tk.StringVar(value="Disconnected")
        self.system_status = tk.StringVar(value="Ready")
        
        ttk.Label(status_frame, text="CAN Status:").grid(row=0, column=0, padx=5, pady=5)
        self.status_label = ttk.Label(status_frame, textvariable=self.connection_status, foreground="red")
        self.status_label.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Button(status_frame, text="Connect CAN", command=self.connect_can).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(status_frame, text="Start System", command=self.start_system).grid(row=0, column=3, padx=5, pady=5)
        ttk.Button(status_frame, text="Stop System", command=self.stop_system).grid(row=0, column=4, padx=5, pady=5)
        
        # Vehicle gauges
        gauges_frame = ttk.LabelFrame(dashboard_frame, text="Vehicle Parameters")
        gauges_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Speed gauge
        speed_frame = tk.Frame(gauges_frame, bg='white', relief=tk.RAISED, bd=2)
        speed_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        tk.Label(speed_frame, text="Speed (km/h)", font=('Arial', 12, 'bold'), bg='white').pack(pady=5)
        self.speed_canvas = tk.Canvas(speed_frame, width=150, height=150, bg='white')
        self.speed_canvas.pack(pady=5)
        self.speed_value_label = tk.Label(speed_frame, text="0.0", font=('Arial', 16, 'bold'), bg='white')
        self.speed_value_label.pack()
        
        # Safety status
        safety_frame = tk.Frame(gauges_frame, bg='lightgreen', relief=tk.RAISED, bd=2)
        safety_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        tk.Label(safety_frame, text="Safety Status", font=('Arial', 12, 'bold'), bg='lightgreen').pack(pady=5)
        self.safety_canvas = tk.Canvas(safety_frame, width=150, height=150, bg='lightgreen')
        self.safety_canvas.pack(pady=5)
        self.safety_status_label = tk.Label(safety_frame, text="SAFE", font=('Arial', 16, 'bold'), bg='lightgreen')
        self.safety_status_label.pack()
        
        # Collision risk indicator
        risk_frame = tk.Frame(gauges_frame, bg='white', relief=tk.RAISED, bd=2)
        risk_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        tk.Label(risk_frame, text="Collision Risk", font=('Arial', 12, 'bold'), bg='white').pack(pady=5)
        self.risk_canvas = tk.Canvas(risk_frame, width=150, height=150, bg='white')
        self.risk_canvas.pack(pady=5)
        self.risk_label = tk.Label(risk_frame, text="LOW", font=('Arial', 16, 'bold'), bg='white', fg='green')
        self.risk_label.pack()
        
        # System indicators
        indicators_frame = ttk.LabelFrame(dashboard_frame, text="Safety Systems")
        indicators_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.abs_indicator = tk.Label(indicators_frame, text="ABS: OFF", bg="lightgray", width=15)
        self.abs_indicator.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.brake_indicator = tk.Label(indicators_frame, text="Emergency Brake: OFF", bg="lightgray", width=20)
        self.brake_indicator.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.collision_indicator = tk.Label(indicators_frame, text="Collision Avoidance: READY", bg="lightgreen", width=25)
        self.collision_indicator.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Statistics
        stats_frame = ttk.LabelFrame(dashboard_frame, text="Communication Statistics")
        stats_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.sent_label = ttk.Label(stats_frame, text="Sent: 0")
        self.sent_label.pack(side=tk.LEFT, padx=10)
        
        self.received_label = ttk.Label(stats_frame, text="Received: 0")
        self.received_label.pack(side=tk.LEFT, padx=10)
        
        self.vehicles_label = ttk.Label(stats_frame, text="Other Vehicles: 0")
        self.vehicles_label.pack(side=tk.LEFT, padx=10)
        
        self.alerts_label = ttk.Label(stats_frame, text="Safety Alerts: 0")
        self.alerts_label.pack(side=tk.LEFT, padx=10)
    
    def create_safety_tab(self):
        """Create safety monitoring tab"""
        safety_frame = ttk.Frame(self.notebook)
        self.notebook.add(safety_frame, text="🛡️ Safety Monitor")
        
        # Safety controls
        controls_frame = ttk.LabelFrame(safety_frame, text="Safety Controls")
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(controls_frame, text="Emergency Response", command=self.trigger_emergency_response).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(controls_frame, text="Send Collision Warning", command=self.send_collision_warning).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(controls_frame, text="Clear Alerts", command=self.clear_safety_alerts).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Safety alerts display
        alerts_frame = ttk.LabelFrame(safety_frame, text="Safety Alerts & Responses")
        alerts_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ('Time', 'Type', 'Message', 'Severity', 'Response')
        self.safety_tree = ttk.Treeview(alerts_frame, columns=columns, show='headings', height=15)
        
        for col in columns:
            self.safety_tree.heading(col, text=col)
            self.safety_tree.column(col, width=120)
        
        scrollbar_safety = ttk.Scrollbar(alerts_frame, orient=tk.VERTICAL, command=self.safety_tree.yview)
        self.safety_tree.configure(yscrollcommand=scrollbar_safety.set)
        
        self.safety_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_safety.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_v2x_monitor_tab(self):
        """Create V2X message monitor tab"""
        v2x_frame = ttk.Frame(self.notebook)
        self.notebook.add(v2x_frame, text="📡 V2X Monitor")
        
        # V2X message display
        columns = ('Time', 'ID', 'Type', 'Data', 'Description')
        self.v2x_tree = ttk.Treeview(v2x_frame, columns=columns, show='headings', height=20)
        
        for col in columns:
            self.v2x_tree.heading(col, text=col)
            self.v2x_tree.column(col, width=120)
        
        scrollbar_v2x = ttk.Scrollbar(v2x_frame, orient=tk.VERTICAL, command=self.v2x_tree.yview)
        self.v2x_tree.configure(yscrollcommand=scrollbar_v2x.set)
        
        self.v2x_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_v2x.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_other_vehicles_tab(self):
        """Create other vehicles monitoring tab"""
        vehicles_frame = ttk.Frame(self.notebook)
        self.notebook.add(vehicles_frame, text="🚙 Other Vehicles")
        
        # Vehicle list
        columns = ('Vehicle ID', 'Speed', 'Distance', 'Last Seen', 'Status')
        self.vehicles_tree = ttk.Treeview(vehicles_frame, columns=columns, show='headings', height=10)
        
        for col in columns:
            self.vehicles_tree.heading(col, text=col)
            self.vehicles_tree.column(col, width=120)
        
        scrollbar_vehicles = ttk.Scrollbar(vehicles_frame, orient=tk.VERTICAL, command=self.vehicles_tree.yview)
        self.vehicles_tree.configure(yscrollcommand=scrollbar_vehicles.set)
        
        self.vehicles_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar_vehicles.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Vehicle details
        details_frame = ttk.LabelFrame(vehicles_frame, text="Vehicle Details")
        details_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.vehicle_details = scrolledtext.ScrolledText(details_frame, height=8)
        self.vehicle_details.pack(fill=tk.BOTH, expand=True)
    
    def create_logs_tab(self):
        """Create system logs tab"""
        log_frame = ttk.Frame(self.notebook)
        self.notebook.add(log_frame, text="📋 System Logs")
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=25, width=100)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def draw_safety_indicator(self, canvas, risk_level):
        """Draw safety status indicator"""
        canvas.delete("all")
        
        if risk_level == "LOW":
            color = "green"
            canvas.configure(bg='lightgreen')
        elif risk_level == "MEDIUM":
            color = "orange"
            canvas.configure(bg='lightyellow')
        else:  # HIGH
            color = "red"
            canvas.configure(bg='lightcoral')
        
        # Draw safety circle
        canvas.create_oval(25, 25, 125, 125, fill=color, outline="black", width=3)
        
        # Draw checkmark or warning
        if risk_level == "LOW":
            # Draw checkmark
            canvas.create_line(50, 75, 70, 95, width=5, fill="white")
            canvas.create_line(70, 95, 100, 55, width=5, fill="white")
        else:
            # Draw warning triangle
            canvas.create_polygon(75, 40, 55, 110, 95, 110, fill="white", outline="black")
            canvas.create_text(75, 75, text="!", font=('Arial', 20, 'bold'), fill="black")
    
    def draw_gauge(self, canvas, value, max_value, color="blue"):
        """Draw circular gauge"""
        canvas.delete("all")
        
        # Draw outer circle
        canvas.create_oval(10, 10, 140, 140, outline="black", width=3)
        
        # Calculate angle
        angle = (value / max_value) * 270
        start_angle = 225
        
        # Draw arc
        canvas.create_arc(15, 15, 135, 135, start=start_angle, extent=-angle, 
                         outline=color, width=8, style="arc")
        
        # Draw center dot
        canvas.create_oval(70, 70, 80, 80, fill=color)
    
    def connect_can(self):
        """Connect to CAN interface"""
        if self.can_interface.connect():
            self.connection_status.set("Connected")
            self.status_label.configure(foreground="green")
            self.log_message("✅ Connected to CAN interface")
        else:
            self.connection_status.set("Failed")
            self.status_label.configure(foreground="red")
            self.log_message("❌ Failed to connect to CAN interface")
    
    def start_system(self):
        """Start the V2X system"""
        if not self.running:
            self.running = True
            self.can_interface.start_monitoring(self.handle_can_message)
            
            # Start simulation thread
            threading.Thread(target=self.simulation_loop, daemon=True).start()
            
            self.system_status.set("Running")
            self.log_message("🚀 V2X System started")
    
    def stop_system(self):
        """Stop the V2X system"""
        self.running = False
        self.can_interface.stop_monitoring()
        self.system_status.set("Stopped")
        self.log_message("🛑 V2X System stopped")
    
    def setup_simulation(self):
        """Setup vehicle simulation"""
        import random
        
        def simulate():
            if self.running:
                # Simulate own vehicle movement (more conservative)
                current_speed = self.vehicle_state['speed'].get()
                if random.random() < 0.2:
                    new_speed = max(0, min(90, current_speed + random.uniform(-5, 8)))
                    self.vehicle_state['speed'].set(new_speed)
                
                # Update RPM
                speed = self.vehicle_state['speed'].get()
                rpm = 800 + (speed * 30) if speed > 0 else 800
                self.vehicle_state['engine_rpm'].set(int(rpm))
            
            self.root.after(1000, simulate)
        
        simulate()
    
    def simulation_loop(self):
        """Main simulation loop"""
        while self.running:
            try:
                # Send own vehicle data
                speed = self.vehicle_state['speed'].get()
                rpm = self.vehicle_state['engine_rpm'].get()
                
                # Send speed message
                speed_msg = V2XProtocol.create_speed_message(speed)
                self.send_can_message(speed_msg)
                
                # Process safety conditions
                self.process_safety_conditions()
                
                time.sleep(0.3)  # ~3Hz update rate
                
            except Exception as e:
                self.log_message(f"❌ Simulation error: {e}")
                time.sleep(1)
    
    def handle_can_message(self, msg):
        """Handle incoming CAN messages"""
        self.messages_received += 1
        
        # Add to message queue for UI update
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        can_id = f"0x{msg.arbitration_id:03X}"
        description = get_message_description(msg.arbitration_id)
        data_str = " ".join(f"{b:02X}" for b in msg.data)
        
        self.message_queue.put(('v2x', timestamp, can_id, 'CAN', data_str, description))
        
        # Process specific message types
        if msg.arbitration_id == CANMessageIDs.VEHICLE_SPEED:
            self.process_other_vehicle_speed(msg)
        elif msg.arbitration_id == CANMessageIDs.COLLISION_WARNING:
            self.process_collision_warning(msg)
        elif msg.arbitration_id == CANMessageIDs.EMERGENCY_VEHICLE:
            self.process_emergency_vehicle(msg)
        elif msg.arbitration_id == CANMessageIDs.SPEED_WARNING:
            self.process_speed_warning(msg)
    
    def process_other_vehicle_speed(self, msg):
        """Process speed message from other vehicle"""
        speed = V2XProtocol.parse_speed_message(msg)
        if speed is not None:
            vehicle_id = "VehicleA"
            self.other_vehicles[vehicle_id] = {
                'speed': speed,
                'distance': 30,  # Simulated
                'last_seen': datetime.now(),
                'status': 'NORMAL'
            }
            
            # Check for collision risk
            if speed > SafetyThresholds.MAX_SPEED:
                self.add_safety_alert("SPEED_VIOLATION", f"Vehicle {vehicle_id} exceeding speed limit", "HIGH", "Monitor")
    
    def process_collision_warning(self, msg):
        """Process collision warning"""
        self.collision_warnings.append({
            'timestamp': datetime.now(),
            'severity': msg.data[1] if len(msg.data) > 1 else 0x80
        })
        
        self.add_safety_alert("COLLISION_WARNING", "Collision warning received", "CRITICAL", "Emergency Response")
        self.trigger_emergency_response()
    
    def process_emergency_vehicle(self, msg):
        """Process emergency vehicle alert"""
        self.add_safety_alert("EMERGENCY_VEHICLE", "Emergency vehicle approaching", "HIGH", "Lane Change")
        self.initiate_lane_change()
    
    def process_speed_warning(self, msg):
        """Process speed warning"""
        self.add_safety_alert("SPEED_WARNING", "Speed limit violation detected", "MEDIUM", "Advisory")
    
    def process_safety_conditions(self):
        """Process current safety conditions"""
        # Determine overall risk level
        risk_level = "LOW"
        
        if len(self.collision_warnings) > 0:
            recent_warnings = [w for w in self.collision_warnings 
                             if (datetime.now() - w['timestamp']).seconds < 10]
            if recent_warnings:
                risk_level = "HIGH"
        
        if len(self.safety_alerts) > 5:
            risk_level = "MEDIUM"
        
        # Update collision risk
        self.vehicle_state['collision_risk'].set(risk_level == "HIGH")
        
        # Update safety status in queue
        self.safety_queue.put(risk_level)
    
    def add_safety_alert(self, alert_type, message, severity, response):
        """Add safety alert"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        alert = {
            'timestamp': timestamp,
            'type': alert_type,
            'message': message,
            'severity': severity,
            'response': response
        }
        
        self.safety_alerts.append(alert)
        self.alert_queue.put((timestamp, alert_type, message, severity, response))
        self.log_message(f"🛡️ Safety Alert: {message}")
    
    def trigger_emergency_response(self):
        """Trigger emergency response"""
        self.vehicle_state['emergency_brake'].set(True)
        self.vehicle_state['abs_active'].set(True)
        
        # Send emergency brake message
        brake_msg = V2XProtocol.create_brake_message(100, abs_active=True)
        self.send_can_message(brake_msg)
        
        # Reduce speed
        current_speed = self.vehicle_state['speed'].get()
        self.vehicle_state['speed'].set(max(0, current_speed - 20))
        
        self.log_message("🚨 EMERGENCY RESPONSE ACTIVATED!")
        
        # Reset after 5 seconds
        self.root.after(5000, self.reset_emergency_state)
    
    def initiate_lane_change(self):
        """Simulate lane change for emergency vehicle"""
        self.log_message("🚗 Initiating lane change for emergency vehicle")
        
        # Simulate steering and lane change
        self.root.after(3000, lambda: self.log_message("✅ Lane change completed"))
    
    def send_collision_warning(self):
        """Send collision warning to other vehicles"""
        warning_msg = V2XProtocol.create_emergency_message(0x01, 0xFF, b'DANGER')
        self.send_can_message(warning_msg)
        self.add_safety_alert("COLLISION_WARNING", "Collision warning sent", "HIGH", "Transmitted")
    
    def clear_safety_alerts(self):
        """Clear all safety alerts"""
        self.safety_alerts.clear()
        self.collision_warnings.clear()
        
        # Clear tree views
        for item in self.safety_tree.get_children():
            self.safety_tree.delete(item)
        
        self.log_message("🧹 Safety alerts cleared")
    
    def reset_emergency_state(self):
        """Reset emergency state"""
        self.vehicle_state['emergency_brake'].set(False)
        self.vehicle_state['abs_active'].set(False)
        self.log_message("✅ Emergency state reset")
    
    def send_can_message(self, msg):
        """Send CAN message"""
        if self.can_interface.send_message(msg.arbitration_id, msg.data):
            self.messages_sent += 1
            self.can_logger.log_message(msg, "TX")
    
    def log_message(self, message):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        self.log_text.configure(state='normal')
        self.log_text.insert(tk.END, log_entry + '\n')
        self.log_text.see(tk.END)
        self.log_text.configure(state='disabled')
    
    def update_ui(self):
        """Update UI elements"""
        # Update gauges
        speed = self.vehicle_state['speed'].get()
        
        # Draw speed gauge
        speed_color = "red" if speed > SafetyThresholds.MAX_SPEED else "blue"
        self.draw_gauge(self.speed_canvas, speed, 120, speed_color)
        self.speed_value_label.configure(text=f"{speed:.1f}")
        
        # Update indicators
        if self.vehicle_state['abs_active'].get():
            self.abs_indicator.configure(text="ABS: ACTIVE", bg="orange")
        else:
            self.abs_indicator.configure(text="ABS: OFF", bg="lightgray")
        
        if self.vehicle_state['emergency_brake'].get():
            self.brake_indicator.configure(text="Emergency Brake: ON", bg="red")
        else:
            self.brake_indicator.configure(text="Emergency Brake: OFF", bg="lightgray")
        
        if self.vehicle_state['collision_risk'].get():
            self.collision_indicator.configure(text="Collision Avoidance: ACTIVE", bg="red")
        else:
            self.collision_indicator.configure(text="Collision Avoidance: READY", bg="lightgreen")
        
        # Update statistics
        self.sent_label.configure(text=f"Sent: {self.messages_sent}")
        self.received_label.configure(text=f"Received: {self.messages_received}")
        self.vehicles_label.configure(text=f"Other Vehicles: {len(self.other_vehicles)}")
        self.alerts_label.configure(text=f"Safety Alerts: {len(self.safety_alerts)}")
        
        # Process safety queue
        try:
            while True:
                risk_level = self.safety_queue.get_nowait()
                self.draw_safety_indicator(self.safety_canvas, risk_level)
                self.safety_status_label.configure(text=risk_level)
                self.risk_label.configure(text=risk_level)
                
                if risk_level == "LOW":
                    self.risk_label.configure(fg="green")
                elif risk_level == "MEDIUM":
                    self.risk_label.configure(fg="orange")
                else:
                    self.risk_label.configure(fg="red")
        except queue.Empty:
            pass
        
        # Process message queue
        try:
            while True:
                msg_type, *data = self.message_queue.get_nowait()
                if msg_type == 'v2x':
                    timestamp, can_id, msg_type, data_str, description = data
                    self.v2x_tree.insert('', 0, values=(timestamp, can_id, msg_type, data_str, description))
                    
                    # Keep only last 100 messages
                    children = self.v2x_tree.get_children()
                    if len(children) > 100:
                        self.v2x_tree.delete(children[-1])
        except queue.Empty:
            pass
        
        # Process alert queue
        try:
            while True:
                timestamp, alert_type, message, severity, response = self.alert_queue.get_nowait()
                self.safety_tree.insert('', 0, values=(timestamp, alert_type, message, severity, response))
                
                # Keep only last 50 alerts
                children = self.safety_tree.get_children()
                if len(children) > 50:
                    self.safety_tree.delete(children[-1])
        except queue.Empty:
            pass
        
        # Update other vehicles display
        self.update_vehicles_display()
        
        # Schedule next update
        self.root.after(100, self.update_ui)
    
    def update_vehicles_display(self):
        """Update other vehicles display"""
        # Clear existing items
        for item in self.vehicles_tree.get_children():
            self.vehicles_tree.delete(item)
        
        # Add current vehicles
        for vehicle_id, data in self.other_vehicles.items():
            last_seen = data['last_seen'].strftime("%H:%M:%S")
            self.vehicles_tree.insert('', 'end', values=(
                vehicle_id,
                f"{data['speed']:.1f} km/h",
                f"{data['distance']} m",
                last_seen,
                data['status']
            ))
        
        # Remove stale vehicles
        current_time = datetime.now()
        stale_vehicles = [vid for vid, data in self.other_vehicles.items() 
                         if (current_time - data['last_seen']).seconds > 10]
        for vid in stale_vehicles:
            del self.other_vehicles[vid]
    
    def on_closing(self):
        """Handle application closing"""
        self.stop_system()
        self.can_interface.disconnect()
        self.root.destroy()

def main():
    """Main function"""
    root = tk.Tk()
    app = VehicleBDashboard(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()