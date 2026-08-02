#!/usr/bin/env python3
"""
Shared CAN interface using file-based communication
"""

import json
import time
import threading
import os
from datetime import datetime

class SharedCANBus:
    def __init__(self, channel='shared'):
        self.channel = channel
        self.msg_file = f"can_messages_{channel}.json"
        self.running = False
        self.callback = None
        self.monitor_thread = None
        
    def send(self, msg):
        """Send CAN message to shared file"""
        try:
            message_data = {
                'timestamp': time.time(),
                'arbitration_id': msg.arbitration_id,
                'data': list(msg.data),
                'dlc': len(msg.data)
            }
            
            # Read existing messages
            messages = []
            if os.path.exists(self.msg_file):
                try:
                    with open(self.msg_file, 'r') as f:
                        messages = json.load(f)
                except:
                    messages = []
            
            # Add new message
            messages.append(message_data)
            
            # Keep only last 100 messages
            if len(messages) > 100:
                messages = messages[-100:]
            
            # Write back to file
            with open(self.msg_file, 'w') as f:
                json.dump(messages, f)
                
        except Exception as e:
            print(f"Send error: {e}")
    
    def recv(self, timeout=1.0):
        """Receive CAN message from shared file"""
        start_time = time.time()
        last_count = 0
        
        while time.time() - start_time < timeout:
            try:
                if os.path.exists(self.msg_file):
                    with open(self.msg_file, 'r') as f:
                        messages = json.load(f)
                    
                    if len(messages) > last_count:
                        # Return newest message
                        msg_data = messages[-1]
                        
                        class CANMessage:
                            def __init__(self, arb_id, data):
                                self.arbitration_id = arb_id
                                self.data = bytes(data)
                                self.timestamp = time.time()
                        
                        last_count = len(messages)
                        return CANMessage(msg_data['arbitration_id'], msg_data['data'])
                
                time.sleep(0.01)
            except:
                time.sleep(0.01)
        
        return None
    
    def start_monitoring(self, callback):
        """Start monitoring for messages"""
        self.callback = callback
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def _monitor_loop(self):
        """Monitor loop for incoming messages"""
        last_count = 0
        
        while self.running:
            try:
                if os.path.exists(self.msg_file):
                    with open(self.msg_file, 'r') as f:
                        messages = json.load(f)
                    
                    if len(messages) > last_count:
                        # Process new messages
                        for msg_data in messages[last_count:]:
                            class CANMessage:
                                def __init__(self, arb_id, data):
                                    self.arbitration_id = arb_id
                                    self.data = bytes(data)
                                    self.timestamp = time.time()
                            
                            msg = CANMessage(msg_data['arbitration_id'], msg_data['data'])
                            if self.callback:
                                self.callback(msg)
                        
                        last_count = len(messages)
                
                time.sleep(0.05)
            except:
                time.sleep(0.05)
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
    
    def shutdown(self):
        """Shutdown bus"""
        self.stop_monitoring()
        # Clean up message file
        try:
            if os.path.exists(self.msg_file):
                os.remove(self.msg_file)
        except:
            pass