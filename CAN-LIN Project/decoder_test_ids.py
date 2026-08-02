#!/usr/bin/env python3
"""
Decoder Test IDs
---------------
Shows the correct CAN IDs to use for testing the decoder
"""

def j1939_pgn_to_can_id(pgn, priority=6, source_address=0):
    """Convert PGN to J1939 CAN ID"""
    pdu_format = (pgn >> 8) & 0xFF
    pdu_specific = pgn & 0xFF
    
    if pdu_format < 240:
        # PDU1 format
        can_id = (priority << 26) | (pgn << 8) | source_address
    else:
        # PDU2 format  
        can_id = (priority << 26) | (pgn << 8) | source_address
    
    return can_id

def print_test_cases():
    """Print test cases for the decoder"""
    print("=== DECODER TEST CASES ===")
    print("Copy these into the Decoder tab:\n")
    
    # Test cases from our CSV
    test_cases = [
        (65108, "Engine Coolant Temperature"),
        (61444, "Engine Speed"), 
        (65267, "Vehicle Speed"),
        (65262, "Engine Coolant Temperature"),
    ]
    
    for pgn, description in test_cases:
        can_id = j1939_pgn_to_can_id(pgn)
        print(f"{description}:")
        print(f"  CAN ID (hex): {can_id:X}")
        print(f"  Data (hex): 55 23 FF FF FF FF FF FF")
        print()
    
    # LIN test cases
    print("LIN Messages:")
    lin_cases = [
        (0x11, "Door Lock Status"),
        (0x12, "Engine Temperature Sensor"),
        (0x14, "Window Position"),
    ]
    
    for lin_id, description in lin_cases:
        can_id = 0x700 + lin_id
        print(f"{description}:")
        print(f"  CAN ID (hex): {can_id:X}")
        print(f"  Data (hex): 11 22 33 44 55 66 77 88")
        print()

if __name__ == "__main__":
    print_test_cases()