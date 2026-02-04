"""
KeyVisualizer - On-screen key display for tutorials and recordings
A lightweight overlay that shows pressed keys at the bottom of the screen.
"""

__version__ = "1.0.0"
__app_name__ = "KeyVisualizer"

import sys
import os
import json
from typing import Optional, List, Deque
from collections import deque
from datetime import datetime

# Hide console window on Windows when running as a script
if sys.platform == 'win32':
    import ctypes
    hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    if hwnd:
        ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE = 0

from PyQt6.QtWidgets import (
    QApplication, QWidget, QSystemTrayIcon, QMenu, QDialog, QVBoxLayout,
    QHBoxLayout, QLabel, QComboBox, QPushButton, QSpinBox, QGroupBox,
    QMessageBox, QColorDialog, QFontComboBox, QCheckBox, QSlider,
    QFrame, QGridLayout, QTabWidget, QLineEdit
)
from PyQt6.QtCore import (
    Qt, QTimer, QSettings, QPoint, QPropertyAnimation, QEasingCurve,
    QRect, QRectF, pyqtSignal, QObject
)
from PyQt6.QtGui import (
    QIcon, QPixmap, QImage, QPainter, QFont, QColor, QAction, QScreen,
    QFontDatabase, QPainterPath, QBrush, QPen, QRadialGradient
)

from pynput import keyboard
from pynput.mouse import Listener as MouseListener, Button


# Key name mappings for display
KEY_DISPLAY_NAMES = {
    'Key.space': 'Space',
    'Key.enter': 'Enter',
    'Key.tab': 'Tab',
    'Key.backspace': 'Backspace',
    'Key.delete': 'Delete',
    'Key.escape': 'Esc',
    'Key.shift': 'Shift',
    'Key.shift_r': 'Shift',
    'Key.ctrl': 'Ctrl',
    'Key.ctrl_l': 'Ctrl',
    'Key.ctrl_r': 'Ctrl',
    'Key.alt': 'Alt',
    'Key.alt_l': 'Alt',
    'Key.alt_r': 'Alt',
    'Key.alt_gr': 'AltGr',
    'Key.cmd': 'Win',
    'Key.cmd_l': 'Win',
    'Key.cmd_r': 'Win',
    'Key.caps_lock': 'CapsLock',
    'Key.num_lock': 'NumLock',
    'Key.scroll_lock': 'ScrollLock',
    'Key.print_screen': 'PrtSc',
    'Key.pause': 'Pause',
    'Key.insert': 'Insert',
    'Key.home': 'Home',
    'Key.end': 'End',
    'Key.page_up': 'PgUp',
    'Key.page_down': 'PgDn',
    'Key.up': '↑',
    'Key.down': '↓',
    'Key.left': '←',
    'Key.right': '→',
    'Key.f1': 'F1',
    'Key.f2': 'F2',
    'Key.f3': 'F3',
    'Key.f4': 'F4',
    'Key.f5': 'F5',
    'Key.f6': 'F6',
    'Key.f7': 'F7',
    'Key.f8': 'F8',
    'Key.f9': 'F9',
    'Key.f10': 'F10',
    'Key.f11': 'F11',
    'Key.f12': 'F12',
    'Key.menu': 'Menu',
}


def get_key_name(key) -> Optional[str]:
    """Convert pynput key to display name."""
    key_str = str(key)
    
    # Check special key mappings
    if key_str in KEY_DISPLAY_NAMES:
        return KEY_DISPLAY_NAMES[key_str]
    
    # Handle character keys
    if hasattr(key, 'char') and key.char:
        char = key.char
        # Show uppercase for letters
        if char.isalpha():
            return char.upper()
        # Filter out control characters (unprintable)
        if char.isprintable():
            return char
        return None  # Will be handled by vk code
    
    # Handle special keys (Key.something)
    if key_str.startswith('Key.'):
        return key_str[4:].replace('_', ' ').title()
    
    # Don't return raw key representations like '<65>' or '\\x01'
    # Let get_key_from_vk handle these
    return None


def get_key_from_vk(key) -> Optional[str]:
    """Try to get a readable key name from virtual key code."""
    vk = None
    
    # Try to get vk code from the key
    if hasattr(key, 'vk') and key.vk is not None:
        vk = key.vk
    elif hasattr(key, '_scan'):
        # Some pynput versions use _scan
        vk = getattr(key, 'vk', None)
    
    if vk is None:
        return None
    
    # Ensure vk is an integer
    if not isinstance(vk, int):
        try:
            vk = int(vk)
        except (ValueError, TypeError):
            return None
    
    # A-Z keys (0x41-0x5A / 65-90)
    if 0x41 <= vk <= 0x5A:
        return chr(vk)
    
    # 0-9 number row keys (0x30-0x39 / 48-57)
    if 0x30 <= vk <= 0x39:
        return chr(vk)
    
    # Numpad 0-9 (0x60-0x69 / 96-105)
    if 0x60 <= vk <= 0x69:
        return str(vk - 0x60)  # Convert to '0'-'9'
    
    # Numpad operators
    numpad_map = {
        0x6A: '*',   # Numpad *
        0x6B: '+',   # Numpad +
        0x6D: '-',   # Numpad -
        0x6E: '.',   # Numpad .
        0x6F: '/',   # Numpad /
    }
    if vk in numpad_map:
        return numpad_map[vk]
    
    # Common punctuation/symbols
    vk_map = {
        0xBB: '=', 0xBC: ',', 0xBD: '-', 0xBE: '.', 0xBF: '/',
        0xBA: ';', 0xDB: '[', 0xDC: '\\', 0xDD: ']', 0xDE: "'",
        0xC0: '`',
    }
    if vk in vk_map:
        return vk_map[vk]
    
    # F1-F12 keys (0x70-0x7B / 112-123)
    if 0x70 <= vk <= 0x7B:
        return f'F{vk - 0x6F}'
    
    # For unmapped keys in printable ASCII range, try to show the character
    if 0x20 <= vk <= 0x7E:
        return chr(vk)
    
    return None


# Modifier key identifiers
MODIFIER_KEYS = {'Ctrl', 'Alt', 'Shift', 'Win', 'AltGr'}


