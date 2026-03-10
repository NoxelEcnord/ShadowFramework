import os
import time
import subprocess
from pathlib import Path
from rich.console import Console
from utils.logger import log_action

console = Console()

class Module:
    MODULE_INFO = {
        'name': 'post/screenshot',
        'description': 'Capture the current screen and save to the loot directory.',
        'options': {
            'OUTPUT': 'Output file path [default: loot/screenshot_<timestamp>.png]',
            'DELAY': 'Delay before capture in seconds [default: 0]',
            'METHOD': 'Capture method: auto, scrot, gnome, xwd, import [default: auto]',
            'DISPLAY': 'X display to capture [default: :0]',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def _capture(self, output, display, method):
        env = os.environ.copy()
        env['DISPLAY'] = display

        methods = {
            'scrot':  ['scrot', '-z', output],
            'import': ['import', '-window', 'root', output],  # ImageMagick
            'gnome':  ['gnome-screenshot', '-f', output],
            'xwd':    None,  # handled separately
        }

        if method == 'auto':
            for m in ['scrot', 'import', 'gnome']:
                if subprocess.run(['which', methods[m][0]], capture_output=True).returncode == 0:
                    method = m
                    break
            else:
                method = 'xwd'

        if method == 'xwd':
            # xwd + convert
            raw = output.replace('.png', '.xwd')
            r1 = subprocess.run(['xwd', '-root', '-silent', '-out', raw], env=env, capture_output=True)
            if r1.returncode == 0:
                subprocess.run(['convert', raw, output], capture_output=True)
                os.remove(raw)
                return True, 'xwd+convert'
            return False, 'xwd failed'

        cmd = methods.get(method)
        if not cmd:
            return False, f'Unknown method: {method}'

        result = subprocess.run(cmd, env=env, capture_output=True)
        return result.returncode == 0, method

        # Fallback: PIL/Pillow
    def _capture_pil(self, output):
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab()
            img.save(output)
            return True
        except Exception:
            return False

    def run(self):
        ts = int(time.time())
        output = self.framework.options.get('OUTPUT', f'loot/screenshot_{ts}.png')
        delay = float(self.framework.options.get('DELAY', 0))
        method = self.framework.options.get('METHOD', 'auto')
        display = self.framework.options.get('DISPLAY', ':0')

        Path('loot').mkdir(exist_ok=True)

        if delay > 0:
            console.print(f"[cyan][*] Waiting {delay}s before capture...[/cyan]")
            time.sleep(delay)

        console.print(f"[cyan][*] Capturing screen → {output}...[/cyan]")
        log_action(f"Screenshot capture to {output}")

        ok, used = self._capture(output, display, method)
        if ok and os.path.exists(output):
            size = os.path.getsize(output)
            console.print(f"[bold green][+] Screenshot saved: {output} ({size} bytes) via {used}[/bold green]")
            log_action(f"Screenshot saved: {output}")
        else:
            console.print("[yellow][!] System screenshot tools failed. Trying PIL/Pillow...[/yellow]")
            if self._capture_pil(output):
                console.print(f"[bold green][+] Screenshot saved via PIL: {output}[/bold green]")
            else:
                console.print("[red][!] Screenshot failed. Install scrot, imagemagick, or pillow.[/red]")
                console.print("[dim]  sudo apt install scrot     OR     pip install Pillow[/dim]")
