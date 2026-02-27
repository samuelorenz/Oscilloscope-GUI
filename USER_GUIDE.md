# User Guide for LeCroy Oscilloscope GUI

This graphical user interface (GUI) allows you to easily control a LeCroy oscilloscope over a network (TCP/IP).

## Requirements

- Python 3.x
- Libraries: `PyQt6`, `pyvisa`, `pyvisa-py` (or NI-VISA)
- Network connection to the oscilloscope

## Features

1. **Connection**: Enter the IP address of your oscilloscope and click **CONNECT**. The status bar will confirm the successful connection.
2. **Horizontal**: Set the time base (Time/Division).
3. **Vertical**: Control Channel 1 (Activation, Volt/Division, Offset).
4. **Trigger**: Set the mode (Auto, Normal, Single, Stop), source, slope, and level.
5. **Sync from Scope**: Reads the current parameters from the oscilloscope and updates the interface.
6. **Apply Settings**: Sends all parameters set on the GUI to the oscilloscope.
7. **Get Screenshot**: Captures and previews the oscilloscope screen directly in the interface.

## Execution

To start the GUI, open your terminal or command prompt in the directory where the file is located and run the following command:

```bash
# This uses the default 'python' command to execute the script.
# Make sure Python 3.x is installed and added to your system's PATH.
# The script 'gui_oscilloscopio_pro.py' contains the main application logic.
python gui_oscilloscopio_pro.py
```

Or if you are using the Windows Python Launcher (`py.exe`), which automatically finds the installed Python version:

```bash
# 'py' is the Python Launcher for Windows.
# It's an alternative to calling 'python' directly and helps manage multiple Python versions.
# Executing this will launch the PyQt6 interface for the oscilloscope.
py gui_oscilloscopio_pro.py
```