class KeyboardListener(QObject):
    """Global keyboard listener using pynput with modifier combination support."""
    key_pressed = pyqtSignal(str)
    key_released = pyqtSignal(str)
    combo_pressed = pyqtSignal(str)  # For key combinations like Ctrl+S
    
    def __init__(self):
        super().__init__()
        self.listener = None
        self.active_modifiers = set()  # Currently held modifier keys
    
    def start(self):
        self.listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self.listener.start()
    
    def stop(self):
        if self.listener:
            self.listener.stop()
            self.listener = None
    
    def _on_press(self, key):
        key_name = get_key_name(key)
        
        # If key_name is None, try to get from vk code
        if key_name is None:
            key_name = get_key_from_vk(key)
        
        if key_name is None:
            return  # Skip unknown keys
        
        # Check if this is a modifier key
        if key_name in MODIFIER_KEYS:
            self.active_modifiers.add(key_name)
            self.key_pressed.emit(key_name)
        else:
            # Non-modifier key - check if we should combine with modifiers
            if self.active_modifiers:
                # Build combo string in standard order: Ctrl+Alt+Shift+Win+Key
                combo_parts = []
                for mod in ['Ctrl', 'Alt', 'Shift', 'Win']:
                    if mod in self.active_modifiers:
                        combo_parts.append(mod)
                combo_parts.append(key_name)
                combo_str = '+'.join(combo_parts)
                self.combo_pressed.emit(combo_str)
            else:
                self.key_pressed.emit(key_name)
    
    def _on_release(self, key):
        key_name = get_key_name(key)
        
        # If key_name is None, try to get from vk code
        if key_name is None:
            key_name = get_key_from_vk(key)
        
        if key_name is None:
            return
        
        # Remove from active modifiers if it's a modifier
        if key_name in MODIFIER_KEYS:
            self.active_modifiers.discard(key_name)
        
        self.key_released.emit(key_name)


# Display names for mouse buttons
MOUSE_BUTTON_NAMES = {
    Button.left: "Left Click",
    Button.right: "Right Click",
    Button.middle: "Middle Click",
}


class MouseClickListener(QObject):
    """Listens for global mouse clicks and emits Qt signals."""
    
    # (button_name, screen_x, screen_y) for spot overlay
    click_pressed = pyqtSignal(str, float, float)
    click_released = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self._listener = None
    
    def start(self):
        """Start listening for mouse clicks."""
        if self._listener is not None:
            return
        self._listener = MouseListener(on_click=self._on_click)
        self._listener.start()
    
    def stop(self):
        """Stop listening."""
        if self._listener:
            self._listener.stop()
            self._listener = None
    
    def _on_click(self, x, y, button, pressed):
        """Called from pynput thread on click/release."""
        name = MOUSE_BUTTON_NAMES.get(button)
        if name is None:
            return
        if pressed:
            self.click_pressed.emit(name, float(x), float(y))
        else:
            self.click_released.emit(name)


class KeyBubble(QWidget):
    """Individual key bubble widget with fade animation."""
    
    def __init__(self, key_text: str, config: dict, parent=None):
        super().__init__(parent)
        self.key_text = key_text
        self.config = config
        self.opacity = 1.0
        
        # Calculate size based on text
        self.calculate_size()
        
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    
    def calculate_size(self):
        """Calculate bubble size based on text and config."""
        # Get font metrics
        font = QFont(self.config['font_family'], self.config['font_size'])
        font.setBold(self.config['font_bold'])
        
        from PyQt6.QtGui import QFontMetrics
        fm = QFontMetrics(font)
        text_width = fm.horizontalAdvance(self.key_text)
        text_height = fm.height()
        
        # Get config values
        font_size = self.config.get('font_size', 24)
        padding = self.config.get('padding', 15)
        min_width = self.config.get('min_bubble_width', 55)
        border_width = self.config['border_width'] if self.config.get('show_border', True) else 0
        
        # Add padding around text
        content_width = text_width + (padding * 2)
        content_height = text_height + (padding * 2)
        
        # Ensure minimum height based on font size (font size * 2.2 is a good minimum)
        min_height = int(font_size * 2.2)
        content_height = max(content_height, min_height)
        
        # Add border space (border draws centered, so we need full width on each side)
        border_space = border_width + 2  # Add 2px margin for clean rendering
        
        # Calculate base dimensions
        width = max(content_width, min_width) + border_space
        height = content_height + border_space
        
        # For single characters, make it square-ish (slightly wider than tall)
        if len(self.key_text) == 1:
            # Use the larger dimension as the base
            target_size = max(width, height)
            width = target_size
            height = int(target_size * 0.95)  # Slightly shorter to look better
        # For short text (2-3 chars), ensure reasonable proportions
        elif len(self.key_text) <= 3:
            # Don't let it get too tall and narrow
            if height > width * 1.3:
                height = int(width * 1.3)
        
        self.setFixedSize(int(width), int(height))
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.setOpacity(self.opacity)
        
        # Get config values
        bg_color = QColor(self.config['bg_color'])
        border_color = QColor(self.config['border_color'])
        text_color = QColor(self.config['text_color'])
        border_width = float(self.config['border_width']) if self.config['show_border'] else 0.0
        radius = float(self.config['border_radius'])
        
        # Calculate inset for border (border is drawn centered on the edge)
        inset = (border_width / 2.0) + 1.0
        
        # Create float rect for smooth rendering
        w = float(self.width())
        h = float(self.height())
        
        x = inset
        y = inset
        rect_w = w - (inset * 2)
        rect_h = h - (inset * 2)
        
        # Ensure radius is reasonable (not larger than half of smallest dimension)
        max_radius = min(rect_w, rect_h) / 2.0
        r = min(radius, max_radius)
        
        # Build path for rounded rectangle manually for maximum control
        path = QPainterPath()
        
        # Start at top-left, after the curve
        path.moveTo(x + r, y)
        
        # Top edge to top-right corner
        path.lineTo(x + rect_w - r, y)
        # Top-right corner arc
        path.arcTo(x + rect_w - 2*r, y, 2*r, 2*r, 90, -90)
        
        # Right edge to bottom-right corner
        path.lineTo(x + rect_w, y + rect_h - r)
        # Bottom-right corner arc
        path.arcTo(x + rect_w - 2*r, y + rect_h - 2*r, 2*r, 2*r, 0, -90)
        
        # Bottom edge to bottom-left corner
        path.lineTo(x + r, y + rect_h)
        # Bottom-left corner arc
        path.arcTo(x, y + rect_h - 2*r, 2*r, 2*r, -90, -90)
        
        # Left edge to top-left corner
        path.lineTo(x, y + r)
        # Top-left corner arc
        path.arcTo(x, y, 2*r, 2*r, 180, -90)
        
        path.closeSubpath()
        
        # Set up pen for border
        if self.config['show_border'] and border_width > 0:
            pen = QPen(border_color, border_width)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
        else:
            painter.setPen(Qt.PenStyle.NoPen)
        
        # Set brush for fill
        painter.setBrush(QBrush(bg_color))
        
        # Draw the path
        painter.drawPath(path)
        
        # Draw text centered
        font = QFont(self.config['font_family'], self.config['font_size'])
        font.setBold(self.config['font_bold'])
        painter.setFont(font)
        painter.setPen(text_color)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.key_text)


