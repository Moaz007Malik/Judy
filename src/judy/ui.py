from __future__ import annotations
import math, os, random, sys, threading, time
import http.server, socketserver
from datetime import datetime, date
from pathlib import Path
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSize, QPoint, QPointF, QRectF, QUrl
from PySide6.QtGui import (
    QAction, QFont, QIcon, QColor, QPalette, QTextCursor, QCursor, QPainterPath,
    QPixmap, QPainter, QBrush, QPen, QRadialGradient, QLinearGradient
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QTextEdit, QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QDialog, QFormLayout, QComboBox, QCheckBox, QMessageBox, QFileDialog,
    QSystemTrayIcon, QMenu, QTableWidget, QTableWidgetItem, QHeaderView,
    QSplitter, QTabWidget, QSpinBox, QProgressBar, QFrame, QScrollArea,
    QStackedWidget, QCalendarWidget
)
try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebEngineCore import QWebEngineSettings
except ImportError:
    QWebEngineView = None
    QWebEngineSettings = None
try:
    import psutil
except ImportError:
    psutil = None

import json
from .config import (
    Settings, APP_DIR, get_api_key, set_api_key, get_smtp_password, set_smtp_password,
    get_provider_key, set_provider_key, get_ollama_status
)
from .file_index import FileIndex
from .tools import ToolRunner
from .assistant import Assistant
from .lead_finder import LeadManager
from .email_client import EmailService, EMAIL_TEMPLATES
from .voice import VoiceService, NATURAL_VOICES
from .startup import set_launch_at_login
from .agents_manager import AgentsManager
from .calendar_manager import CalendarManager
from .memory_manager import MemoryManager
from .workflow_manager import WorkflowManager
from .themes import (
    THEMES, DEFAULT_THEME, Theme, get_theme, get_theme_stylesheet
)

def create_judy_icon(primary: str = "#00E5FF", secondary: str = "#0066FF", bg: str = "#050B14") -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    grad = QRadialGradient(32, 32, 30)
    grad.setColorAt(0.0, QColor(primary))
    grad.setColorAt(0.6, QColor(secondary))
    grad.setColorAt(1.0, QColor(bg))
    painter.setBrush(QBrush(grad))
    painter.setPen(QPen(QColor(primary), 2))
    painter.drawEllipse(4, 4, 56, 56)
    painter.setPen(QPen(QColor("#FFFFFF"), 3))
    painter.setFont(QFont("Segoe UI", 26, QFont.Weight.Bold))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "J")
    painter.end()
    return QIcon(pixmap)

# Default dynamic HUD stylesheet
HUD_STYLE = get_theme_stylesheet(get_theme(DEFAULT_THEME))

class _QuietHTTPHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

class Judy3DWidget(QWidget):
    """Hosts the real 3D glTF model of Judy located in C:\\Users\\Moaz Malik\\Documents\\My Data\\My Codes\\Jarvis\\Judy.
    Renders high-fidelity WebGL 3D model with Three.js, interactive orbit controls, real-time
    cursor-following head tilt, speech articulation lighting & animation, and cyberpunk holographic rings."""
    _server = None
    _port = None

    @classmethod
    def _ensure_server(cls) -> int:
        if cls._server is None:
            judy_dir = str(Path(__file__).resolve().parent.parent.parent / "Judy")
            handler = lambda *args: _QuietHTTPHandler(*args, directory=judy_dir)
            cls._server = socketserver.TCPServer(("127.0.0.1", 0), handler)
            cls._port = cls._server.server_address[1]
            t = threading.Thread(target=cls._server.serve_forever, daemon=True)
            t.start()
        return cls._port

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 240)
        self.setMouseTracking(True)
        self.is_speaking = False
        self.current_theme = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if QWebEngineView is not None:
            try:
                port = self._ensure_server()
                self.web_view = QWebEngineView(self)
                s = self.web_view.settings()
                s.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
                s.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
                s.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
                s.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
                self.web_view.page().setBackgroundColor(QColor("#050B14"))
                self.web_view.setStyleSheet("background-color: #050B14; border: none; border-radius: 8px;")
                layout.addWidget(self.web_view)

                url = f"http://127.0.0.1:{port}/viewer.html"
                self.web_view.loadFinished.connect(lambda ok: self.apply_theme(self.current_theme) if (ok and self.current_theme) else None)
                self.web_view.load(QUrl(url))

                # Real-time cursor tracking timer (~30 FPS)
                self.track_timer = QTimer(self)
                self.track_timer.timeout.connect(self._track_cursor)
                self.track_timer.start(33)
            except Exception:
                self.web_view = None
                fallback = QLabel("Judy 3D Core Active")
                fallback.setAlignment(Qt.AlignmentFlag.AlignCenter)
                fallback.setStyleSheet("color: #00E5FF; font-weight: bold;")
                layout.addWidget(fallback)
        else:
            self.web_view = None
            fallback = QLabel("Judy 3D Core Active")
            fallback.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(fallback)

    def apply_theme(self, theme: Theme):
        self.current_theme = theme
        if not theme:
            return
        if self.web_view is not None:
            try:
                self.web_view.page().setBackgroundColor(QColor(theme.bg_main))
                self.web_view.setStyleSheet(f"background-color: {theme.bg_main}; border: none; border-radius: 8px;")
                js_data = json.dumps({
                    "bg": theme.webgl_bg,
                    "keyLight": theme.webgl_key_light,
                    "rimLight": theme.webgl_rim_light,
                    "speechLight": theme.webgl_speech_light,
                    "ring1": theme.webgl_ring1,
                    "ring2": theme.webgl_ring2,
                    "grid": theme.webgl_grid,
                    "border": theme.border,
                    "accent": theme.accent_primary
                })
                self.web_view.page().runJavaScript(f"if (window.setTheme) window.setTheme({js_data});")
            except Exception:
                pass

    def _track_cursor(self):
        if not self.isVisible() or self.web_view is None:
            return
        try:
            cursor_global = QCursor.pos()
            local_pos = self.mapFromGlobal(cursor_global)
            w, h = self.width(), self.height()
            if w > 0 and h > 0:
                cx, cy = w / 2.0, h / 2.0
                dx = (local_pos.x() - cx) / (w / 2.0)
                dy = (local_pos.y() - cy) / (h / 2.0)
                nx = max(-1.6, min(1.6, dx))
                ny = max(-1.6, min(1.6, dy))
                self.web_view.page().runJavaScript(f"if (window.setCursorGaze) window.setCursorGaze({nx:.3f}, {ny:.3f});")
        except Exception:
            pass

    def set_speaking(self, speaking: bool):
        try:
            self.is_speaking = bool(speaking)
            if self.web_view is not None:
                val_str = "true" if self.is_speaking else "false"
                self.web_view.page().runJavaScript(f"if (window.setSpeaking) window.setSpeaking({val_str});")
        except Exception:
            pass

    def simulate_speech(self, duration_sec: float = 3.0):
        self.set_speaking(True)
        QTimer.singleShot(int(duration_sec * 1000), lambda: self.set_speaking(False))

# Alias so both class names are valid across the application
HologramSphereWidget = Judy3DWidget

class CircularGauge(QWidget):
    """Circular ring gauge for CPU, RAM, and Disk metrics."""
    def __init__(self, title: str, value: int, color_hex: str = "#00E5FF", track_hex: str = "#142B45", parent=None):
        super().__init__(parent)
        self.title = title
        self.value = value
        self.color = QColor(color_hex)
        self.track_color = QColor(track_hex)
        self.setFixedSize(85, 85)

    def set_color(self, color_hex: str, track_hex: str = "#142B45"):
        self.color = QColor(color_hex)
        self.track_color = QColor(track_hex)
        self.update()

    def set_value(self, val: int):
        val = max(0, min(100, val))
        if val != self.value:
            self.value = val
            if self.isVisible():
                self.update()

    def paintEvent(self, event):
        if not self.isVisible():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = 30
        cx, cy = 42, 42

        # Background track
        track_pen = QPen(self.track_color, 5)
        painter.setPen(track_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        # Progress Arc
        prog_pen = QPen(self.color, 5)
        prog_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(prog_pen)
        span = int(-self.value * 360 * 16 / 100)
        painter.drawArc(cx - r, cy - r, r * 2, r * 2, 90 * 16, span)

        # Value text
        painter.setPen(QColor("#FFFFFF"))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.drawText(QRectF(cx - r, cy - 16, r * 2, 18), Qt.AlignmentFlag.AlignCenter, f"{self.value}%")

        painter.setPen(QColor("#7E9BB8"))
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Normal))
        painter.drawText(QRectF(cx - r, cy + 2, r * 2, 16), Qt.AlignmentFlag.AlignCenter, self.title)

class MemoryConstellationWidget(QWidget):
    """Draws the neural constellation graph in the Memory Insights card."""
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(180, 80)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.accent_color = QColor("#00E5FF")
        self.nodes = [
            (20, 45), (45, 30), (75, 55), (100, 25), (130, 40), (160, 20),
            (60, 65), (115, 60), (145, 65)
        ]

    def set_accent_color(self, color_hex: str):
        self.accent_color = QColor(color_hex)
        self.update()

    def mousePressEvent(self, event):
        self.clicked.emit()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen_line = QPen(QColor(self.accent_color.red(), self.accent_color.green(), self.accent_color.blue(), 60), 1)
        painter.setPen(pen_line)

        # Draw connecting constellation lines
        for i in range(len(self.nodes) - 1):
            x1, y1 = self.nodes[i]
            x2, y2 = self.nodes[i + 1]
            painter.drawLine(x1, y1, x2, y2)

        # Cross connections
        painter.drawLine(45, 30, 100, 25)
        painter.drawLine(75, 55, 115, 60)

        # Draw glowing nodes
        painter.setPen(Qt.PenStyle.NoPen)
        for x, y in self.nodes:
            glow = QRadialGradient(x, y, 5)
            glow.setColorAt(0.0, self.accent_color)
            glow.setColorAt(1.0, QColor(self.accent_color.red(), self.accent_color.green(), self.accent_color.blue(), 0))
            painter.setBrush(QBrush(glow))
            painter.drawEllipse(x - 5, y - 5, 10, 10)
            painter.setBrush(QColor("#FFFFFF"))
            painter.drawEllipse(x - 2, y - 2, 4, 4)

class InteractiveMemoryMapCanvas(QWidget):
    node_selected = Signal(dict)

    def __init__(self, memories, parent=None):
        super().__init__(parent)
        self.memories = memories
        self.setMinimumSize(480, 360)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pulse = 0.0
        self.selected_node_id = None
        self.hovered_node_id = None
        self.search_filter = ""
        self.node_positions = {}

        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._tick)
        self.anim_timer.start(55)

    def _tick(self):
        if not self.isVisible():
            return
        self.pulse = (self.pulse + 0.08) % (2 * math.pi)
        self.update()

    def set_filter(self, text: str):
        self.search_filter = text.lower().strip()
        self.update()

    def set_memories(self, mems):
        self.memories = mems
        self.update()

    def set_theme(self, theme: Theme):
        self.theme = theme
        self.update()

    def paintEvent(self, event):
        if not self.isVisible():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2

        bg_col = QColor(self.theme.bg_input if hasattr(self, 'theme') and self.theme else "#08111D")
        painter.fillRect(self.rect(), bg_col)

        acc = QColor(self.theme.accent_primary if hasattr(self, 'theme') and self.theme else "#00E5FF")
        glow = QRadialGradient(cx, cy, min(w, h) // 2)
        glow.setColorAt(0.0, QColor(acc.red(), acc.green(), acc.blue(), 25))
        glow.setColorAt(0.7, QColor(acc.red(), acc.green(), acc.blue(), 10))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(glow))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(self.rect())

        filtered = []
        for m in self.memories:
            if not self.search_filter or (self.search_filter in m.get("key_topic", "").lower() or self.search_filter in m.get("content", "").lower() or self.search_filter in m.get("category", "").lower()):
                filtered.append(m)

        if not filtered:
            painter.setPen(QColor("#7E9BB8"))
            painter.setFont(QFont("Segoe UI", 12))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No matching neural memory nodes")
            return

        n = len(filtered)
        r_orbit = min(w, h) // 2 - 50
        self.node_positions.clear()

        cat_colors = {
            "User Preference": QColor("#00E5FF"),
            "Technical Context": QColor("#38BDF8"),
            "Operations": QColor("#00E676"),
            "Client & Outreach": QColor("#A855F7"),
            "System": QColor("#FFB300")
        }

        coords = []
        for i, m in enumerate(filtered):
            angle = (2 * math.pi / max(1, n)) * i + math.sin(self.pulse * 0.5 + i) * 0.05
            radius = r_orbit if (i % 2 == 0) else int(r_orbit * 0.72)
            nx = cx + int(radius * math.cos(angle))
            ny = cy + int(radius * math.sin(angle))
            color = cat_colors.get(m.get("category", ""), QColor("#00E5FF"))
            self.node_positions[m["id"]] = (nx, ny, 16, m, color)
            coords.append((nx, ny, color, m))

        for i in range(len(coords)):
            for j in range(i + 1, len(coords)):
                x1, y1, c1, m1 = coords[i]
                x2, y2, c2, m2 = coords[j]
                dist = math.hypot(x2 - x1, y2 - y1)
                same_cat = m1.get("category") == m2.get("category")
                if same_cat or dist < r_orbit * 0.8:
                    alpha = 60 if same_cat else 25
                    pen = QPen(QColor(0, 229, 255, alpha), 1.0)
                    painter.setPen(pen)
                    painter.drawLine(x1, y1, x2, y2)

        for nid, (nx, ny, nr, m, color) in self.node_positions.items():
            is_hover = (nid == self.hovered_node_id)
            is_sel = (nid == self.selected_node_id)

            if is_sel or is_hover:
                halo_r = nr + 8 + 3 * math.sin(self.pulse * 2)
                glow_pen = QPen(color, 2)
                painter.setPen(glow_pen)
                painter.setBrush(QColor(color.red(), color.green(), color.blue(), 45))
                painter.drawEllipse(QPointF(nx, ny), halo_r, halo_r)

            grad = QRadialGradient(nx, ny, nr)
            grad.setColorAt(0.0, QColor("#FFFFFF"))
            grad.setColorAt(0.4, color)
            grad.setColorAt(1.0, QColor(color.red(), color.green(), color.blue(), 120))
            painter.setBrush(QBrush(grad))
            painter.setPen(QPen(color, 1.5))
            painter.drawEllipse(QPointF(nx, ny), nr, nr)

            topic = m.get("key_topic", f"Node #{nid}")
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold if is_sel else QFont.Weight.Normal))
            painter.setPen(QColor("#FFFFFF" if is_sel else "#E0F2FE"))
            painter.drawText(QRectF(nx - 70, ny + nr + 2, 140, 20), Qt.AlignmentFlag.AlignCenter, topic[:18])

    def mouseMoveEvent(self, event):
        pos = event.position()
        old_hover = self.hovered_node_id
        self.hovered_node_id = None
        for nid, (nx, ny, nr, m, _) in self.node_positions.items():
            if math.hypot(pos.x() - nx, pos.y() - ny) <= nr + 6:
                self.hovered_node_id = nid
                self.setToolTip(f"<b>{m.get('key_topic')}</b> [{m.get('category')}]<br>{m.get('content')}")
                break
        if self.hovered_node_id is None:
            self.setToolTip("")
        if old_hover != self.hovered_node_id:
            self.update()

    def mousePressEvent(self, event):
        pos = event.position()
        for nid, (nx, ny, nr, m, _) in self.node_positions.items():
            if math.hypot(pos.x() - nx, pos.y() - ny) <= nr + 8:
                self.selected_node_id = nid
                self.node_selected.emit(m)
                self.update()
                break

