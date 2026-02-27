# TECHNICAL DOCUMENTATION: Professional Oscilloscope Suite

This documentation provides a detailed explanation of the logic, architecture, and technologies used in the control software for professional oscilloscopes.

---

## 1. Software Objective

The software allows full remote control of compatible oscilloscopes via Ethernet connection (TCP/IP). It is designed to provide a modern interface (GitHub Dark style) that overcomes the limitations of the old built-in web panels on the instruments.

## 2. Technological Architecture

The system is built entirely in **Python 3** using the following key components:

### A. Graphical Interface (PyQt6)

The interface is based on the **PyQt6** framework, chosen for:

- **High Performance**: Smooth handling of large PNG images coming from the oscilloscope's screen.
- **Advanced Styling**: Use of stylesheets (CSS-like) for a professional and dark mode aesthetic.
- **Signals and Slots**: A thread-safe communication system that allows the program's "engine" to talk to the "graphics" without freezing the window.

### B. VISA Communication (PyVISA)

To talk to the oscilloscope, the industrial standard **VISA** (Virtual Instrument Software Architecture) is used.

- **Backend**: Uses `pyvisa`, which interfaces with the NI-VISA or Keysight libraries installed on the PC.
- **Protocol**: TCP/IP (LXI). The oscilloscope is identified via its IP address with the string: `TCPIP::<IP>::INSTR`.

### C. Command Language (Automation Model)

In addition to standard SCPI commands (e.g., `*IDN?`), the software leverages the power of the instrument's **Automation Object Model** via **VBS** (Visual Basic Scripting) commands.

- This provides access to deep instrument functions (e.g., `app.Measure.P1.Out.Result.Value`) that would not be reachable with simple textual commands.

---

## 3. Code Structure (The Files)

- **`main.py`**: The entry point. Initializes the `QApplication` and starts the main window.
- **`main_gui.py`**: The visual core. Manages the 3-column layout, timers for the Live View, and the logic for displaying data.
- **`visa_worker.py`**: The background "engine". Executes the actual commands. It is separated from the GUI to prevent the program from hanging ("Not Responding") if the network is slow.
- **`widgets.py`**: Contains custom components, such as channel controls (Vertical) and safety popups.
- **`styles.py`**: Contains the aesthetic definitions (colors, borders, animations) to keep the GUI code clean.

---

## 4. Functionality of Key Modules

### The Live View System

1. A **Timer** triggers every 1.2 seconds.
2. A **separate Thread** is started, which requests the screenshot from the oscilloscope via the `SCDP` command.
3. The oscilloscope sends the binary dump of its screen.
4. The Worker searches for the PNG header (`\x89PNG...`) in the raw data.
5. The image is passed to the GUI, resized proportionally, and shown in the center monitor.

### Channel Management (Vertical)

Each channel has independent controls for Volt/Div, Offset, and Coupling.

- **50 Ohm Safety**: If the user selects "DC50", the software intercepts the action and shows a hazard warning before sending the command to the instrument (overvoltage protection).

### Data Export

The software can download the entire waveform of the selected channel in binary format (`.bin`), which is useful for subsequent analysis in MATLAB or Excel.

---

## 5. Usage Instructions

1. **Connection**: Enter the instrument's IP address and click **CONNECT**. If the connection is successful, the heartbeat indicator will turn green.
2. **Synchronization**: Click **SYNC FROM SCOPE** to read the oscilloscope's current settings and populate the interface.
3. **Live View**: Click **START LIVE** to see the oscilloscope screen in real-time.
4. **Snapshot**: Use the 📸 button to save a still image to your Desktop in the `Screenshots_Oscilloscope` folder.
5. **Auto-Apply**: If the box is checked, every modification on the GUI (e.g., changing Volt/Div) is instantly sent to the oscilloscope.

---

## 6. Safety

The software includes forced commands to:

- Prevent the oscilloscope from saving screenshots internally or on a USB drive (avoids "Disk Full" or "USB Not Found" errors).
- Force data output to the remote network port.

---
> Documentation written for Samuele Lorenzoni - February 2026