class KeyOverlay(QWidget):
    """Main overlay window that displays key presses."""
    
    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.key_bubbles: List[KeyBubble] = []
        self.fade_timers: dict = {}
        self.active_keys: dict = {}  # Track currently held keys
        self.combo_key_map: dict = {}  # Maps individual keys to their combo (e.g., "S" -> "Ctrl+S")
        
        self.setup_ui()
        self.update_position()
    
    def setup_ui(self):
        # Frameless, always on top, transparent, click-through
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        # Set size - height will auto-adjust based on font
        self.setMinimumWidth(400)
        self.update_height()
    
    def calculate_required_height(self) -> int:
        """Calculate the minimum overlay height needed for current font size."""
        font_size = self.config.get('font_size', 24)
        padding = self.config.get('padding', 15)
        border_width = self.config.get('border_width', 3) if self.config.get('show_border', True) else 0
        
        # Calculate bubble height: font height + padding + border + margins
        # Font height is approximately 1.4x font size
        font_height = int(font_size * 1.4)
        bubble_height = font_height + (padding * 2) + (border_width * 2) + 4
        
        # For single characters, we make bubbles square-ish, so use max dimension
        min_bubble_size = int(font_size * 2.2)
        bubble_height = max(bubble_height, min_bubble_size)
        
        # Add vertical margin (space above and below the bubble)
        vertical_margin = 10
        
        return bubble_height + (vertical_margin * 2)
    
    def update_height(self):
        """Update overlay height based on font size."""
        required_height = self.calculate_required_height()
        # Use the larger of calculated height or configured minimum
        min_height = self.config.get('overlay_height', 80)
        actual_height = max(required_height, min_height)
        self.setFixedHeight(actual_height)
    
    def update_position(self):
        """Position overlay based on configuration."""
        # Get the selected screen
        screen_selection = self.config.get('screen_selection', 'primary')
        screens = QApplication.screens()
        
        if not screens:
            return
        
        # Determine which screen to use
        if screen_selection == 'primary':
            screen = QApplication.primaryScreen()
        elif screen_selection.startswith('screen_'):
            # Extract screen index (e.g., 'screen_0' -> 0)
            try:
                screen_index = int(screen_selection.split('_')[1])
                if 0 <= screen_index < len(screens):
                    screen = screens[screen_index]
                else:
                    screen = QApplication.primaryScreen()  # Fallback
            except (ValueError, IndexError):
                screen = QApplication.primaryScreen()  # Fallback
        else:
            screen = QApplication.primaryScreen()  # Fallback
        
        if not screen:
            return
        
        geometry = screen.availableGeometry()
        
        # Set width with margins
        overlay_width = geometry.width() - 200
        self.setFixedWidth(overlay_width)
        
        # Calculate horizontal position
        h_pos = self.config.get('position_horizontal', 'center')
        h_margin = self.config.get('margin_horizontal', 0)
        
        if h_pos == 'left':
            x = geometry.x() + h_margin + 20
        elif h_pos == 'right':
            x = geometry.x() + geometry.width() - self.width() - h_margin - 20
        else:  # center
            x = geometry.x() + (geometry.width() - self.width()) // 2 + h_margin
        
        # Calculate vertical position
        v_pos = self.config.get('position_vertical', 'bottom')
        v_margin = self.config['margin_bottom']
        
        if v_pos == 'top':
            y = geometry.y() + v_margin
        else:  # bottom
            y = geometry.y() + geometry.height() - self.height() - v_margin
        
        self.move(int(x), int(y))
    
    def add_key(self, key_name: str):
        """Add a key bubble to the display."""
        # If key already shown and held, reset its timer
        if key_name in self.active_keys:
            bubble = self.active_keys[key_name]
            bubble.opacity = 1.0
            bubble.update()
            if key_name in self.fade_timers:
                self.fade_timers[key_name].stop()
                del self.fade_timers[key_name]
            return
        
        # Create new bubble
        bubble = KeyBubble(key_name, self.config, self)
        self.key_bubbles.append(bubble)
        self.active_keys[key_name] = bubble
        
        # Position bubbles
        self.layout_bubbles()
        
        bubble.show()
        
        # Limit number of visible keys
        max_keys = self.config['max_keys']
        while len(self.key_bubbles) > max_keys:
            old_bubble = self.key_bubbles.pop(0)
            key_to_remove = None
            for k, v in self.active_keys.items():
                if v == old_bubble:
                    key_to_remove = k
                    break
            if key_to_remove:
                del self.active_keys[key_to_remove]
                if key_to_remove in self.fade_timers:
                    self.fade_timers[key_to_remove].stop()
                    del self.fade_timers[key_to_remove]
            old_bubble.deleteLater()
    
    def release_key(self, key_name: str):
        """Start fade out for released key."""
        # Check if this key is part of a combo
        if key_name in self.combo_key_map:
            combo = self.combo_key_map[key_name]
            # Release the combo instead
            self._start_fade(combo)
            # Clean up all keys mapped to this combo
            keys_to_remove = [k for k, v in self.combo_key_map.items() if v == combo]
            for k in keys_to_remove:
                del self.combo_key_map[k]
            return
        
        self._start_fade(key_name)
    
    def _start_fade(self, key_name: str):
        """Start fade timer for a key."""
        if key_name not in self.active_keys:
            return
        
        # Start fade timer
        if key_name not in self.fade_timers:
            timer = QTimer()
            timer.timeout.connect(lambda: self.fade_key(key_name))
            timer.start(50)  # Update every 50ms
            self.fade_timers[key_name] = timer
    
    def show_combo(self, combo: str):
        """Show a key combination, removing individual modifier bubbles."""
        # Parse combo to get parts (e.g., "Ctrl+S" -> ["Ctrl", "S"])
        parts = combo.split('+')
        
        # Remove modifier bubbles that are part of this combo
        for part in parts[:-1]:  # All except the last (the actual key)
            if part in self.active_keys:
                bubble = self.active_keys[part]
                if part in self.fade_timers:
                    self.fade_timers[part].stop()
                    del self.fade_timers[part]
                if bubble in self.key_bubbles:
                    self.key_bubbles.remove(bubble)
                del self.active_keys[part]
                bubble.deleteLater()
        
        # Map all parts of the combo to the combo name for release tracking
        for part in parts:
            self.combo_key_map[part] = combo
        
        # Add the combo as a single bubble
        self.add_key(combo)
    
    def fade_key(self, key_name: str):
        """Gradually fade out a key bubble."""
        if key_name not in self.active_keys:
            if key_name in self.fade_timers:
                self.fade_timers[key_name].stop()
                del self.fade_timers[key_name]
            return
        
        bubble = self.active_keys[key_name]
        fade_speed = self.config['fade_speed'] / 1000.0 * 50  # Convert to per-tick
        bubble.opacity -= fade_speed
        bubble.update()
        
        if bubble.opacity <= 0:
            # Remove bubble
            self.fade_timers[key_name].stop()
            del self.fade_timers[key_name]
            del self.active_keys[key_name]
            if bubble in self.key_bubbles:
                self.key_bubbles.remove(bubble)
            bubble.deleteLater()
            self.layout_bubbles()
    
    def layout_bubbles(self):
        """Arrange bubbles horizontally centered."""
        if not self.key_bubbles:
            return
        
        spacing = self.config['bubble_spacing']
        total_width = sum(b.width() for b in self.key_bubbles) + spacing * (len(self.key_bubbles) - 1)
        
        start_x = (self.width() - total_width) // 2
        y = (self.height() - self.key_bubbles[0].height()) // 2 if self.key_bubbles else 0
        
        x = start_x
        for bubble in self.key_bubbles:
            bubble.move(int(x), int(y))
            x += bubble.width() + spacing
    
    def update_config(self, config: dict):
        """Update configuration and refresh display."""
        self.config = config
        self.update_height()  # Auto-adjust height based on font size
        self.update_position()
        
        # Clear existing bubbles
        for bubble in self.key_bubbles:
            bubble.deleteLater()
        self.key_bubbles.clear()
        self.active_keys.clear()
        self.combo_key_map.clear()
        for timer in self.fade_timers.values():
            timer.stop()
        self.fade_timers.clear()
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.layout_bubbles()


