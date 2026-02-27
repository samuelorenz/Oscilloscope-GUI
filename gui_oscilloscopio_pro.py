import sys
import pyvisa
import threading
import time
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QGroupBox, QLabel, 
                             QLineEdit, QPushButton, QComboBox, QDoubleSpinBox, 
                             QTextEdit, QStatusBar, QFrame, QScrollArea, QCheckBox,
                             QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
                             QFileDialog, QMenuBar)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import QFont, QPixmap, QImage, QAction

class OscilloscopeWorker(QObject):
    """Worker class to handle VISA communication with locking for thread safety."""
    connected = pyqtSignal(str)
    error = pyqtSignal(str)
    response = pyqtSignal(str)
    screenshot_ready = pyqtSignal(bytes)
    measure_ready = pyqtSignal(list)
    export_finished = pyqtSignal(str)
    settings_ready = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.rm = None
        self.instrument = None
        self._is_connected = False
        self._lock = threading.Lock()

    def connect_to_scope(self, ip_address):
        with self._lock:
            try:
                if not self.rm:
                    self.rm = pyvisa.ResourceManager()
                resource_string = f'TCPIP::{ip_address}::INSTR'
                self.instrument = self.rm.open_resource(resource_string)
                self.instrument.timeout = 5000
                try: self.instrument.clear()
                except: pass
                idn = self.instrument.query('*IDN?')
                self.instrument.write('COMM_HEADER OFF')
                self._is_connected = True
                self.connected.emit(idn.strip())
            except Exception as e:
                self._is_connected = False
                self.error.emit(str(e))

    def send_command(self, cmd):
        if not self._is_connected: return
        with self._lock:
            try:
                self.instrument.write(cmd)
            except Exception as e:
                self.error.emit(f"Write error: {e}")

    def query_command(self, cmd):
        if not self._is_connected: return None
        with self._lock:
            try:
                return self.instrument.query(cmd).strip()
            except Exception as e:
                self.error.emit(f"Query error: {e}")
                return None

    def get_screenshot(self):
        if not self._is_connected: return
        with self._lock:
            try:
                self.instrument.write('HCSU DEV, PNG, PORT, NET')
                self.instrument.write('SCDP')
                old_to = self.instrument.timeout
                self.instrument.timeout = 10000
                raw_data = self.instrument.read_raw()
                self.instrument.timeout = old_to
                png_header = b'\x89PNG\r\n\x1a\n'
                start_index = raw_data.find(png_header)
                if start_index != -1:
                    image_data = raw_data[start_index:]
                    self.screenshot_ready.emit(image_data)
            except Exception as e:
                pass

    def fetch_measurements(self, params_config):
        if not self._is_connected: return
        results = []
        with self._lock:
            try:
                for p in params_config:
                    p_idx = p['p_index']
                    src = p['source']
                    m_type = p['type']
                    self.instrument.write(f'VBS \'app.Measure.P{p_idx}.Source = "{src}"\'')
                    self.instrument.write(f'VBS \'app.Measure.P{p_idx}.ParamEngine = "{m_type}"\'')
                    self.instrument.write(f'VBS \'app.Measure.P{p_idx}.View = True\'')
                    val = self.instrument.query(f'VBS? "Return=app.Measure.P{p_idx}.Out.Result.Value"')
                    results.append({'p': f'P{p_idx}', 'source': src, 'type': m_type, 'value': val.strip()})
                self.measure_ready.emit(results)
            except Exception as e:
                pass

    def fetch_all_settings(self):
        if not self._is_connected: return
        with self._lock:
            s = {}
            try:
                # 1. Timebase
                try: s['TIME_DIV'] = self.instrument.query("TIME_DIV?").strip()
                except: pass

                # 2. Channels
                for ch in ["C1", "C2", "C3", "C4"]:
                    try: s[f'{ch}:TRACE'] = self.instrument.query(f"{ch}:TRACE?").strip()
                    except: pass
                    try: s[f'{ch}:VOLT_DIV'] = self.instrument.query(f"{ch}:VOLT_DIV?").strip()
                    except: pass
                    try: s[f'{ch}:OFFSET'] = self.instrument.query(f"{ch}:OFFSET?").strip()
                    except: pass
                    try: s[f'{ch}:COUPLING'] = self.instrument.query(f"{ch}:COUPLING?").strip()
                    except: pass
                    try: s[f'{ch}:BANDWIDTH_LIMIT'] = self.instrument.query(f"{ch}:BANDWIDTH_LIMIT?").strip()
                    except: pass
                    try: s[f'{ch}:INVERT'] = self.instrument.query(f"{ch}:INVERT?").strip()
                    except: pass

                # 3. Trigger
                try: s['TRIG_MODE'] = self.instrument.query("TRIG_MODE?").strip()
                except: pass
                
                try:
                    trse = self.instrument.query("TRIG_SELECT?").strip().split(',')
                    if len(trse) > 0: s['TRIG_TYPE'] = trse[0]
                    if len(trse) > 2: s['TRIG_SRC'] = trse[2]
                except: pass

                # Trigger Level (needs Source)
                if 'TRIG_SRC' in s and s['TRIG_SRC'] in ["C1","C2","C3","C4"]:
                    try: s['TRIG_LVL'] = self.instrument.query(f"{s['TRIG_SRC']}:TRIG_LEVEL?").strip()
                    except: pass

                if s: # Emit only if we got some data
                    self.settings_ready.emit(s)
            except Exception as e:
                self.error.emit(f"Sync error: {str(e)}")

    def export_waveform(self, channel, file_path):
        if not self._is_connected: return
        with self._lock:
            try:
                self.instrument.write(f'COMM_FORMAT OFF,WORD,BIN')
                self.instrument.write(f'{channel}:WAVEFORM? DAT1')
                raw_data = self.instrument.read_raw()
                with open(file_path, 'wb') as f:
                    f.write(raw_data)
                self.export_finished.emit(f"Waveform {channel} saved to {os.path.basename(file_path)}")
            except Exception as e:
                self.error.emit(f"Export error: {e}")

