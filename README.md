# LeCroy SDA 812zi Professional Suite – Oscilloscope GUI

Advanced Graphical Interface in **Python / PyQt6** for remote control of **LeCroy** oscilloscopes (e.g., SDA series, WaveMaster) via **TCP/IP (LXI)** network.

The goal is to replace the old built-in web panels with a modern dark-mode GUI, optimized for:

- Fast control of **timebase, channels, triggers, and measurements**
- **Live view** of the instrument's screen
- Saving **screenshots** and **waveforms** for subsequent analysis

---

## Main Features

- **TCP/IP Connection** to LeCroy oscilloscopes (`TCPIP::<IP>::INSTR`)
- **Full Control of Channels (C1–C4)**:
  - Trace ON/OFF
  - Volt/Division, Offset, Coupling, Bandwidth limit, Invert
  - **SAVE DATA** quick button to export the waveform in binary format
- **Trigger Management**:
  - Mode (AUTO, NORM, SINGLE, STOP)
  - Type (EDGE, WIDTH, GLITCH, TV)
  - Source, slope, level
- **Live Screen Monitor**:
  - Periodic screen update using the `SCDP` command
  - Real-time resized visualization
  - Saves screenshots to the Desktop (`Screenshots_Oscilloscope`)
- **Automatic Measurements**:
  - Parameter configuration (P1, P2, …) via VBS
  - Reading values like PKPK, MAX, MIN, FREQ, PERIOD
- **Robust Architecture**:
  - VISA worker runs in a separate **QThread** (`visa_worker.py`) from the GUI (`main_gui.py`)
  - Thread-safe communication via **PyQt6 signals/slots**
  - Safety checks on 50 Ω coupling and high voltages

---

## Requirements

- **Python** 3.9+ (recommended)
- Python Dependencies listed in `requirements.txt`:
  - `PyQt6`
  - `pyvisa`
  - `pyvisa-py` (or NI‑VISA as the backend)
- A compatible LeCroy oscilloscope, reachable over the network (same IP subnet as the PC)

Installation Example (Virtual Environment recommended):

```bash
# Create a virtual environment
python -m venv .venv
# Activate it on Windows
.venv\Scripts\activate
# Install requirements
pip install -r requirements.txt
```

If you use NI-VISA, install the package from the National Instruments website and configure `pyvisa` to use that backend.

---

## Project Structure

- `main.py` – main entry point: creates the `QApplication` and opens the `OscilloscopeGUI` window.
- `main_gui.py` – main 3-column GUI (system status, monitor, channels) + menu, live timer, event log.
- `visa_worker.py` – PyQt worker running in a **QThread**:
  - handles VISA connection, SCPI/VBS commands, screenshots, measurements, waveform export, settings sync.
- `widgets.py` – custom widgets, specifically `ChannelControl` for each C1–C4 channel.
- `styles.py` – GitHub-style dark theme (global stylesheet `STYLE_MAIN`).
- `USER_GUIDE.md` – User Guide (operational usage).
- `TECHNICAL_DOCUMENTATION.md` – Detailed technical documentation (architecture, workflows, commands).

The `oscilloscope_gui_pro.py` file contains an older "monolithic" version (GUI + worker in the same file), which is now out-of-date and superseded by the new modular architecture (`main.py` + `main_gui.py` + `visa_worker.py` + `widgets.py` + `styles.py`).

---

## Installation and Execution

1. **Clone the repository** or copy the project folder.
2. (Optional but recommended) create a **virtualenv** and install the requirements:

    ```bash
    # Create the virtual environment
    python -m venv .venv
    # Activate the virtual environment
    .venv\Scripts\activate
    # Install the dependencies mapped out in requirements.txt
    pip install -r requirements.txt
    ```

3. Ensure the oscilloscope is:
   - Reachable via IP from your machine
   - Configured to accept LXI/TCPIP connections.

4. Start the GUI:

    ```bash
    # This will execute the main file starting the script.
    python main.py
    ```

    Alternatively, you can launch the older monolithic version:

    ```bash
    # This launches the old monolithic version.
    python oscilloscope_gui_pro.py
    ```

---

## Quick Start

- **Connection**
  - Enter the oscilloscope's IP address in the `IP` field.
  - Click **CONNECT**.
  - If the connection is successful, the log will show the `*IDN?` query result and the interface state will switch to connected.

- **Settings Synchronization**
  - Click **SYNC FROM SCOPE** to read:
    - timebase (`TIME_DIV`)
    - channel status (TRACE, VOLT_DIV, OFFSET, COUPLING, BANDWIDTH, INVERT)
    - trigger parameters (MODE, TYPE, SRC, LEVEL).
  - The GUI updates without sending any new application commands back to the instrument.

- **Apply Settings**
  - Modify channels, timebase, or trigger in the GUI.
  - Click **APPLY TO SCOPE** to send all commands in bulk (`send_multiple_commands` inside the worker).

- **Live View & Screenshot**
  - Click **▶ START LIVE STREAM** to enable the live screen refresh:
    - the worker cyclically sends `HCSU` + `SCDP` commands and passes a `QImage` to the GUI
    - every N cycles, settings synchronization is also executed.
  - Click **📸 SNAPSHOT** for a single capture.
  - Enable **AUTO-SAVE LIVE** to automatically save screenshots in:
    - `Desktop/Screenshots_Oscilloscope`

- **Measurements**
  - Choose **Source** (C1–C4) and **Type** (PKPK, MAX, MIN, FREQ, PERIOD).
  - In live mode, upon each cycle the worker updates the table with the current value.

For deeper details see `USER_GUIDE.md` and `TECHNICAL_DOCUMENTATION.md`.

---

## Safety Notes

- When coupling is set to **DC50** (50 Ω) the software:
  - displays an explicit **warning** on the GUI side (`ChannelControl.validate_coupling_change`)
  - prevents potentially dangerous Volt/Div sizes from the worker side (`send_command` in `visa_worker.py`),
    blocking commands that exceed a certain threshold with a 50 Ω input.
- During **cleanup** (closing the application) the worker:
  - restores the instrument's initial hardcopy/screenshot configuration
  - properly releases VISA resources.

Regardless, it is ultimately the user's responsibility to adhere to the oscilloscope's voltage limits and safety specifications!

---

## Debug and Code Status

- The main Python files (`main.py`, `main_gui.py`, `visa_worker.py`, `widgets.py`, `oscilloscope_gui_pro.py`) contain **no linting errors** and use a coherent structure.
- Communication between GUI and worker is managed via **QThread** and signals/slots, avoiding the `threading` module entirely within the new architecture.
- The worker implements **busy state** controls to avoid concurrent requests and properly handles VISA errors mapping them into straightforward log messages.

If you encounter specific runtime errors (e.g., VISA connection issues, crashes, or strange behaviors), open a **GitHub issue** including:

- Python version
- PyQt6/pyvisa/VISA backend version
- LeCroy oscilloscope model and its firmware
- The explicit error message logged inside the console or the interface's built-in log.
