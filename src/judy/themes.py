"""
JUDY Multi-Theme Architecture & Design System.
Provides 6 meticulously crafted, high-tech HUD themes with cohesive color palettes
for PySide6 UI, custom vector gauges, memory graphs, and the Three.js 3D WebGL core.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict

@dataclass
class Theme:
    id: str
    name: str
    description: str
    icon: str
    
    # Core Background Colors
    bg_main: str          # Global canvas background
    bg_card: str          # Primary HUD cards
    bg_sidebar: str       # Left navigation sidebar
    bg_header: str        # Top command header
    bg_subcard: str       # Internal feed cards, chips, dialog panels
    bg_input: str         # Input fields, text areas, dropdowns
    
    # Borders & Outlines
    border: str           # Subtle card border
    border_hover: str     # Card hover border
    border_active: str    # Focus / active element border
    
    # Text Typography
    text_primary: str     # Bright primary text
    text_muted: str       # Subtle secondary / metadata text
    text_dim: str         # Timestamp / quiet hints
    
    # Accents & Glow
    accent_primary: str   # Main glowing brand color
    accent_secondary: str # Supporting complementary accent
    status_optimal: str   # Green/active status indicator
    
    # Buttons & Gradients
    btn_grad_start: str
    btn_grad_end: str
    btn_hover_start: str
    btn_hover_end: str
    
    # WebGL 3D Scene Parameters
    webgl_bg: str
    webgl_key_light: str
    webgl_rim_light: str
    webgl_speech_light: str
    webgl_ring1: str
    webgl_ring2: str
    webgl_grid: str


THEMES: Dict[str, Theme] = {
    "cyberpunk": Theme(
        id="cyberpunk",
        name="Cyberpunk Cyan",
        description="Electric Cyan, Stark Blue & Deep Space Void",
        icon="💠",
        bg_main="#050B14",
        bg_card="#0A1322",
        bg_sidebar="#070F1B",
        bg_header="#070F1B",
        bg_subcard="#0B192C",
        bg_input="#08111D",
        border="#142B45",
        border_hover="#00E5FF",
        border_active="#00E5FF",
        text_primary="#E0F2FE",
        text_muted="#7E9BB8",
        text_dim="#5C7C99",
        accent_primary="#00E5FF",
        accent_secondary="#0066FF",
        status_optimal="#00E676",
        btn_grad_start="#0052CC",
        btn_grad_end="#0088FF",
        btn_hover_start="#0066FF",
        btn_hover_end="#00A3FF",
        webgl_bg="#050B14",
        webgl_key_light="#00E5FF",
        webgl_rim_light="#A855F7",
        webgl_speech_light="#00E5FF",
        webgl_ring1="#00E5FF",
        webgl_ring2="#A855F7",
        webgl_grid="#00E5FF"
    ),
    "obsidian_gold": Theme(
        id="obsidian_gold",
        name="Obsidian Gold",
        description="Sleek Carbon, Champagne Brass & Amber Glow",
        icon="⚜️",
        bg_main="#09090B",
        bg_card="#131317",
        bg_sidebar="#0D0D10",
        bg_header="#0D0D10",
        bg_subcard="#1A1A20",
        bg_input="#16161C",
        border="#2E281C",
        border_hover="#F59E0B",
        border_active="#F59E0B",
        text_primary="#FEF3C7",
        text_muted="#A19E95",
        text_dim="#78716C",
        accent_primary="#F59E0B",
        accent_secondary="#D97706",
        status_optimal="#10B981",
        btn_grad_start="#B45309",
        btn_grad_end="#F59E0B",
        btn_hover_start="#D97706",
        btn_hover_end="#FBBF24",
        webgl_bg="#09090B",
        webgl_key_light="#F59E0B",
        webgl_rim_light="#FDE68A",
        webgl_speech_light="#F59E0B",
        webgl_ring1="#F59E0B",
        webgl_ring2="#D97706",
        webgl_grid="#B45309"
    ),
    "synthwave": Theme(
        id="synthwave",
        name="Synthwave Sunset",
        description="Neon Magenta, Cyber Violet & Dark Indigo",
        icon="🌇",
        bg_main="#0D0714",
        bg_card="#180D26",
        bg_sidebar="#130A20",
        bg_header="#130A20",
        bg_subcard="#221237",
        bg_input="#1E0F31",
        border="#3D1B58",
        border_hover="#EC4899",
        border_active="#EC4899",
        text_primary="#FDF2F8",
        text_muted="#C4B5FD",
        text_dim="#8B5CF6",
        accent_primary="#EC4899",
        accent_secondary="#8B5CF6",
        status_optimal="#06B6D4",
        btn_grad_start="#9333EA",
        btn_grad_end="#EC4899",
        btn_hover_start="#A855F7",
        btn_hover_end="#F43F5E",
        webgl_bg="#0D0714",
        webgl_key_light="#EC4899",
        webgl_rim_light="#8B5CF6",
        webgl_speech_light="#EC4899",
        webgl_ring1="#EC4899",
        webgl_ring2="#8B5CF6",
        webgl_grid="#EC4899"
    ),
    "matrix": Theme(
        id="matrix",
        name="Matrix Emerald",
        description="Terminal Phosphor, Toxic Mint & Deep Carbon",
        icon="📟",
        bg_main="#040D08",
        bg_card="#0A1C12",
        bg_sidebar="#07150E",
        bg_header="#07150E",
        bg_subcard="#0F2A1B",
        bg_input="#0D2417",
        border="#143D24",
        border_hover="#10B981",
        border_active="#10B981",
        text_primary="#ECFDF5",
        text_muted="#6EE7B7",
        text_dim="#059669",
        accent_primary="#10B981",
        accent_secondary="#059669",
        status_optimal="#34D399",
        btn_grad_start="#047857",
        btn_grad_end="#10B981",
        btn_hover_start="#059669",
        btn_hover_end="#34D399",
        webgl_bg="#040D08",
        webgl_key_light="#10B981",
        webgl_rim_light="#34D399",
        webgl_speech_light="#10B981",
        webgl_ring1="#10B981",
        webgl_ring2="#059669",
        webgl_grid="#10B981"
    ),
    "arctic_frost": Theme(
        id="arctic_frost",
        name="Arctic Frost",
        description="Glacial Blue, Titanium Slate & Crisp Platinum",
        icon="❄️",
        bg_main="#070D18",
        bg_card="#0F1B2E",
        bg_sidebar="#0B1525",
        bg_header="#0B1525",
        bg_subcard="#152640",
        bg_input="#122036",
        border="#1E375A",
        border_hover="#38BDF8",
        border_active="#38BDF8",
        text_primary="#F0F9FF",
        text_muted="#94A3B8",
        text_dim="#64748B",
        accent_primary="#38BDF8",
        accent_secondary="#6366F1",
        status_optimal="#00E676",
        btn_grad_start="#2563EB",
        btn_grad_end="#38BDF8",
        btn_hover_start="#3B82F6",
        btn_hover_end="#7DD3FC",
        webgl_bg="#070D18",
        webgl_key_light="#38BDF8",
        webgl_rim_light="#818CF8",
        webgl_speech_light="#38BDF8",
        webgl_ring1="#38BDF8",
        webgl_ring2="#6366F1",
        webgl_grid="#38BDF8"
    ),
    "blood_moon": Theme(
        id="blood_moon",
        name="Blood Moon HUD",
        description="Tactical Crimson, Alert Orange & Void Shadow",
        icon="🔴",
        bg_main="#110505",
        bg_card="#1C0A0A",
        bg_sidebar="#150808",
        bg_header="#150808",
        bg_subcard="#281111",
        bg_input="#230E0E",
        border="#401616",
        border_hover="#EF4444",
        border_active="#EF4444",
        text_primary="#FEF2F2",
        text_muted="#FCA5A5",
        text_dim="#B91C1C",
        accent_primary="#EF4444",
        accent_secondary="#F97316",
        status_optimal="#10B981",
        btn_grad_start="#991B1B",
        btn_grad_end="#EF4444",
        btn_hover_start="#B91C1C",
        btn_hover_end="#F87171",
        webgl_bg="#110505",
        webgl_key_light="#EF4444",
        webgl_rim_light="#FB923C",
        webgl_speech_light="#EF4444",
        webgl_ring1="#EF4444",
        webgl_ring2="#F97316",
        webgl_grid="#EF4444"
    ),
}

DEFAULT_THEME = "cyberpunk"

def get_theme(theme_id: str | None) -> Theme:
    if not theme_id or theme_id not in THEMES:
        return THEMES[DEFAULT_THEME]
    return THEMES[theme_id]

def get_theme_stylesheet(t: Theme) -> str:
    """Generates the full futuristic HUD QSS stylesheet for the provided theme."""
    return f"""
