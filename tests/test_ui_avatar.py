import sys
import unittest
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PySide6.QtWidgets import QApplication
from judy.ui import Judy3DWidget, HologramSphereWidget

class TestJudy3DAvatar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_avatar_initialization(self):
        widget = Judy3DWidget()
        self.assertFalse(widget.is_speaking)
        self.assertIsNotNone(widget.web_view)

    def test_alias_compatibility(self):
        self.assertIs(Judy3DWidget, HologramSphereWidget)
        widget = HologramSphereWidget()
        self.assertFalse(widget.is_speaking)

    def test_speaking_toggle(self):
        widget = Judy3DWidget()
        widget.set_speaking(True)
        self.assertTrue(widget.is_speaking)

        widget.set_speaking(False)
        self.assertFalse(widget.is_speaking)

    def test_cursor_tracking_safety(self):
        widget = Judy3DWidget()
        widget.resize(320, 240)
        widget.show()
        # Ensure _track_cursor executes cleanly without exception
        widget._track_cursor()

if __name__ == "__main__":
    unittest.main()
