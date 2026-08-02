#!/usr/bin/env python3
"""
Vehicle A Dashboard - Professional UI for V2X Primary Vehicle
Real-time visualization of CAN messages and V2X communications
"""

import sys
import os
import time
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext
from datetime import datetime
import queue
import math

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Shared'))

from can_protocol import CANMessageIDs, V2XProtocol, SafetyThresholds, get_message_description
from rpi_can_interface import RPiCANInterface, CANLogger

class VehicleADashboard:
    """Professional Dashboard for Vehicle A"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("🚗 Vehicle A - V2X Primary Controller Dashboard")
        self.root.geometry("1200x800")
        self.root.configure(bg='#2c3e50')
        
        # Initialize CAN interface
        self.can_interface = RPiCANInterface('can0')
        self.can_logger = CANLogger("vehicle_a_dashboard.log")
        self.running = False
        
        # Vehicle state
        self.vehicle_state = {
            'speed': tk.DoubleVar(value=0.0),
            'engine_rpm': tk.IntVar(value=800),
            'engine_temp': tk.IntVar(value=85),
            'brake_pressure': tk.IntVar(value=0),
            'fuel_level': tk.IntVar(value=75),
            'abs_active': tk.BooleanVar(value=False),
            'emergency_brake': tk.BooleanVar(value=False)
        }
        
        # UI queues for thread safety
        self.message_queue = queue.Queue()
        self.alert_queue = queue.Queue()
        
        # Message counters
        self.messages_sent = 0
        self.messages_received = 0
        self.v2x_alerts = []
        
        # Create UI
        self.create_ui()
        self.setup_simulation()
        
        # Start UI update loop
        self.update_ui()
    
    def create_ui(self):
        """Create the main dashboard UI"""
        # Main container
        main_frame = tk.Frame(self.root, bg='#2c3e50')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        title_label = tk.Label(main_frame, text="🚗 Vehicle A - V2X Primary Controller", 
                              font=('Arial', 18, 'bold'), fg='white', bg='#2c3e50')
        title_label.pack(pady=(0, 20))
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create tabs
        self.create_dashboard_tab()
        self.create_can_monitor_tab()
        self.create_v2x_tab()
        self.create_control_tab()
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
        
        # RPM gauge
        rpm_frame = tk.Frame(gauges_frame, bg='white', relief=tk.RAISED, bd=2)
        rpm_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        tk.Label(rpm_frame, text="Engine RPM", font=('Arial', 12, 'bold'), bg='white').pack(pady=5)
        self.rpm_canvas = tk.Canvas(rpm_frame, width=150, height=150, bg='white')
        self.rpm_canvas.pack(pady=5)
        self.rpm_value_label = tk.Label(rpm_frame, text="800", font=('Arial', 16, 'bold'), bg='white')
        self.rpm_value_label.pack()
        
        # Temperature gauge
        temp_frame = tk.Frame(gauges_frame, bg='white', relief=tk.RAISED, bd=2)
        temp_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        tk.Label(temp_frame, text="Engine Temp (°C)", font=('Arial', 12, 'bold'), bg='white').pack(pady=5)
        self.temp_canvas = tk.Canvas(temp_frame, width=150, height=150, bg='white')
        self.temp_canvas.pack(pady=5)
        self.temp_value_label = tk.Label(temp_frame, text="85", font=('Arial', 16, 'bold'), bg='white')
        self.temp_value_label.pack()
        
        # System indicators
        indicators_frame = ttk.LabelFrame(dashboard_frame, text="System Indicators")
        indicators_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.abs_indicator = tk.Label(indicators_frame, text="ABS: OFF", bg="lightgray", width=15)
        self.abs_indicator.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.brake_indicator = tk.Label(indicators_frame, text="Emergency Brake: OFF", bg="lightgray", width=20)
        self.brake_indicator.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Statistics
        stats_frame = ttk.LabelFrame(dashboard_frame, text="Message Statistics")
        stats_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.sent_label = ttk.Label(stats_frame, text="Sent: 0")
        self.sent_label.pack(side=tk.LEFT, padx=10)
        
        self.received_label = ttk.Label(stats_frame, text="Received: 0")
        self.received_label.pack(side=tk.LEFT, padx=10)
        
        self.alerts_label = ttk.Label(stats_frame, text="V2X Alerts: 0")
        self.alerts_label.pack(side=tk.LEFT, padx=10)
    
    def create_can_monitor_tab(self):
        """Create CAN message monitor tab"""
        can_frame = ttk.Frame(self.notebook)
        self.notebook.add(can_frame, text="🔌 CAN Monitor")
        
        # CAN message display
        columns = ('Time', 'ID', 'DLC', 'Data', 'Description')
        self.can_tree = ttk.Treeview(can_frame, columns=columns, show='headings', height=20)
        
        for col in columns:
            self.can_tree.heading(col, text=col)
            self.can_tree.column(col, width=120)
        
        scrollbar_can = ttk.Scrollbar(can_frame, orient=tk.VERTICAL, command=self.can_tree.yview)
        self.can_tree.configure(yscrollcommand=scrollbar_can.set)
        
        self.can_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_can.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_v2x_tab(self):
        """Create V2X communications tab"""
        v2x_frame = ttk.Frame(self.notebook)
        self.notebook.add(v2x_frame, text="📡 V2X Communications")
        
        # V2X controls
        controls_frame = ttk.LabelFrame(v2x_frame, text="V2X Controls")
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(controls_frame, text="Send Speed Warning", command=self.send_speed_warning).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(controls_frame, text="Emergency Brake", command=self.trigger_emergency_brake).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(controls_frame, text="Collision Alert", command=self.send_collision_alert).pack(side=tk.LEFT, padx=5, pady=5)
        
        # V2X alerts display
        alerts_frame = ttk.LabelFrame(v2x_frame, text="V2X Alerts & Communications")
        alerts_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ('Time', 'Type', 'Message', 'Severity')
        self.v2x_tree = ttk.Treeview(alerts_frame, columns=columns, show='headings', height=15)
        
        for col in columns:
            self.v2x_tree.heading(col, text=col)
            self.v2x_tree.column(col, width=150)
        
        scrollbar_v2x = ttk.Scrollbar(alerts_frame, orient=tk.VERTICAL, command=self.v2x_tree.yview)
        self.v2x_tree.configure(yscrollcommand=scrollbar_v2x.set)
        
        self.v2x_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_v2x.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_control_tab(self):
        """Create vehicle control tab"""
        control_frame = ttk.Frame(self.notebook)
        self.notebook.add(control_frame, text="🎮 Vehicle Control")
        
        # Manual controls
        manual_frame = ttk.LabelFrame(control_frame, text="Manual Vehicle Control")
        manual_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Speed control
        ttk.Label(manual_frame, text="Speed:").grid(row=0, column=0, padx=5, pady=5)
        self.speed_scale = ttk.Scale(manual_frame, from_=0, to=120, orient=tk.HORIZONTAL, length=200)
        self.speed_scale.grid(row=0, column=1, padx=5, pady=5)
        self.speed_scale.bind("<Motion>", self.update_manual_speed)
        
        # RPM control
        ttk.Label(manual_frame, text="RPM:").grid(row=1, column=0, padx=5, pady=5)
        self.rpm_scale = ttk.Scale(manual_frame, from_=800, to=6000, orient=tk.HORIZONTAL, length=200)
        self.rpm_scale.grid(row=1, column=1, padx=5, pady=5)
        self.rpm_scale.bind("<Motion>", self.update_manual_rpm)
        
        # Simulation controls
        sim_frame = ttk.LabelFrame(control_frame, text="Simulation Control")
        sim_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.auto_sim = tk.BooleanVar(value=True)
        ttk.Checkbutton(sim_frame, text="Auto Simulation", variable=self.auto_sim).pack(side=tk.LEFT, padx=5, pady=5)
        
        ttk.Button(sim_frame, text="Reset Values", command=self.reset_values).pack(side=tk.LEFT, padx=5, pady=5)
    
    def create_logs_tab(self):
        """Create system logs tab"""
        log_frame = ttk.Frame(self.notebook)
        self.notebook.add(log_frame, text="📋 System Logs")
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=25, width=100)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def draw_gauge(self, canvas, value, max_value, color="blue"):
        """Draw circular gauge"""
        canvas.delete("all")
        
        # Draw outer circle
        canvas.create_oval(10, 10, 140, 140, outline="black", width=3)
        
        # Calculate angle (270 degrees total, starting from bottom)
        angle = (value / max_value) * 270
        start_angle = 225  # Start from bottom left
        
        # Draw arc
        canvas.create_arc(15, 15, 135, 135, start=start_angle, extent=-angle, 
                         outline=color, width=8, style="arc")
        
        # Draw center dot
        canvas.create_oval(70, 70, 80, 80, fill=color)
        
        # Draw tick marks
        for i in range(0, int(max_value) + 1, int(max_value/10)):
            tick_angle = (i / max_value) * 270
            x1 = 75 + 55 * math.cos(math.radians(start_angle - tick_angle))
            y1 = 75 + 55 * math.sin(math.radians(start_angle - tick_angle))
            x2 = 75 + 45 * math.cos(math.radians(start_angle - tick_angle))
            y2 = 75 + 45 * math.sin(math.radians(start_angle - tick_angle))
            canvas.create_line(x1, y1, x2, y2, width=2)
    
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
            if self.auto_sim.get() and self.running:
                # Simulate speed changes
                current_speed = self.vehicle_state['speed'].get()
                if random.random() < 0.3:
                    new_speed = max(0, min(120, current_speed + random.uniform(-10, 15)))
                    self.vehicle_state['speed'].set(new_speed)
                
                # Simulate RPM based on speed
                speed = self.vehicle_state['speed'].get()
                rpm = 800 + (speed * 35) if speed > 0 else 800
                self.vehicle_state['engine_rpm'].set(int(rpm))
                
                # Simulate temperature
                temp = self.vehicle_state['engine_temp'].get()
                if rpm > 3000:
                    temp = min(temp + 1, 120)
                else:
                    temp = max(temp - 0.5, 85)
                self.vehicle_state['engine_temp'].set(int(temp))
            
            self.root.after(500, simulate)
        
        simulate()
    
    def simulation_loop(self):
        """Main simulation loop"""
        import random
        
        while self.running:
            try:
                # Send vehicle data
                speed = self.vehicle_state['speed'].get()
                rpm = self.vehicle_state['engine_rpm'].get()
                temp = self.vehicle_state['engine_temp'].get()
                
                # Send speed message
                speed_msg = V2XProtocol.create_speed_message(speed)
                self.send_can_message(speed_msg)
                
                # Send engine message
                engine_msg = V2XProtocol.create_engine_message(rpm, temp)
                self.send_can_message(engine_msg)
                
                # Check for speed warnings
                if speed > SafetyThresholds.MAX_SPEED:
                    self.add_v2x_alert("SPEED_WARNING", f"Speed {speed:.1f} km/h exceeds limit", "HIGH")
                
                time.sleep(0.2)  # 5Hz update rate
                
            except Exception as e:
                self.log_message(f"❌ Simulation error: {e}")
                time.sleep(1)
    
    def handle_can_message(self, msg):
        """Handle incoming CAN messages"""
        self.messages_received += 1
        
        # Add to message queue for UI update
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        can_id = f"0x{msg.arbitration_id:03X}"
        dlc = len(msg.data)
        data_str = " ".join(f"{b:02X}" for b in msg.data)
        description = get_message_description(msg.arbitration_id)
        
        self.message_queue.put(('can', timestamp, can_id, dlc, data_str, description))
        
        # Process V2X messages
        if msg.arbitration_id == CANMessageIDs.COLLISION_WARNING:
            self.add_v2x_alert("COLLISION_WARNING", "Collision warning received from other vehicle", "CRITICAL")
        elif msg.arbitration_id == CANMessageIDs.EMERGENCY_VEHICLE:
            self.add_v2x_alert("EMERGENCY_VEHICLE", "Emergency vehicle approaching", "HIGH")
    
    def send_can_message(self, msg):
        """Send CAN message"""
        if self.can_interface.send_message(msg.arbitration_id, msg.data):
            self.messages_sent += 1
            self.can_logger.log_message(msg, "TX")
    
    def add_v2x_alert(self, alert_type, message, severity):
        """Add V2X alert"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.alert_queue.put((timestamp, alert_type, message, severity))
        self.log_message(f"📡 V2X Alert: {message}")
    
    def send_speed_warning(self):
        """Send speed warning"""
        speed = self.vehicle_state['speed'].get()
        msg = V2XProtocol.create_speed_warning(speed, SafetyThresholds.MAX_SPEED)
        self.send_can_message(msg)
        self.add_v2x_alert("SPEED_WARNING", f"Speed warning sent: {speed:.1f} km/h", "HIGH")
    
    def trigger_emergency_brake(self):
        """Trigger emergency brake"""
        self.vehicle_state['emergency_brake'].set(True)
        msg = V2XProtocol.create_brake_message(100, abs_active=True)
        self.send_can_message(msg)
        
        emergency_msg = V2XProtocol.create_emergency_message(0x02, 0xFF, b'BRAKE!')
        self.send_can_message(emergency_msg)
        
        self.add_v2x_alert("EMERGENCY_BRAKE", "Emergency brake activated", "CRITICAL")
        
        # Reset after 3 seconds
        self.root.after(3000, lambda: self.vehicle_state['emergency_brake'].set(False))
    
    def send_collision_alert(self):
        """Send collision alert"""
        msg = V2XProtocol.create_emergency_message(0x01, 0xFF, b'DANGER')
        self.send_can_message(msg)
        self.add_v2x_alert("COLLISION_ALERT", "Collision alert sent to other vehicles", "CRITICAL")
    
    def update_manual_speed(self, event):
        """Update speed from manual control"""
        if not self.auto_sim.get():
            speed = self.speed_scale.get()
            self.vehicle_state['speed'].set(speed)
    
    def update_manual_rpm(self, event):
        """Update RPM from manual control"""
        if not self.auto_sim.get():
            rpm = self.rpm_scale.get()
            self.vehicle_state['engine_rpm'].set(int(rpm))
    
    def reset_values(self):
        """Reset all values to defaults"""
        self.vehicle_state['speed'].set(0.0)
        self.vehicle_state['engine_rpm'].set(800)
        self.vehicle_state['engine_temp'].set(85)
        self.vehicle_state['brake_pressure'].set(0)
        self.vehicle_state['emergency_brake'].set(False)
    
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
        rpm = self.vehicle_state['engine_rpm'].get()
        temp = self.vehicle_state['engine_temp'].get()
        
        # Draw gauges
        speed_color = "red" if speed > SafetyThresholds.MAX_SPEED else "green"
        self.draw_gauge(self.speed_canvas, speed, 120, speed_color)
        self.speed_value_label.configure(text=f"{speed:.1f}")
        
        rpm_color = "red" if rpm > 5000 else "blue"
        self.draw_gauge(self.rpm_canvas, rpm, 6000, rpm_color)
        self.rpm_value_label.configure(text=str(rpm))
        
        temp_color = "red" if temp > SafetyThresholds.MAX_ENGINE_TEMP else "orange"
        self.draw_gauge(self.temp_canvas, temp, 120, temp_color)
        self.temp_value_label.configure(text=f"{temp}°C")
        
        # Update indicators
        if self.vehicle_state['abs_active'].get():
            self.abs_indicator.configure(text="ABS: ACTIVE", bg="orange")
        else:
            self.abs_indicator.configure(text="ABS: OFF", bg="lightgray")
        
        if self.vehicle_state['emergency_brake'].get():
            self.brake_indicator.configure(text="Emergency Brake: ON", bg="red")
        else:
            self.brake_indicator.configure(text="Emergency Brake: OFF", bg="lightgray")
        
        # Update statistics
        self.sent_label.configure(text=f"Sent: {self.messages_sent}")
        self.received_label.configure(text=f"Received: {self.messages_received}")
        self.alerts_label.configure(text=f"V2X Alerts: {len(self.v2x_alerts)}")
        
        # Process message queue
        try:
            while True:
                msg_type, *data = self.message_queue.get_nowait()
                if msg_type == 'can':
                    timestamp, can_id, dlc, data_str, description = data
                    self.can_tree.insert('', 0, values=(timestamp, can_id, dlc, data_str, description))
                    
                    # Keep only last 100 messages
                    children = self.can_tree.get_children()
                    if len(children) > 100:
                        self.can_tree.delete(children[-1])
        except queue.Empty:
            pass
        
        # Process alert queue
        try:
            while True:
                timestamp, alert_type, message, severity = self.alert_queue.get_nowait()
                self.v2x_tree.insert('', 0, values=(timestamp, alert_type, message, severity))
                self.v2x_alerts.append((timestamp, alert_type, message, severity))
                
                # Keep only last 50 alerts
                children = self.v2x_tree.get_children()
                if len(children) > 50:
                    self.v2x_tree.delete(children[-1])
        except queue.Empty:
            pass
        
        # Schedule next update
        self.root.after(100, self.update_ui)
    
    def on_closing(self):
        """Handle application closing"""
        self.stop_system()
        self.can_interface.disconnect()
        self.root.destroy()

def main():
    """Main function"""
    root = tk.Tk()
    app = VehicleADashboard(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()