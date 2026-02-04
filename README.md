# KeyVisualizer

A lightweight on-screen key display for tutorials and recordings. Shows pressed keys in a sleek overlay at the bottom of your screen with the same dark, modern style as the AirCube tray app.

## Features

- **Real-time key display** - Shows keys as you press them with smooth fade-out animation
- **Key combinations** - Displays shortcuts like `Ctrl+S`, `Alt+Tab`, `Ctrl+Shift+N` properly
- **Highly configurable** - Customize colors, fonts, sizes, positioning, and more
- **Flexible positioning** - Place overlay at top/bottom, left/center/right of screen
- **Preset themes** - Quick switch between Dark, Light, Minimal, and Colorful themes
- **System tray integration** - Runs quietly in the background
- **Click-through overlay** - Never interferes with your work
- **Windows startup** - Optional auto-start with Windows

## Installation

### From Source

1. Install Python 3.8 or higher
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python keyVisualizer.py
   ```

### Standalone Executable

1. Download the latest release from the releases page
2. Run `KeyVisualizer.exe`

## Building the Executable

### Option 1: Just the EXE

To build a standalone `.exe` file:

```bash
python build_exe.py
```

The executable will be created in the `dist` folder.

### Option 2: Full Windows Installer (Recommended)

To build a complete Windows installer with shortcuts, startup options, and uninstaller:

1. **Install Inno Setup** (one-time setup):
   - Download from [https://jrsoftware.org/isdl.php](https://jrsoftware.org/isdl.php)
   - Install with default options

2. **Build the installer**:
   ```bash
   python build_installer.py
   ```

3. The installer will be created in the `installer_output` folder as `KeyVisualizer_Setup_v1.0.2.exe`

The installer will:
- Install KeyVisualizer to Program Files
- Create Start Menu shortcuts
- Optionally create a Desktop shortcut
- Optionally add to Windows startup
- Create an uninstaller

## Usage

| Action | How |
|--------|-----|
| **Pause/Resume** | Single-click tray icon |
| **Settings** | Double-click tray icon, or right-click > Settings |
| **Quit** | Right-click tray icon > Quit |

## Configuration Options

### Appearance
| Setting | Description |
|---------|-------------|
| Background color | Bubble background color |
| Text color | Key text color |
| Border color | Bubble border color |
| Show border | Toggle border visibility |
| Font family | Choose any installed font |
| Font size | Adjust text size (8-72pt) |
| Font bold | Toggle bold text |

### Bubble Size
| Setting | Description |
|---------|-------------|
| Padding | Space around text inside bubble |
| Min width | Minimum bubble width |
| Border radius | Corner roundness |
| Border width | Border thickness |

### Position
| Setting | Description |
|---------|-------------|
| Horizontal | Left, Center, or Right |
| Vertical | Top or Bottom |
| Vertical margin | Distance from screen edge |
| Horizontal offset | Fine-tune left/right position |

### Behavior
| Setting | Description |
|---------|-------------|
| Overlay height | Height of the display area |
| Bubble spacing | Gap between key bubbles |
| Fade speed | How quickly keys fade out |
| Max keys shown | Limit visible keys |

### Startup
| Setting | Description |
|---------|-------------|
| Start minimized | Launch to tray |
| Start with Windows | Auto-start on login |

## Supported Keys

All keys are captured and displayed, including:
- Letters (A-Z)
- Numbers (0-9, including numpad)
- Function keys (F1-F12)
- Modifiers (Ctrl, Alt, Shift, Win)
- Navigation (Arrows, Home, End, PgUp, PgDn)
- Special keys (Space, Enter, Tab, Backspace, etc.)
- Key combinations (Ctrl+S, Alt+F4, Ctrl+Shift+Esc, etc.)

## Presets

Quick theme presets available:
| Preset | Description |
|--------|-------------|
| Dark (default) | Dark background (#2b2b2b), white text |
| Light | White background, dark text |
| Minimal | Black background, no border |
| Colorful | Blue accent color |

## Requirements

- Windows 10/11
- Python 3.8+ (for running from source)

## Dependencies

- PyQt6 - GUI framework
- pynput - Global keyboard capture
- PyInstaller - Executable building (optional)

## License

Apache License 2.0 - See LICENSE file for details

## Credits

Created by StuckAtPrototype
