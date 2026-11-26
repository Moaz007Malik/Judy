import sys
import unittest
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from judy.themes import THEMES, DEFAULT_THEME, get_theme, get_theme_stylesheet
from PySide6.QtWidgets import QApplication
from judy.config import Settings
from judy.ui import MainWindow, create_judy_icon

class TestJudyThemes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_theme_registry(self):
        self.assertIn("cyberpunk", THEMES)
        self.assertIn("obsidian_gold", THEMES)
        self.assertIn("synthwave", THEMES)
        self.assertIn("matrix", THEMES)
        self.assertIn("arctic_frost", THEMES)
        self.assertIn("blood_moon", THEMES)
        self.assertGreaterEqual(len(THEMES), 6)

    def test_stylesheet_generation(self):
        for tid, theme in THEMES.items():
            css = get_theme_stylesheet(theme)
            self.assertIn(theme.bg_main, css)
            self.assertIn(theme.accent_primary, css)
            self.assertIn("hudCard", css)
            self.assertIn("hudSidebar", css)
            self.assertIn("hudDock", css)

    def test_icon_generation_with_theme_colors(self):
        theme = get_theme("obsidian_gold")
        icon = create_judy_icon(theme.accent_primary, theme.accent_secondary, theme.bg_main)
        self.assertFalse(icon.isNull())

    def test_apply_theme_on_window(self):
        settings = Settings.load()
        win = MainWindow(settings)
        for tid in ["obsidian_gold", "synthwave", "matrix", "arctic_frost", "blood_moon", "cyberpunk"]:
            win.apply_theme(tid)
            self.assertEqual(win.settings.theme, tid)
            self.assertEqual(win.current_theme.id, tid)
            # Ensure gauges and constellation updated
            self.assertEqual(win.gauge_cpu.color.name().upper(), win.current_theme.accent_primary.upper())
            self.assertEqual(win.mem_constellation.accent_color.name().upper(), win.current_theme.accent_primary.upper())

    def test_assistant_theme_command(self):
        settings = Settings.load()
        win = MainWindow(settings)
        res = win.assistant.respond("change theme to obsidian gold")
        self.assertIn("Obsidian Gold", res)
        self.assertEqual(win.settings.theme, "obsidian_gold")

        res_list = win.assistant.respond("what themes are available")
        self.assertIn("Cyberpunk Cyan", res_list)
        self.assertIn("Synthwave Sunset", res_list)

if __name__ == "__main__":
    unittest.main()
