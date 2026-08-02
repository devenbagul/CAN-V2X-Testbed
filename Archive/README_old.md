# LIN-CAN Gateway Project

A complete implementation of a LIN-CAN gateway with graphical user interface, message processing, and J1939 decoding capabilities.

## Features

- **Graphical User Interface**: Complete UI for monitoring CAN/LIN messages
- **LIN-CAN Translation**: Bidirectional translation between LIN and CAN protocols
- **J1939 Decoder**: Decode J1939 messages using SPN definitions
- **Message Sender**: Test application for sending CAN messages
- **Message Receiver**: Gateway application for processing incoming messages
- **Real-time Monitoring**: Live display of CAN/LIN traffic

## Project Structure

```
CAN-LIN Project/
├── main.py                     # Main entry point
├── ui_decode.py               # GUI application
├── sender-code.py             # CAN message sender
├── reciever-code.py           # CAN receiver/gateway
├── pgn_fileread.py            # PGN file reader
├── main_cont_1.py             # Additional controller
├── updated-lin-can-gateway-ui.py  # Alternative UI
├── sample_spn_data.csv        # Sample SPN definitions
├── pgn.txt                    # PGN list for testing
├── setup_vcan.py              # Virtual CAN setup
├── requirements.txt           # Dependencies
└── README.md                  # This file
```

## Installation

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup virtual CAN interface (Linux):**
   ```bash
   python setup_vcan.py
   ```

3. **For Windows:** The application will use virtual interfaces for testing

## Usage

### Quick Start - GUI Application
```bash
python main.py ui
```

### Command Line Options
```bash
# Start GUI
python main.py ui

# Run message sender
python main.py sender

# Run receiver/gateway
python main.py receiver

# Run PGN test
python main.py pgn

# Show help
python main.py help
```

### GUI Features

1. **Gateway Tab:**
   - Connect to CAN interfaces
   - Start/stop gateway processing
   - View real-time messages
   - Monitor LIN-over-CAN traffic

2. **Decoder Tab:**
   - Load SPN definition CSV files
   - Manually decode CAN messages
   - View decoded parameter values

3. **Logs Tab:**
   - View application logs
   - Debug message processing
   - Monitor system status

## Configuration

### CAN Interface Setup

**Linux:**
```bash
# Physical CAN interface
sudo ip link set can0 up type can bitrate 500000

# Virtual CAN interface (for testing)
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0
```

**Windows:**
- Use virtual interface or CAN simulator
- The application supports python-can virtual interface

### SPN Database

Load your SPN definitions CSV file with columns:
- PGN: Parameter Group Number
- SPN: Suspect Parameter Number  
- Start Bit: Bit position in message
- Length: Number of bits
- Resolution: Scaling factor
- Offset: Value offset
- Min/Max: Valid range
- Description: Parameter description

## LIN-CAN Translation

The gateway translates between LIN and CAN protocols:

- **LIN to CAN**: LIN messages are encapsulated in CAN frames (ID range 0x700-0x73F)
- **CAN to LIN**: Specific PGN requests trigger LIN sensor queries
- **Bidirectional**: Real-time translation in both directions

### LIN Message IDs
- 0x11: Door Lock Status
- 0x12: Engine Temperature Sensor
- 0x13: Light Status
- 0x14: Window Position
- 0x22: Climate Control
- 0x33: Seat Position

## Testing

### Send Test Messages
```bash
python main.py sender
```

### Monitor Messages
```bash
python main.py receiver
```

### GUI Testing
1. Start the GUI: `python main.py ui`
2. Connect to vcan0 interface
3. Start the gateway
4. Run sender in another terminal
5. Observe messages in the GUI

## Troubleshooting

### Common Issues

1. **CAN Interface Not Found:**
   - Check interface is up: `ip link show`
   - Setup virtual CAN: `python setup_vcan.py`

2. **Permission Denied:**
   - Run with sudo for physical interfaces
   - Use virtual interfaces for testing

3. **Import Errors:**
   - Install dependencies: `pip install -r requirements.txt`
   - Check Python path

4. **No Messages Received:**
   - Verify CAN interface is active
   - Check bitrate settings match
   - Ensure sender and receiver use same interface

### Debug Mode
```bash
python main.py ui --debug
```

## Development

### Adding New Features

1. **New LIN Messages:** Update `lin_id_descriptions` in gateway classes
2. **New PGNs:** Add to `pgn_descriptions` mappings
3. **Custom Decoders:** Extend `CANDecoder` class
4. **UI Enhancements:** Modify `ui_decode.py`

### Code Structure

- **Gateway Logic:** `LINCANGateway` class handles protocol translation
- **UI Components:** `LINCANGatewayApp` provides graphical interface
- **Decoder:** `CANDecoder` processes J1939 messages
- **Message Handling:** Threaded processing for real-time operation

## License

This project is provided as-is for educational and development purposes.

## Support

For issues and questions:
1. Check the logs in the GUI Logs tab
2. Run with `--debug` flag for detailed logging
3. Verify CAN interface setup
4. Check sample files are present