def _default_click_spot_config() -> dict:
    """Default config values for click spot (used when key missing)."""
    return {
        'click_spot_radius': 45,
        'click_spot_fade_ms': 400,
        'click_spot_color_left': '#6490ff',
        'click_spot_color_right': '#ff7864',
        'click_spot_color_middle': '#8cc88c',
        'click_spot_opacity': 0.7,
    }


class ClickSpotOverlay(QWidget):
    """Full-screen overlay that draws a gradient circle at each click position."""
    
    FADE_TICK_MS = 40
    
    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.config = config
        self.spots: List[dict] = []
        self._fade_timer = QTimer(self)
        self._fade_timer.timeout.connect(self._tick_fade)
        self.setup_ui()
    
    def update_config(self, config: dict):
        """Update config (e.g. after settings change)."""
        self.config = config
    
    def setup_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setGeometry(0, 0, 1, 1)  # Set by update_geometry()
    
    def update_geometry(self):
        """Size and position to cover all screens (multi-monitor support)."""
        screens = QApplication.screens()
        if not screens:
            return
        
        # Calculate bounding rectangle that covers all screens
        min_x = min(s.geometry().x() for s in screens)
        min_y = min(s.geometry().y() for s in screens)
        max_x = max(s.geometry().x() + s.geometry().width() for s in screens)
        max_y = max(s.geometry().y() + s.geometry().height() for s in screens)
        
        self.setGeometry(min_x, min_y, max_x - min_x, max_y - min_y)
    
    def add_spot(self, screen_x: float, screen_y: float, button_name: str):
        """Add a gradient circle at the given screen position."""
        import time
        self.spots.append({
            "x": screen_x,
            "y": screen_y,
            "alpha": 1.0,
            "button_name": button_name,
            "created_at": time.perf_counter(),
        })
        if not self._fade_timer.isActive():
            self._fade_timer.start(self.FADE_TICK_MS)
        self.update()
    
    def _tick_fade(self):
        """Decay alpha for all spots and remove dead ones."""
        import time
        cfg = _default_click_spot_config()
        cfg.update(self.config)
        fade_ms = cfg.get('click_spot_fade_ms', 400)
        now = time.perf_counter()
        for s in self.spots:
            elapsed_ms = (now - s["created_at"]) * 1000
            s["alpha"] = max(0.0, 1.0 - elapsed_ms / fade_ms)
        self.spots = [s for s in self.spots if s["alpha"] > 0.001]
        if not self.spots:
            self._fade_timer.stop()
        self.update()
    
    def _spot_colors(self) -> dict:
        """Resolve spot colors from config."""
        cfg = _default_click_spot_config()
        cfg.update(self.config)
        return {
            "Left Click": QColor(cfg.get('click_spot_color_left', '#6490ff')),
            "Right Click": QColor(cfg.get('click_spot_color_right', '#ff7864')),
            "Middle Click": QColor(cfg.get('click_spot_color_middle', '#8cc88c')),
        }
    
    def paintEvent(self, event):
        cfg = _default_click_spot_config()
        cfg.update(self.config)
        r = int(cfg.get('click_spot_radius', 45))
        opacity = float(cfg.get('click_spot_opacity', 0.7))
        spot_colors = self._spot_colors()
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        
        win_x = self.geometry().x()
        win_y = self.geometry().y()
        
        for s in self.spots:
            local_x = s["x"] - win_x
            local_y = s["y"] - win_y
            alpha = s["alpha"]
            button_name = s.get("button_name", "Left Click")
            
            center_color = spot_colors.get(button_name, spot_colors["Left Click"])
            center_color = QColor(center_color)
            center_color.setAlphaF(alpha * opacity)
            edge_color = QColor(center_color)
            edge_color.setAlphaF(0.0)
            
            gradient = QRadialGradient(local_x, local_y, r, local_x, local_y)
            gradient.setColorAt(0.0, center_color)
            gradient.setColorAt(0.5, edge_color)
            gradient.setColorAt(1.0, edge_color)
            
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(gradient))
            painter.drawEllipse(int(local_x - r), int(local_y - r), int(r * 2), int(r * 2))


