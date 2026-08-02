#!/usr/bin/env python3
"""
LIN-CAN Gateway Project - Main Entry Point
------------------------------------------
Complete LIN-CAN Gateway with UI, sender, receiver, and decoder
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
            logging.FileHandler("lin_can_gateway.log"),
            logging.StreamHandler()
        ]
    )

def run_ui():
    """Run the main UI application"""
    try:
        from ui_decode import LINCANGatewayApp
        import tkinter as tk
        
        root = tk.Tk()
        app = LINCANGatewayApp(root)
        root.protocol("WM_DELETE_WINDOW", app.on_closing)
        root.mainloop()
    except ImportError as e:
        print(f"Error importing UI components: {e}")
        print("Make sure all required modules are installed")
    except Exception as e:
        print(f"Error running UI: {e}")

def run_sender():
    """Run the sender test application"""
    try:
        import subprocess
        subprocess.run([sys.executable, "sender-code.py"])
    except Exception as e:
        print(f"Error running sender: {e}")

def run_receiver():
    """Run the receiver application"""
    try:
        import subprocess
        subprocess.run([sys.executable, "reciever-code.py"])
    except Exception as e:
        print(f"Error running receiver: {e}")

def run_pgn_test():
    """Run PGN file reader test"""
    try:
        import subprocess
        subprocess.run([sys.executable, "pgn_fileread.py"])
    except Exception as e:
        print(f"Error running PGN test: {e}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="LIN-CAN Gateway Project")
    parser.add_argument("mode", choices=["ui", "sender", "receiver", "pgn", "help"], 
                       help="Mode to run")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(log_level)
    
    if args.mode == "ui":
        print("Starting LIN-CAN Gateway UI...")
        run_ui()
    elif args.mode == "sender":
        print("Starting sender test...")
        run_sender()
    elif args.mode == "receiver":
        print("Starting receiver...")
        run_receiver()
    elif args.mode == "pgn":
        print("Starting PGN test...")
        run_pgn_test()
    elif args.mode == "help":
        print_help()

def print_help():
    """Print detailed help information"""
    help_text = """
LIN-CAN Gateway Project
======================

This project provides a complete LIN-CAN gateway implementation with:
- Graphical User Interface for monitoring and control
- CAN message sender for testing
- CAN message receiver with LIN translation
- J1939 decoder with SPN support

USAGE:
------
python main.py <mode> [options]

MODES:
------
ui       - Launch the graphical user interface (recommended)
sender   - Run CAN message sender for testing
receiver - Run CAN message receiver/gateway
pgn      - Run PGN file reader test
help     - Show this help message

OPTIONS:
--------
--debug  - Enable debug logging

EXAMPLES:
---------
python main.py ui                    # Start the GUI
python main.py sender --debug        # Run sender with debug logging
python main.py receiver              # Run receiver/gateway

SETUP:
------
1. Install dependencies: pip install -r requirements.txt
2. Setup virtual CAN (Linux): python setup_vcan.py
3. Run the application: python main.py ui

FILES:
------
main.py                 - This main entry point
ui_decode.py           - Main GUI application
sender-code.py         - CAN message sender
reciever-code.py       - CAN receiver/gateway
pgn_fileread.py        - PGN file reader
sample_spn_data.csv    - Sample SPN definitions
pgn.txt               - PGN list for testing
setup_vcan.py         - Virtual CAN setup script
requirements.txt      - Python dependencies
"""
    print(help_text)

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("LIN-CAN Gateway Project")
        print("Run 'python main.py help' for usage information")
        print("Quick start: python main.py ui")
    else:
        main()