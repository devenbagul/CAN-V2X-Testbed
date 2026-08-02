#!/usr/bin/env python3
"""
V2X Automotive CAN System - Main Entry Point
--------------------------------------------
Professional CAN-based vehicle safety and V2X communication system
"""

import sys
import os
import argparse
import logging

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def setup_logging(level=logging.INFO):
    """Setup logging configuration"""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("v2x_system.log"),
            logging.StreamHandler()
        ]
    )

def run_ui():
    """Run the main V2X UI application"""
    try:
        from v2x_ui import V2XSystemApp
        import tkinter as tk
        
        root = tk.Tk()
        app = V2XSystemApp(root)
        root.protocol("WM_DELETE_WINDOW", app.on_closing)
        root.mainloop()
    except ImportError as e:
        print(f"Error importing V2X UI components: {e}")
        print("Make sure all required modules are installed")
    except Exception as e:
        print(f"Error running V2X UI: {e}")

def run_vehicle_simulator():
    """Run the vehicle simulator"""
    try:
        from v2x_simulator import V2XSimulator
        simulator = V2XSimulator()
        simulator.start_simulation()
    except Exception as e:
        print(f"Error running vehicle simulator: {e}")

def run_safety_monitor():
    """Run the safety monitoring system"""
    try:
        from v2x_safety import V2XSafetySystem
        safety = V2XSafetySystem()
        safety.monitor_messages()
    except Exception as e:
        print(f"Error running safety monitor: {e}")

def run_v2x_gateway():
    """Run V2X communication gateway"""
    try:
        from v2x_ui import V2XSystemApp
        import tkinter as tk
        root = tk.Tk()
        app = V2XSystemApp(root)
        root.protocol("WM_DELETE_WINDOW", app.on_closing)
        root.mainloop()
    except Exception as e:
        print(f"Error running V2X gateway: {e}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="V2X Automotive CAN System")
    parser.add_argument("mode", choices=["ui", "simulator", "safety", "v2x", "help"], 
                       help="Mode to run")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(log_level)
    
    if args.mode == "ui":
        print("Starting V2X System UI...")
        run_ui()
    elif args.mode == "simulator":
        print("Starting Vehicle Simulator...")
        run_vehicle_simulator()
    elif args.mode == "safety":
        print("Starting Safety Monitor...")
        run_safety_monitor()
    elif args.mode == "v2x":
        print("Starting V2X Gateway...")
        run_v2x_gateway()
    elif args.mode == "help":
        print_help()

def print_help():
    """Print detailed help information"""
    help_text = """
V2X Automotive CAN System
========================

This system provides comprehensive CAN-based vehicle safety and V2X communication:
- Real-time vehicle system monitoring (Engine, Brakes, Airbags, Steering)
- V2X safety alerts (Speed warnings, Emergency braking, Collision avoidance)
- Professional automotive-grade CAN communication
- Cross-platform support (Windows virtual, Linux real CAN)

USAGE:
------
python main.py <mode> [options]

MODES:
------
ui         - Launch the main V2X system interface (recommended)
simulator  - Run vehicle ECU simulator
safety     - Run safety monitoring system
v2x        - Run V2X communication gateway
help       - Show this help message

OPTIONS:
--------
--debug    - Enable debug logging

EXAMPLES:
---------
python main.py ui                    # Start the main UI
python main.py simulator --debug     # Run simulator with debug logging
python main.py safety               # Run safety monitor

SETUP (Linux):
--------------
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0

FEATURES:
---------
• Engine Control Unit (ECU) simulation
• Anti-lock Braking System (ABS) monitoring
• Airbag deployment system
• Electronic Stability Control (ESC)
• V2X speed limit warnings
• Emergency collision alerts
• Real-time CAN message monitoring
• Professional automotive UI
"""
    print(help_text)

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("V2X Automotive CAN System")
        print("Run 'python main.py help' for usage information")
        print("Quick start: python main.py ui")
    else:
        main()