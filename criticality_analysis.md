# Software Criticality Analysis - LeCroy Oscilloscope

This analysis lists the technical and functional issues found in the current code, along with their resolution options.

## 1. Architecture and Threading (HIGHEST PRIORITY)

- [x] **Thread Pile-up**: Resolved with a "chain-link" system (SingleShot timer + Signals).
- [ ] **Interface Freezing**: (Option B suggested for the future).
- [ ] **Lack of Queueing**: (To be implemented if necessary).

## 2. Communication Reliability

- [x] **Variable Timeouts**: Dynamic timeouts implemented (1s basic, 15s screenshot).
- [x] **Resource Cleanup**: VISA sessions properly closed in `closeEvent`.

## 3. Screenshot and Memory Management

- [x] **CPU Load**: Image resizing moved into the Worker's thread.
- [x] **Fragile PNG Header**: Added integrity check verifying the PNG `IEND` footer.

## 4. User Experience (UX)

- [x] **Missing Feedback**: Added a Status Bar with real-time logging of instrument responses.
- [ ] **Monitor Scaling**: (Improved support, but flexible layout needs refinement).

## 5. Instrument Safety

- [x] **50 Ohm Protection**: The software prevents voltages > 5V if the instrument is in 50 Ohm mode.
- [x] **Error State**: Automatic check of the "Status Register" (`*ESR?`) after every command.

## 6. Synchronization (Auto-Sync)

- [x] **Passive Sync**: Automatic synchronization of main parameters every 5 refresh cycles.

---
> *Suggested next step: Start from Point 1 (Thread Pile-up) using Option B (Chain-link timer).*
