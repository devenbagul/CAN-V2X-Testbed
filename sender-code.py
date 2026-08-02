#!/usr/bin/env python3
import can
import time
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("lin_can_test_sender.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('LIN-CAN-Test-Sender')

# Setup CAN interface (Windows compatible)
logger.info("Setting up CAN interface...")

# Open CAN bus interface
try:
    # Use shared virtual bus for better message passing
    from shared_bus import SharedCANInterface
    bus = SharedCANInterface()
    logger.info("Connected to shared virtual CAN bus successfully")
except Exception as e:
    logger.error(f"Failed to initialize shared CAN bus: {e}")
    # Fallback to regular virtual interface
    try:
        bus = can.interface.Bus(interface='virtual')
        logger.info("Connected to virtual CAN bus successfully")
    except Exception as e2:
        logger.error(f"Failed to initialize CAN bus: {e2}")
        logger.info("Note: On Windows, use virtual interface for testing")
        raise

def send_pgn_request(requested_pgn, source_address):
    """
    Send a PGN request over CAN bus
    
    Args:
        requested_pgn (int): The Parameter Group Number to request
        source_address (int): Source address for the CAN message
    """
    can_id = (requested_pgn << 8 | source_address)
    msg = can.Message(arbitration_id=can_id, data=[0xFF])
    try:
        bus.send(msg)
        logger.info(f"Sent PGN request: {requested_pgn} (0x{requested_pgn:X}), Source: {source_address}")
        return True
    except can.CanError as e:
        logger.error(f"Failed to transmit PGN request: {e}")
        return False

def send_lin_as_can(lin_id, lin_data_bytes, description=None):
    """
    Send a LIN message encapsulated in a CAN frame
    
    Args:
        lin_id (int): LIN identifier (0-63)
        lin_data_bytes (list): Data bytes for the LIN message
        description (str, optional): Description of the message for logging
    """
    if lin_id > 63:
        logger.warning(f"Invalid LIN ID: {lin_id}. Must be 0-63.")
        return False
        
    # Calculate LIN checksum (simple sum for demonstration)
    checksum = sum(lin_data_bytes) & 0xFF
    
    # Ensure data is maximum 7 bytes (leaving 1 byte for checksum in 8-byte CAN frame)
    if len(lin_data_bytes) > 7:
        lin_data_bytes = lin_data_bytes[:7]
        logger.warning(f"LIN data truncated to 7 bytes for ID 0x{lin_id:02X}")
    
    # Map to an unused CAN ID range (0x700-0x73F is used for LIN messages)
    lin_as_can_id = 0x700 + lin_id
    
    # Create padded data with checksum
    padded_data = lin_data_bytes + [checksum] + [0x00] * (7 - len(lin_data_bytes))
    
    lin_msg = can.Message(arbitration_id=lin_as_can_id, data=padded_data, is_extended_id=False)
    try:
        bus.send(lin_msg)
        desc_str = f" ({description})" if description else ""
        logger.info(f"Sent LIN-over-CAN message with ID 0x{lin_id:02X}{desc_str}: Data={[hex(b)[2:].zfill(2) for b in lin_data_bytes]}, Checksum={hex(checksum)}")
        return True
    except can.CanError as e:
        logger.error(f"Failed to transmit LIN message over CAN: {e}")
        return False

def receive_can_messages(timeout_seconds=2):
    """
    Receive and log CAN messages for the specified timeout period
    
    Args:
        timeout_seconds (float): How long to listen for messages
    
    Returns:
        list: List of received CAN messages
    """
    responses = []
    start_time = time.time()
    
    logger.info(f"Listening for responses for {timeout_seconds} seconds...")
    
    while time.time() - start_time < timeout_seconds:
        message = bus.recv(timeout=0.1)
        if message:
            # Check if this is a LIN-over-CAN message
            if 0x700 <= message.arbitration_id <= 0x73F:
                lin_id = message.arbitration_id - 0x700
                logger.info(f"Received LIN-over-CAN message with LIN ID: 0x{lin_id:02X}, Data: {[hex(b)[2:].zfill(2) for b in message.data]}")
            else:
                # Regular CAN message
                pgn = (message.arbitration_id >> 8) & 0x1FFFFF
                sa = message.arbitration_id & 0xFF
                logger.info(f"Received CAN message with ID: 0x{message.arbitration_id:X}, PGN: {pgn}, SA: {sa}, Data: {[hex(b)[2:].zfill(2) for b in message.data]}")
            
            responses.append(message)
    
    logger.info(f"Received {len(responses)} total responses")
    return responses

def run_lin_can_tests():
    """Run a series of LIN-CAN gateway tests"""
    # Path to file containing PGN values to request
    pgn_file_path = "/home/monarch/Desktop/PGN_Receiver/pgn.txt"
    
    try:
        with open(pgn_file_path, 'r') as file:
            pgn_list = [line.strip() for line in file.readlines()]
    except Exception as e:
        logger.error(f"Failed to read PGN file: {e}")
        # Define default PGNs for testing if file can't be read
        pgn_list = ["65108", "61444", "65267", "65262"]
    
    source_address = 254  # Source address for requests
    
    logger.info(f"Loaded {len(pgn_list)} PGNs for testing")
    
    # LIN message definitions for testing
    lin_test_messages = [
        {"id": 0x11, "data": [0xAA, 0xBB, 0xCC], "desc": "Door Lock Status: Locked"},
        {"id": 0x12, "data": [0x45], "desc": "Engine Temperature: 69°C"},
        {"id": 0x13, "data": [0x01, 0x02], "desc": "Light Status: Headlights On"},
        {"id": 0x14, "data": [0x32], "desc": "Window Position: 50% Open"},
        {"id": 0x22, "data": [0x05, 0x18], "desc": "Climate Control: AC On, 24°C"},
        {"id": 0x33, "data": [0x55, 0x66, 0x77, 0x88], "desc": "Seat Position: Driver Memory 1"}
    ]
    
    # Run tests for each PGN
    for i, pgn_str in enumerate(pgn_list):
        pgn = int(pgn_str)
        logger.info(f"\n\n=== TEST SCENARIO {i+1}: PGN {pgn} ===\n")
        
        # Test 1: Send some LIN messages over CAN
        logger.info("STEP 1: Sending LIN messages over CAN")
        for msg in lin_test_messages[:3]:  # Send first 3 LIN test messages
            send_lin_as_can(msg["id"], msg["data"], msg["desc"])
            time.sleep(0.1)
        
        # Receive any responses to our LIN messages
        receive_can_messages(1)
        
        # Test 2: Send PGN request and see if we get CAN responses
        # and/or LIN-over-CAN responses
        logger.info(f"\nSTEP 2: Sending PGN {pgn} request")
        send_pgn_request(pgn, source_address)
        responses = receive_can_messages(2)
        
        # Test 3: If this is a PGN known to trigger LIN messages,
        # verify we got the expected LIN-over-CAN response
        expected_lin_responses = {
            65108: 0x12,  # Engine Temperature -> LIN ID 0x12
            61444: 0x13,  # Electronic Engine Controller -> LIN ID 0x13
            65267: 0x33,  # Vehicle Position -> LIN ID 0x33
        }
        
        if pgn in expected_lin_responses:
            expected_lin_id = expected_lin_responses[pgn]
            found = False
            for msg in responses:
                if 0x700 <= msg.arbitration_id <= 0x73F:
                    lin_id = msg.arbitration_id - 0x700
                    if lin_id == expected_lin_id:
                        found = True
                        logger.info(f"Verified expected LIN response with ID 0x{lin_id:02X} for PGN {pgn}")
                        break
            
            if not found:
                logger.warning(f"Did not receive expected LIN response with ID 0x{expected_lin_id:02X} for PGN {pgn}")
        
        # Wait before next test
        time.sleep(1)
    
    logger.info("\n=== ALL TESTS COMPLETED ===")

def main():
    """Main entry point for the LIN-CAN test application"""
    try:
        logger.info("Starting LIN-CAN Gateway Test Application")
        run_lin_can_tests()
    except KeyboardInterrupt:
        logger.info("Test application terminated by user")
    except Exception as e:
        logger.error(f"Test application error: {e}")
    finally:
        if 'bus' in globals():
            bus.shutdown()
            logger.info("CAN bus interface shutdown")

if __name__ == "__main__":
    main()