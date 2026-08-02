#!/usr/bin/env python3
"""
Shared Virtual CAN Bus
----------------------
Creates a shared virtual CAN bus that all components can use
"""

import can
import threading
import time
import queue
import logging

class SharedVirtualBus:
    """Shared virtual CAN bus that allows message passing between components"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, 'initialized'):
            return
        
        self.initialized = True
        self.subscribers = []
        self.message_queue = queue.Queue()
        self.running = True
        self.dispatcher_thread = threading.Thread(target=self._message_dispatcher, daemon=True)
        self.dispatcher_thread.start()
        logging.info("Shared virtual CAN bus initialized")
    
    def subscribe(self, callback):
        """Subscribe to receive messages"""
        self.subscribers.append(callback)
        logging.info(f"New subscriber added. Total: {len(self.subscribers)}")
    
    def unsubscribe(self, callback):
        """Unsubscribe from messages"""
        if callback in self.subscribers:
            self.subscribers.remove(callback)
            logging.info(f"Subscriber removed. Total: {len(self.subscribers)}")
    
    def send_message(self, msg):
        """Send a message to all subscribers"""
        self.message_queue.put(msg)
        logging.info(f"Message queued: ID=0x{msg.arbitration_id:X}")
    
    def _message_dispatcher(self):
        """Dispatch messages to all subscribers"""
        while self.running:
            try:
                msg = self.message_queue.get(timeout=0.1)
                for callback in self.subscribers:
                    try:
                        callback(msg)
                    except Exception as e:
                        logging.error(f"Error in subscriber callback: {e}")
            except queue.Empty:
                continue
            except Exception as e:
                logging.error(f"Error in message dispatcher: {e}")
    
    def shutdown(self):
        """Shutdown the shared bus"""
        self.running = False
        if self.dispatcher_thread.is_alive():
            self.dispatcher_thread.join(timeout=1)
        logging.info("Shared virtual CAN bus shutdown")

class SharedCANInterface:
    """CAN interface that uses the shared virtual bus"""
    
    def __init__(self):
        self.shared_bus = SharedVirtualBus()
        self.message_callback = None
        
    def send(self, msg):
        """Send a message via shared bus"""
        self.shared_bus.send_message(msg)
        
    def recv(self, timeout=None):
        """Receive messages (not implemented for shared bus)"""
        # For shared bus, we use callbacks instead
        return None
        
    def set_callback(self, callback):
        """Set callback for received messages"""
        if self.message_callback:
            self.shared_bus.unsubscribe(self.message_callback)
        self.message_callback = callback
        self.shared_bus.subscribe(callback)
        
    def shutdown(self):
        """Shutdown this interface"""
        if self.message_callback:
            self.shared_bus.unsubscribe(self.message_callback)