import sys
import os
import time
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QGridLayout, QGroupBox, QLabel, QLineEdit, 
                             QPushButton, QComboBox, QDoubleSpinBox, QTextEdit, 
                             QScrollArea, QCheckBox, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QFileDialog, QSizePolicy,
                             QStatusBar)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QPixmap, QImage, QAction

from visa_worker import OscilloscopeWorker
from widgets import ChannelControl
from styles import STYLE_MAIN

class OscilloscopeGUI(QMainWindow):
    request_connect = pyqtSignal(str)
    request_screenshot = pyqtSignal(tuple)
    request_measurements = pyqtSignal(list)
    request_sync = pyqtSignal()
    request_command = pyqtSignal(str)
    request_multiple_commands = pyqtSignal(list)
    request_waveform = pyqtSignal(str, str)
    request_cleanup = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Professional Oscilloscope Suite")
        self.resize(1400, 950)
        self._auto_apply = True
        self._live_active = False
        self._is_gui_updating = False
        self._is_syncing = False
        self.screenshot_count = 0
        self.screenshot_dir = os.path.join(os.path.expanduser("~"), "Desktop", "Screenshots_Oscilloscope")
        self.log_dir = os.path.join(os.path.expanduser("~"), "Desktop", "Oscilloscope_Logs")
        self.log_file_path = os.path.join(self.log_dir, f"session_{time.strftime('%Y%m%d_%H%M%S')}.log")
        
        self.setStyleSheet(STYLE_MAIN)

        # ---------------------------------------------------------
        # 1. REAL QTHREAD IMPLEMENTATION (Mandatory Pattern)
        # ---------------------------------------------------------
        self.worker_thread = QThread()
        self.worker = OscilloscopeWorker()
        self.worker.moveToThread(self.worker_thread)
        
        self.worker.connected.connect(self.on_connected)
        self.worker.error.connect(self.on_error)
        self.worker.screenshot_ready.connect(self.display_screenshot)
        self.worker.measure_ready.connect(self.update_measures_table)
        self.worker.export_finished.connect(lambda m: self.log(m))
        self.worker.settings_ready.connect(self.apply_synced_settings)
        self.worker.response.connect(self.update_status_bar)
        self.worker.refresh_cycle_complete.connect(self.on_refresh_done)
        self.worker.busy_state.connect(self.on_worker_busy)

        self.request_connect.connect(self.worker.connect_to_scope)
        self.request_screenshot.connect(self.worker.get_screenshot)
        self.request_measurements.connect(self.worker.fetch_measurements)
        self.request_sync.connect(self.worker.fetch_all_settings)
        self.request_command.connect(self.worker.send_command)
        self.request_multiple_commands.connect(self.worker.send_multiple_commands)
        self.request_waveform.connect(self.worker.export_waveform)
        self.request_cleanup.connect(self.worker.cleanup)

        self.worker_thread.start()
        # ---------------------------------------------------------

        self.live_timer = QTimer()
        self.live_timer.setSingleShot(True) 
        self.live_timer.timeout.connect(self.on_live_tick)
        
        self.sync_counter = 0

        self.init_menu()
        self.init_ui()
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("System Ready")

    def init_menu(self):
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("File")
        save_img_action = QAction("Save Screenshot", self)
        save_img_action.triggered.connect(self.save_screenshot_to_file)
        file_menu.addAction(save_img_action)
        file_menu.addAction("Exit", self.close)
        
        setup_menu = menubar.addMenu("Setup")
        setup_menu.addAction("Export Device Setup", self.export_setup)
        setup_menu.addAction("Import Device Setup", self.import_setup)
        
        info_menu = menubar.addMenu("Info")
        info_menu.addAction("About", lambda: self.log("Professional Oscilloscope Suite v2.1"))

    def init_ui(self):
        central = QWidget(); self.setCentralWidget(central); main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(15, 15, 15, 15); main_layout.setSpacing(15)

        # COLUMN 1: SYSTEM CONTROLS
        col1 = QWidget(); col1.setFixedWidth(320); col1_lay = QVBoxLayout(col1); main_layout.addWidget(col1)

        conn_box = QGroupBox("SYSTEM STATUS")
        c_lay = QGridLayout()
        
        hb_lay = QHBoxLayout()
        self.hb_led = QLabel(); self.hb_led.setFixedSize(10, 10); self.hb_led.setObjectName("heartbeat_off")
        hb_lay.addWidget(self.hb_led); hb_lay.addWidget(QLabel("LIVE BUS STATUS"))
        c_lay.addLayout(hb_lay, 0, 0, 1, 2)
        
        self.ip_input = QLineEdit("10.0.10.142")
        c_lay.addWidget(QLabel("IP:"), 1, 0); c_lay.addWidget(self.ip_input, 1, 1)
        self.connect_btn = QPushButton("CONNECT"); self.connect_btn.setObjectName("connect_btn")
        self.connect_btn.clicked.connect(self.toggle_connection)
        c_lay.addWidget(self.connect_btn, 2, 0, 1, 2)
        
        self.sync_from_btn = QPushButton("SYNC FROM SCOPE")
        self.sync_from_btn.clicked.connect(self.poll_settings)
        c_lay.addWidget(self.sync_from_btn, 3, 0)
        
        self.apply_to_btn = QPushButton("APPLY TO SCOPE"); self.apply_to_btn.setObjectName("apply_btn_clean")
        self.apply_to_btn.clicked.connect(self.force_apply)
        c_lay.addWidget(self.apply_to_btn, 3, 1)
        
        conn_box.setLayout(c_lay); col1_lay.addWidget(conn_box)

        # Timebase & Trigger Essentials
        tb_box = QGroupBox("CHRONO & TRIGGER")
        t_lay = QGridLayout()
        
        t_lay.addWidget(QLabel("Time/Div:"), 0, 0)
        self.timebase_cb = QComboBox()
        tbs = [("1ns", 1e-9), ("10ns", 1e-8), ("100ns", 1e-7), ("1us", 1e-6), ("1ms", 1e-3), ("10ms", 1e-2), ("1s", 1.0)]
        for l, v in tbs: self.timebase_cb.addItem(l, v)
        self.timebase_cb.currentIndexChanged.connect(self.on_ui_change)
        t_lay.addWidget(self.timebase_cb, 0, 1)
        
        t_lay.addWidget(QLabel("Trig Mode:"), 1, 0)
        self.trig_mode = QComboBox(); self.trig_mode.addItems(["AUTO", "NORM", "SINGLE", "STOP"])
        self.trig_mode.currentIndexChanged.connect(self.on_ui_change)
        t_lay.addWidget(self.trig_mode, 1, 1)
        
        t_lay.addWidget(QLabel("Trig Type:"), 2, 0)
        self.trig_type = QComboBox(); self.trig_type.addItems(["EDGE", "WIDTH", "GLITCH", "TV"])
        self.trig_type.currentIndexChanged.connect(self.on_ui_change)
        t_lay.addWidget(self.trig_type, 2, 1)

        t_lay.addWidget(QLabel("Trig Src:"), 3, 0)
        self.trig_src = QComboBox(); self.trig_src.addItems(["C1", "C2", "C3", "C4", "LINE"])
        self.trig_src.currentIndexChanged.connect(self.on_ui_change)
        t_lay.addWidget(self.trig_src, 3, 1)

        t_lay.addWidget(QLabel("Trig Slope:"), 4, 0)
        self.trig_slope = QComboBox(); self.trig_slope.addItems(["POS", "NEG", "WINDOW"])
        self.trig_slope.currentIndexChanged.connect(self.on_ui_change)
        t_lay.addWidget(self.trig_slope, 4, 1)

        t_lay.addWidget(QLabel("Trig Level:"), 5, 0)
        self.trig_lvl = QDoubleSpinBox(); self.trig_lvl.setRange(-20, 20); self.trig_lvl.setSingleStep(0.01)
        self.trig_lvl.valueChanged.connect(self.on_ui_change)
        t_lay.addWidget(self.trig_lvl, 5, 1)
        
        tb_box.setLayout(t_lay); col1_lay.addWidget(tb_box)
        
        qa_box = QGroupBox("QUICK ACTIONS")
        qa_lay = QGridLayout()
        for i, m in enumerate(["AUTO", "NORM", "SINGLE", "STOP"]):
            btn = QPushButton(m); btn.clicked.connect(lambda checked, mode=m: self.set_trigger_mode(mode))
            qa_lay.addWidget(btn, i//2, i%2)
        qa_box.setLayout(qa_lay); col1_lay.addWidget(qa_box)
        
        col1_lay.addWidget(QLabel("<b>ACTIVITY LOG</b>"))
        self.log_txt = QTextEdit()
        self.log_txt.setReadOnly(True)
        self.log_txt.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.log_txt.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.log_txt.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        col1_lay.addWidget(self.log_txt)

        # COLUMN 2: PRIMARY MONITOR 
        col2 = QWidget(); col2_lay = QVBoxLayout(col2); main_layout.addWidget(col2, 1)
        
        mon_head = QHBoxLayout()
        mon_head.addWidget(QLabel("<b><span style='font-size: 16px; color: #c9d1d9;'>REAL-TIME SCOPE MONITOR</span></b>"))
        mon_head.addStretch()
        self.capture_btn = QPushButton("📸 SNAPSHOT")
        self.capture_btn.clicked.connect(self.single_capture)
        mon_head.addWidget(self.capture_btn)
        self.live_btn = QPushButton("▶ START LIVE STREAM")
        self.live_btn.clicked.connect(self.toggle_live)
        mon_head.addWidget(self.live_btn)
        self.auto_save_cb = QCheckBox("AUTO-SAVE LIVE")
        mon_head.addWidget(self.auto_save_cb)
        col2_lay.addLayout(mon_head)

        self.screen_label = QLabel("DISCONNECTED"); self.screen_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.screen_label.setStyleSheet("background-color: #000; border: 2px solid #30363d; border-radius: 12px; color: #484f58; min-height: 600px;")
        col2_lay.addWidget(self.screen_label, 1)
        
        m_box = QGroupBox("ON-SCREEN MEASUREMENTS")
        m_lay = QHBoxLayout()
        self.m_src = QComboBox(); self.m_src.addItems(["C1", "C2", "C3", "C4"])
        self.m_type = QComboBox(); self.m_type.addItems(["PKPK", "MAX", "MIN", "FREQ", "PERIOD"])
        m_lay.addWidget(QLabel("Source:"))
        m_lay.addWidget(self.m_src)
        m_lay.addWidget(QLabel("Type:"))
        m_lay.addWidget(self.m_type)
        self.m_table = QTableWidget(1, 4); self.m_table.setHorizontalHeaderLabels(["Param", "Type", "Source", "Value"])
        self.m_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch); self.m_table.setFixedHeight(90)
        m_lay.addWidget(self.m_table, 1)
        m_box.setLayout(m_lay); col2_lay.addWidget(m_box)

        # COLUMN 3: CHANNEL SETTINGS
        col3_scroll = QScrollArea(); col3_scroll.setFixedWidth(340); col3_scroll.setWidgetResizable(True)
        col3_wrapper = QWidget(); col3_lay = QVBoxLayout(col3_wrapper); col3_scroll.setWidget(col3_wrapper)
        main_layout.addWidget(col3_scroll)
        
        col3_lay.addWidget(QLabel("<b>CHANNEL SETTINGS</b>"))
        self.channels = {}
        for ch in ["1", "2", "3", "4"]:
            ctrl = ChannelControl(ch); ctrl.settingChanged.connect(self.on_ui_change)
            ctrl.export_btn.clicked.connect(lambda checked, c=ch: self.save_waveform(c))
            col3_lay.addWidget(ctrl); self.channels[f"C{ch}"] = ctrl
        col3_lay.addStretch()

    def log(self, msg, error=False):
        color = "#f85149" if error else "#7ee787"
        timestamp = time.strftime('%H:%M:%S')
        self.log_txt.append(f"<span style='color: {color};'>[{timestamp}] {msg}</span>")

        # Persistent log to file (best-effort, does not block GUI on error)
        try:
            if not os.path.exists(self.log_dir):
                os.makedirs(self.log_dir, exist_ok=True)
            with open(self.log_file_path, "a", encoding="utf-8") as f:
                prefix = "ERROR " if error else "INFO  "
                f.write(f"[{timestamp}] {prefix}{msg}\n")
        except Exception:
            # Avoid generating further GUI errors if the disk is unavailable
            pass

    def on_worker_busy(self, is_busy):
        self.apply_to_btn.setEnabled(not is_busy)
        self.sync_from_btn.setEnabled(not is_busy)
        self.capture_btn.setEnabled(not is_busy)
        if is_busy:
            self.pulse_heartbeat(True)
        else:
            self.pulse_heartbeat(self.worker._is_connected)

    def toggle_connection(self):
        if self.worker._is_connected: 
            self.log("Disconnecting from instrument...")
            self.request_cleanup.emit()
            self.connect_btn.setText("CONNECT")
            self.pulse_heartbeat(False)
        else:
            self.request_connect.emit(self.ip_input.text())

    def on_connected(self, idn): 
        self.log(f"CONNECTED: {idn}")
        self.connect_btn.setText("DISCONNECT")
        self.pulse_heartbeat(True)
        self.log("Ready. Use SYNC/APPLY buttons to manage settings.")

    def poll_settings(self):
        if self.worker._is_connected and not self._is_syncing:
            self._is_syncing = True
            self.log("Fetching instrument state...")
            self.request_sync.emit()

    def on_error(self, err): 
        self.log(f"CRITICAL ERROR: {err}", True)
        if self._live_active:
            self.toggle_live()
        self.update_status_bar(f"Error: {err}")

    def toggle_live(self):
        if not self.worker._is_connected: return
        self._live_active = not self._live_active
        self.live_btn.setText("STOP LIVE" if self._live_active else "START LIVE")
        if self._live_active:
            self.live_timer.start(100)
        else:
            self.live_timer.stop()

    def update_status_bar(self, msg):
        self.status_bar.showMessage(msg, 3000)

    def closeEvent(self, event):
        self.log("Closing application...", False)
        
        self.live_timer.stop()
        self._live_active = False
        
        self.request_cleanup.emit()
        
        self.worker_thread.quit()
        self.worker_thread.wait(2000) 
        
        event.accept()

    def single_capture(self):
        if not self.worker._is_connected: return
        self.log("Capturing screen...")
        
        lbl_w = self.screen_label.width()
        lbl_h = self.screen_label.height()
        target_size = (max(640, lbl_w - 20), max(480, lbl_h - 20))
        
        self.request_screenshot.emit(target_size)

    def on_live_tick(self):
        if not self.worker._is_connected or not self._live_active:
            return

        m_src = self.m_src.currentText()
        m_type = self.m_type.currentText()
        
        lbl_w = self.screen_label.width()
        lbl_h = self.screen_label.height()
        target_size = (max(640, lbl_w - 20), max(480, lbl_h - 20))

        self.request_screenshot.emit(target_size)
        
        config = [{'p_index': 1, 'source': m_src, 'type': m_type}]
        self.request_measurements.emit(config)
        
        self.sync_counter += 1
        if self.sync_counter >= 5:
            self.sync_counter = 0
            self.request_sync.emit()

    def on_refresh_done(self):
        if self._live_active:
            self.live_timer.start(200)

    def display_screenshot(self, img):
        if img.isNull(): return
        
        from PyQt6.QtCore import QBuffer, QIODevice
        ba = QBuffer()
        ba.open(QIODevice.OpenModeFlag.WriteOnly)
        img.save(ba, "PNG")
        self._last_image_data = ba.data().data()

        pix = QPixmap.fromImage(img)
        self.screen_label.setPixmap(pix)
        
        if self.auto_save_cb.isChecked():
            self.save_screenshot_to_file(is_auto=True)

    def update_measures_table(self, data):
        for i, m in enumerate(data):
            self.m_table.setItem(i, 0, QTableWidgetItem(m['p']))
            self.m_table.setItem(i, 1, QTableWidgetItem(m['type']))
            self.m_table.setItem(i, 2, QTableWidgetItem(m['source']))
            self.m_table.setItem(i, 3, QTableWidgetItem(m['value']))

    def on_ui_change(self):
        if self._is_gui_updating: return
        self.apply_to_btn.setObjectName("apply_btn_dirty")
        self.apply_to_btn.style().unpolish(self.apply_to_btn)
        self.apply_to_btn.style().polish(self.apply_to_btn)

    def pulse_heartbeat(self, active):
        self.hb_led.setObjectName("heartbeat_on" if active else "heartbeat_off")
        self.hb_led.style().unpolish(self.hb_led); self.hb_led.style().polish(self.hb_led)

    def apply_synced_settings(self, s):
        self._is_gui_updating = True
        self.pulse_heartbeat(True)
        try:
            def parse_num(val_str):
                if not val_str: return 0.0
                clean = "".join(c for c in val_str if c in "0123456789.eE+-")
                try: return float(clean)
                except: return 0.0

            def set_combo_by_data(cb, val):
                min_diff = float('inf'); best_idx = -1
                for i in range(cb.count()):
                    try:
                        cbd = float(cb.itemData(i))
                        if abs(cbd - val) < min_diff: min_diff = abs(cbd - val); best_idx = i
                    except: pass
                if best_idx >= 0 and cb.currentIndex() != best_idx:
                    cb.blockSignals(True); cb.setCurrentIndex(best_idx); cb.blockSignals(False)
            
            def set_combo_by_text(cb, text):
                if not text: return
                best_idx = -1
                for i in range(cb.count()):
                    if cb.itemText(i).upper() == text.upper(): best_idx = i; break
                if best_idx >= 0 and cb.currentIndex() != best_idx:
                    cb.blockSignals(True); cb.setCurrentIndex(best_idx); cb.blockSignals(False)

            if 'TIME_DIV' in s:
                try: set_combo_by_data(self.timebase_cb, parse_num(s['TIME_DIV']))
                except Exception as e: self.log(f"Error syncing TIME_DIV: {e}", True)

            cpl_map = {"D50":"DC50", "D1M":"DC1M", "AC1M":"AC1M", "GND":"GND"}
            bw_map = {"OFF":"Full", "200MHZ":"200MHz", "20MHZ":"20MHz"}

            for ch in ["C1", "C2", "C3", "C4"]:
                if ch not in self.channels: continue
                ctrl = self.channels[ch]
                try:
                    if f'{ch}:TRACE' in s: set_combo_by_text(ctrl.trace_cb, s[f'{ch}:TRACE'])
                    if f'{ch}:VOLT_DIV' in s:
                        try: set_combo_by_data(ctrl.volt_cb, parse_num(s[f'{ch}:VOLT_DIV']))
                        except Exception as e: self.log(f"Error syncing {ch}:VOLT_DIV: {e}", True)
                    if f'{ch}:OFFSET' in s:
                        try: 
                            nv = parse_num(s[f'{ch}:OFFSET'])
                            if abs(ctrl.offset_sb.value() - nv) > 0.001:
                                ctrl.offset_sb.blockSignals(True); ctrl.offset_sb.setValue(nv); ctrl.offset_sb.blockSignals(False)
                        except Exception as e: self.log(f"Error syncing {ch}:OFFSET: {e}", True)
                    if f'{ch}:COUPLING' in s:
                        cpl = cpl_map.get(s[f'{ch}:COUPLING'].upper(), s[f'{ch}:COUPLING'].upper())
                        idx = ctrl.coupling_cb.findText(cpl)
                        if idx >= 0:
                            ctrl.coupling_cb.blockSignals(True); ctrl.coupling_cb.setCurrentIndex(idx); ctrl.last_coupling_idx = idx; ctrl.coupling_cb.blockSignals(False)
                    if f'{ch}:BANDWIDTH_LIMIT' in s:
                        set_combo_by_text(ctrl.bw_cb, bw_map.get(s[f'{ch}:BANDWIDTH_LIMIT'].upper(), s[f'{ch}:BANDWIDTH_LIMIT']))
                    if f'{ch}:INVERT' in s:
                        is_on = s[f'{ch}:INVERT'].upper() == "ON"
                        if ctrl.invert_cb.isChecked() != is_on:
                            ctrl.invert_cb.blockSignals(True); ctrl.invert_cb.setChecked(is_on); ctrl.invert_cb.blockSignals(False)
                except Exception as e:
                    self.log(f"Error syncing channel {ch} settings: {e}", True)

            if 'TRIG_MODE' in s: set_combo_by_text(self.trig_mode, s['TRIG_MODE'])
            if 'TRIG_TYPE' in s: set_combo_by_text(self.trig_type, s['TRIG_TYPE'])
            if 'TRIG_SRC' in s: set_combo_by_text(self.trig_src, s['TRIG_SRC'])
            if 'TRIG_SLOPE' in s: set_combo_by_text(self.trig_slope, s['TRIG_SLOPE'])
            if 'TRIG_LVL' in s:
                try: 
                    nv = parse_num(s['TRIG_LVL'])
                    if abs(self.trig_lvl.value() - nv) > 0.001:
                        self.trig_lvl.blockSignals(True); self.trig_lvl.setValue(nv); self.trig_lvl.blockSignals(False)
                except Exception as e: self.log(f"Error syncing TRIG_LVL: {e}", True)
            self.log("Sync completed.")
        except Exception as e:
            self.log(f"Sync UI Error: {e}", True)
            for ctrl in self.channels.values():
                ctrl.volt_cb.blockSignals(False)
                ctrl.offset_sb.blockSignals(False)
                ctrl.coupling_cb.blockSignals(False)
        finally:
            self._is_gui_updating = False
            self._is_syncing = False
            self.pulse_heartbeat(self.worker._is_connected)

    def force_apply(self):
        if not self.worker._is_connected: return
        self.apply_to_btn.setEnabled(False)
        self.log("Applying GUI settings to instrument...")
        self.pulse_heartbeat(True)
        
        cmds = []
        cmds.append(f"TIME_DIV {self.timebase_cb.currentData()}")
        
        for ch_id, ctrl in self.channels.items():
            cmds.append(f"{ch_id}:TRACE {'ON' if ctrl.trace_cb.currentText() == 'ON' else 'OFF'}")
            cmds.append(f"{ch_id}:VOLT_DIV {ctrl.volt_cb.currentData()}")
            cmds.append(f"{ch_id}:OFFSET {ctrl.offset_sb.value()}")
            cpl = ctrl.coupling_cb.currentText()
            cpl_cmd = {"DC50":"D50", "DC1M":"D1M", "AC1M":"A1M", "GND":"GND"}.get(cpl, "D1M")
            cmds.append(f"{ch_id}:COUPLING {cpl_cmd}")
            bw = ctrl.bw_cb.currentText()
            bw_cmd = {"Full":"OFF", "200MHz":"200MHZ", "20MHz":"20MHZ"}.get(bw, "OFF")
            cmds.append(f"{ch_id}:BANDWIDTH_LIMIT {bw_cmd}")
            cmds.append(f"{ch_id}:INVERT {'ON' if ctrl.invert_cb.isChecked() else 'OFF'}")

        cmds.append(f"TRIG_MODE {self.trig_mode.currentText()}")
        cmds.append(f"TRIG_SRC {self.trig_src.currentText()}")
        cmds.append(f"TRIG_LVL {self.trig_lvl.value()}")
        cmds.append(f"TRIG_SELECT {self.trig_type.currentText()},{self.trig_src.currentText()}")
        cmds.append(f"{self.trig_src.currentText()}:TRIG_SLOPE {self.trig_slope.currentText()}")
        
        self.request_multiple_commands.emit(cmds)
        
        QTimer.singleShot(500, lambda: self.apply_to_btn.setEnabled(True))
        QTimer.singleShot(500, lambda: self.apply_to_btn.setObjectName("apply_btn_clean"))
        QTimer.singleShot(500, lambda: self.apply_to_btn.style().unpolish(self.apply_to_btn))
        QTimer.singleShot(500, lambda: self.apply_to_btn.style().polish(self.apply_to_btn))

    def set_trigger_mode(self, mode):
        idx = self.trig_mode.findText(mode)
        if idx >= 0: self.trig_mode.setCurrentIndex(idx)
        if self.worker._is_connected: 
            self.request_command.emit(f"TRIG_MODE {mode}")

    def save_waveform(self, ch):
        if not self.worker._is_connected: return
        path, _ = QFileDialog.getSaveFileName(self, "Save Waveform Data", f"waveform_{ch}.bin", "Binary (*.bin)")
        if path: 
            self.request_waveform.emit(f"C{ch}", path)

    def save_screenshot_to_file(self, is_auto=False):
        if hasattr(self, '_last_image_data'):
            if not os.path.exists(self.screenshot_dir):
                try: os.makedirs(self.screenshot_dir)
                except Exception as e:
                    self.log(f"Dir Creation Error: {e}", True)
                    return

            self.screenshot_count += 1
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"capture_{self.screenshot_count:03d}_{timestamp}.png"
            path = os.path.join(self.screenshot_dir, filename)
            
            try:
                with open(path, 'wb') as f: f.write(self._last_image_data)
                if not is_auto:
                    self.log(f"📸 Saved: {filename} in Desktop/Screenshots_Oscilloscope")
            except Exception as e:
                if not is_auto:
                    self.log(f"Save Error: {e}", True)
        else:
            if not is_auto:
                self.log("No image to save!", True)

    def export_setup(self): self.log("Export setup function called.")
    def import_setup(self): self.log("Import setup function called.")
