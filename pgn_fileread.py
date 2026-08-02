import can
import time

# Windows compatible setup
try:
    bus = can.interface.Bus(interface='virtual')
    print("Connected to virtual CAN interface")
except Exception as e:
    print(f"Failed to connect to CAN: {e}")
    print("Using virtual interface for testing")
    bus = can.interface.Bus(interface='virtual')
import os
pgn_file_path = os.path.join(os.path.dirname(__file__), 'pgn.txt')
if not os.path.exists(pgn_file_path):
    pgn_file_path = 'pgn.txt'
file = open(pgn_file_path, 'r')
x = file.readlines()
print(x)

def send_pgn_request(requested_pgn, source_address):
    can_id = (requested_pgn << 8 | source_address)
    msg = can.Message(arbitration_id=can_id, data=[0xFF])
    try:
        bus.send(msg)
        print("Sent PGN request:", requested_pgn)
        print(msg)
    except can.CanError as e:
        print("Failed to transmit PGN request:", e)

def send_lin_as_can(lin_id, lin_data_bytes):
    padded_data = lin_data_bytes + [0x00] * (8 - len(lin_data_bytes))
    lin_as_can_id = 0x700 + lin_id
    lin_msg = can.Message(arbitration_id=lin_as_can_id, data=padded_data, is_extended_id=False)
    try:
        bus.send(lin_msg)
        print(f"Sent LIN-over-CAN message with ID 0x{lin_id:02X}: Data={padded_data}")
    except can.CanError as e:
        print("Failed to transmit LIN message over CAN:", e)

def main():
    i = 0
    while i != len(x):
        print(int(x[i][:-1]))
        requested_pgn = int(x[i][:-1])
        source_address = 254

        # ✅ Send simulated LIN message first
        send_lin_as_can(0x12, [0x11, 0x22, 0x33])

        # ✅ Then send actual CAN PGN request
        send_pgn_request(requested_pgn, source_address)
        print("Waiting for responses...")

        responses = []
        start_time = time.time()
        timeout = 2

        while True:
            message = bus.recv(timeout=0.1)
            if message:
                responses.append(message)
                print("Response received:", message)
            elif time.time() - start_time > timeout:
                break

        print(f"Received {len(responses)} responses. You can send another request.")
        i += 1
        time.sleep(0.01)

if __name__ == "__main__":
    main()
    file.close()