/* Global Canvas */
QWidget {{
    background-color: {t.bg_main};
    color: {t.text_primary};
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    font-size: 13px;
    outline: none;
}}

/* Shell Structure Frames */
QFrame#hudSidebar {{
    background-color: {t.bg_sidebar};
    border-right: 1px solid {t.border};
}}

QFrame#hudHeader {{
    background-color: {t.bg_header};
    border-bottom: 1px solid {t.border};
}}

QFrame#hudDock {{
    background-color: {t.bg_sidebar};
    border: 1px solid {t.border};
    border-radius: 8px;
}}

/* Scrollbars */
QScrollBar:vertical {{
    border: none;
    background: {t.bg_main};
    width: 6px;
    margin: 0px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {t.border};
    min-height: 20px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical:hover {{
    background: {t.accent_primary};
}}

/* HUD Cards & Panels */
QFrame#hudCard {{
    background-color: {t.bg_card};
    border: 1px solid {t.border};
    border-radius: 10px;
}}
QFrame#hudCard:hover {{
    border-color: {t.border_hover};
}}

QFrame#hudSubCard {{
    background-color: {t.bg_subcard};
    border: 1px solid {t.border};
    border-radius: 8px;
}}

/* Sidebar Navigation Items */
QPushButton#navBtn {{
    background: transparent;
    color: {t.text_muted};
    border: none;
    border-left: 3px solid transparent;
    padding: 10px 14px;
    text-align: left;
    font-weight: 600;
    font-size: 13px;
    border-radius: 0px;
}}
QPushButton#navBtn:hover {{
    background-color: {t.bg_subcard};
    color: {t.text_primary};
}}
QPushButton#navBtnActive {{
    background-color: {t.bg_card};
    color: {t.accent_primary};
    border: none;
    border-left: 3px solid {t.accent_primary};
    padding: 10px 14px;
    text-align: left;
    font-weight: 700;
    font-size: 13px;
}}

