import sys
from PyQt6.QtWidgets import QApplication
from main_gui import OscilloscopeGUI

def main():
    app = QApplication(sys.argv)
    window = OscilloscopeGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
