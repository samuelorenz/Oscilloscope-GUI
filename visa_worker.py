import pyvisa
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QImage
import pyvisa.errors
import time
import os

class OscilloscopeWorker(QObject):
    """Worker class for true QThread VISA communication. No threading module allowed."""
    connected = pyqtSignal(str)
    error = pyqtSignal(str)
    response = pyqtSignal(str)
    screenshot_ready = pyqtSignal(QImage)
    measure_ready = pyqtSignal(list)
    export_finished = pyqtSignal(str)
    settings_ready = pyqtSignal(dict)
    refresh_cycle_complete = pyqtSignal()
    busy_state = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.rm = None
        self.instrument = None
        self._is_connected = False
        self._is_busy = False

    def _safety_check_command(self, cmd: str) -> bool:
        """
        Software-side safety checks for 50 Ohm protection:
        - Limits Volt/Div if the channel is in DC50.
        - Limits OFFSET if the channel is in DC50.
        Returns True if the command is safe to execute, False otherwise.
        """
        upper = cmd.upper()
        try:
            if ":VOLT_DIV" in upper or ":OFFSET" in upper:
                parts = cmd.split()
                if len(parts) < 2:
                    return True
                value = float(parts[1])
                ch = parts[0].split(':')[0]
                cpl = self.instrument.query(f"{ch}:COUPLING?").strip().upper()

                # Conservative limits for 50 Ohm coupling
                if cpl == "D50":
                    if ":VOLT_DIV" in upper and value > 5.0:
                        self.error.emit(f"SAFETY ERROR: {parts[0]} in 50 Ω - Volt/Div {value}V is too high.")
                        return False
                    if ":OFFSET" in upper and abs(value) > 5.0:
                        self.error.emit(f"SAFETY ERROR: {parts[0]} in 50 Ω - Offset {value}V is out of safe range.")
                        return False
        except pyvisa.errors.VisaIOError as e:
            self.error.emit(f"VISA Error in safety checks (COUPLING?): {str(e)}")
            return False
        except Exception as e:
            self.error.emit(f"System Error in safety checks: {str(e)}")
            return False

        return True

    @pyqtSlot()
    def cleanup(self):
        """Safely restore instrument state and close VISA resources."""
        if not self.instrument:
            self.error.emit("VISA Error in cleanup: No connected instrument to clean up.")
            return
        
        try:
            self.instrument.write('HCSU DEV, PNG, PORT, PRINT')
            self.instrument.write('VBS "app.Hardcopy.AutoSave = ""None"""')
            self.instrument.write('*GTL') # Go To Local 
        except pyvisa.errors.VisaIOError as e:
            self.error.emit(f"VISA Error in cleanup (State restore): {str(e)}")
        except Exception as e:
            self.error.emit(f"System Error in cleanup (State restore): {str(e)}")
            
        try:
            self.instrument.close()
            if self.rm:
                self.rm.close()
        except pyvisa.errors.VisaIOError as e:
            self.error.emit(f"VISA Error in cleanup (Resource close): {str(e)}")
        except Exception as e:
            self.error.emit(f"System Error in cleanup (Resource close): {str(e)}")
        finally:
            self._is_connected = False
            self.instrument = None
            self.rm = None

    @pyqtSlot(str)
    def connect_to_scope(self, ip_address):
        try:
            if not self.rm:
                self.rm = pyvisa.ResourceManager()
            resource_string = f'TCPIP::{ip_address}::INSTR'
            self.instrument = self.rm.open_resource(resource_string)
            self.instrument.timeout = 5000
            
            self.instrument.clear()
            idn = self.instrument.query('*IDN?')
            self.instrument.write('COMM_HEADER OFF')
            self.instrument.write('HCSU DEV, PNG, PORT, REMOTE')
            
            self._is_connected = True
            self.connected.emit(idn.strip())
        except pyvisa.errors.VisaIOError as e:
            self._is_connected = False
            self.error.emit(f"VISA Error in connect_to_scope: {str(e)}")
        except Exception as e:
            self._is_connected = False
            self.error.emit(f"System Error in connect_to_scope: {str(e)}")

    @pyqtSlot(str)
    def send_command(self, cmd):
        if not self._is_connected:
            self.error.emit(f"Error in send_command: Instrument not connected, unable to send {cmd}.")
            return
            
        if self._is_busy:
            self.error.emit(f"Error in send_command: Worker is busy, unable to send {cmd}.")
            return

        if not self._safety_check_command(cmd):
            return

        self._is_busy = True
        try:
            self.instrument.write(cmd)
            esr = self.instrument.query("*ESR?").strip()
            self.response.emit(f"Cmd OK | ESR: {esr}")
        except pyvisa.errors.VisaIOError as e:
            self._is_connected = False
            self.error.emit(f"VISA Error in send_command (Execution of {cmd}): {str(e)}")
        except Exception as e:
            self.error.emit(f"System Error in send_command (Execution of {cmd}): {str(e)}")
        finally:
            self._is_busy = False

    @pyqtSlot(list)
    def send_multiple_commands(self, cmds):
        if not self._is_connected:
            self.error.emit("Error in send_multiple_commands: Instrument not connected.")
            return
            
        if self._is_busy:
            self.error.emit("Error in send_multiple_commands: Worker currently busy.")
            return
        
        self._is_busy = True
        self.busy_state.emit(True)
        try:
            for cmd in cmds:
                if not self._safety_check_command(cmd):
                    continue
                self.instrument.write(cmd)
            esr = self.instrument.query("*ESR?").strip()
            self.response.emit(f"Bulk Commands OK | ESR: {esr}")
        except pyvisa.errors.VisaIOError as e:
            self._is_connected = False
            self.error.emit(f"VISA Error in send_multiple_commands: {str(e)}")
        except Exception as e:
            self.error.emit(f"System Error in send_multiple_commands: {str(e)}")
        finally:
            self._is_busy = False
            self.busy_state.emit(False)

    @pyqtSlot(tuple)
    def get_screenshot(self, target_size):
        if not self._is_connected:
            self.error.emit("Error in get_screenshot: Instrument not connected.")
            return
        
        if self._is_busy:
            self.error.emit("Error in get_screenshot: Worker busy. Request discarded.")
            return 

        self._is_busy = True
        try:
            self.instrument.write('HCSU DEV, PNG, PORT, REMOTE')
            time.sleep(0.15)
            self.instrument.write('SCDP')
            
            old_to = self.instrument.timeout
            self.instrument.timeout = 10000
            raw_data = self.instrument.read_raw()
            self.instrument.timeout = old_to
            
            png_header = b'\x89PNG\r\n\x1a\n'
            png_footer = b'IEND\xaeB`\x82'
            
            start_index = raw_data.find(png_header)
            if start_index != -1:
                image_data = raw_data[start_index:]
                if png_footer not in image_data[-30:]:
                    self.error.emit("Error in get_screenshot: PNG IEND footer not found (Incomplete or corrupted data).")
                    return

                img = QImage.fromData(image_data)
                if img.isNull():
                    self.error.emit("Error in get_screenshot: Failed to render image (Null Image).")
                    return
                
                if target_size and len(target_size) == 2 and target_size[0] > 0 and target_size[1] > 0:
                    from PyQt6.QtCore import Qt
                    img = img.scaled(
                        target_size[0], target_size[1],
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                
                self.screenshot_ready.emit(img)
            else:
                self.error.emit("Error in get_screenshot: PNG header not found in the response.")
        except pyvisa.errors.VisaIOError as e:
            self._is_connected = False
            self.error.emit(f"VISA Error in get_screenshot (Communication interrupted): {str(e)}")
        except Exception as e:
            self.error.emit(f"System Error in get_screenshot: {str(e)}")
        finally:
            self._is_busy = False
            self.refresh_cycle_complete.emit()

    @pyqtSlot(list)
    def fetch_measurements(self, params_config):
        if not self._is_connected:
            self.error.emit("Error in fetch_measurements: Instrument not connected.")
            return
            
        if self._is_busy:
            self.error.emit("Error in fetch_measurements: Worker busy.")
            return 

        self._is_busy = True
        results = []
        try:
            for p in params_config:
                p_idx = p.get('p_index', 1)
                src = p['source']
                m_type = p['type']
                self.instrument.write(f'VBS \'app.Measure.P{p_idx}.Source = "{src}"\'')
                self.instrument.write(f'VBS \'app.Measure.P{p_idx}.ParamEngine = "{m_type}"\'')
                self.instrument.write(f'VBS \'app.Measure.P{p_idx}.View = True\'')
                val = self.instrument.query(f'VBS? "Return=app.Measure.P{p_idx}.Out.Result.Value"')
                results.append({'p': f'P{p_idx}', 'source': src, 'type': m_type, 'value': val.strip()})
            self.measure_ready.emit(results)
        except pyvisa.errors.VisaIOError as e:
            self._is_connected = False
            self.error.emit(f"VISA Error in fetch_measurements: {str(e)}")
        except Exception as e:
            self.error.emit(f"System Error in fetch_measurements: {str(e)}")
        finally:
            self._is_busy = False

    @pyqtSlot()
    def fetch_all_settings(self):
        if not self._is_connected:
            self.error.emit("Error in fetch_all_settings: Instrument not connected.")
            return
            
        if self._is_busy:
            self.error.emit("Error in fetch_all_settings: Worker busy. Synchronization skipped.")
            return 

        self._is_busy = True
        self.busy_state.emit(True)
        s = {}
        
        try:
            # 1. Timebase
            try: 
                s['TIME_DIV'] = self.instrument.query("TIME_DIV?").strip()
            except pyvisa.errors.VisaIOError as e: 
                self.error.emit(f"VISA Error in fetch_all_settings (TIME_DIV): {str(e)}")
            except Exception as e: 
                self.error.emit(f"System Error in fetch_all_settings (TIME_DIV): {str(e)}")

            # 2. Channels
            for ch in ["C1", "C2", "C3", "C4"]:
                try: s[f'{ch}:TRACE'] = self.instrument.query(f"{ch}:TRACE?").strip()
                except pyvisa.errors.VisaIOError as e: self.error.emit(f"VISA Error in fetch_all_settings ({ch}:TRACE): {str(e)}")
                except Exception as e: self.error.emit(f"System Error in fetch_all_settings ({ch}:TRACE): {str(e)}")
                
                try: s[f'{ch}:VOLT_DIV'] = self.instrument.query(f"{ch}:VOLT_DIV?").strip()
                except pyvisa.errors.VisaIOError as e: self.error.emit(f"VISA Error in fetch_all_settings ({ch}:VOLT_DIV): {str(e)}")
                except Exception as e: self.error.emit(f"System Error in fetch_all_settings ({ch}:VOLT_DIV): {str(e)}")
                
                try: s[f'{ch}:OFFSET'] = self.instrument.query(f"{ch}:OFFSET?").strip()
                except pyvisa.errors.VisaIOError as e: self.error.emit(f"VISA Error in fetch_all_settings ({ch}:OFFSET): {str(e)}")
                except Exception as e: self.error.emit(f"System Error in fetch_all_settings ({ch}:OFFSET): {str(e)}")
                
                try: s[f'{ch}:COUPLING'] = self.instrument.query(f"{ch}:COUPLING?").strip()
                except pyvisa.errors.VisaIOError as e: self.error.emit(f"VISA Error in fetch_all_settings ({ch}:COUPLING): {str(e)}")
                except Exception as e: self.error.emit(f"System Error in fetch_all_settings ({ch}:COUPLING): {str(e)}")
                
                try: s[f'{ch}:BANDWIDTH_LIMIT'] = self.instrument.query(f"{ch}:BANDWIDTH_LIMIT?").strip()
                except pyvisa.errors.VisaIOError as e: self.error.emit(f"VISA Error in fetch_all_settings ({ch}:BANDWIDTH_LIMIT): {str(e)}")
                except Exception as e: self.error.emit(f"System Error in fetch_all_settings ({ch}:BANDWIDTH_LIMIT): {str(e)}")
                
                try: s[f'{ch}:INVERT'] = self.instrument.query(f"{ch}:INVERT?").strip()
                except pyvisa.errors.VisaIOError as e: self.error.emit(f"VISA Error in fetch_all_settings ({ch}:INVERT): {str(e)}")
                except Exception as e: self.error.emit(f"System Error in fetch_all_settings ({ch}:INVERT): {str(e)}")

            # 3. Trigger
            try: s['TRIG_MODE'] = self.instrument.query("TRIG_MODE?").strip()
            except pyvisa.errors.VisaIOError as e: self.error.emit(f"VISA Error in fetch_all_settings (TRIG_MODE): {str(e)}")
            except Exception as e: self.error.emit(f"System Error in fetch_all_settings (TRIG_MODE): {str(e)}")
            
            try:
                trse = self.instrument.query("TRIG_SELECT?").strip().split(',')
                if len(trse) > 0: s['TRIG_TYPE'] = trse[0]
                if len(trse) > 2: s['TRIG_SRC'] = trse[2]
            except pyvisa.errors.VisaIOError as e: 
                self.error.emit(f"VISA Error in fetch_all_settings (TRIG_SELECT): {str(e)}")
            except Exception as e: 
                self.error.emit(f"System Error in fetch_all_settings (TRIG_SELECT): {str(e)}")

            # Trigger Level
            if 'TRIG_SRC' in s and s['TRIG_SRC'] in ["C1","C2","C3","C4"]:
                try: s['TRIG_LVL'] = self.instrument.query(f"{s['TRIG_SRC']}:TRIG_LEVEL?").strip()
                except pyvisa.errors.VisaIOError as e: self.error.emit(f"VISA Error in fetch_all_settings (TRIG_LEVEL for {s['TRIG_SRC']}): {str(e)}")
                except Exception as e: self.error.emit(f"System Error in fetch_all_settings (TRIG_LEVEL for {s['TRIG_SRC']}): {str(e)}")

            if s: 
                self.settings_ready.emit(s)
                
        except Exception as e:
            self.error.emit(f"Critical Error in fetch_all_settings (Main loop): {str(e)}")
        finally:
            self._is_busy = False
            self.busy_state.emit(False)

    @pyqtSlot(str, str)
    def export_waveform(self, channel, file_path):
        if not self._is_connected:
            self.error.emit("Error in export_waveform: Instrument not connected.")
            return
            
        if self._is_busy:
            self.error.emit("Error in export_waveform: Worker busy.")
            return
        
        self._is_busy = True
        try:
            self.instrument.write(f'COMM_FORMAT OFF,WORD,BIN')
            self.instrument.write(f'{channel}:WAVEFORM? DAT1')
            raw_data = self.instrument.read_raw()
            with open(file_path, 'wb') as f:
                f.write(raw_data)
            self.export_finished.emit(f"Waveform {channel} saved to {os.path.basename(file_path)}")
        except pyvisa.errors.VisaIOError as e:
            self._is_connected = False
            self.error.emit(f"VISA Error in export_waveform (DAT1 extraction on {channel}): {str(e)}")
        except Exception as e:
            self.error.emit(f"System Error in export_waveform (File save on {channel}): {str(e)}")
        finally:
            self._is_busy = False