/* Badges & Pills */
QLabel#hudBadge {{
    background-color: {t.bg_subcard};
    color: {t.accent_primary};
    border: 1px solid {t.border};
    border-radius: 8px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 700;
}}
QLabel#hudAccent {{
    color: {t.accent_primary};
}}
QLabel#hudMuted {{
    color: {t.text_muted};
}}
QLabel#hudDim {{
    color: {t.text_dim};
}}
QLabel#statusOptimal {{
    background-color: {t.bg_subcard};
    color: {t.status_optimal};
    border: 1px solid {t.border};
    border-radius: 10px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: 700;
}}

/* Link Buttons */
QPushButton#linkBtn {{
    background: transparent;
    border: none;
    color: {t.accent_primary};
    font-size: 11px;
    font-weight: 700;
    padding: 0;
}}
QPushButton#linkBtn:hover {{
    color: {t.accent_secondary};
    text-decoration: underline;
}}

/* Brand Titles */
QLabel#brandTitle {{
    color: {t.accent_primary};
    font-weight: 800;
    font-size: 16px;
    letter-spacing: 1px;
}}
QLabel#brandSubtitle {{
    color: {t.text_dim};
    font-weight: 700;
    font-size: 10px;
    letter-spacing: 0.5px;
}}

/* Input Fields */
QLineEdit, QTextEdit, QComboBox, QSpinBox {{
    background-color: {t.bg_input};
    border: 1px solid {t.border};
    border-radius: 6px;
    padding: 7px 10px;
    color: {t.text_primary};
    selection-background-color: {t.accent_secondary};
}}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border: 1px solid {t.accent_primary};
    background-color: {t.bg_card};
}}
QComboBox QAbstractItemView {{
    background-color: {t.bg_card};
    border: 1px solid {t.border};
    selection-background-color: {t.bg_subcard};
    selection-color: {t.accent_primary};
    color: {t.text_primary};
}}