class MemoryMapDialog(QDialog):
    """Interactive visual constellation explorer of neural memories."""
    def __init__(self, mem_mgr, parent=None):
        super().__init__(parent)
        self.mem_mgr = mem_mgr
        self.setWindowTitle("JUDY — Neural Memory Map & Knowledge Graph")
        self.resize(960, 620)
        self.setStyleSheet(HUD_STYLE)
        self.selected_memory = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(12)

        top_bar = QHBoxLayout()
        title_box = QVBoxLayout()
        t1 = QLabel("<h2>🧠 Neural Memory Map & Knowledge Constellation</h2>")
        t1.setStyleSheet("color:#00E5FF; font-weight:800; margin:0;")
        t2 = QLabel("Interactive visual map of stored facts, preferences, and context.")
        t2.setStyleSheet("color:#7E9BB8; font-size:11px; margin:0;")
        title_box.addWidget(t1)
        title_box.addWidget(t2)
        top_bar.addLayout(title_box)
        top_bar.addStretch()

        self.search_in = QLineEdit()
        self.search_in.setPlaceholderText("🔍 Filter memory nodes...")
        self.search_in.setFixedWidth(240)
        top_bar.addWidget(self.search_in)

        add_btn = QPushButton("➕ Store New Fact")
        add_btn.clicked.connect(self._add_fact)
        top_bar.addWidget(add_btn)
        layout.addLayout(top_bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.canvas = InteractiveMemoryMapCanvas(self.mem_mgr.get_memories())
        self.search_in.textChanged.connect(self.canvas.set_filter)
        self.canvas.node_selected.connect(self._on_node_selected)
        splitter.addWidget(self.canvas)

        self.inspector = QFrame()
        self.inspector.setObjectName("hudCard")
        self.inspector.setFixedWidth(340)
        ins_l = QVBoxLayout(self.inspector)
        ins_l.setContentsMargins(14, 14, 14, 14)
        ins_l.setSpacing(10)

        ins_l.addWidget(QLabel("<b>Node Inspector:</b>"))

        self.ins_cat_badge = QLabel("Select a memory node on the map")
        self.ins_cat_badge.setObjectName("hudBadge")
        ins_l.addWidget(self.ins_cat_badge)

        self.ins_topic_in = QLineEdit()
        self.ins_topic_in.setPlaceholderText("Topic / Key")
        ins_l.addWidget(self.ins_topic_in)

        self.ins_content_in = QTextEdit()
        self.ins_content_in.setPlaceholderText("Stored Fact Content")
        ins_l.addWidget(self.ins_content_in, 1)

        self.ins_conf_label = QLabel("Confidence: --%")
        self.ins_conf_label.setStyleSheet("color:#00E676; font-size:11px; font-weight:bold;")
        ins_l.addWidget(self.ins_conf_label)

        btn_row = QHBoxLayout()
        save_btn = QPushButton("💾 Save Fact")
        save_btn.clicked.connect(self._save_current_fact)
        btn_row.addWidget(save_btn)

        del_btn = QPushButton("🗑️ Delete")
        del_btn.setObjectName("dangerBtn")
        del_btn.clicked.connect(self._delete_current_fact)
        btn_row.addWidget(del_btn)
        ins_l.addLayout(btn_row)

        splitter.addWidget(self.inspector)
        layout.addWidget(splitter, 1)

        mems = self.mem_mgr.get_memories()
        if mems:
            self._on_node_selected(mems[0])

    def _on_node_selected(self, m: dict):
        self.selected_memory = m
        self.ins_cat_badge.setText(f"● {m.get('category', 'Fact')}")
        self.ins_topic_in.setText(m.get("key_topic", ""))
        self.ins_content_in.setPlainText(m.get("content", ""))
        conf = int(m.get("confidence", 1.0) * 100)
        self.ins_conf_label.setText(f"Neural Confidence: {conf}%")

    def _save_current_fact(self):
        if not self.selected_memory:
            return
        mid = self.selected_memory["id"]
        topic = self.ins_topic_in.text().strip()
        content = self.ins_content_in.toPlainText().strip()
        if topic and content:
            self.mem_mgr.update_memory(mid, key_topic=topic, content=content)
            self.canvas.set_memories(self.mem_mgr.get_memories())

    def _delete_current_fact(self):
        if not self.selected_memory:
            return
        mid = self.selected_memory["id"]
        self.mem_mgr.delete_memory(mid)
        mems = self.mem_mgr.get_memories()
        self.canvas.set_memories(mems)
        if mems:
            self._on_node_selected(mems[0])
        else:
            self.selected_memory = None
            self.ins_cat_badge.setText("No nodes")
            self.ins_topic_in.clear()
            self.ins_content_in.clear()

    def _add_fact(self):
        d = QDialog(self)
        d.setWindowTitle("Store New Neural Memory")
        d.setStyleSheet(HUD_STYLE)
        f = QFormLayout(d)
        c_in = QLineEdit("User Preference")
        t_in = QLineEdit()
        txt_in = QTextEdit()
        txt_in.setMaximumHeight(80)
        f.addRow("Category:", c_in)
        f.addRow("Topic:", t_in)
        f.addRow("Fact Content:", txt_in)
        b = QPushButton("Save Node")
        b.clicked.connect(d.accept)
        f.addRow(b)
        if d.exec() == QDialog.DialogCode.Accepted and t_in.text().strip():
            self.mem_mgr.add_memory(
                key_topic=t_in.text().strip(),
                content=txt_in.toPlainText().strip(),
                category=c_in.text().strip()
            )
            mems = self.mem_mgr.get_memories()
            self.canvas.set_memories(mems)
            self._on_node_selected(mems[-1])

class ManageProvidersDialog(QDialog):
    """Configuration dialog for Ollama, OpenAI, Claude, Gemini, Groq, OpenRouter."""
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("⚡ Manage LLM Providers & API Keys")
        self.resize(680, 560)
        self.setStyleSheet(HUD_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        t_lbl = QLabel("<h2>⚡ AI Provider & API Key Infrastructure</h2><p style='color:#7E9BB8'>Configure local Ollama models and cloud provider credentials securely in Windows Credential Locker.</p>")
        layout.addWidget(t_lbl)

        form = QFormLayout()
        form.setSpacing(10)

        # Ollama
        ol_box = QHBoxLayout()
        self.ollama_in = QLineEdit(self.settings.ollama_base_url)
        ol_test_btn = QPushButton("🔄 Test Ollama")
        ol_test_btn.setObjectName("secondaryBtn")
        self.ollama_status_lbl = QLabel("Checking...")
        ol_test_btn.clicked.connect(self._test_ollama)
        ol_box.addWidget(self.ollama_in, 1)
        ol_box.addWidget(ol_test_btn)
        ol_box.addWidget(self.ollama_status_lbl)
        form.addRow("Ollama Endpoint:", ol_box)

        # API Keys
        self.openai_in = QLineEdit(get_provider_key("openai"))
        self.openai_in.setEchoMode(QLineEdit.EchoMode.Password)
        self.openai_in.setPlaceholderText("sk-proj-...")
        form.addRow("OpenAI API Key:", self.openai_in)

        self.claude_in = QLineEdit(get_provider_key("claude"))
        self.claude_in.setEchoMode(QLineEdit.EchoMode.Password)
        self.claude_in.setPlaceholderText("sk-ant-...")
        form.addRow("Anthropic Claude Key:", self.claude_in)

        self.gemini_in = QLineEdit(get_provider_key("gemini"))
        self.gemini_in.setEchoMode(QLineEdit.EchoMode.Password)
        self.gemini_in.setPlaceholderText("AIzaSy...")
        form.addRow("Google Gemini Key:", self.gemini_in)

        self.groq_in = QLineEdit(get_provider_key("groq"))
        self.groq_in.setEchoMode(QLineEdit.EchoMode.Password)
        self.groq_in.setPlaceholderText("gsk_...")
        form.addRow("Groq API Key:", self.groq_in)

        self.openrouter_in = QLineEdit(get_provider_key("openrouter"))
        self.openrouter_in.setEchoMode(QLineEdit.EchoMode.Password)
        self.openrouter_in.setPlaceholderText("sk-or-...")
        form.addRow("OpenRouter Key:", self.openrouter_in)

        self.elevenlabs_in = QLineEdit(get_provider_key("elevenlabs"))
        self.elevenlabs_in.setEchoMode(QLineEdit.EchoMode.Password)
        self.elevenlabs_in.setPlaceholderText("xi-api-key-...")
        form.addRow("ElevenLabs Voice Key:", self.elevenlabs_in)

        layout.addLayout(form)
        layout.addStretch()

        btn_row = QHBoxLayout()
        save_btn = QPushButton("💾 Save & Synchronize Providers")
        save_btn.clicked.connect(self._save_all)
        btn_row.addStretch()
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

        self._test_ollama()

    def _test_ollama(self):
        url = self.ollama_in.text().strip() or "http://127.0.0.1:11434"
        st, col, models = get_ollama_status(url)
        self.ollama_status_lbl.setText(st)
        self.ollama_status_lbl.setStyleSheet(f"color:{col}; font-weight:bold; font-size:11px;")

    def _save_all(self):
        set_provider_key("openai", self.openai_in.text().strip())
        set_provider_key("claude", self.claude_in.text().strip())
        set_provider_key("gemini", self.gemini_in.text().strip())
        set_provider_key("groq", self.groq_in.text().strip())
        set_provider_key("openrouter", self.openrouter_in.text().strip())
        set_provider_key("elevenlabs", self.elevenlabs_in.text().strip())

        self.settings.ollama_base_url = self.ollama_in.text().strip() or "http://127.0.0.1:11434"
        self.settings.save()
        self.accept()

class ScanWorker(QThread):
    progress = Signal(int, int, float, str)
    finished_scan = Signal(int, int, bool, str)

    def __init__(self, index: FileIndex, settings: Settings):
        super().__init__()
        self.index = index
        self.settings = settings
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            indexed, errors, interrupted = self.index.scan(
                self.settings,
                progress=lambda d, t, p, f: self.progress.emit(d, t, p, f),
                should_cancel=lambda: self._cancelled
            )
            self.finished_scan.emit(indexed, errors, interrupted, "")
        except Exception as ex:
            self.finished_scan.emit(0, 0, False, str(ex))

class AsyncTelemetryWorker(QThread):
    telemetry_ready = Signal(dict)

    def __init__(self, base_url: str, cloud_model: str, default_ollama_model: str, parent=None):
        super().__init__(parent)
        self.base_url = base_url
        self.cloud_model = cloud_model
        self.default_ollama_model = default_ollama_model

    def run(self):
        try:
            ol_stat, ol_col, ol_models = get_ollama_status(self.base_url)
            ol_model_name = ol_models[0] if ol_models else self.default_ollama_model

            openai_key = bool(get_provider_key("openai"))
            claude_key = bool(get_provider_key("claude"))
            gemini_key = bool(get_provider_key("gemini"))
            groq_key = bool(get_provider_key("groq"))
            or_key = bool(get_provider_key("openrouter"))

            providers = [
                ("Ollama", ol_stat != "Offline", f"Local: {ol_model_name}", ol_col),
                ("OpenAI", openai_key, self.cloud_model, "#00E676" if openai_key else "#5C7C99"),
                ("Claude", claude_key, "claude-3-5-sonnet", "#00E676" if claude_key else "#5C7C99"),
                ("Gemini", gemini_key, "gemini-1.5-pro", "#00E676" if gemini_key else "#5C7C99"),
                ("Groq", groq_key, "llama-3.3-70b", "#00E676" if groq_key else "#5C7C99"),
                ("OpenRouter", or_key, "deepseek-r1", "#00E676" if or_key else "#5C7C99")
            ]

            self.telemetry_ready.emit({
                "ol_stat": ol_stat,
                "ol_col": ol_col,
                "ol_model_name": ol_model_name,
                "providers": providers
            })
        except Exception:
            pass

class AssistantWorker(QThread):
    response_ready = Signal(str, str)
    failed = Signal(str, str)

    def __init__(self, assistant: Assistant, text: str, parent=None):
        super().__init__(parent)
        self.assistant = assistant
        self.text = text

    def run(self):
        try:
            answer = self.assistant.respond(self.text)
            self.response_ready.emit(self.text, answer)
        except Exception as e:
            self.failed.emit(self.text, str(e))

class MainWindow(QMainWindow):
    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.index = FileIndex()
        self.tools = ToolRunner(self, self.index, settings, settings.confirm_risky_actions)
        self.assistant = Assistant(settings, self.tools)
        self.lead_mgr = LeadManager()
        self.email_svc = EmailService(settings)
        self.voice_svc = VoiceService(settings)
        self.agents_mgr = AgentsManager()
        self.cal_mgr = CalendarManager()
        self.mem_mgr = MemoryManager()
        self.memory = self.mem_mgr
        self.session_turns = 0
        self.tool_calls_count = 0
        self.telemetry_worker = None
        self.wf_mgr = WorkflowManager(self.tools)
        self.scan_worker = None
        self._active_workers = []

        # Window settings
        self.setWindowTitle("JUDY — Autonomous AI Command Center")
        self.resize(1420, 890)
        self.setMinimumSize(1260, 780)
        self.setStyleSheet(HUD_STYLE)
        self.app_icon = create_judy_icon()
        self.setWindowIcon(self.app_icon)

        # Central Root Layout
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 1. Left HUD Sidebar
        sidebar = self._build_sidebar()
        root.addWidget(sidebar)

        # 2. Main Right Area (Header + Stacked Pages + Bottom Dock)
        main_area = QWidget()
        m_layout = QVBoxLayout(main_area)
        m_layout.setContentsMargins(14, 12, 14, 12)
        m_layout.setSpacing(10)

        # Top HUD Header
        header = self._build_top_header()
        m_layout.addWidget(header)

        # Central Stack of Pages
        self.pages = QStackedWidget()
        self.page_command = self._build_page_command_center()
        self.page_ai_core = self._build_page_ai_core()
        self.page_agents = self._build_page_agents()
        self.page_tasks = self._build_page_tasks()
        self.page_calendar = self._build_page_calendar()
        self.page_memory = self._build_page_memory()
        self.page_chat = self._build_page_conversations()
        self.page_knowledge = self._build_page_knowledge_base()
        self.page_tools = self._build_page_tools()
        self.page_workflows = self._build_page_workflows()

        self.pages.addWidget(self.page_command)     # 0
        self.pages.addWidget(self.page_ai_core)     # 1
        self.pages.addWidget(self.page_agents)      # 2
        self.pages.addWidget(self.page_tasks)       # 3
        self.pages.addWidget(self.page_calendar)    # 4
        self.pages.addWidget(self.page_memory)      # 5
        self.pages.addWidget(self.page_chat)        # 6
        self.pages.addWidget(self.page_knowledge)   # 7
        self.pages.addWidget(self.page_tools)       # 8
        self.pages.addWidget(self.page_workflows)   # 9

        m_layout.addWidget(self.pages, 1)

        # Bottom Dock Bar
        dock = self._build_bottom_dock()
        m_layout.addWidget(dock)

        root.addWidget(main_area, 1)

        # System Tray Icon
        self._init_tray()

        # Apply active theme
        self.apply_theme(self.settings.theme or DEFAULT_THEME)

        # Connect Voice
        self.voice_svc.wake_triggered.connect(self.on_wake_triggered)
        self.voice_svc.voice_heard.connect(self.on_voice_heard)
        self.voice_svc.status_changed.connect(self.on_voice_status)
        if settings.wake_word_enabled:
            self.voice_svc.start_wake_listener()

        # Live Clock Timer
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)

        # System Monitor Poller Timer (0-lag psutil polling every 4s)
        self.sys_timer = QTimer(self)
        self.sys_timer.timeout.connect(self._poll_system_vitals)
        self.sys_timer.start(4000)

        # Command Center live telemetry refresh timer (every 8s)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._refresh_command_center)
        self.refresh_timer.start(8000)

        # Initial live refresh of all Command Center cards
        self._refresh_command_center(force=True)
        self._poll_system_vitals(force=True)

        # Initial greeting in chat
        self.say("Command Center online. All core subsystems optimal. Say *'Hey Judy'* to execute commands, delegate tasks to active agents, or launch workflows.")

    # ------------------ SIDEBAR ------------------

    def _build_sidebar(self) -> QWidget:
        side = QFrame()
        side.setObjectName("hudSidebar")
        side.setFixedWidth(230)
        layout = QVBoxLayout(side)
        layout.setContentsMargins(0, 14, 0, 14)
        layout.setSpacing(4)

        # Top Brand Title
        brand_box = QHBoxLayout()
        brand_box.setContentsMargins(14, 0, 14, 12)
        orb = QLabel("💠")
        orb.setStyleSheet("font-size: 20px;")
        brand_box.addWidget(orb)

        v_brand = QVBoxLayout()
        t1 = QLabel("JUDY")
        t1.setObjectName("brandTitle")
        t2 = QLabel("COMMAND CENTER")
        t2.setObjectName("brandSubtitle")
        v_brand.addWidget(t1)
        v_brand.addWidget(t2)
        brand_box.addLayout(v_brand)
        brand_box.addStretch()
        layout.addLayout(brand_box)

        # Navigation Buttons
        self.nav_buttons = []
        nav_items = [
            ("🎛️ Command Center", 0, None),
            ("🧠 AI Core", 1, None),
            ("🤖 Agents", 2, "6"),
            ("📋 Tasks", 3, "4"),
            ("📅 Calendar", 4, None),
            ("💾 Memory", 5, None),
            ("💬 Conversations", 6, "12"),
            ("📚 Knowledge Base", 7, None),
            ("🛠️ Tools & Skills", 8, "18"),
            ("🔄 Workflows", 9, None)
        ]

        for label, idx, badge in nav_items:
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 14, 0)
            btn = QPushButton(label)
            btn.setObjectName("navBtnActive" if idx == 0 else "navBtn")
            btn.clicked.connect(lambda _, i=idx: self.switch_page(i))
            self.nav_buttons.append(btn)
            row.addWidget(btn, 1)

            if badge:
                b_lbl = QLabel(badge)
                b_lbl.setObjectName("hudBadge")
                row.addWidget(b_lbl)

            layout.addLayout(row)

        layout.addStretch()

        # Bottom Sidebar: Voice Status Card
        v_card = QFrame()
        v_card.setObjectName("hudSubCard")
        v_card.setStyleSheet("margin: 10px;")
        vc_layout = QVBoxLayout(v_card)
        vc_layout.setContentsMargins(10, 10, 10, 10)
        vc_layout.setSpacing(6)

        v_head = QHBoxLayout()
        v_lbl = QLabel("VOICE STATUS")
        v_lbl.setObjectName("hudDim")
        v_lbl.setStyleSheet("font-size:10px; font-weight:700;")
        v_head.addWidget(v_lbl)
        v_head.addStretch()
        v_head.addWidget(QLabel("›"))
        vc_layout.addLayout(v_head)

        # Audio Waveform Equalizer
        self.wave_label = QLabel(" ılılı·lllı·lıl ")
        self.wave_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.wave_label.setObjectName("hudAccent")
        self.wave_label.setStyleSheet("font-size:16px; font-weight:bold;")
        vc_layout.addWidget(self.wave_label)

        self.voice_sub_label = QLabel("Listening…")
        self.voice_sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.voice_sub_label.setObjectName("hudMuted")
        self.voice_sub_label.setStyleSheet("font-size:10px;")
        vc_layout.addWidget(self.voice_sub_label)

        # Glowing Arc Mic Button
        self.sidebar_mic_btn = QPushButton("🎙️ Tap to Speak")
        self.sidebar_mic_btn.setObjectName("sidebarMicBtn")
        self.sidebar_mic_btn.clicked.connect(self.start_mic_recording)
        vc_layout.addWidget(self.sidebar_mic_btn)

        # Focus Mode Button
        focus_btn = QPushButton("⚡ Focus Mode")
        focus_btn.setObjectName("secondaryBtn")
        focus_btn.clicked.connect(lambda: self.switch_page(6))
        vc_layout.addWidget(focus_btn)

        layout.addWidget(v_card)
        return side

    def switch_page(self, index: int):
        self.pages.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setObjectName("navBtnActive" if i == index else "navBtn")
            btn.setStyle(btn.style())

    # ------------------ TOP HEADER ------------------

    def _build_top_header(self) -> QWidget:
        header = QFrame()
        header.setObjectName("hudHeader")
        header.setFixedHeight(50)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(12)

        # System Status Pill
        self.top_status = QLabel("SYSTEM STATUS  ● OPTIMAL")
        self.top_status.setObjectName("statusOptimal")
        h_layout.addWidget(self.top_status)

        h_layout.addStretch()

        # Date & Large Glowing Digital Clock
        self.clock_date = QLabel()
        self.clock_date.setObjectName("hudMuted")
        self.clock_date.setStyleSheet("font-size:11px; font-weight:600;")

        self.clock_time = QLabel()
        self.clock_time.setObjectName("hudAccent")
        self.clock_time.setStyleSheet("font-size:18px; font-weight:800; letter-spacing:1px;")

        time_box = QVBoxLayout()
        time_box.setSpacing(0)
        time_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        time_box.addWidget(self.clock_date, 0, Qt.AlignmentFlag.AlignCenter)
        time_box.addWidget(self.clock_time, 0, Qt.AlignmentFlag.AlignCenter)
        h_layout.addLayout(time_box)

        self._update_clock()
        h_layout.addStretch()

        # Search Bar
        self.top_search = QLineEdit()
        self.top_search.setPlaceholderText("🔍 Search anything...")
        self.top_search.setFixedWidth(180)
        self.top_search.returnPressed.connect(self._handle_top_search)
        h_layout.addWidget(self.top_search)

        # Visual Theme Quick-Selector
        theme_box = QHBoxLayout()
        theme_box.setSpacing(4)
        t_icon = QLabel("🎨")
        t_icon.setStyleSheet("font-size:14px;")
        theme_box.addWidget(t_icon)

        self.theme_combo = QComboBox()
        self.theme_combo.setFixedHeight(34)
        self.theme_combo.setToolTip("Switch Visual Theme")
        for tid, t in THEMES.items():
            self.theme_combo.addItem(f"{t.icon} {t.name}", tid)
        cur_t_idx = self.theme_combo.findData(self.settings.theme or DEFAULT_THEME)
        if cur_t_idx >= 0:
            self.theme_combo.setCurrentIndex(cur_t_idx)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_combo_changed)
        theme_box.addWidget(self.theme_combo)
        h_layout.addLayout(theme_box)

        # Settings Button
        set_btn = QPushButton("⚙️")
        set_btn.setFixedSize(36, 36)
        set_btn.setObjectName("secondaryBtn")
        set_btn.clicked.connect(self.open_settings)
        h_layout.addWidget(set_btn)

        # Operator / Commander Profile Pill
        user_pill = QLabel("👤 Operator / Commander")
        user_pill.setObjectName("hudBadge")
        h_layout.addWidget(user_pill)

        return header

    def _on_theme_combo_changed(self, index: int):
        tid = self.theme_combo.itemData(index)
        if tid:
            self.apply_theme(tid)

    def apply_theme(self, theme_id: str):
        theme = get_theme(theme_id)
        self.current_theme = theme
        self.settings.theme = theme.id
        self.settings.save()

        # 1. Update whole-app QSS stylesheet
        qss = get_theme_stylesheet(theme)
        self.setStyleSheet(qss)

        # 2. Update 3D WebGL core
        if hasattr(self, "hologram_widget") and self.hologram_widget:
            self.hologram_widget.apply_theme(theme)

        # 3. Update circular gauges
        if hasattr(self, "gauge_cpu") and self.gauge_cpu:
            self.gauge_cpu.set_color(theme.accent_primary, theme.border)
        if hasattr(self, "gauge_ram") and self.gauge_ram:
            self.gauge_ram.set_color(theme.accent_secondary, theme.border)
        if hasattr(self, "gauge_disk") and self.gauge_disk:
            self.gauge_disk.set_color(theme.status_optimal, theme.border)

        # 4. Update Memory Constellation graph
        if hasattr(self, "mem_constellation") and self.mem_constellation:
            self.mem_constellation.set_accent_color(theme.accent_primary)

        # 5. Update Digital Clock
        if hasattr(self, "clock_time") and self.clock_time:
            self.clock_time.setStyleSheet(f"color:{theme.accent_primary}; font-size:18px; font-weight:800; letter-spacing:1px;")

        # 6. Update App Icon & System Tray
        self.app_icon = create_judy_icon(theme.accent_primary, theme.accent_secondary, theme.bg_main)
        self.setWindowIcon(self.app_icon)
        if hasattr(self, "tray") and self.tray:
            self.tray.setIcon(self.app_icon)

        # 7. Sync top header combo without signal feedback loop
        if hasattr(self, "theme_combo") and self.theme_combo:
            idx = self.theme_combo.findData(theme.id)
            if idx >= 0 and self.theme_combo.currentIndex() != idx:
                self.theme_combo.blockSignals(True)
                self.theme_combo.setCurrentIndex(idx)
                self.theme_combo.blockSignals(False)

    def _update_clock(self):
        now = datetime.now()
        self.clock_date.setText(now.strftime("%A, %d %B %Y"))
        self.clock_time.setText(now.strftime("%I:%M:%S %p"))

    def _handle_top_search(self):
        q = self.top_search.text().strip()
        if not q:
            return
        self.top_search.clear()
        self.switch_page(6)  # Switch to Conversations
        self.send_prompt(q)

    # ------------------ PAGE 0: COMMAND CENTER (MAIN DASHBOARD) ------------------

    def _build_page_command_center(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border:none; background:transparent;")

        container = QWidget()
        container.setStyleSheet("background:transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 4, 0)
        layout.setSpacing(12)

        # ===== ROW 1: AI CORE OVERVIEW | HOLOGRAPHIC AI CORE | LIVE INTELLIGENCE FEED =====
        r1 = QHBoxLayout()
        r1.setSpacing(12)

        # Card 1: AI CORE OVERVIEW
        card_ai_overview = QFrame()
        card_ai_overview.setObjectName("hudCard")
        c1 = QVBoxLayout(card_ai_overview)
        c1.setContentsMargins(14, 12, 14, 12)
        c1.setSpacing(10)

        c1_head = QLabel("AI CORE OVERVIEW")
        c1_head.setStyleSheet("color:#7E9BB8; font-size:11px; font-weight:700;")
        c1.addWidget(c1_head)

        self.lbl_ov_ai_core = QLabel("Hybrid")
        self.lbl_ov_memory = QLabel("0 Stored")
        self.lbl_ov_voice = QLabel("Online")
        self.lbl_ov_agents = QLabel("0 Running")
        self.lbl_ov_llms = QLabel("0 Connected")
        self.lbl_ov_system = QLabel("Optimal")

        ov_items = [
            ("🧠 AI Core", self.lbl_ov_ai_core, "#00E5FF"),
            ("💾 Memory", self.lbl_ov_memory, "#00E5FF"),
            ("🎙️ Voice", self.lbl_ov_voice, "#00E5FF"),
            ("🤖 Agents", self.lbl_ov_agents, "#A855F7"),
            ("⚡ LLMs", self.lbl_ov_llms, "#FFB300"),
            ("🛡️ System", self.lbl_ov_system, "#00E676")
        ]
        for name, lbl_val, col in ov_items:
            row = QHBoxLayout()
            l1 = QLabel(name)
            l1.setStyleSheet("color:#E0F2FE; font-weight:600; font-size:12px;")
            lbl_val.setStyleSheet(f"color:{col}; font-weight:700; font-size:11px;")
            row.addWidget(l1)
            row.addStretch()
            row.addWidget(lbl_val)
            c1.addLayout(row)

        c1.addStretch()
        btn_ai_ov_more = QPushButton("Configure AI Core ›")
        btn_ai_ov_more.setStyleSheet("background:transparent; border:none; color:#00E5FF; font-weight:700; text-align:left; font-size:11px; padding:0;")
        btn_ai_ov_more.clicked.connect(lambda: self.switch_page(1))
        c1.addWidget(btn_ai_ov_more)
        r1.addWidget(card_ai_overview, 2)

        # Card 2: HOLOGRAPHIC AI CORE SPHERE (Center)
        card_sphere = QFrame()
        card_sphere.setObjectName("hudCard")
        c2 = QVBoxLayout(card_sphere)
        c2.setContentsMargins(6, 6, 6, 6)
        self.hologram_widget = HologramSphereWidget()
        c2.addWidget(self.hologram_widget)
        r1.addWidget(card_sphere, 4)

        # Card 3: LIVE INTELLIGENCE FEED (Right)
        card_intel = QFrame()
        # Card 3: LIVE INTELLIGENCE FEED (Right)
        card_intel = QFrame()
        card_intel.setObjectName("hudCard")
        c3 = QVBoxLayout(card_intel)
        c3.setContentsMargins(14, 12, 14, 12)
        c3.setSpacing(8)

        c3_top = QHBoxLayout()
        i_title = QLabel("LIVE INTELLIGENCE FEED")
        i_title.setStyleSheet("color:#7E9BB8; font-size:11px; font-weight:700;")
        c3_top.addWidget(i_title)
        c3_top.addStretch()
        live_pill = QLabel("● LIVE")
        live_pill.setStyleSheet("color:#00E676; font-size:10px; font-weight:700;")
        c3_top.addWidget(live_pill)
        c3.addLayout(c3_top)

        self.feed_box = QVBoxLayout()
        self.feed_box.setSpacing(6)
        c3.addLayout(self.feed_box)

        # Pre-allocate 5 static feed slots (0 layout thrashing)
        self.feed_slots = []
        for _ in range(5):
            f_frame = QFrame()
            f_frame.setStyleSheet("background-color:#0B192C; border:1px solid #142B45; border-radius:6px; padding:2px;")
            f_l = QHBoxLayout(f_frame)
            f_l.setContentsMargins(8, 6, 8, 6)
            f_l.setSpacing(8)

            ic_lbl = QLabel("💠")
            ic_lbl.setStyleSheet("font-size:14px;")
            f_l.addWidget(ic_lbl)

            v_txt = QVBoxLayout()
            v_txt.setSpacing(1)
            t_lbl = QLabel("")
            d_lbl = QLabel("")
            v_txt.addWidget(t_lbl)
            v_txt.addWidget(d_lbl)
            f_l.addLayout(v_txt, 1)

            b_lbl = QLabel("Live")
            b_lbl.setStyleSheet("color:#5C7C99; font-size:9px; font-weight:700; background:#071220; border:1px solid #142B45; border-radius:4px; padding:2px 6px;")
            f_l.addWidget(b_lbl)

            self.feed_box.addWidget(f_frame)
            self.feed_slots.append((ic_lbl, t_lbl, d_lbl, b_lbl))

        c3.addStretch()
        btn_intel_more = QPushButton("View All Intelligence ›")
        btn_intel_more.setStyleSheet("background:transparent; border:none; color:#00E5FF; font-weight:700; text-align:left; font-size:11px; padding:0;")
        btn_intel_more.clicked.connect(lambda: self.switch_page(3))
        c3.addWidget(btn_intel_more)

        r1.addWidget(card_intel, 3)
        layout.addLayout(r1)

        # ===== ROW 2: ACTIVE AGENTS | MISSION TIMELINE | QUICK COMMANDS =====
        r2 = QHBoxLayout()
        r2.setSpacing(12)

        # Card 4: ACTIVE AGENTS
        card_agents = QFrame()
        card_agents.setObjectName("hudCard")
        c4 = QVBoxLayout(card_agents)
        c4.setContentsMargins(14, 12, 14, 12)
        c4.setSpacing(8)

        c4_top = QHBoxLayout()
        ag_title = QLabel("ACTIVE AGENTS")
        ag_title.setStyleSheet("color:#7E9BB8; font-size:11px; font-weight:700;")
        c4_top.addWidget(ag_title)
        c4_top.addStretch()
        ag_view = QPushButton("View All ›")
        ag_view.setStyleSheet("background:transparent; border:none; color:#00E5FF; font-weight:700; font-size:11px; padding:0;")
        ag_view.clicked.connect(lambda: self.switch_page(2))
        c4_top.addWidget(ag_view)
        c4.addLayout(c4_top)

        self.hud_agents_grid = QGridLayout()
        self.hud_agents_grid.setSpacing(8)
        c4.addLayout(self.hud_agents_grid)

        # Pre-allocate 4 agent cards
        self.hud_agent_slots = []
        for i in range(4):
            box = QFrame()
            box.setStyleSheet("background-color:#0B192C; border:1px solid #142B45; border-radius:8px;")
            bl = QVBoxLayout(box)
            bl.setContentsMargins(10, 8, 10, 8)
            bl.setSpacing(4)

            top_r = QHBoxLayout()
            av_lbl = QLabel("🤖")
            av_lbl.setStyleSheet("font-size:14px;")
            name_lbl = QLabel("Agent")
            name_lbl.setStyleSheet("color:#E0F2FE; font-size:11px;")
            top_r.addWidget(av_lbl)
            top_r.addWidget(name_lbl)
            top_r.addStretch()

            st_pill = QLabel("● Standby")
            st_pill.setStyleSheet("color:#38BDF8; font-size:9px; font-weight:700;")
            top_r.addWidget(st_pill)
            bl.addLayout(top_r)

            role_lbl = QLabel("")
            bl.addWidget(role_lbl)

            btn = QPushButton("Deploy Task ›")
            btn.setStyleSheet("background:transparent; border:none; color:#00E5FF; font-size:10px; font-weight:700; text-align:right; padding:0;")
            btn.clicked.connect(lambda: self.switch_page(2))
            bl.addWidget(btn)

            self.hud_agents_grid.addWidget(box, i // 2, i % 2)
            self.hud_agent_slots.append((av_lbl, name_lbl, st_pill, role_lbl, btn))

        r2.addWidget(card_agents, 4)

        # Card 5: MISSION TIMELINE
        card_timeline = QFrame()
        card_timeline.setObjectName("hudCard")
        c5 = QVBoxLayout(card_timeline)
        c5.setContentsMargins(14, 12, 14, 12)
        c5.setSpacing(8)

        c5_top = QHBoxLayout()
        t_title = QLabel("MISSION TIMELINE")
        t_title.setStyleSheet("color:#7E9BB8; font-size:11px; font-weight:700;")
        c5_top.addWidget(t_title)
        c5_top.addStretch()
        t_sub = QLabel("Today ▾")
        t_sub.setStyleSheet("color:#00E5FF; font-size:11px; font-weight:700;")
        c5_top.addWidget(t_sub)
        c5.addLayout(c5_top)

        self.hud_timeline_box = QVBoxLayout()
        self.hud_timeline_box.setSpacing(6)
        c5.addLayout(self.hud_timeline_box)

        # Pre-allocate 3 timeline rows
        self.hud_timeline_slots = []
        for _ in range(3):
            ev_box = QFrame()
            ev_box.setStyleSheet("background-color:#0B192C; border:1px solid #142B45; border-radius:6px;")
            el = QHBoxLayout(ev_box)
            el.setContentsMargins(10, 6, 10, 6)
            el.setSpacing(8)

            t_badge = QLabel("12:00 PM")
            t_badge.setStyleSheet("color:#00E5FF; font-weight:700; font-size:10px;")
            el.addWidget(t_badge)

            v = QVBoxLayout()
            v.setSpacing(1)
            title_lbl = QLabel("")
            cat_lbl = QLabel("")
            v.addWidget(title_lbl)
            v.addWidget(cat_lbl)
            el.addLayout(v, 1)

            st_icon = QLabel("⏳")
            el.addWidget(st_icon)

            self.hud_timeline_box.addWidget(ev_box)
            self.hud_timeline_slots.append((t_badge, title_lbl, cat_lbl, st_icon))

        c5.addStretch()
        full_sched = QPushButton("View Full Schedule ›")
        full_sched.setStyleSheet("background:transparent; border:none; color:#00E5FF; font-weight:700; text-align:left; font-size:11px; padding:0;")
        full_sched.clicked.connect(lambda: self.switch_page(4))
        c5.addWidget(full_sched)

        r2.addWidget(card_timeline, 3)

        # Card 6: QUICK COMMANDS
        card_cmds = QFrame()
        card_cmds.setObjectName("hudCard")
        c6 = QVBoxLayout(card_cmds)
        c6.setContentsMargins(14, 12, 14, 12)
        c6.setSpacing(8)

        qc_title = QLabel("QUICK COMMANDS")
        qc_title.setStyleSheet("color:#7E9BB8; font-size:11px; font-weight:700;")
        c6.addWidget(qc_title)

        commands = [
            ("➕ Start New Task", lambda: self.switch_page(3)),
            ("📅 Open Calendar", lambda: self.switch_page(4)),
            ("🎙️ Start Voice Chat", self.start_mic_recording),
            ("▶️ Run Workflow", lambda: self.switch_page(9))
        ]
        for label, handler in commands:
            b = QPushButton(label)
            b.setObjectName("secondaryBtn")
            b.setMinimumHeight(30)
            b.clicked.connect(handler)
            c6.addWidget(b)

        c6.addStretch()
        r2.addWidget(card_cmds, 2)
        layout.addLayout(r2)

        # ===== ROW 3: SYSTEM MONITOR | MEMORY INSIGHTS | LLM STATUS =====
        r3 = QHBoxLayout()
        r3.setSpacing(12)

        # Card 7: SYSTEM MONITOR
        card_sys = QFrame()
        card_sys.setObjectName("hudCard")
        c7 = QVBoxLayout(card_sys)
        c7.setContentsMargins(14, 12, 14, 12)
        c7.setSpacing(8)

        sys_title = QLabel("SYSTEM MONITOR")
        sys_title.setStyleSheet("color:#7E9BB8; font-size:11px; font-weight:700;")
        c7.addWidget(sys_title)

        gauge_row = QHBoxLayout()
        self.gauge_cpu = CircularGauge("CPU", 15, "#00E5FF")
        self.gauge_ram = CircularGauge("RAM", 54, "#38BDF8")
        self.gauge_disk = CircularGauge("Disk", 40, "#00E676")
        gauge_row.addWidget(self.gauge_cpu)
        gauge_row.addWidget(self.gauge_ram)
        gauge_row.addWidget(self.gauge_disk)
        c7.addLayout(gauge_row)
        r3.addWidget(card_sys, 3)

        # Card 8: MEMORY INSIGHTS
        card_mem = QFrame()
        card_mem.setObjectName("hudCard")
        c8 = QVBoxLayout(card_mem)
        c8.setContentsMargins(14, 12, 14, 12)
        c8.setSpacing(6)

        m_title = QLabel("MEMORY INSIGHTS")
        m_title.setStyleSheet("color:#7E9BB8; font-size:11px; font-weight:700;")
        c8.addWidget(m_title)

        m_split = QHBoxLayout()
        self.mem_constellation = MemoryConstellationWidget()
        self.mem_constellation.clicked.connect(self.open_memory_map)
        m_split.addWidget(self.mem_constellation, 1)

        v_m_stats = QVBoxLayout()
        v_m_stats.setSpacing(2)
        self.lbl_mem_count = QLabel("Memories: <b style='color:#00E5FF'>--</b>")
        self.lbl_session_turns = QLabel("Session Turns: <b style='color:#E0F2FE'>0</b>")
        self.lbl_tool_calls = QLabel("Tool Calls: <b style='color:#00E676'>0</b>")
        v_m_stats.addWidget(self.lbl_mem_count)
        v_m_stats.addWidget(self.lbl_session_turns)
        v_m_stats.addWidget(self.lbl_tool_calls)
        m_split.addLayout(v_m_stats)
        c8.addLayout(m_split)

        btn_v_map = QPushButton("View Memory Map ›")
        btn_v_map.setStyleSheet("background:transparent; border:none; color:#00E5FF; font-weight:700; text-align:left; font-size:11px; padding:0;")
        btn_v_map.clicked.connect(self.open_memory_map)
        c8.addWidget(btn_v_map)
        r3.addWidget(card_mem, 3)

        # Card 9: LLM STATUS
        card_llm = QFrame()
        card_llm.setObjectName("hudCard")
        c9 = QVBoxLayout(card_llm)
        c9.setContentsMargins(14, 12, 14, 12)
        c9.setSpacing(6)

        c9_top = QHBoxLayout()
        llm_title = QLabel("LLM STATUS")
        llm_title.setStyleSheet("color:#7E9BB8; font-size:11px; font-weight:700;")
        c9_top.addWidget(llm_title)
        c9_top.addStretch()
        self.lbl_llm_conn_pill = QLabel("1 Connected")
        self.lbl_llm_conn_pill.setStyleSheet("color:#00E676; font-size:10px; font-weight:700;")
        c9_top.addWidget(self.lbl_llm_conn_pill)
        c9.addLayout(c9_top)

        self.llm_grid = QGridLayout()
        self.llm_grid.setSpacing(6)
        c9.addLayout(self.llm_grid)

        # Pre-allocate 6 provider chips
        self.llm_chip_slots = []
        init_names = ["Ollama", "OpenAI", "Claude", "Gemini", "Groq", "OpenRouter"]
        for idx, name in enumerate(init_names):
            chip = QFrame()
            chip.setStyleSheet("background-color:#0A1626; border:1px solid #142B45; border-radius:6px;")
            cl = QHBoxLayout(chip)
            cl.setContentsMargins(8, 4, 8, 4)
            cl.setSpacing(6)

            dot = QLabel("○")
            dot.setStyleSheet("color:#5C7C99; font-size:10px; font-weight:bold;")
            cl.addWidget(dot)

            v_txt = QVBoxLayout()
            v_txt.setSpacing(0)
            n_lbl = QLabel(f"<b>{name}</b>")
            n_lbl.setStyleSheet("color:#E0F2FE; font-size:10px;")
            m_lbl = QLabel("<span style='color:#7E9BB8; font-size:9px;'>Checking...</span>")
            v_txt.addWidget(n_lbl)
            v_txt.addWidget(m_lbl)
            cl.addLayout(v_txt, 1)

            st_badge = QLabel("Unlinked")
            st_badge.setStyleSheet("color:#5C7C99; font-size:8px; font-weight:700;")
            cl.addWidget(st_badge)

            self.llm_grid.addWidget(chip, idx // 2, idx % 2)
            self.llm_chip_slots.append((dot, n_lbl, m_lbl, st_badge))

        c9.addStretch()
        btn_manage_llm = QPushButton("Manage Providers ›")
        btn_manage_llm.setStyleSheet("background:transparent; border:none; color:#00E5FF; font-weight:700; text-align:left; font-size:11px; padding:0;")
        btn_manage_llm.clicked.connect(self.open_manage_providers)
        c9.addWidget(btn_manage_llm)

        r3.addWidget(card_llm, 3)
        layout.addLayout(r3)

        scroll.setWidget(container)
        return scroll

    # ------------------ PAGE 1: AI CORE ------------------

    def _build_page_ai_core(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)

        card = QFrame()
        card.setObjectName("hudCard")
        c_layout = QVBoxLayout(card)
        c_layout.addWidget(QLabel("<h2>🧠 JUDY AI Core Engine Configuration</h2><p style='color:#7E9BB8'>Direct control over LLM providers, temperature, context length, and model checkpoints.</p>"))

        form = QFormLayout()
        mode_box = QComboBox()
        mode_box.addItem("Hybrid — Local Ollama with Cloud Fallback", "hybrid")
        mode_box.addItem("Local Ollama Only", "local")
        mode_box.addItem("Cloud Only", "cloud")
        form.addRow("AI Mode", mode_box)

        ollama_in = QLineEdit(self.settings.ollama_base_url)
        form.addRow("Ollama Endpoint", ollama_in)

        model_in = QLineEdit(self.settings.ollama_model)
        form.addRow("Local Model", model_in)

        cloud_in = QLineEdit(self.settings.cloud_model)
        form.addRow("Cloud Model", cloud_in)

        c_layout.addLayout(form)
        c_layout.addStretch()

        save_btn = QPushButton("Save AI Core Settings")
        save_btn.clicked.connect(lambda: self.say("AI Core parameters updated and synchronized."))
        c_layout.addWidget(save_btn)

        layout.addWidget(card)
        return panel

    # ------------------ PAGE 2: AGENTS ------------------

    def _build_page_agents(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)

        # Header bar
        top = QFrame()
        top.setObjectName("hudCard")
        t_l = QHBoxLayout(top)
        t_l.addWidget(QLabel("<h2>🤖 Autonomous Agent Fleet</h2>"))
        t_l.addStretch()

        new_agent_btn = QPushButton("➕ Create Custom Agent")
        new_agent_btn.clicked.connect(self._dialog_create_agent)
        t_l.addWidget(new_agent_btn)

        assign_task_btn = QPushButton("📋 Assign Task to Agent")
        assign_task_btn.setObjectName("secondaryBtn")
        assign_task_btn.clicked.connect(self._dialog_assign_task)
        t_l.addWidget(assign_task_btn)

        layout.addWidget(top)

        # Agents Grid
        self.agents_grid = QGridLayout()
        self.agents_grid.setSpacing(12)
        layout.addLayout(self.agents_grid)

        # Tasks Table for Agents
        t_card = QFrame()
        t_card.setObjectName("hudCard")
        t_layout = QVBoxLayout(t_card)
        t_layout.addWidget(QLabel("<b>Active Assigned Agent Tasks:</b>"))

        self.agent_task_table = QTableWidget()
        self.agent_task_table.setColumnCount(6)
        self.agent_task_table.setHorizontalHeaderLabels(["ID", "Agent", "Task Title", "Priority", "Status", "Due Date"])
        self.agent_task_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.agent_task_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        t_layout.addWidget(self.agent_task_table)

        layout.addWidget(t_card, 1)

        self._refresh_agents_view()
        return panel

    def _refresh_agents_view(self):
        # Clear existing
        while self.agents_grid.count():
            item = self.agents_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        agents = self.agents_mgr.get_all_agents()
        for idx, ag in enumerate(agents):
            card = QFrame()
            card.setObjectName("hudCard")
            c = QVBoxLayout(card)
            c.setContentsMargins(12, 10, 12, 10)
            c.setSpacing(6)

            h = QHBoxLayout()
            h.addWidget(QLabel(f"<span style='font-size:18px'>{ag['avatar']}</span> <b>{ag['name']}</b>"))
            h.addStretch()
            col = "#00E676" if ag["status"] == "Active" else "#A855F7"
            st_lbl = QLabel(f"● {ag['status']}")
            st_lbl.setStyleSheet(f"color:{col}; font-weight:700; font-size:11px;")
            h.addWidget(st_lbl)
            c.addLayout(h)

            r_lbl = QLabel(ag["role"])
            r_lbl.setStyleSheet("color:#7E9BB8; font-size:11px;")
            c.addWidget(r_lbl)

            d_lbl = QLabel(ag["description"][:120])
            d_lbl.setWordWrap(True)
            d_lbl.setStyleSheet("color:#E0F2FE; font-size:11px;")
            c.addWidget(d_lbl)

            row = idx // 3
            col_pos = idx % 3
            self.agents_grid.addWidget(card, row, col_pos)

        # Refresh tasks
        tasks = self.agents_mgr.get_tasks()
        self.agent_task_table.setRowCount(len(tasks))
        for row, t in enumerate(tasks):
            self.agent_task_table.setItem(row, 0, QTableWidgetItem(str(t["id"])))
            self.agent_task_table.setItem(row, 1, QTableWidgetItem(f"{t.get('agent_avatar','🤖')} {t.get('agent_name','Agent')}"))
            self.agent_task_table.setItem(row, 2, QTableWidgetItem(t["title"]))
            self.agent_task_table.setItem(row, 3, QTableWidgetItem(t["priority"]))
            self.agent_task_table.setItem(row, 4, QTableWidgetItem(t["status"]))
            self.agent_task_table.setItem(row, 5, QTableWidgetItem(t["due_date"]))

    def _dialog_create_agent(self):
        d = QDialog(self)
        d.setWindowTitle("Create New Autonomous Agent")
        d.setWindowIcon(self.app_icon)
        d.setStyleSheet(HUD_STYLE)
        f = QFormLayout(d)
        name_in = QLineEdit()
        role_in = QLineEdit()
        avatar_in = QLineEdit("🤖")
        desc_in = QTextEdit()
        desc_in.setMaximumHeight(80)
        skills_in = QLineEdit()

        f.addRow("Agent Name", name_in)
        f.addRow("Role / Function", role_in)
        f.addRow("Icon / Avatar", avatar_in)
        f.addRow("Description", desc_in)
        f.addRow("Skills (comma separated)", skills_in)

        btn = QPushButton("Deploy Agent")
        btn.clicked.connect(d.accept)
        f.addRow(btn)

        if d.exec() == QDialog.DialogCode.Accepted and name_in.text().strip():
            self.agents_mgr.add_agent(
                name=name_in.text().strip(),
                role=role_in.text().strip(),
                avatar=avatar_in.text().strip() or "🤖",
                description=desc_in.toPlainText().strip(),
                skills=skills_in.text().strip()
            )
            self._refresh_agents_view()
            self.say(f"Agent **{name_in.text()}** successfully deployed to fleet.")

    def _dialog_assign_task(self):
        d = QDialog(self)
        d.setWindowTitle("Assign Task to Agent")
        d.setWindowIcon(self.app_icon)
        d.setStyleSheet(HUD_STYLE)
        f = QFormLayout(d)

        ag_combo = QComboBox()
        agents = self.agents_mgr.get_all_agents()
        for ag in agents:
            ag_combo.addItem(f"{ag['avatar']} {ag['name']}", ag["id"])
        f.addRow("Assign To Agent", ag_combo)

        title_in = QLineEdit()
        f.addRow("Task Title", title_in)

        desc_in = QTextEdit()
        desc_in.setMaximumHeight(80)
        f.addRow("Task Objective", desc_in)

        prio_combo = QComboBox()
        for p in ["Urgent", "High", "Medium", "Low"]:
            prio_combo.addItem(p)
        f.addRow("Priority", prio_combo)

        due_in = QLineEdit("Today")
        f.addRow("Due Date", due_in)

        btn = QPushButton("Assign & Dispatch")
        btn.clicked.connect(d.accept)
        f.addRow(btn)

        if d.exec() == QDialog.DialogCode.Accepted and title_in.text().strip():
            self.agents_mgr.assign_task(
                agent_id=ag_combo.currentData(),
                title=title_in.text().strip(),
                description=desc_in.toPlainText().strip(),
                priority=prio_combo.currentText(),
                due_date=due_in.text().strip()
            )
            self._refresh_agents_view()
            self.say(f"Task **{title_in.text()}** assigned to {ag_combo.currentText()}.")

    # ------------------ PAGE 3: TASKS ------------------

    def _build_page_tasks(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)

        top = QFrame()
        top.setObjectName("hudCard")
        tl = QHBoxLayout(top)
        tl.addWidget(QLabel("<h2>📋 Mission Task Operations</h2>"))
        tl.addStretch()

        add_t_btn = QPushButton("➕ Add Task")
        add_t_btn.clicked.connect(self._dialog_assign_task)
        tl.addWidget(add_t_btn)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setObjectName("secondaryBtn")
        refresh_btn.clicked.connect(self._refresh_agents_view)
        tl.addWidget(refresh_btn)

        layout.addWidget(top)

        # Task Table
        self.main_task_table = QTableWidget()
        self.main_task_table.setColumnCount(6)
        self.main_task_table.setHorizontalHeaderLabels(["ID", "Agent Assignee", "Task Title", "Priority", "Status", "Due Date"])
        self.main_task_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.main_task_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.main_task_table, 1)

        # Actions
        act_row = QHBoxLayout()
        done_btn = QPushButton("✅ Mark Completed")
        done_btn.clicked.connect(self._mark_task_done)
        act_row.addWidget(done_btn)

        del_btn = QPushButton("🗑️ Delete Task")
        del_btn.setObjectName("dangerBtn")
        del_btn.clicked.connect(self._delete_task)
        act_row.addWidget(del_btn)
        act_row.addStretch()
        layout.addLayout(act_row)

        self._populate_tasks_page()
        return panel

    def _populate_tasks_page(self):
        tasks = self.agents_mgr.get_tasks()
        self.main_task_table.setRowCount(len(tasks))
        for row, t in enumerate(tasks):
            self.main_task_table.setItem(row, 0, QTableWidgetItem(str(t["id"])))
            self.main_task_table.setItem(row, 1, QTableWidgetItem(f"{t.get('agent_avatar','🤖')} {t.get('agent_name','Agent')}"))
            self.main_task_table.setItem(row, 2, QTableWidgetItem(t["title"]))
            self.main_task_table.setItem(row, 3, QTableWidgetItem(t["priority"]))
            self.main_task_table.setItem(row, 4, QTableWidgetItem(t["status"]))
            self.main_task_table.setItem(row, 5, QTableWidgetItem(t["due_date"]))

    def _mark_task_done(self):
        r = self.main_task_table.currentRow()
        if r >= 0:
            tid = int(self.main_task_table.item(r, 0).text())
            self.agents_mgr.update_task_status(tid, "Completed", "Finished by operator")
            self._populate_tasks_page()
            self._refresh_agents_view()

    def _delete_task(self):
        r = self.main_task_table.currentRow()
        if r >= 0:
            tid = int(self.main_task_table.item(r, 0).text())
            self.agents_mgr.delete_task(tid)
            self._populate_tasks_page()
            self._refresh_agents_view()

    # ------------------ PAGE 4: CALENDAR ------------------

    def _build_page_calendar(self) -> QWidget:
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setSpacing(14)

        # Left: Interactive Calendar Widget
        left = QFrame()
        left.setObjectName("hudCard")
        ll = QVBoxLayout(left)
        ll.addWidget(QLabel("<h2>📅 Command Calendar</h2>"))

        self.cal_widget = QCalendarWidget()
        self.cal_widget.setStyleSheet("""
            QCalendarWidget QWidget { background-color: #08111D; color: #E0F2FE; }
            QCalendarWidget QToolButton { color: #00E5FF; font-weight: bold; }
            QCalendarWidget QMenu { background-color: #0A1322; }
        """)
        ll.addWidget(self.cal_widget)

        add_ev_btn = QPushButton("➕ Schedule New Milestone")
        add_ev_btn.clicked.connect(self._dialog_add_event)
        ll.addWidget(add_ev_btn)
        layout.addWidget(left, 1)

        # Right: Mission Timeline Event List
        right = QFrame()
        right.setObjectName("hudCard")
        rl = QVBoxLayout(right)
        rl.addWidget(QLabel("<h3>Today's Mission Timeline:</h3>"))

        self.cal_event_list = QListWidget()
        rl.addWidget(self.cal_event_list, 1)
        layout.addWidget(right, 1)

        self._refresh_calendar_events()
        return panel

    def _refresh_calendar_events(self):
        self.cal_event_list.clear()
        events = self.cal_mgr.get_today_timeline()
        for ev in events:
            st = "✅ Completed" if ev["is_completed"] else "⏳ Scheduled"
            item = QListWidgetItem(f"⏰ {ev['event_time']} — {ev['title']} [{ev['category']}]\n   Status: {st}\n   Note: {ev['description']}")
            self.cal_event_list.addItem(item)

    def _dialog_add_event(self):
        d = QDialog(self)
        d.setWindowTitle("Schedule Milestone")
        d.setWindowIcon(self.app_icon)
        d.setStyleSheet(HUD_STYLE)
        f = QFormLayout(d)
        t_in = QLineEdit()
        time_in = QLineEdit("03:00 PM")
        cat_in = QLineEdit("Operations")
        desc_in = QLineEdit()

        f.addRow("Event Title", t_in)
        f.addRow("Time", time_in)
        f.addRow("Category", cat_in)
        f.addRow("Description", desc_in)

        b = QPushButton("Add Event")
        b.clicked.connect(d.accept)
        f.addRow(b)

        if d.exec() == QDialog.DialogCode.Accepted and t_in.text().strip():
            self.cal_mgr.add_event(
                title=t_in.text().strip(),
                event_date=date.today().isoformat(),
                event_time=time_in.text().strip(),
                category=cat_in.text().strip(),
                description=desc_in.text().strip()
            )
            self._refresh_calendar_events()

    # ------------------ PAGE 5: MEMORY ------------------

    def _build_page_memory(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)

        top = QFrame()
        top.setObjectName("hudCard")
        tl = QHBoxLayout(top)
        tl.addWidget(QLabel("<h2>💾 Neural Memory Insights & Graph</h2>"))
        tl.addStretch()

        self.mem_search_in = QLineEdit()
        self.mem_search_in.setPlaceholderText("Search neural memories...")
        self.mem_search_in.returnPressed.connect(self._search_memory)
        tl.addWidget(self.mem_search_in)

        map_btn = QPushButton("🗺️ Visual Constellation Map")
        map_btn.setObjectName("secondaryBtn")
        map_btn.clicked.connect(self.open_memory_map)
        tl.addWidget(map_btn)

        add_mem_btn = QPushButton("➕ Add Fact")
        add_mem_btn.clicked.connect(self._dialog_add_memory)
        tl.addWidget(add_mem_btn)

        layout.addWidget(top)

        # Memory Table
        self.mem_table = QTableWidget()
        self.mem_table.setColumnCount(5)
        self.mem_table.setHorizontalHeaderLabels(["ID", "Category", "Key Topic", "Stored Content", "Confidence"])
        self.mem_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.mem_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.mem_table.itemDoubleClicked.connect(lambda _: self.open_memory_map())
        layout.addWidget(self.mem_table, 1)

        self._populate_memory_table()
        return panel

    def _populate_memory_table(self, memories=None):
        mems = memories if memories is not None else self.mem_mgr.get_memories()
        self.mem_table.setRowCount(len(mems))
        for row, m in enumerate(mems):
            self.mem_table.setItem(row, 0, QTableWidgetItem(str(m["id"])))
            self.mem_table.setItem(row, 1, QTableWidgetItem(m["category"]))
            self.mem_table.setItem(row, 2, QTableWidgetItem(m["key_topic"]))
            self.mem_table.setItem(row, 3, QTableWidgetItem(m["content"]))
            self.mem_table.setItem(row, 4, QTableWidgetItem(f"{int(m['confidence']*100)}%"))

    def _search_memory(self):
        q = self.mem_search_in.text().strip()
        if q:
            results = self.mem_mgr.search_memories(q)
            self._populate_memory_table(results)
        else:
            self._populate_memory_table()

    def _dialog_add_memory(self):
        d = QDialog(self)
        d.setWindowTitle("Add Memory Fact")
        d.setWindowIcon(self.app_icon)
        d.setStyleSheet(HUD_STYLE)
        f = QFormLayout(d)
        cat_in = QLineEdit("User Preference")
        topic_in = QLineEdit()
        content_in = QTextEdit()
        content_in.setMaximumHeight(80)

        f.addRow("Category", cat_in)
        f.addRow("Topic / Key", topic_in)
        f.addRow("Memory Content", content_in)

        b = QPushButton("Store in Neural Memory")
        b.clicked.connect(d.accept)
        f.addRow(b)

        if d.exec() == QDialog.DialogCode.Accepted and topic_in.text().strip():
            self.mem_mgr.add_memory(
                key_topic=topic_in.text().strip(),
                content=content_in.toPlainText().strip(),
                category=cat_in.text().strip()
            )
            self._populate_memory_table()
            self._refresh_command_center()
            self.say(f"Fact **{topic_in.text()}** saved to persistent neural memory.")

    # ------------------ PAGE 6: CONVERSATIONS (CHAT) ------------------

    def _build_page_conversations(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)

        # Chat View
        self.chat_view = QTextEdit()
        self.chat_view.setReadOnly(True)
        self.chat_view.setFont(QFont("Segoe UI", 11))
        layout.addWidget(self.chat_view, 1)

        # Quick chips
        chips_layout = QHBoxLayout()
        chips = [
            ("🎯 Find 5 marketing leads in Miami", "Find 5 leads for digital marketing in Miami"),
            ("✉️ Draft outreach pitch", "Draft outreach email offering web design"),
            ("💻 Check system diagnostics", "Check system performance and cpu"),
            ("🤖 Run Lead Gen Workflow", "Run lead outreach blitz workflow"),
            ("📸 Take screenshot", "Take a screenshot")
        ]
        for label, prompt in chips:
            btn = QPushButton(label)
            btn.setObjectName("secondaryBtn")
            btn.setStyleSheet("border-radius:14px; font-size:11px; padding:4px 10px;")
            btn.clicked.connect(lambda _, p=prompt: self.send_prompt(p))
            chips_layout.addWidget(btn)
        chips_layout.addStretch()
        layout.addLayout(chips_layout)

        # Input Dock
        dock = QHBoxLayout()
        dock.setSpacing(8)

        self.mic_btn = QPushButton("🎙️ Speak")
        self.mic_btn.setMinimumHeight(40)
        self.mic_btn.setStyleSheet("background: #0066FF; font-weight: bold; padding: 0 16px;")
        self.mic_btn.clicked.connect(self.start_mic_recording)
        dock.addWidget(self.mic_btn)

        self.chat_input = QLineEdit()
        self.chat_input.setMinimumHeight(40)
        self.chat_input.setPlaceholderText("Ask Judy anything, delegate to an agent, or say 'Hey Judy'...")
        self.chat_input.returnPressed.connect(self.send_chat)
        dock.addWidget(self.chat_input, 1)

        send_btn = QPushButton("Execute 🚀")
        send_btn.setMinimumHeight(40)
        send_btn.clicked.connect(self.send_chat)
        dock.addWidget(send_btn)

        layout.addLayout(dock)
        return panel

    # ------------------ PAGE 7: KNOWLEDGE BASE (FILE INDEXING) ------------------

    def _build_page_knowledge_base(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)

        # Progress / Resume Card
        prog_card = QFrame()
        prog_card.setObjectName("hudCard")
        p_layout = QVBoxLayout(prog_card)
        p_layout.setSpacing(8)

        top_row = QHBoxLayout()
        self.scan_status_label = QLabel("● Document Index Engine Ready")
        self.scan_status_label.setStyleSheet("font-weight: 700; color: #00E5FF; font-size: 13px;")
        top_row.addWidget(self.scan_status_label)
        top_row.addStretch()

        self.scan_pct_label = QLabel("0.0%")
        self.scan_pct_label.setStyleSheet("font-weight: 700; color: #00E676; font-size: 13px;")
        top_row.addWidget(self.scan_pct_label)
        p_layout.addLayout(top_row)

        self.scan_file_label = QLabel("📄 No active indexing job")
        self.scan_file_label.setStyleSheet("color: #7E9BB8; font-size: 11px;")
        p_layout.addWidget(self.scan_file_label)

        self.scan_progress_bar = QProgressBar()
        self.scan_progress_bar.setRange(0, 100)
        self.scan_progress_bar.setValue(0)
        p_layout.addWidget(self.scan_progress_bar)

        ctrl_row = QHBoxLayout()
        self.scan_btn = QPushButton("🔄 Scan PC Documents Now")
        self.scan_btn.clicked.connect(self.start_file_scan)
        ctrl_row.addWidget(self.scan_btn)

        self.pause_scan_btn = QPushButton("⏸️ Pause Scan")
        self.pause_scan_btn.setObjectName("secondaryBtn")
        self.pause_scan_btn.setEnabled(False)
        self.pause_scan_btn.clicked.connect(self.pause_file_scan)
        ctrl_row.addWidget(self.pause_scan_btn)

        self.clear_scan_btn = QPushButton("🧹 Clear Checkpoint")
        self.clear_scan_btn.setObjectName("secondaryBtn")
        self.clear_scan_btn.clicked.connect(self.clear_scan_checkpoint)
        ctrl_row.addWidget(self.clear_scan_btn)

        ctrl_row.addStretch()
        p_layout.addLayout(ctrl_row)
        layout.addWidget(prog_card)

        # Search Bar
        search_card = QFrame()
        search_card.setObjectName("hudCard")
        sc_l = QHBoxLayout(search_card)
        self.kb_search_in = QLineEdit()
        self.kb_search_in.setPlaceholderText("Search inside indexed files (PDF, DOCX, TXT, MD, CSV)...")
        self.kb_search_in.returnPressed.connect(self._search_kb)
        sc_l.addWidget(self.kb_search_in, 1)

        search_btn = QPushButton("Search Knowledge")
        search_btn.clicked.connect(self._search_kb)
        sc_l.addWidget(search_btn)
        layout.addWidget(search_card)

        # Results
        self.kb_results = QListWidget()
        self.kb_results.itemDoubleClicked.connect(self._open_kb_file)
        layout.addWidget(self.kb_results, 1)

        act_r = QHBoxLayout()
        open_btn = QPushButton("Open Selected Document")
        open_btn.clicked.connect(self._open_kb_file)
        act_r.addWidget(open_btn)
        act_r.addStretch()
        layout.addLayout(act_r)

        return panel

    def _search_kb(self):
        q = self.kb_search_in.text().strip()
        if not q:
            return
        results = self.index.search(q, limit=25)
        self.kb_results.clear()
        if not results:
            self.kb_results.addItem("No matching documents found.")
            return
        for r in results:
            it = QListWidgetItem(f"📄 {r['name']} — {r['path']}\n   Match: {r['snippet'] or '(filename match)'}")
            it.setData(Qt.ItemDataRole.UserRole, r["path"])
            self.kb_results.addItem(it)

    def _open_kb_file(self):
        it = self.kb_results.currentItem()
        if it:
            p = it.data(Qt.ItemDataRole.UserRole)
            if p:
                self.tools.open_file(p)

    def start_file_scan(self):
        if self.scan_worker and self.scan_worker.isRunning():
            return
        if not self.settings.search_roots:
            docs = str(Path.home() / "Documents")
            self.settings.search_roots.append(docs)
            self.settings.save()

        self.scan_btn.setEnabled(False)
        self.pause_scan_btn.setEnabled(True)
        self.scan_worker = ScanWorker(self.index, self.settings)
        self.scan_worker.progress.connect(self.on_scan_progress)
        self.scan_worker.finished_scan.connect(self.on_scan_finished)
        self.scan_worker.start()

    def pause_file_scan(self):
        if self.scan_worker and self.scan_worker.isRunning():
            self.scan_worker.cancel()

    def clear_scan_checkpoint(self):
        self.index.clear_checkpoint()
        self.scan_progress_bar.setValue(0)
        self.scan_pct_label.setText("0.0%")
        self.scan_status_label.setText("● Checkpoint cleared. Next scan starts from 0%.")

    def on_scan_progress(self, done: int, total: int, pct: float, current_file: str):
        self.scan_progress_bar.setValue(int(pct))
        self.scan_pct_label.setText(f"{pct:.1f}%")
        self.scan_status_label.setText(f"● Indexing: {done:,} / {total:,} files ({pct:.1f}%)")
        self.scan_file_label.setText(f"📄 {current_file}")

    def on_scan_finished(self, indexed: int, errors: int, was_interrupted: bool, err_msg: str):
        self.scan_btn.setEnabled(True)
        self.pause_scan_btn.setEnabled(False)
        if was_interrupted:
            done, total = self.index.get_checkpoint_stats()
            pct = round((done / total) * 100.0, 1) if total else 0
            self.scan_status_label.setText(f"⏸️ Indexing Paused at {pct:.1f}% ({done:,}/{total:,} files). Checkpoint saved.")
            self.scan_btn.setText(f"🔄 Resume Indexing ({pct:.0f}%)")
        else:
            self.scan_progress_bar.setValue(100)
            self.scan_pct_label.setText("100.0%")
            self.scan_status_label.setText(f"✅ Indexing complete: {indexed:,} files indexed ({errors} errors).")
            self.scan_btn.setText("🔄 Scan PC Documents Now")

    # ------------------ PAGE 8: TOOLS & SKILLS ------------------

    def _build_page_tools(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)

        card = QFrame()
        card.setObjectName("hudCard")
        cl = QVBoxLayout(card)
        cl.addWidget(QLabel("<h2>🛠️ 18 Active Tools & Skills</h2><p style='color:#7E9BB8'>Full desktop integration, B2B lead generation, and executive outreach.</p>"))

        grid = QGridLayout()
        grid.setSpacing(10)

        tool_cards = [
            ("🎯 Lead Finder Studio", "Search real client leads by niche & city", lambda: self.switch_page(6)),
            ("✉️ Cold Email Engine", "AI cold pitch generator & SMTP sender", lambda: self.switch_page(6)),
            ("🌐 Real-Time Web Search", "Live web search & summary extraction", lambda: self.tools.search_web("latest tech news")),
            ("💻 PowerShell Runner", "Execute system commands with approval", lambda: self.switch_page(0)),
            ("📸 Screen Capture", "Instant full-desktop screenshot", self.tools.take_screenshot),
            ("🚀 App Launcher", "Launch Chrome, VS Code, Spotify, etc.", lambda: self.tools.open_app("chrome")),
            ("📊 System Diagnostics", "Live CPU, RAM, disk, IP address query", self.tools.get_system_info),
            ("📁 File Intelligence", "Search inside indexed PDFs & DOCXs", lambda: self.switch_page(7)),
            ("🤖 Multi-Agent Dispatch", "Assign autonomous tasks to agents", lambda: self.switch_page(2))
        ]
        for idx, (title, desc, handler) in enumerate(tool_cards):
            c_box = QFrame()
            c_box.setStyleSheet("background-color:#0D1E32; border:1px solid #142B45; border-radius:8px;")
            c_l = QVBoxLayout(c_box)
            c_l.setContentsMargins(12, 10, 12, 10)
            c_l.addWidget(QLabel(f"<b>{title}</b>"))
            c_l.addWidget(QLabel(f"<span style='color:#7E9BB8; font-size:11px'>{desc}</span>"))
            b = QPushButton("Activate Tool")
            b.setObjectName("secondaryBtn")
            b.clicked.connect(handler)
            c_l.addWidget(b)
            grid.addWidget(c_box, idx // 3, idx % 3)

        cl.addLayout(grid)
        layout.addWidget(card)
        return panel

    # ------------------ PAGE 9: WORKFLOWS ------------------

    def _build_page_workflows(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)

        top = QFrame()
        top.setObjectName("hudCard")
        tl = QVBoxLayout(top)
        tl.addWidget(QLabel("<h2>🔄 Automated Workflows & Pipelines</h2><p style='color:#7E9BB8'>One-click multi-step autonomous pipelines executed by JUDY.</p>"))
        layout.addWidget(top)

        wf_grid = QHBoxLayout()
        wfs = self.wf_mgr.get_available_workflows()
        for wf in wfs:
            c = QFrame()
            c.setObjectName("hudCard")
            cl = QVBoxLayout(c)
            cl.setContentsMargins(14, 12, 14, 12)
            cl.addWidget(QLabel(f"<b>{wf['name']}</b>"))
            cl.addWidget(QLabel(f"<span style='color:#7E9BB8; font-size:11px'>{wf['description']}</span>"))

            steps_box = QLabel("<b>Pipeline Steps:</b><br>" + "<br>".join(f"• {s}" for s in wf["steps"]))
            steps_box.setStyleSheet("color:#E0F2FE; font-size:11px; margin:6px 0;")
            cl.addWidget(steps_box)

            b = QPushButton(f"Execute Pipeline ({wf['badge']})")
            b.clicked.connect(lambda _, w=wf["id"]: self._run_workflow_ui(w))
            cl.addWidget(b)
            wf_grid.addWidget(c)

        layout.addLayout(wf_grid)

        # Terminal output
        log_card = QFrame()
        log_card.setObjectName("hudCard")
        log_l = QVBoxLayout(log_card)
        log_l.addWidget(QLabel("<b>Workflow Execution Terminal Log:</b>"))
        self.wf_log = QTextEdit()
        self.wf_log.setReadOnly(True)
        self.wf_log.setFont(QFont("Consolas", 10))
        self.wf_log.setPlaceholderText("Pipeline execution steps will log here in real time...")
        log_l.addWidget(self.wf_log)

        layout.addWidget(log_card, 1)
        return panel

    def _run_workflow_ui(self, wf_id: str):
        self.wf_log.append(f"\n--- Launching {wf_id} at {datetime.now().strftime('%H:%M:%S')} ---")
        def work():
            self.wf_mgr.run_workflow(wf_id, lambda msg: QTimer.singleShot(0, lambda m=msg: self.wf_log.append(f"> {m}")))
        threading.Thread(target=work, daemon=True).start()

    # ------------------ BOTTOM DOCK BAR (FROM SCREENSHOT) ------------------

    def _build_bottom_dock(self) -> QWidget:
        dock = QFrame()
        dock.setObjectName("hudDock")
        dock.setFixedHeight(54)
        d_layout = QHBoxLayout(dock)
        d_layout.setContentsMargins(14, 6, 14, 6)
        d_layout.setSpacing(16)

        # Left: Location & Weather & Network
        d_layout.addWidget(QLabel("📍 Location: <b>Local PC</b>"))
        d_layout.addWidget(QLabel("☀️ Weather: <b>28°C Clear</b>"))
        d_layout.addWidget(QLabel("📶 Network: <b style='color:#00E676'>Excellent</b>"))

        d_layout.addStretch()

        # Center: TALK TO JUDY glowing pill button with audio waveform
        self.talk_pill_btn = QPushButton("  TALK TO JUDY  —  I am listening...  ")
        self.talk_pill_btn.setObjectName("talkPillBtn")
        self.talk_pill_btn.clicked.connect(self.start_mic_recording)
        d_layout.addWidget(self.talk_pill_btn)

        d_layout.addStretch()

        # Right: Visualizer dots + Executive Briefing Button
        dots = QLabel(" • • • • • • • ")
        dots.setObjectName("hudAccent")
        dots.setStyleSheet("font-weight:bold;")
        d_layout.addWidget(dots)

        briefing_btn = QPushButton("▶ Executive Briefing")
        briefing_btn.setObjectName("secondaryBtn")
        briefing_btn.clicked.connect(lambda: self._run_workflow_ui("morning_briefing"))
        d_layout.addWidget(briefing_btn)

        return dock

    # ------------------ COMMAND CENTER ACTIONS & REAL POPULATORS ------------------

    def open_memory_map(self):
        d = MemoryMapDialog(self.mem_mgr, self)
        d.exec()
        self._populate_memory_table()
        self._refresh_command_center()

    def open_manage_providers(self):
        d = ManageProvidersDialog(self.settings, self)
        if d.exec() == QDialog.DialogCode.Accepted:
            self._refresh_command_center()

    def _refresh_command_center(self, force: bool = False):
        if not force and not self.isVisible():
            return
        try:
            self._update_ai_overview_card()
            self._update_intelligence_feed()
            self._update_active_agents_grid()
            self._update_hud_timeline()
            stats = self.mem_mgr.get_stats()
            self.lbl_mem_count.setText(f"Memories: <b style='color:#00E5FF'>{stats['total']} Stored</b>")
            self.lbl_session_turns.setText(f"Session Turns: <b style='color:#E0F2FE'>{self.session_turns}</b>")
            self.lbl_tool_calls.setText(f"Tool Calls: <b style='color:#00E676'>{self.tool_calls_count}</b>")
            self._poll_llm_telemetry_async()
        except Exception:
            pass

    def _update_ai_overview_card(self):
        self.lbl_ov_ai_core.setText(self.settings.provider_mode.capitalize())
        stats = self.mem_mgr.get_stats()
        self.lbl_ov_memory.setText(f"{stats['total']} Stored")
        v_status = "Online" if self.settings.voice_output_enabled else "Muted"
        self.lbl_ov_voice.setText(f"{v_status}")
        agents = self.agents_mgr.get_all_agents()
        self.lbl_ov_agents.setText(f"{len(agents)} Standby")
        self.lbl_ov_system.setText("Optimal")

    def _update_intelligence_feed(self):
        mem_stats = self.mem_mgr.get_stats()
        doc_count = self.index.get_indexed_count()
        agents = self.agents_mgr.get_all_agents()

        feed_items = [
            ("🧠", "Neural Memory Constellation", f"{mem_stats['total']} facts indexed across {len(mem_stats['categories'])} neural categories", "#00E5FF", "Retained"),
            ("📁", "Local Document Intelligence", f"{doc_count:,} PC files indexed in searchable vector base", "#38BDF8", "Indexed"),
            ("🤖", "Multi-Agent Fleet Coordination", f"{len(agents)} autonomous agents active and ready for dispatch", "#A855F7", "Standby"),
            ("⚡", "LLM Inference Engine", "Local Ollama + Cloud Engine", "#00E676", "Live"),
            ("🎙️", "Neural Voice Synthesizer", f"Natural UK human cadence active ({self.settings.neural_voice})", "#00E5FF", "Online")
        ]

        for idx, (icon, title, desc, col, badge) in enumerate(feed_items):
            if idx < len(self.feed_slots):
                ic_lbl, t_lbl, d_lbl, b_lbl = self.feed_slots[idx]
                ic_lbl.setText(icon)
                t_lbl.setText(f"<b style='color:{col}; font-size:11px;'>{title}</b>")
                d_lbl.setText(f"<span style='color:#7E9BB8; font-size:10px;'>{desc}</span>")
                b_lbl.setText(badge)

    def _update_active_agents_grid(self):
        agents = self.agents_mgr.get_all_agents()[:4]
        for idx, ag in enumerate(agents):
            if idx < len(self.hud_agent_slots):
                av_lbl, name_lbl, st_pill, role_lbl, btn = self.hud_agent_slots[idx]
                av_lbl.setText(ag["avatar"])
                name_lbl.setText(f"<b>{ag['name']}</b>")
                is_active = (ag["status"] == "Active")
                st_pill.setText("● Active" if is_active else "● Standby")
                st_pill.setStyleSheet(f"color:{'#00E676' if is_active else '#38BDF8'}; font-size:9px; font-weight:700;")
                role_lbl.setText(f"<span style='color:#7E9BB8; font-size:10px;'>{ag['role']}</span>")

    def _update_hud_timeline(self):
        events = self.cal_mgr.get_today_timeline()[:3]
        for idx, ev in enumerate(events):
            if idx < len(self.hud_timeline_slots):
                t_badge, title_lbl, cat_lbl, st_icon = self.hud_timeline_slots[idx]
                t_badge.setText(ev["event_time"])
                title_lbl.setText(f"<b style='color:#E0F2FE; font-size:11px;'>{ev['title']}</b>")
                cat_lbl.setText(f"<span style='color:#5C7C99; font-size:9px;'>{ev['category']}</span>")
                st_icon.setText("✅" if ev["is_completed"] else "⏳")

    def _poll_llm_telemetry_async(self):
        if self.telemetry_worker and self.telemetry_worker.isRunning():
            return
        self.telemetry_worker = AsyncTelemetryWorker(
            self.settings.ollama_base_url,
            self.settings.cloud_model,
            self.settings.ollama_model,
            self
        )
        self.telemetry_worker.telemetry_ready.connect(self._on_telemetry_ready)
        self.telemetry_worker.start()

    def _on_telemetry_ready(self, data: dict):
        providers = data.get("providers", [])
        connected_count = sum(1 for p in providers if p[1])
        self.lbl_llm_conn_pill.setText(f"{connected_count} Connected")
        self.lbl_llm_conn_pill.setStyleSheet(
            f"color:{'#00E676' if connected_count > 0 else '#FF5252'}; font-size:10px; font-weight:700;"
        )
        self.lbl_ov_llms.setText(f"{connected_count} Connected")

        for idx, (name, is_connected, model_desc, dot_col) in enumerate(providers):
            if idx < len(self.llm_chip_slots):
                dot, n_lbl, m_lbl, st_badge = self.llm_chip_slots[idx]
                dot.setText("●" if is_connected else "○")
                dot.setStyleSheet(f"color:{dot_col}; font-size:10px; font-weight:bold;")
                n_lbl.setText(f"<b>{name}</b>")
                m_lbl.setText(f"<span style='color:#7E9BB8; font-size:9px;'>{model_desc}</span>")
                st_badge.setText("Active" if is_connected else "Unlinked")
                st_badge.setStyleSheet(f"color:{'#00E676' if is_connected else '#5C7C99'}; font-size:8px; font-weight:700;")

    # ------------------ SYSTEM MONITOR & VITALS ------------------

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_command_center(force=True)
        self._poll_system_vitals(force=True)

    def _poll_system_vitals(self, force: bool = False):
        if not force and not self.isVisible():
            return
        try:
            if psutil is not None:
                cpu_val = int(psutil.cpu_percent(interval=None))
                ram_val = int(psutil.virtual_memory().percent)
                try:
                    disk_val = int(psutil.disk_usage("C:\\").percent)
                except Exception:
                    disk_val = 45
                self.gauge_cpu.set_value(cpu_val)
                self.gauge_ram.set_value(ram_val)
                self.gauge_disk.set_value(disk_val)
                if cpu_val > 85:
                    self.lbl_ov_system.setText("High Load")
                    self.lbl_ov_system.setStyleSheet("color:#FF5252; font-weight:700; font-size:11px;")
                else:
                    self.lbl_ov_system.setText("Optimal")
                    self.lbl_ov_system.setStyleSheet("color:#00E676; font-weight:700; font-size:11px;")
        except Exception:
            pass

    # ------------------ VOICE & EVENT HANDLERS ------------------

    def say(self, text: str):
        now = datetime.now().strftime("%H:%M")
        theme = get_theme(self.settings.theme)
        html = f"""
        <div style='margin-bottom:12px;'>
            <span style='color:{theme.accent_primary}; font-weight:700;'>{theme.icon} JUDY AI CORE</span>
            <span style='color:{theme.text_dim}; font-size:10px;'> {now}</span><br>
            <div style='background-color:{theme.bg_subcard}; border:1px solid {theme.border}; border-radius:8px; padding:10px 14px; margin-top:4px;'>
                {text}
            </div>
        </div>
        """
        self.chat_view.append(html)
        self.chat_view.moveCursor(QTextCursor.MoveOperation.End)
        if self.settings.voice_output_enabled:
            self.voice_svc.speak(text)
        else:
            if hasattr(self, "hologram_widget"):
                plain = text.replace("<br>", " ").replace("<b>", "").replace("</b>", "")
                dur = min(7.0, max(2.0, len(plain.split()) * 0.28))
                self.hologram_widget.simulate_speech(dur)

    def say_user(self, text: str):
        now = datetime.now().strftime("%H:%M")
        theme = get_theme(self.settings.theme)
        html = f"""
        <div style='margin-bottom:12px; text-align:right;'>
            <span style='color:{theme.accent_secondary}; font-weight:700;'>COMMANDER</span>
            <span style='color:{theme.text_dim}; font-size:10px;'> {now}</span><br>
            <div style='display:inline-block; background-color:{theme.bg_input}; border:1px solid {theme.border}; border-radius:8px; padding:10px 14px; margin-top:4px; text-align:left;'>
                {text.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')}
            </div>
        </div>
        """
        self.chat_view.append(html)
        self.chat_view.moveCursor(QTextCursor.MoveOperation.End)

    def send_chat(self):
        text = self.chat_input.text().strip()
        if not text:
            return
        self.chat_input.clear()
        self.send_prompt(text)

    def send_prompt(self, text: str):
        self.say_user(text)
        self.chat_input.setEnabled(False)
        self.top_status.setText("SYSTEM STATUS  ● PROCESSING")
        self.session_turns += 1
        self.lbl_session_turns.setText(f"Session Turns: <b style='color:#E0F2FE'>{self.session_turns}</b>")
        if hasattr(self, "voice_sub_label"):
            self.voice_sub_label.setText("Thinking…")

        worker = AssistantWorker(self.assistant, text, self)
        worker.response_ready.connect(self._on_assistant_response)
        worker.failed.connect(self._on_assistant_error)
        self._active_workers.append(worker)
        worker.finished.connect(lambda: self._active_workers.remove(worker) if worker in self._active_workers else None)
        worker.start()

    def _on_assistant_response(self, prompt: str, answer: str):
        lower_ans = answer.lower()
        if any(k in lower_ans for k in ("lead", "email", "powershell", "system info", "cpu", "screenshot", "file", "document", "indexed", "weather", "launch")):
            self.tool_calls_count += 1
            self.lbl_tool_calls.setText(f"Tool Calls: <b style='color:#00E676'>{self.tool_calls_count}</b>")

        formatted = answer.replace("\n", "<br>")
        self.say(formatted)
        self.chat_input.setEnabled(True)
        self.chat_input.setFocus()
        self.top_status.setText("SYSTEM STATUS  ● OPTIMAL")
        self._refresh_command_center()

    def _on_assistant_error(self, prompt: str, error_msg: str):
        self.say(f"Subsystem error: {error_msg}")
        self.chat_input.setEnabled(True)
        self.chat_input.setFocus()
        self.top_status.setText("SYSTEM STATUS  ● OPTIMAL")

    def on_wake_triggered(self, query: str):
        self.showNormal()
        self.activateWindow()
        self.switch_page(6)
        self.send_prompt(query or "Hello Commander")

    def on_voice_status(self, status: str):
        if status == "speaking":
            self.wave_label.setText(" ılılılllıılıl ")
            self.voice_sub_label.setText("Speaking…")
            if hasattr(self, "hologram_widget"):
                self.hologram_widget.set_speaking(True)
        elif status == "listening":
            self.wave_label.setText(" ılılı·lllı·lıl ")
            self.voice_sub_label.setText("Listening…")
            if hasattr(self, "hologram_widget"):
                self.hologram_widget.set_speaking(False)
        elif status == "idle":
            self.wave_label.setText(" ··· ··· ··· ")
            self.voice_sub_label.setText("Ready")
            if hasattr(self, "hologram_widget"):
                self.hologram_widget.set_speaking(False)
        elif status == "processing":
            self.voice_sub_label.setText("Thinking…")
            if hasattr(self, "hologram_widget"):
                self.hologram_widget.set_speaking(False)

    def on_voice_heard(self, text: str):
        if text:
            self.voice_sub_label.setText("Recognized!")
            self.switch_page(6)
            self.send_prompt(text)
        else:
            self.voice_sub_label.setText("No speech heard")
            QTimer.singleShot(2500, lambda: self.voice_sub_label.setText("Ready"))

    def start_mic_recording(self):
        self.voice_sub_label.setText("Listening (4s)…")
        self.sidebar_mic_btn.setEnabled(False)
        QTimer.singleShot(4500, lambda: self.sidebar_mic_btn.setEnabled(True))
        self.voice_svc.start_recording_async(seconds=4.0)

    def open_settings(self):
        theme = get_theme(self.settings.theme)
        d = QDialog(self)
        d.setWindowTitle("JUDY Command Center Settings")
        d.setWindowIcon(self.app_icon)
        d.setStyleSheet(get_theme_stylesheet(theme))
        f = QFormLayout(d)

        mode_c = QComboBox()
        mode_c.addItem("Hybrid", "hybrid")
        mode_c.addItem("Local", "local")
        mode_c.addItem("Cloud", "cloud")
        cur_m_idx = mode_c.findData(self.settings.provider_mode)
        if cur_m_idx >= 0:
            mode_c.setCurrentIndex(cur_m_idx)
        f.addRow("AI Mode", mode_c)

        # Theme Selector Dropdown
        theme_combo_dialog = QComboBox()
        for tid, t in THEMES.items():
            theme_combo_dialog.addItem(f"{t.icon}  {t.name} — {t.description}", tid)
        cur_t_idx = theme_combo_dialog.findData(self.settings.theme or DEFAULT_THEME)
        if cur_t_idx >= 0:
            theme_combo_dialog.setCurrentIndex(cur_t_idx)
        f.addRow("Visual Theme", theme_combo_dialog)

        wake_chk = QCheckBox("Enable Wake Word ('Hey Judy')")
        wake_chk.setChecked(self.settings.wake_word_enabled)
        f.addRow("Voice Wake Word", wake_chk)

        tts_chk = QCheckBox("Voice Output (Neural Speech)")
        tts_chk.setChecked(self.settings.voice_output_enabled)
        f.addRow("Voice Audio", tts_chk)

        v_box = QHBoxLayout()
        v_combo = QComboBox()
        for label, code in NATURAL_VOICES.items():
            v_combo.addItem(label, code)
        cur_v_idx = v_combo.findData(self.settings.neural_voice)
        if cur_v_idx >= 0:
            v_combo.setCurrentIndex(cur_v_idx)
        v_box.addWidget(v_combo, 1)

        test_voice_btn = QPushButton("🔊 Preview")
        test_voice_btn.setToolTip("Hear an instant live sample of this voice")
        test_voice_btn.clicked.connect(lambda: self.voice_svc.preview_voice(v_combo.currentData()))
        v_box.addWidget(test_voice_btn)
        f.addRow("Neural Voice", v_box)

        b = QPushButton("Save Settings")
        b.clicked.connect(d.accept)
        f.addRow(b)

        if d.exec() == QDialog.DialogCode.Accepted:
            selected_theme = theme_combo_dialog.currentData()
            if selected_theme and selected_theme != self.settings.theme:
                self.apply_theme(selected_theme)
            self.settings.provider_mode = mode_c.currentData()
            self.settings.wake_word_enabled = wake_chk.isChecked()
            self.settings.voice_output_enabled = tts_chk.isChecked()
            self.settings.neural_voice = v_combo.currentData()
            self.settings.save()
            self.say("Settings updated and applied.")

    def _init_tray(self):
        self.tray = QSystemTrayIcon(self.app_icon, self)
        self.tray.setToolTip("JUDY — Autonomous AI Command Center")
        menu = QMenu()
        show_action = QAction("Open Command Center", self)
        show_action.triggered.connect(self.showNormal)
        menu.addAction(show_action)

        quit_action = QAction("Exit JUDY", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: self.showNormal() if reason == QSystemTrayIcon.ActivationReason.DoubleClick else None)
        self.tray.show()

    def closeEvent(self, event):
        if self.scan_worker and self.scan_worker.isRunning():
            self.scan_worker.cancel()
            self.scan_worker.wait(1000)

        if self.settings.minimize_to_tray and self.tray.isVisible():
            self.hide()
            self.tray.showMessage("JUDY Command Center", "Minimized to tray. Double click or say 'Hey Judy' to reopen.", QSystemTrayIcon.MessageIcon.Information, 2500)
            event.ignore()
        else:
            self.voice_svc.stop_speaking()
            self.voice_svc.stop_wake_listener()
            self.index.close()
            event.accept()

class SetupWizard(QDialog):
    """Initial onboarding dialog for configuring Judy Command Center."""
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("JUDY — Subsystem Initialization")
        self.resize(520, 480)
        self.setStyleSheet(HUD_STYLE)
        self.setWindowIcon(create_judy_icon())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        title = QLabel("<h2>💠 AI Command Center Initialization</h2>")
        title.setStyleSheet("color: #00E5FF; font-weight: 800;")
        layout.addWidget(title)

        desc = QLabel("<p style='color:#7E9BB8;'>Welcome Commander. Configure your core subsystems to initialize the autonomous Stark HUD Command Center.</p>")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        form = QFormLayout()
        form.setSpacing(12)

        self.name_in = QLineEdit(self.settings.assistant_name or "Judy")
        form.addRow("Assistant Name:", self.name_in)

        self.wake_chk = QCheckBox("Enable Wake Word ('Hey Judy')")
        self.wake_chk.setChecked(self.settings.wake_word_enabled)
        form.addRow("Voice Wake Word:", self.wake_chk)

        self.voice_combo = QComboBox()
        for label, code in NATURAL_VOICES.items():
            self.voice_combo.addItem(label, code)
        form.addRow("Neural Voice:", self.voice_combo)

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Hybrid (Local Ollama + Cloud)", "hybrid")
        self.mode_combo.addItem("Local Ollama Only", "local")
        self.mode_combo.addItem("Cloud Only", "cloud")
        form.addRow("AI Engine Mode:", self.mode_combo)

        docs_path = str(Path.home() / "Documents")
        self.dir_in = QLineEdit(self.settings.search_roots[0] if self.settings.search_roots else docs_path)
        form.addRow("PC Search Root:", self.dir_in)

        layout.addLayout(form)
        layout.addStretch()

        init_btn = QPushButton("🚀 Initialize Command Center")
        init_btn.setMinimumHeight(44)
        init_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0052CC, stop:1 #00E5FF);
                color: #FFFFFF;
                font-weight: 800;
                font-size: 14px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background: #00E5FF;
                color: #050B14;
            }
        """)
        init_btn.clicked.connect(self.accept)
        layout.addWidget(init_btn)

    def apply(self):
        self.settings.assistant_name = self.name_in.text().strip() or "Judy"
        self.settings.wake_word_enabled = self.wake_chk.isChecked()
        self.settings.neural_voice = self.voice_combo.currentData() or "en-US-AvaNeural"
        self.settings.provider_mode = self.mode_combo.currentData() or "hybrid"
        d = self.dir_in.text().strip()
        if d:
            self.settings.search_roots = [d]
        self.settings.setup_complete = True
        self.settings.save()

STYLE = HUD_STYLE

def run_setup(settings: Settings) -> bool:
    return True

