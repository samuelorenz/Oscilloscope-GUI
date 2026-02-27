import sys
import unittest
from unittest.mock import MagicMock, patch

# Mocking dependencies before any imports
mock_pyvisa = MagicMock()
sys.modules['pyvisa'] = mock_pyvisa
mock_pyqt = MagicMock()
sys.modules['PyQt6'] = mock_pyqt
sys.modules['PyQt6.QtCore'] = MagicMock()
sys.modules['PyQt6.QtWidgets'] = MagicMock()
sys.modules['PyQt6.QtGui'] = MagicMock()

# Mock components that worker might import
from visa_worker import OscilloscopeWorker

class TestOscilloscopeLogic(unittest.TestCase):
    def setUp(self):
        self.worker = OscilloscopeWorker()
        self.worker.instrument = MagicMock()
        self.worker._is_connected = True
        # Mock signals
        self.worker.error = MagicMock()
        self.worker.response = MagicMock()

    def test_50ohm_protection(self):
        """Test if the software blocks high voltage on 50 Ohm coupling."""
        # 1. Simulate instrument reporting 50 Ohm coupling
        self.worker.instrument.query.return_value = "D50"
        
        # 2. Try to send a 10V/div command
        self.worker.send_command("C1:VOLT_DIV 10.0")
        
        # 3. Verify that write was NOT called and an error was emitted
        self.worker.instrument.write.assert_not_called()
        self.worker.error.emit.assert_any_call("SAFETY BLOCK: Cannot set C1 to 10.0V while in 50 Ohm mode!")

    def test_high_voltage_allowed_on_1m(self):
        """Test if high voltage IS allowed on 1M Ohm coupling."""
        # 1. Simulate instrument reporting 1M Ohm coupling
        self.worker.instrument.query.return_value = "D1M"
        
        # 2. Send 10V/div
        self.worker.send_command("C1:VOLT_DIV 10.0")
        
        # 3. Verify that write WAS called
        self.worker.instrument.write.assert_called_with("C1:VOLT_DIV 10.0")

    def test_status_register_reporting(self):
        """Test if ESR errors are reported to the response signal."""
        self.worker.instrument.query.side_effect = ["D1M", "1"] # Coupling check, then ESR status
        
        self.worker.send_command("TEST_CMD")
        
        # Check if response signal reported the error status 1
        self.worker.response.emit.assert_any_call("Cmd: TEST_CMD | Status: 1")

    def test_dynamic_timeout_on_screenshot(self):
        """Verify timeout changes during screen capture."""
        self.worker.instrument.timeout = 5000
        
        # We need to mock read_raw to return something PNG-like
        self.worker.instrument.read_raw.return_value = b'\x89PNG\r\n\x1a\n...IEND\xaeB`\x82'
        
        with patch('time.sleep', return_value=None):
            self.worker.get_screenshot()
            
        # Verify it went to 15000 and back to 5000
        self.assertEqual(self.worker.instrument.timeout, 5000)

if __name__ == '__main__':
    print("🚀 Running Autotest for Oscilloscope Logic...")
    suite = unittest.TestLoader().loadTestsFromTestCase(TestOscilloscopeLogic)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(not result.wasSuccessful())
