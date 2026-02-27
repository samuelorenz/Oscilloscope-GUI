import sys
from PyQt6.QtWidgets import QApplication
from main_gui import OscilloscopeGUI

def main():
    # Create the main QApplication instance, which manages the GUI application's control flow and main settings.
    # We pass `sys.argv` to allow command-line arguments to be processed by PyQt6 if needed.
    app = QApplication(sys.argv)
    
    # Instantiate out main application window (OscilloscopeGUI), containing controls and logic for our oscilloscope app.
    window = OscilloscopeGUI()
    
    # Display the window to the user
    window.show()
    
    # Start the event loop. `app.exec()` runs infinitely until the window is closed.
    # `sys.exit` ensures that Python handles an eventual clean exit based on the exec result.
    sys.exit(app.exec())

if __name__ == "__main__":
    # If the script is run directly, execute the main() function.
    main()
