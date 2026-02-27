from PyQt6.QtWidgets import (QGroupBox, QGridLayout, QLabel, QComboBox, 
                             QDoubleSpinBox, QCheckBox, QPushButton, QMessageBox)
from PyQt6.QtCore import pyqtSignal

class ChannelControl(QGroupBox):
    settingChanged = pyqtSignal()

    def __init__(self, ch_name, parent=None):
        super().__init__(f"CHANNEL {ch_name}", parent)
        self.ch_name = ch_name
        self.setObjectName(f"C{ch_name}") # For CSS accents
        layout = QGridLayout(self)
        layout.setContentsMargins(10, 25, 10, 10)
        layout.setSpacing(8)
        
        # Trace Status
        layout.addWidget(QLabel("Trace:"), 0, 0)
        self.trace_cb = QComboBox()
        self.trace_cb.addItems(["ON", "OFF"])
        self.trace_cb.setCurrentText("ON" if ch_name == "1" else "OFF")
        self.trace_cb.currentIndexChanged.connect(self.settingChanged.emit)
        layout.addWidget(self.trace_cb, 0, 1)

        # Volt/Div
        layout.addWidget(QLabel("Volt/Div:"), 1, 0)
        self.volt_cb = QComboBox()
        volts = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10]
        for v in volts:
            txt = f"{v*1000:.0f} mV" if v < 1 else f"{v} V"
            self.volt_cb.addItem(txt, v)
        self.volt_cb.setCurrentIndex(9) # 1V default
        self.volt_cb.currentIndexChanged.connect(self.settingChanged.emit)
        layout.addWidget(self.volt_cb, 1, 1)

        # Coupling & Impedance
        layout.addWidget(QLabel("Coupling:"), 2, 0)
        self.coupling_cb = QComboBox()
        self.coupling_cb.addItems(["DC1M", "DC50", "AC1M", "GND"])
        self.coupling_cb.setCurrentText("DC1M")
        self.last_coupling_idx = 0
        self.coupling_cb.currentIndexChanged.connect(self.validate_coupling_change)
        layout.addWidget(self.coupling_cb, 2, 1)

        # Bandwidth Limit
        layout.addWidget(QLabel("Bndwidth:"), 3, 0)
        self.bw_cb = QComboBox()
        self.bw_cb.addItems(["Full", "200MHz", "20MHz"])
        self.bw_cb.currentIndexChanged.connect(self.settingChanged.emit)
        layout.addWidget(self.bw_cb, 3, 1)

        # Offset
        layout.addWidget(QLabel("Offset (V):"), 4, 0)
        self.offset_sb = QDoubleSpinBox()
        self.offset_sb.setRange(-100, 100) # Increased range for SDA
        self.offset_sb.setSingleStep(0.1)
        self.offset_sb.valueChanged.connect(self.settingChanged.emit)
        layout.addWidget(self.offset_sb, 4, 1)

        # Actions
        self.invert_cb = QCheckBox("Invert")
        self.invert_cb.toggled.connect(self.settingChanged.emit)
        layout.addWidget(self.invert_cb, 5, 0)
        
        self.export_btn = QPushButton("SAVE DATA")
        self.export_btn.setStyleSheet("background-color: #1f6feb; border: none; padding: 4px; color: white;")
        layout.addWidget(self.export_btn, 5, 1)

    def validate_coupling_change(self, index):
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
            "trace": self.trace_cb.currentText(),
            "vdiv": self.volt_cb.currentData(),
            "coupling": self.coupling_cb.currentText(),
            "bw": self.bw_cb.currentText(),
            "offset": self.offset_sb.value(),
            "invert": "ON" if self.invert_cb.isChecked() else "OFF"
        }
