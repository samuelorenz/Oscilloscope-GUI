# User Guide for Professional Oscilloscope GUI

This graphical user interface (GUI) allows you to easily control a compatible oscilloscope over a network (TCP/IP).

## Requirements

- Python 3.9+
- Libraries: `PyQt6`, `pyvisa`, `pyvisa-py`, `python-vxi11`, `zeroconf`
- Network connection to the oscilloscope

## Features

1. **Connection**: Enter the IP address of your oscilloscope and click **CONNECT**. The status bar will confirm the successful connection.
2. **Horizontal**: Set the time base (Time/Division).
3. **Vertical**: Control Channels 1-4 (Activation, Volt/Division, Offset, Coupling, Bandwidth).
4. **Trigger**: Set the mode (Auto, Normal, Single, Stop), type, source, slope, and level.
5. **Sync from Scope**: Reads the current parameters from the oscilloscope and updates the interface.
6. **Apply Settings**: Sends all parameters set on the GUI to the oscilloscope.
7. **Get Screenshot**: Captures and previews the oscilloscope screen directly in the interface.
8. **Live Stream**: Starts a real-time refresh of the screen and measurements.

## Execution

To start the GUI, open your terminal or command prompt in the project directory and run:

```bash
# Using Python directly
python main.py
```

Professional Oscilloscope Suite is designed for high-performance interaction with remote instruments.