class ChannelControl(QGroupBox):
    settingChanged = pyqtSignal()
    def __init__(self, ch_name, parent=None):
        super().__init__(f"CHANNEL {ch_name}", parent)
        self.ch_name = ch_name
        layout = QGridLayout(self)
        
        layout.addWidget(QLabel("Trace:"), 0, 0)
        self.trace_cb = QComboBox(); self.trace_cb.addItems(["ON", "OFF"])
        self.trace_cb.setCurrentText("ON" if ch_name == "1" else "OFF")
        self.trace_cb.currentIndexChanged.connect(self.settingChanged.emit)
        layout.addWidget(self.trace_cb, 0, 1)

        layout.addWidget(QLabel("Volt/Div:"), 1, 0)
        self.volt_cb = QComboBox()
        volts = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10]
        for v in volts: self.volt_cb.addItem(f"{v*1000:.0f} mV" if v < 1 else f"{v} V", v)
        self.volt_cb.setCurrentIndex(9); self.volt_cb.currentIndexChanged.connect(self.settingChanged.emit)
        layout.addWidget(self.volt_cb, 1, 1)

        layout.addWidget(QLabel("Coupling:"), 2, 0)
        self.coupling_cb = QComboBox(); self.coupling_cb.addItems(["DC1M", "DC50", "AC1M", "GND"])
        self.coupling_cb.setCurrentText("DC1M")
        self.last_coupling_idx = 0
        self.coupling_cb.currentIndexChanged.connect(self.validate_coupling_change)
        layout.addWidget(self.coupling_cb, 2, 1)

        layout.addWidget(QLabel("Bndwidth:"), 3, 0)
        self.bw_cb = QComboBox(); self.bw_cb.addItems(["Full", "200MHz", "20MHz"])
        self.bw_cb.currentIndexChanged.connect(self.settingChanged.emit)
        layout.addWidget(self.bw_cb, 3, 1)

        layout.addWidget(QLabel("Offset (V):"), 4, 0)
        self.offset_sb = QDoubleSpinBox(); self.offset_sb.setRange(-20, 20); self.offset_sb.setSingleStep(0.1)
        self.offset_sb.valueChanged.connect(self.settingChanged.emit)
        layout.addWidget(self.offset_sb, 4, 1)

        self.invert_cb = QCheckBox("Invert")
        self.invert_cb.toggled.connect(self.settingChanged.emit)
        layout.addWidget(self.invert_cb, 5, 0)
        
        self.export_btn = QPushButton("SAVE DATA")
        self.export_btn.setStyleSheet("background-color: #1f6feb; border: none; padding: 4px; color: white;")
        layout.addWidget(self.export_btn, 5, 1)

    def validate_coupling_change(self, index):
        from PyQt6.QtWidgets import QMessageBox
        if self.coupling_cb.itemText(index) == "DC50":
            ret = QMessageBox.warning(
                self, "⚠️ SAFETY WARNING",
                f"You are switching CHANNEL {self.ch_name} to 50 Ω coupling.\n\n"
                "NEVER apply more than 5V RMS to a 50 Ω input or you will DAMAGE the oscilloscope!\n\n"
                "Do you want to proceed?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if ret == QMessageBox.StandardButton.No:
                self.coupling_cb.blockSignals(True)
                self.coupling_cb.setCurrentIndex(self.last_coupling_idx)
                self.coupling_cb.blockSignals(False)
                return
        
        self.last_coupling_idx = index
        self.settingChanged.emit()

    def get_settings(self):
        return {
            "trace": self.trace_cb.currentText(), "vdiv": self.volt_cb.currentData(),
            "coupling": self.coupling_cb.currentText(), "bw": self.bw_cb.currentText(),
            "offset": self.offset_sb.value(), "invert": "ON" if self.invert_cb.isChecked() else "OFF"
        }

class OscilloscopeGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LeCroy SDA 812zi Professional Suite")
        self.resize(1400, 950)
        self._auto_apply = True
        self._live_active = False
        self._is_gui_updating = False
        self._is_syncing = False
        self.screenshot_count = 0
        self.screenshot_dir = os.path.join(os.path.expanduser("~"), "Desktop", "Screenshots_Oscilloscope")
        if not os.path.exists(self.screenshot_dir):
            try: os.makedirs(self.screenshot_dir)
            except: pass
        
        self.setStyleSheet("""
            QMainWindow { background-color: #0d1117; }
            QMenuBar { background-color: #161b22; color: #c9d1d9; border-bottom: 1px solid #30363d; }
            QMenuBar::item:selected { background-color: #30363d; }
            QMenu { background-color: #161b22; color: #c9d1d9; border: 1px solid #30363d; }
            QMenu::item:selected { background-color: #1f6feb; }
            QGroupBox {
                border: 1px solid #30363d; border-radius: 8px; font-weight: bold;
                color: #58a6ff; margin-top: 10px; padding-top: 20px; background-color: #161b22;
            }
            QLabel { color: #8b949e; font-size: 13px; }
            QLineEdit, QComboBox, QDoubleSpinBox {
                background-color: #0d1117; color: #c9d1d9; border: 1px solid #30363d;
                border-radius: 6px; padding: 6px; min-height: 25px;
            }
            QComboBox QAbstractItemView { background-color: #161b22; color: #c9d1d9; selection-background-color: #1f6feb; selection-color: white; border: 1px solid #30363d; }
            QPushButton { background-color: #21262d; color: #c9d1d9; border: 1px solid #30363d; border-radius: 6px; padding: 10px; font-weight: 600; }
            QPushButton:hover { background-color: #30363d; }
            QPushButton#connect_btn { background-color: #238636; color: white; border: none; }
            QPushButton#capture_btn { background-color: #1f6feb; color: white; border: none; }
            QTabWidget::pane { border: 1px solid #30363d; background: #161b22; border-radius: 4px; }
            QTabBar::tab { background: #0d1117; color: #8b949e; border: 1px solid #30363d; padding: 8px 15px; }
            QTabBar::tab:selected { background: #161b22; color: #58a6ff; }
            QTextEdit { background-color: #010409; color: #7ee787; font-family: 'Consolas', monospace; }
        """)

        self.worker = OscilloscopeWorker()
        self.worker.connected.connect(self.on_connected)
        self.worker.error.connect(self.on_error)
        self.worker.screenshot_ready.connect(self.display_screenshot)
        self.worker.measure_ready.connect(self.update_measures_table)
        self.worker.export_finished.connect(lambda m: self.log(m))
        self.worker.settings_ready.connect(self.apply_synced_settings)

        self.live_timer = QTimer()
        self.live_timer.timeout.connect(self.on_live_tick)
        
        self.sync_timer = QTimer()
        self.sync_timer.timeout.connect(self.poll_settings)

        self.init_menu()
        self.init_ui()

    def init_menu(self):
        menubar = self.menuBar()
        
        # File Menu
        file_menu = menubar.addMenu("File")
        save_img_action = QAction("Save Screenshot", self)
        save_img_action.triggered.connect(self.save_screenshot_to_file)
        file_menu.addAction(save_img_action)
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Setup Menu
        setup_menu = menubar.addMenu("Setup")
        export_setup_action = QAction("Export Device Setup", self)
        export_setup_action.triggered.connect(self.export_setup)
        setup_menu.addAction(export_setup_action)
        
        import_setup_action = QAction("Import Device Setup", self)
        import_setup_action.triggered.connect(self.import_setup)
        setup_menu.addAction(import_setup_action)
        
        # Info Menu
        info_menu = menubar.addMenu("Info")
        about_action = QAction("About SDA Suite", self)
        about_action.triggered.connect(lambda: self.log("LeCroy SDA 812zi Professional Suite v2.0"))
        info_menu.addAction(about_action)

    def init_ui(self):
        central = QWidget(); self.setCentralWidget(central); layout = QHBoxLayout(central)
        left_scroll = QScrollArea(); left_scroll.setWidgetResizable(True); left_scroll.setFixedWidth(420); left_scroll.setStyleSheet("border: none;")
        left_wrapper = QWidget(); left_layout = QVBoxLayout(left_wrapper); left_scroll.setWidget(left_wrapper); layout.addWidget(left_scroll)

        # 1. Connection
        conn_box = QGroupBox("INSTRUMENT")
        c_lay = QGridLayout()
        self.ip_input = QLineEdit("10.0.10.142")
        c_lay.addWidget(QLabel("IP:"), 0, 0); c_lay.addWidget(self.ip_input, 0, 1)
        self.connect_btn = QPushButton("CONNECT"); self.connect_btn.setObjectName("connect_btn"); self.connect_btn.clicked.connect(self.toggle_connection)
        c_lay.addWidget(self.connect_btn, 1, 0, 1, 2)
        self.auto_apply_cb = QCheckBox("Instant Auto-Apply (Safety Active)"); self.auto_apply_cb.setChecked(True)
        c_lay.addWidget(self.auto_apply_cb, 2, 0, 1, 2)
        conn_box.setLayout(c_lay); left_layout.addWidget(conn_box)

        # 2. Main Tabs
        main_tabs = QTabWidget()
        v_page = QWidget(); v_lay = QVBoxLayout(v_page)
        self.ch_tabs = QTabWidget(); self.channels = {}
        for ch in ["1", "2", "3", "4"]:
            ctrl = ChannelControl(ch); ctrl.settingChanged.connect(self.on_ui_change)
            ctrl.export_btn.clicked.connect(lambda checked, c=ch: self.save_waveform(c))
            self.ch_tabs.addTab(ctrl, f"CH {ch}"); self.channels[f"C{ch}"] = ctrl
        v_lay.addWidget(self.ch_tabs); main_tabs.addTab(v_page, "VERTICAL")

        h_page = QWidget(); h_lay = QGridLayout(h_page)
        self.timebase_cb = QComboBox()
        tbs = [("1ns", 1e-9), ("10ns", 1e-8), ("100ns", 1e-7), ("1us", 1e-6), ("1ms", 1e-3), ("10ms", 1e-2), ("1s", 1.0)]
        for l, v in tbs: self.timebase_cb.addItem(l, v)
        self.timebase_cb.currentIndexChanged.connect(self.on_ui_change)
        h_lay.addWidget(QLabel("Time/Div:"), 0, 0); h_lay.addWidget(self.timebase_cb, 0, 1)
        main_tabs.addTab(h_page, "HORIZONTAL")

        t_page = QWidget(); t_lay = QGridLayout(t_page)
        self.trig_mode = QComboBox(); self.trig_mode.addItems(["AUTO", "NORM", "SINGLE", "STOP"])
        t_lay.addWidget(QLabel("Mode:"), 0, 0); t_lay.addWidget(self.trig_mode, 0, 1)
        
        self.trig_type = QComboBox(); self.trig_type.addItems(["EDGE", "WIDTH", "GLITCH", "TV"])
        t_lay.addWidget(QLabel("Type:"), 1, 0); t_lay.addWidget(self.trig_type, 1, 1)

        self.trig_src = QComboBox(); self.trig_src.addItems(["C1", "C2", "C3", "C4", "LINE"])
        t_lay.addWidget(QLabel("Source:"), 2, 0); t_lay.addWidget(self.trig_src, 2, 1)

        self.trig_slope = QComboBox(); self.trig_slope.addItems(["POS", "NEG", "WINDOW"])
        t_lay.addWidget(QLabel("Slope:"), 3, 0); t_lay.addWidget(self.trig_slope, 3, 1)

        self.trig_lvl = QDoubleSpinBox(); self.trig_lvl.setRange(-20, 20); self.trig_lvl.setSingleStep(0.01)
        t_lay.addWidget(QLabel("Level:"), 4, 0); t_lay.addWidget(self.trig_lvl, 4, 1)
        main_tabs.addTab(t_page, "TRIGGER")
        left_layout.addWidget(main_tabs)

        # 3. Measures
        m_box = QGroupBox("MEASURES")
        m_lay = QVBoxLayout()
        m_sub = QHBoxLayout()
        self.m_src = QComboBox(); self.m_src.addItems(["C1", "C2", "C3", "C4"])
        self.m_type = QComboBox(); self.m_type.addItems(["PKPK", "MAX", "MIN", "FREQ", "PERIOD"])
        m_sub.addWidget(self.m_src); m_sub.addWidget(self.m_type); m_lay.addLayout(m_sub)
        self.m_table = QTableWidget(1, 3); self.m_table.setHorizontalHeaderLabels(["Param", "Type", "Value"])
        self.m_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch); self.m_table.setFixedHeight(80)
        m_lay.addWidget(self.m_table); m_box.setLayout(m_lay); left_layout.addWidget(m_box)
        left_layout.addStretch()

        # RIGHT SIDE
        right_panel = QWidget(); right_layout = QVBoxLayout(right_panel); layout.addWidget(right_panel, 1)
        
        # Dashboard Header
        dash_head = QHBoxLayout()
        dash_head.addWidget(QLabel("<b>DASHBOARD</b>"))
        
        # Trigger Shortcuts
        for m in ["AUTO", "NORM", "SINGLE", "STOP"]:
            btn = QPushButton(m); btn.setFixedWidth(60)
            if m == "STOP": btn.setStyleSheet("background-color: #da3633; color: white; border: none;")
            btn.clicked.connect(lambda checked, mode=m: self.set_trigger_mode(mode))
            dash_head.addWidget(btn)
        dash_head.addStretch()
        right_layout.addLayout(dash_head)

        # Screen Monitor Header
        l_head = QHBoxLayout()
        l_head.addWidget(QLabel("<b>SCREEN VIEW</b>"))
        self.capture_btn = QPushButton("SINGLE CAPTURE"); self.capture_btn.setObjectName("capture_btn")
        self.capture_btn.setFixedWidth(140); self.capture_btn.clicked.connect(self.single_capture)
        l_head.addWidget(self.capture_btn)
        self.live_btn = QPushButton("START LIVE"); self.live_btn.setFixedWidth(120); self.live_btn.clicked.connect(self.toggle_live)
        l_head.addWidget(self.live_btn)
        right_layout.addLayout(l_head)

        self.screen_label = QLabel("DISCONNECTED"); self.screen_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.screen_label.setStyleSheet("background-color: #000; border: 2px solid #30363d; border-radius: 8px; color: #484f58; min-height: 500px;")
        right_layout.addWidget(self.screen_label, 5)
        self.log_txt = QTextEdit(); self.log_txt.setReadOnly(True); right_layout.addWidget(self.log_txt, 1)

    def log(self, msg, error=False):
        color = "#f85149" if error else "#7ee787"
        self.log_txt.append(f"<span style='color: {color};'>[{time.strftime('%H:%M:%S')}] {msg}</span>")

    def toggle_connection(self):
        if self.worker._is_connected: 
            self.worker._is_connected = False
            self.connect_btn.setText("CONNECT")
            self.sync_timer.stop()
        else: threading.Thread(target=self.worker.connect_to_scope, args=(self.ip_input.text(),), daemon=True).start()

    def on_connected(self, idn): 
        self.log(f"SUCCESS: {idn}")
        self.connect_btn.setText("DISCONNECT")
        self.log("Syncing settings from instrument...")
        self.sync_timer.start(2500)
        self.poll_settings()

    def poll_settings(self):
        if self.worker._is_connected:
            threading.Thread(target=self.worker.fetch_all_settings, daemon=True).start()

    def on_error(self, err): self.log(f"ERROR: {err}", True)

    def toggle_live(self):
        if not self.worker._is_connected: return
        self._live_active = not self._live_active
        self.live_btn.setText("STOP LIVE" if self._live_active else "START LIVE")
        self.live_timer.start(1200) if self._live_active else self.live_timer.stop()

    def single_capture(self):
        if not self.worker._is_connected: return
        self.log("Capturing screen...")
        threading.Thread(target=self.worker.get_screenshot, daemon=True).start()

    def on_live_tick(self):
        # Sequential update to stay thread-safe within the lock
        threading.Thread(target=self._live_refresh, daemon=True).start()

    def _live_refresh(self):
        self.worker.get_screenshot()
        config = [{'p_index': 1, 'source': self.m_src.currentText(), 'type': self.m_type.currentText()}]
        self.worker.fetch_measurements(config)

    def display_screenshot(self, data):
        self._last_image_data = data # Keep for saving
        img = QImage.fromData(data)
        if img.isNull(): return
        
        # Use a safety margin to prevent layout expansion loops
        target_size = self.screen_label.size()
        target_w = max(400, target_size.width() - 8)
        target_h = max(300, target_size.height() - 8)
        
        pix = QPixmap.fromImage(img).scaled(
            target_w, target_h, 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
        self.screen_label.setPixmap(pix)

    def update_measures_table(self, data):
        for i, m in enumerate(data):
            self.m_table.setItem(i, 0, QTableWidgetItem(m['p']))
            self.m_table.setItem(i, 1, QTableWidgetItem(f"{m['source']} {m['type']}"))
            self.m_table.setItem(i, 2, QTableWidgetItem(m['value']))

    def on_ui_change(self):
        if hasattr(self, '_is_gui_updating') and self._is_gui_updating: return
        if self.auto_apply_cb.isChecked() and self.worker._is_connected: self.force_apply()

    def apply_synced_settings(self, s):
        self._is_gui_updating = True
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
            best_idx = -1
            for i in range(cb.count()):
                if cb.itemText(i).upper() == text.upper(): best_idx = i; break
            if best_idx >= 0 and cb.currentIndex() != best_idx:
                cb.blockSignals(True); cb.setCurrentIndex(best_idx); cb.blockSignals(False)

        if 'TIME_DIV' in s:
            try: set_combo_by_data(self.timebase_cb, float(s['TIME_DIV']))
            except: pass

        cpl_map = {"D50":"DC50", "D1M":"DC1M", "A1M":"AC1M", "GND":"GND"}
        bw_map = {"OFF":"Full", "200MHZ":"200MHz", "20MHZ":"20MHz"}

        for ch in ["C1", "C2", "C3", "C4"]:
            if ch not in self.channels: continue
            ctrl = self.channels[ch]
            if f'{ch}:TRACE' in s: set_combo_by_text(ctrl.trace_cb, s[f'{ch}:TRACE'])
            if f'{ch}:VOLT_DIV' in s:
                try: set_combo_by_data(ctrl.volt_cb, float(s[f'{ch}:VOLT_DIV']))
                except: pass
            if f'{ch}:OFFSET' in s:
                try: 
                    nv = float(s[f'{ch}:OFFSET'])
                    if abs(ctrl.offset_sb.value() - nv) > 0.001:
                        ctrl.offset_sb.blockSignals(True); ctrl.offset_sb.setValue(nv); ctrl.offset_sb.blockSignals(False)
                except: pass
            if f'{ch}:COUPLING' in s:
                cpl = cpl_map.get(s[f'{ch}:COUPLING'].upper(), s[f'{ch}:COUPLING'].upper())
                idx = ctrl.coupling_cb.findText(cpl)
                if idx >= 0 and ctrl.coupling_cb.currentIndex() != idx:
                    ctrl.coupling_cb.blockSignals(True)
                    ctrl.coupling_cb.setCurrentIndex(idx)
                    ctrl.last_coupling_idx = idx
                    ctrl.coupling_cb.blockSignals(False)
            if f'{ch}:BANDWIDTH_LIMIT' in s:
                bw = bw_map.get(s[f'{ch}:BANDWIDTH_LIMIT'].upper(), s[f'{ch}:BANDWIDTH_LIMIT'].upper())
                set_combo_by_text(ctrl.bw_cb, bw)
            if f'{ch}:INVERT' in s:
                is_on = s[f'{ch}:INVERT'].upper() == "ON"
                if ctrl.invert_cb.isChecked() != is_on:
                    ctrl.invert_cb.blockSignals(True); ctrl.invert_cb.setChecked(is_on); ctrl.invert_cb.blockSignals(False)

        if 'TRIG_MODE' in s: set_combo_by_text(self.trig_mode, s['TRIG_MODE'])
        if 'TRIG_TYPE' in s: set_combo_by_text(self.trig_type, s['TRIG_TYPE'])
        if 'TRIG_SRC' in s: set_combo_by_text(self.trig_src, s['TRIG_SRC'])
        if 'TRIG_LVL' in s:
            try: 
                nv = float(s['TRIG_LVL'])
                if abs(self.trig_lvl.value() - nv) > 0.001:
                    self.trig_lvl.blockSignals(True); self.trig_lvl.setValue(nv); self.trig_lvl.blockSignals(False)
            except: pass
        self._is_gui_updating = False
        # Update heartbeat LED status
        if hasattr(self, 'hb_led'):
             self.hb_led.setObjectName("heartbeat_on" if self.worker._is_connected else "heartbeat_off")
             self.hb_led.style().unpolish(self.hb_led); self.hb_led.style().polish(self.hb_led)

    def force_apply(self):
        if not self.worker._is_connected: return
        self.worker.send_command(f"TIME_DIV {self.timebase_cb.currentData()}")
        for ch, ctrl in self.channels.items():
            s = ctrl.get_settings()
            self.worker.send_command(f"{ch}:TRACE {'ON' if s['trace'] == 'ON' else 'OFF'}")
            self.worker.send_command(f"{ch}:VOLT_DIV {s['vdiv']}")
            self.worker.send_command(f"{ch}:OFFSET {s['offset']}")
            self.worker.send_command(f"{ch}:COUPLING {s['coupling']}")
            self.worker.send_command(f"{ch}:BANDWIDTH_LIMIT {s['bw']}")
            self.worker.send_command(f"{ch}:INVERT {s['invert']}")
        self.worker.send_command(f"TRIG_MODE {self.trig_mode.currentText()}")

    def set_trigger_mode(self, mode):
        idx = self.trig_mode.findText(mode)
        if idx >= 0: self.trig_mode.setCurrentIndex(idx)
        if self.worker._is_connected: self.worker.send_command(f"TRIG_MODE {mode}")

    def save_waveform(self, ch):
        if not self.worker._is_connected: return
        path, _ = QFileDialog.getSaveFileName(self, "Save Waveform Data", f"waveform_{ch}.bin", "Binary (*.bin)")
        if path: threading.Thread(target=self.worker.export_waveform, args=(f"C{ch}", path), daemon=True).start()

    def save_screenshot_to_file(self):
        if hasattr(self, '_last_image_data'):
            self.screenshot_count += 1
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"capture_{self.screenshot_count:03d}_{timestamp}.png"
            path = os.path.join(self.screenshot_dir, filename)
            try:
                with open(path, 'wb') as f: f.write(self._last_image_data)
                self.log(f"📸 Saved: {filename} (Desktop/Screenshots_Oscilloscope)")
            except Exception as e:
                self.log(f"Save Error: {e}", True)
        else: self.log("No screenshot captured yet.", True)

    def export_setup(self):
        if not self.worker._is_connected: return
        path, _ = QFileDialog.getSaveFileName(self, "Export Setup", "setup.lss", "LeCroy Setup Files (*.lss)")
        if path:
            self.log("Exporting device setup...")
            # Command to store setup as file/buffer
            # Note: SDA usually saves setup internally, we can request it via VBS.

    def import_setup(self):
        if not self.worker._is_connected: return
        path, _ = QFileDialog.getOpenFileName(self, "Import Setup", "", "LeCroy Setup Files (*.lss)")
        if path: self.log(f"Setup {os.path.basename(path)} imported.")

if __name__ == "__main__":
    app = QApplication(sys.argv); window = OscilloscopeGUI(); window.show(); sys.exit(app.exec())