class SettingsDialog(QDialog):
    """Configuration dialog for KeyVisualizer."""
    
    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.config = config.copy()
        self.setWindowTitle("KeyVisualizer Settings")
        self.setMinimumWidth(500)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Tab widget for organized settings
        tabs = QTabWidget()
        
        # Appearance tab
        appearance_tab = QWidget()
        appearance_layout = QVBoxLayout(appearance_tab)
        
        # Colors group
        colors_group = QGroupBox("Colors")
        colors_layout = QGridLayout(colors_group)
        
        # Background color
        colors_layout.addWidget(QLabel("Background:"), 0, 0)
        self.bg_color_btn = QPushButton()
        self.bg_color_btn.setFixedSize(80, 30)
        self.update_color_button(self.bg_color_btn, self.config['bg_color'])
        self.bg_color_btn.clicked.connect(lambda: self.pick_color('bg_color', self.bg_color_btn))
        colors_layout.addWidget(self.bg_color_btn, 0, 1)
        
        # Text color
        colors_layout.addWidget(QLabel("Text:"), 0, 2)
        self.text_color_btn = QPushButton()
        self.text_color_btn.setFixedSize(80, 30)
        self.update_color_button(self.text_color_btn, self.config['text_color'])
        self.text_color_btn.clicked.connect(lambda: self.pick_color('text_color', self.text_color_btn))
        colors_layout.addWidget(self.text_color_btn, 0, 3)
        
        # Border color
        colors_layout.addWidget(QLabel("Border:"), 1, 0)
        self.border_color_btn = QPushButton()
        self.border_color_btn.setFixedSize(80, 30)
        self.update_color_button(self.border_color_btn, self.config['border_color'])
        self.border_color_btn.clicked.connect(lambda: self.pick_color('border_color', self.border_color_btn))
        colors_layout.addWidget(self.border_color_btn, 1, 1)
        
        # Show border checkbox
        self.show_border_cb = QCheckBox("Show border")
        self.show_border_cb.setChecked(self.config['show_border'])
        colors_layout.addWidget(self.show_border_cb, 1, 2, 1, 2)
        
        appearance_layout.addWidget(colors_group)
        
        # Font group
        font_group = QGroupBox("Font")
        font_layout = QGridLayout(font_group)
        
        font_layout.addWidget(QLabel("Family:"), 0, 0)
        self.font_combo = QFontComboBox()
        self.font_combo.setCurrentFont(QFont(self.config['font_family']))
        font_layout.addWidget(self.font_combo, 0, 1, 1, 3)
        
        font_layout.addWidget(QLabel("Size:"), 1, 0)
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 72)
        self.font_size_spin.setValue(self.config['font_size'])
        font_layout.addWidget(self.font_size_spin, 1, 1)
        
        self.font_bold_cb = QCheckBox("Bold")
        self.font_bold_cb.setChecked(self.config['font_bold'])
        font_layout.addWidget(self.font_bold_cb, 1, 2)
        
        appearance_layout.addWidget(font_group)
        
        # Size group
        size_group = QGroupBox("Bubble Size")
        size_layout = QGridLayout(size_group)
        
        size_layout.addWidget(QLabel("Padding:"), 0, 0)
        self.padding_spin = QSpinBox()
        self.padding_spin.setRange(4, 40)
        self.padding_spin.setValue(self.config['padding'])
        size_layout.addWidget(self.padding_spin, 0, 1)
        
        size_layout.addWidget(QLabel("Min Width:"), 0, 2)
        self.min_width_spin = QSpinBox()
        self.min_width_spin.setRange(20, 200)
        self.min_width_spin.setValue(self.config['min_bubble_width'])
        size_layout.addWidget(self.min_width_spin, 0, 3)
        
        size_layout.addWidget(QLabel("Border Radius:"), 1, 0)
        self.radius_spin = QSpinBox()
        self.radius_spin.setRange(0, 100)  # Allow larger radius for big fonts
        self.radius_spin.setValue(self.config['border_radius'])
        size_layout.addWidget(self.radius_spin, 1, 1)
        
        size_layout.addWidget(QLabel("Border Width:"), 1, 2)
        self.border_width_spin = QSpinBox()
        self.border_width_spin.setRange(1, 10)
        self.border_width_spin.setValue(self.config['border_width'])
        size_layout.addWidget(self.border_width_spin, 1, 3)
        
        appearance_layout.addWidget(size_group)
        appearance_layout.addStretch()
        
        tabs.addTab(appearance_tab, "Appearance")
        
        # Behavior tab
        behavior_tab = QWidget()
        behavior_layout = QVBoxLayout(behavior_tab)
        
        # Position group
        position_group = QGroupBox("Position")
        position_layout = QGridLayout(position_group)
        
        # Horizontal position
        position_layout.addWidget(QLabel("Horizontal:"), 0, 0)
        self.h_pos_combo = QComboBox()
        self.h_pos_combo.addItem("Left", "left")
        self.h_pos_combo.addItem("Center", "center")
        self.h_pos_combo.addItem("Right", "right")
        current_h = self.config.get('position_horizontal', 'center')
        self.h_pos_combo.setCurrentIndex({'left': 0, 'center': 1, 'right': 2}.get(current_h, 1))
        position_layout.addWidget(self.h_pos_combo, 0, 1)
        
        # Vertical position
        position_layout.addWidget(QLabel("Vertical:"), 0, 2)
        self.v_pos_combo = QComboBox()
        self.v_pos_combo.addItem("Top", "top")
        self.v_pos_combo.addItem("Bottom", "bottom")
        current_v = self.config.get('position_vertical', 'bottom')
        self.v_pos_combo.setCurrentIndex({'top': 0, 'bottom': 1}.get(current_v, 1))
        position_layout.addWidget(self.v_pos_combo, 0, 3)
        
        # Screen selection (for multi-monitor setups)
        position_layout.addWidget(QLabel("Screen:"), 1, 0)
        self.screen_combo = QComboBox()
        
        # Populate with available screens
        screens = QApplication.screens()
        self.screen_combo.addItem("Primary Screen", "primary")
        for i, screen in enumerate(screens):
            screen_name = screen.name() if screen.name() else f"Screen {i + 1}"
            self.screen_combo.addItem(f"{screen_name} ({screen.size().width()}x{screen.size().height()})", f"screen_{i}")
        
        # Set current selection
        current_screen = self.config.get('screen_selection', 'primary')
        for i in range(self.screen_combo.count()):
            if self.screen_combo.itemData(i) == current_screen:
                self.screen_combo.setCurrentIndex(i)
                break
        
        position_layout.addWidget(self.screen_combo, 1, 1, 1, 3)  # Span 3 columns
        
        # Margins
        position_layout.addWidget(QLabel("Vertical Margin:"), 2, 0)
        self.margin_spin = QSpinBox()
        self.margin_spin.setRange(0, 500)
        self.margin_spin.setValue(self.config['margin_bottom'])
        position_layout.addWidget(self.margin_spin, 2, 1)
        
        position_layout.addWidget(QLabel("Horizontal Offset:"), 2, 2)
        self.h_margin_spin = QSpinBox()
        self.h_margin_spin.setRange(-500, 500)
        self.h_margin_spin.setValue(self.config.get('margin_horizontal', 0))
        position_layout.addWidget(self.h_margin_spin, 2, 3)
        
        # Size settings (overlay height auto-adjusts with font size)
        position_layout.addWidget(QLabel("Min Height:"), 3, 0)
        self.height_spin = QSpinBox()
        self.height_spin.setRange(40, 300)
        self.height_spin.setValue(self.config['overlay_height'])
        self.height_spin.setToolTip("Minimum overlay height (auto-adjusts based on font size)")
        position_layout.addWidget(self.height_spin, 3, 1)
        
        position_layout.addWidget(QLabel("Bubble Spacing:"), 3, 2)
        self.spacing_spin = QSpinBox()
        self.spacing_spin.setRange(2, 50)
        self.spacing_spin.setValue(self.config['bubble_spacing'])
        position_layout.addWidget(self.spacing_spin, 3, 3)
        
        behavior_layout.addWidget(position_group)
        
        # Animation group
        anim_group = QGroupBox("Animation")
        anim_layout = QGridLayout(anim_group)
        
        anim_layout.addWidget(QLabel("Fade Speed:"), 0, 0)
        self.fade_slider = QSlider(Qt.Orientation.Horizontal)
        self.fade_slider.setRange(1, 20)
        self.fade_slider.setValue(int(self.config['fade_speed'] * 10))
        anim_layout.addWidget(self.fade_slider, 0, 1)
        self.fade_label = QLabel(f"{self.config['fade_speed']:.1f}")
        self.fade_slider.valueChanged.connect(lambda v: self.fade_label.setText(f"{v/10:.1f}"))
        anim_layout.addWidget(self.fade_label, 0, 2)
        
        anim_layout.addWidget(QLabel("Max Keys Shown:"), 1, 0)
        self.max_keys_spin = QSpinBox()
        self.max_keys_spin.setRange(1, 20)
        self.max_keys_spin.setValue(self.config['max_keys'])
        anim_layout.addWidget(self.max_keys_spin, 1, 1)
        
        behavior_layout.addWidget(anim_group)
        
        # Startup group
        startup_group = QGroupBox("Startup")
        startup_layout = QVBoxLayout(startup_group)
        
        self.start_minimized_cb = QCheckBox("Start minimized to tray")
        self.start_minimized_cb.setChecked(self.config.get('start_minimized', True))
        startup_layout.addWidget(self.start_minimized_cb)
        
        self.autostart_cb = QCheckBox("Start with Windows")
        self.autostart_cb.setChecked(self.config.get('autostart', False))
        startup_layout.addWidget(self.autostart_cb)
        
        behavior_layout.addWidget(startup_group)
        behavior_layout.addStretch()
        
        tabs.addTab(behavior_tab, "Behavior")
        
        # Presets tab
        presets_tab = QWidget()
        presets_layout = QVBoxLayout(presets_tab)
        
        presets_group = QGroupBox("Quick Presets")
        presets_btn_layout = QVBoxLayout(presets_group)
        
        dark_btn = QPushButton("Dark Theme (Default)")
        dark_btn.clicked.connect(self.apply_dark_preset)
        presets_btn_layout.addWidget(dark_btn)
        
        light_btn = QPushButton("Light Theme")
        light_btn.clicked.connect(self.apply_light_preset)
        presets_btn_layout.addWidget(light_btn)
        
        minimal_btn = QPushButton("Minimal")
        minimal_btn.clicked.connect(self.apply_minimal_preset)
        presets_btn_layout.addWidget(minimal_btn)
        
        colorful_btn = QPushButton("Colorful")
        colorful_btn.clicked.connect(self.apply_colorful_preset)
        presets_btn_layout.addWidget(colorful_btn)
        
        presets_layout.addWidget(presets_group)
        presets_layout.addStretch()
        
        tabs.addTab(presets_tab, "Presets")
        
        # Click Spot tab
        click_spot_tab = QWidget()
        click_spot_layout = QVBoxLayout(click_spot_tab)
        
        click_spot_group = QGroupBox("Click spot (circle at click position)")
        cs_layout = QGridLayout(click_spot_group)
        
        self.show_click_spot_cb = QCheckBox("Show click spot")
        self.show_click_spot_cb.setChecked(self.config.get('show_click_spot', True))
        cs_layout.addWidget(self.show_click_spot_cb, 0, 0, 1, 2)
        
        cs_layout.addWidget(QLabel("Radius:"), 1, 0)
        self.click_spot_radius_spin = QSpinBox()
        self.click_spot_radius_spin.setRange(10, 120)
        self.click_spot_radius_spin.setValue(self.config.get('click_spot_radius', 45))
        cs_layout.addWidget(self.click_spot_radius_spin, 1, 1)
        
        cs_layout.addWidget(QLabel("Fade (ms):"), 1, 2)
        self.click_spot_fade_spin = QSpinBox()
        self.click_spot_fade_spin.setRange(100, 1500)
        self.click_spot_fade_spin.setValue(self.config.get('click_spot_fade_ms', 400))
        self.click_spot_fade_spin.setSuffix(" ms")
        cs_layout.addWidget(self.click_spot_fade_spin, 1, 3)
        
        cs_layout.addWidget(QLabel("Center opacity:"), 2, 0)
        self.click_spot_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.click_spot_opacity_slider.setRange(10, 100)
        self.click_spot_opacity_slider.setValue(int(self.config.get('click_spot_opacity', 0.7) * 100))
        cs_layout.addWidget(self.click_spot_opacity_slider, 2, 1)
        self.click_spot_opacity_label = QLabel(f"{self.config.get('click_spot_opacity', 0.7):.2f}")
        self.click_spot_opacity_slider.valueChanged.connect(
            lambda v: self.click_spot_opacity_label.setText(f"{v/100:.2f}")
        )
        cs_layout.addWidget(self.click_spot_opacity_label, 2, 2)
        
        cs_layout.addWidget(QLabel("Left click color:"), 3, 0)
        self.click_spot_left_btn = QPushButton()
        self.click_spot_left_btn.setFixedSize(80, 28)
        self.update_color_button(self.click_spot_left_btn, self.config.get('click_spot_color_left', '#6490ff'))
        self.click_spot_left_btn.clicked.connect(lambda: self.pick_color('click_spot_color_left', self.click_spot_left_btn))
        cs_layout.addWidget(self.click_spot_left_btn, 3, 1)
        
        cs_layout.addWidget(QLabel("Right click color:"), 3, 2)
        self.click_spot_right_btn = QPushButton()
        self.click_spot_right_btn.setFixedSize(80, 28)
        self.update_color_button(self.click_spot_right_btn, self.config.get('click_spot_color_right', '#ff7864'))
        self.click_spot_right_btn.clicked.connect(lambda: self.pick_color('click_spot_color_right', self.click_spot_right_btn))
        cs_layout.addWidget(self.click_spot_right_btn, 3, 3)
        
        cs_layout.addWidget(QLabel("Middle click color:"), 4, 0)
        self.click_spot_middle_btn = QPushButton()
        self.click_spot_middle_btn.setFixedSize(80, 28)
        self.update_color_button(self.click_spot_middle_btn, self.config.get('click_spot_color_middle', '#8cc88c'))
        self.click_spot_middle_btn.clicked.connect(lambda: self.pick_color('click_spot_color_middle', self.click_spot_middle_btn))
        cs_layout.addWidget(self.click_spot_middle_btn, 4, 1)
        
        click_spot_layout.addWidget(click_spot_group)
        click_spot_layout.addStretch()
        
        tabs.addTab(click_spot_tab, "Click Spot")
        
        layout.addWidget(tabs)
        
        # Dialog buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        ok_btn = QPushButton("OK")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def update_color_button(self, button: QPushButton, color: str):
        """Update button appearance with color preview."""
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                border: 1px solid #555;
                border-radius: 4px;
            }}
        """)
    
    def pick_color(self, config_key: str, button: QPushButton):
        """Open color picker dialog."""
        current = QColor(self.config[config_key])
        color = QColorDialog.getColor(current, self, f"Select {config_key.replace('_', ' ').title()}")
        if color.isValid():
            self.config[config_key] = color.name()
            self.update_color_button(button, color.name())
    
    def apply_dark_preset(self):
        """Apply dark theme preset."""
        self.config.update({
            'bg_color': '#2b2b2b',
            'text_color': '#ffffff',
            'border_color': '#555555',
            'show_border': True,
        })
        self.refresh_color_buttons()
    
    def apply_light_preset(self):
        """Apply light theme preset."""
        self.config.update({
            'bg_color': '#ffffff',
            'text_color': '#333333',
            'border_color': '#cccccc',
            'show_border': True,
        })
        self.refresh_color_buttons()
    
    def apply_minimal_preset(self):
        """Apply minimal preset."""
        self.config.update({
            'bg_color': '#000000',
            'text_color': '#ffffff',
            'border_color': '#000000',
            'show_border': False,
        })
        self.refresh_color_buttons()
    
    def apply_colorful_preset(self):
        """Apply colorful preset."""
        self.config.update({
            'bg_color': '#4a90d9',
            'text_color': '#ffffff',
            'border_color': '#2e6bb0',
            'show_border': True,
        })
        self.refresh_color_buttons()
    
    def refresh_color_buttons(self):
        """Update all color buttons after preset change."""
        self.update_color_button(self.bg_color_btn, self.config['bg_color'])
        self.update_color_button(self.text_color_btn, self.config['text_color'])
        self.update_color_button(self.border_color_btn, self.config['border_color'])
        self.show_border_cb.setChecked(self.config['show_border'])
    
    def get_config(self) -> dict:
        """Return updated configuration."""
        return {
            'bg_color': self.config['bg_color'],
            'text_color': self.config['text_color'],
            'border_color': self.config['border_color'],
            'show_border': self.show_border_cb.isChecked(),
            'font_family': self.font_combo.currentFont().family(),
            'font_size': self.font_size_spin.value(),
            'font_bold': self.font_bold_cb.isChecked(),
            'padding': self.padding_spin.value(),
            'min_bubble_width': self.min_width_spin.value(),
            'border_radius': self.radius_spin.value(),
            'border_width': self.border_width_spin.value(),
            'overlay_height': self.height_spin.value(),
            'margin_bottom': self.margin_spin.value(),
            'margin_horizontal': self.h_margin_spin.value(),
            'bubble_spacing': self.spacing_spin.value(),
            'fade_speed': self.fade_slider.value() / 10.0,
            'max_keys': self.max_keys_spin.value(),
            'start_minimized': self.start_minimized_cb.isChecked(),
            'autostart': self.autostart_cb.isChecked(),
            'position_horizontal': self.h_pos_combo.currentData(),
            'position_vertical': self.v_pos_combo.currentData(),
            'screen_selection': self.screen_combo.currentData(),
            'show_click_spot': self.show_click_spot_cb.isChecked(),
            'click_spot_radius': self.click_spot_radius_spin.value(),
            'click_spot_fade_ms': self.click_spot_fade_spin.value(),
            'click_spot_color_left': self.config.get('click_spot_color_left', '#6490ff'),
            'click_spot_color_right': self.config.get('click_spot_color_right', '#ff7864'),
            'click_spot_color_middle': self.config.get('click_spot_color_middle', '#8cc88c'),
            'click_spot_opacity': self.click_spot_opacity_slider.value() / 100.0,
        }


def create_tray_icon() -> QIcon:
    """Create the system tray icon."""
    size = 64
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    # Draw rounded rectangle background
    painter.setBrush(QColor("#4a90d9"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(4, 4, size - 8, size - 8, 10, 10)
    
    # Draw "K" for Keys
    painter.setPen(QColor("white"))
    painter.setFont(QFont("Segoe UI", 32, QFont.Weight.Bold))
    painter.drawText(img.rect(), Qt.AlignmentFlag.AlignCenter, "K")
    
    painter.end()
    return QIcon(QPixmap.fromImage(img))


class KeyVisualizerApp(QSystemTrayIcon):
    """Main application with system tray integration."""
    
    DEFAULT_CONFIG = {
        'bg_color': '#2b2b2b',
        'text_color': '#ffffff',
        'border_color': '#555555',
        'show_border': True,
        'font_family': 'Segoe UI',
        'font_size': 20,
        'font_bold': True,
        'padding': 15,
        'min_bubble_width': 55,
        'border_radius': 25,
        'border_width': 3,
        'overlay_height': 80,
        'margin_bottom': 50,
        'margin_horizontal': 0,
        'bubble_spacing': 10,
        'fade_speed': 0.5,
        'max_keys': 10,
        'start_minimized': True,
        'autostart': False,
        'position_horizontal': 'center',  # left, center, right
        'position_vertical': 'bottom',    # top, bottom
        'screen_selection': 'primary',     # 'primary', 'screen_0', 'screen_1', etc.
        # Click spot overlay (circle at click position)
        'show_click_spot': True,
        'click_spot_radius': 45,
        'click_spot_fade_ms': 400,
        'click_spot_color_left': '#6490ff',
        'click_spot_color_right': '#ff7864',
        'click_spot_color_middle': '#8cc88c',
        'click_spot_opacity': 0.7,
    }
    
    def __init__(self):
        super().__init__()
        
        # Load settings
        self.settings = QSettings("StuckAtPrototype", "KeyVisualizer")
        self.config = self.load_config()
        
        # State
        self.is_active = True
        self.keyboard_listener = KeyboardListener()
        self.mouse_listener = MouseClickListener()
        
        # Create overlays
        self.overlay = KeyOverlay(self.config)
        self.click_spot_overlay = ClickSpotOverlay(self.config)
        self.click_spot_overlay.update_geometry()
        
        # Setup UI
        self.setup_tray()
        
        # Connect keyboard signals
        self.keyboard_listener.key_pressed.connect(self.on_key_pressed)
        self.keyboard_listener.key_released.connect(self.on_key_released)
        self.keyboard_listener.combo_pressed.connect(self.on_combo_pressed)
        
        # Connect mouse signals
        self.mouse_listener.click_pressed.connect(self.on_click_pressed)
        self.mouse_listener.click_released.connect(self.on_click_released)
        
        # Start listening (show click spot first so key overlay stays on top)
        self.keyboard_listener.start()
        self.mouse_listener.start()
        if self.config.get('show_click_spot', True):
            self.click_spot_overlay.show()
        self.overlay.show()
        self.overlay.raise_()
    
    def load_config(self) -> dict:
        """Load configuration from settings."""
        config = self.DEFAULT_CONFIG.copy()
        
        stored = self.settings.value("config")
        if stored:
            try:
                stored_config = json.loads(stored)
                config.update(stored_config)
            except (json.JSONDecodeError, TypeError):
                pass
        
        return config
    
    def save_config(self):
        """Save configuration to settings."""
        self.settings.setValue("config", json.dumps(self.config))
    
    def setup_tray(self):
        """Setup system tray icon and menu."""
        self.setIcon(create_tray_icon())
        self.setToolTip("KeyVisualizer - Right-click for menu")
        
        # Create menu - store as instance variable to prevent garbage collection
        self.menu = QMenu()
        
        self.status_action = QAction("Active")
        self.status_action.setEnabled(False)
        self.menu.addAction(self.status_action)
        
        self.menu.addSeparator()
        
        self.toggle_action = QAction("Pause")
        self.toggle_action.triggered.connect(self.toggle_active)
        self.menu.addAction(self.toggle_action)
        
        # Store as instance variable to prevent garbage collection
        self.settings_action = QAction("Settings...")
        self.settings_action.triggered.connect(self.show_settings)
        self.menu.addAction(self.settings_action)
        
        # Reset to defaults option
        self.reset_action = QAction("Reset to Defaults")
        self.reset_action.triggered.connect(self.reset_to_defaults)
        self.menu.addAction(self.reset_action)
        
        self.menu.addSeparator()
        
        # Store as instance variable to prevent garbage collection
        self.quit_action = QAction("Quit")
        self.quit_action.triggered.connect(self.quit_app)
        self.menu.addAction(self.quit_action)
        
        self.setContextMenu(self.menu)
        
        # Click handling
        self.activated.connect(self.on_activated)
    
    def on_activated(self, reason):
        """Handle tray icon clicks (double-click opens settings; single-click does nothing)."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_settings()
    
    def toggle_active(self):
        """Toggle key visualization on/off."""
        self.is_active = not self.is_active
        
        if self.is_active:
            if self.config.get('show_click_spot', True):
                self.click_spot_overlay.show()
            self.overlay.show()
            self.overlay.raise_()
            self.toggle_action.setText("Pause")
            self.status_action.setText("Active")
            self.setToolTip("KeyVisualizer - Active\nRight-click for menu")
        else:
            self.overlay.hide()
            self.click_spot_overlay.hide()
            self.toggle_action.setText("Resume")
            self.status_action.setText("Paused")
            self.setToolTip("KeyVisualizer - Paused\nRight-click for menu")
    
    def on_key_pressed(self, key_name: str):
        """Handle key press event."""
        if self.is_active:
            self.overlay.add_key(key_name)
    
    def on_key_released(self, key_name: str):
        """Handle key release event."""
        if self.is_active:
            self.overlay.release_key(key_name)
    
    def on_combo_pressed(self, combo: str):
        """Handle key combination press (e.g., Ctrl+S)."""
        if self.is_active:
            # Remove individual modifier bubbles and show the combo instead
            self.overlay.show_combo(combo)
    
    def on_click_pressed(self, button_name: str, x: float, y: float):
        """Handle mouse click (Left Click, Right Click, etc.)."""
        if self.is_active:
            self.overlay.add_key(button_name)
            if self.config.get('show_click_spot', True):
                self.click_spot_overlay.add_spot(x, y, button_name)
    
    def on_click_released(self, button_name: str):
        """Handle mouse release."""
        if self.is_active:
            self.overlay.release_key(button_name)
    
    def show_settings(self):
        """Show settings dialog."""
        dialog = SettingsDialog(self.config)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.config = dialog.get_config()
            self.save_config()
            self.overlay.update_config(self.config)
            self.click_spot_overlay.update_config(self.config)
            
            # Show/hide click spot overlay based on setting
            if self.config.get('show_click_spot', True):
                if self.is_active:
                    self.click_spot_overlay.show()
            else:
                self.click_spot_overlay.hide()
            
            # Handle autostart
            if self.config.get('autostart'):
                self.enable_autostart()
            else:
                self.disable_autostart()
    
    def reset_to_defaults(self):
        """Reset all settings to default values."""
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            None,
            "Reset to Defaults",
            "This will reset all settings to their default values. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Reset to default config
            self.config = self.DEFAULT_CONFIG.copy()
            self.save_config()
            self.overlay.update_config(self.config)
            
            QMessageBox.information(
                None,
                "Reset Complete",
                "Settings have been reset to defaults."
            )
    
    def enable_autostart(self):
        """Add to Windows startup."""
        if sys.platform != 'win32':
            return
        import winreg
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE
            )
            winreg.SetValueEx(key, "KeyVisualizer", 0, winreg.REG_SZ, sys.executable)
            winreg.CloseKey(key)
        except Exception:
            pass
    
    def disable_autostart(self):
        """Remove from Windows startup."""
        if sys.platform != 'win32':
            return
        import winreg
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE
            )
            winreg.DeleteValue(key, "KeyVisualizer")
            winreg.CloseKey(key)
        except Exception:
            pass
    
    def quit_app(self):
        """Clean shutdown."""
        self.keyboard_listener.stop()
        self.mouse_listener.stop()
        self.overlay.hide()
        self.click_spot_overlay.hide()
        self.save_config()
        QApplication.quit()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")
    
    # Check if system tray is available
    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(
            None, "Error",
            "System tray is not available on this system."
        )
        sys.exit(1)
    
    visualizer = KeyVisualizerApp()
    visualizer.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