/* Action Buttons */
QPushButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {t.btn_grad_start}, stop:1 {t.btn_grad_end});
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 8px 14px;
    font-weight: 600;
}}
QPushButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {t.btn_hover_start}, stop:1 {t.btn_hover_end});
}}
QPushButton#secondaryBtn {{
    background: {t.bg_subcard};
    color: {t.text_muted};
    border: 1px solid {t.border};
}}
QPushButton#secondaryBtn:hover {{
    background: {t.bg_card};
    color: {t.text_primary};
    border-color: {t.accent_primary};
}}
QPushButton#dangerBtn {{
    background: #991B1B;
    color: #FFFFFF;
}}

/* Center Talk Pill Button */
QPushButton#talkPillBtn {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {t.btn_grad_start}, stop:0.5 {t.accent_primary}, stop:1 {t.btn_grad_start});
    color: {t.bg_main};
    border: 2px solid {t.accent_primary};
    border-radius: 18px;
    padding: 8px 24px;
    font-weight: 800;
    font-size: 13px;
    letter-spacing: 1px;
}}
QPushButton#talkPillBtn:hover {{
    background: {t.accent_primary};
    color: {t.bg_main};
}}

/* Sidebar Mic Button */
QPushButton#sidebarMicBtn {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {t.btn_grad_start}, stop:1 {t.bg_main});
    border: 2px solid {t.accent_primary};
    border-radius: 18px;
    padding: 8px;
    font-weight: 700;
    color: #FFFFFF;
}}
QPushButton#sidebarMicBtn:hover {{
    background: {t.accent_primary};
    color: {t.bg_main};
}}

/* Tables */
QTableWidget {{
    background-color: {t.bg_input};
    border: 1px solid {t.border};
    border-radius: 6px;
    gridline-color: {t.border};
    color: {t.text_primary};
    selection-background-color: {t.bg_subcard};
    selection-color: {t.accent_primary};
}}
QHeaderView::section {{
    background-color: {t.bg_sidebar};
    color: {t.text_muted};
    padding: 7px;
    border: 1px solid {t.border};
    font-weight: 700;
}}

/* Progress Bar */
QProgressBar {{
    background-color: {t.bg_input};
    border: 1px solid {t.border};
    border-radius: 6px;
    height: 18px;
    text-align: center;
    color: #FFFFFF;
    font-weight: 700;
    font-size: 11px;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {t.btn_grad_start}, stop:0.5 {t.accent_primary}, stop:1 {t.status_optimal});
    border-radius: 5px;
}}

/* Calendar */
QCalendarWidget {{
    background-color: {t.bg_main};
    color: {t.text_primary};
}}
QCalendarWidget QWidget#qt_calendar_navigationbar {{
    background-color: {t.bg_sidebar};
}}
"""
