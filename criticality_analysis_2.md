# Software Criticality Analysis - Oscilloscope - Phase 2

In this second analysis, we explore latent bugs, bottlenecks, and stability improvements based on the logical "stress test".

## 1. Exception Handling and GUI Locking (HIGH PRIORITY)

- [ ] **Permanent Block States**: In `apply_synced_settings`, if an exception occurs mid-parsing (e.g., corrupted data from the instrument), the `self._is_gui_updating` flag remains `True`, permanently preventing the user from modifying the GUI.
  - **Resolution**: Use a `try...finally` block to ensure the flag is reset.
- [ ] **Blocked Signals post-Error**: Similarly, if `blockSignals(True)` is called and the code crashes before `False`, the widget becomes "dead".

## 2. Performance Optimization (Live View)

- [ ] **Query Serialization**: `fetch_all_settings` runs around 30 individual queries. On slow networks or older instruments, this can take seconds, blocking the Worker and delaying user inputs.
  - **Resolution**: Batch critical readings or make synchronization "lazy" (active channels only).
- [ ] **Screenshot Signal Overhead**: Sending raw `bytes` via a signal and then converting them into a `QImage` and then a `QPixmap` can be optimized using references or shared buffers if speed increases.

## 3. Code Robustness (Discovered Bugs)

- [ ] **Crash on Window Resize**: If the window is minimized to zero width/height, `target_size` in `main_gui.py` could generate invalid values for scaling.
- [ ] **Fragile DAT1 Export**: `WAVEFORM? DAT1` downloads binary data requiring specific parsing of the LeCroy header (WAVEDESC) to be useful in CSV/Excel. Currently, we only save a raw binary blob that is difficult to read.
- [ ] **Hardcoded Default IP**: If the instrument doesn't respond, the 5s timeout during the first connection blocks the thread (now fixed in a thread, but lacks an "Abort Connect" button).

## 4. New Safety Features

- [ ] **Input Protection Check**: If a channel is in 50 Ohm mode, the physical offset knob has tighter limits (usually +/- 5V or less). Exceeding these limits via software can cause an "Internal Error" within the instrument.
- [ ] **Lack of Permanent Log**: Console errors (`log_txt`) are lost upon exiting.
  - **Option**: Automatically save a `session.log` file.

## 5. Autotest Proposal

- [ ] **VISA Mocking**: Create a script that acts as an oscilloscope to test the 50 Ohm protection logic without risking real hardware.
