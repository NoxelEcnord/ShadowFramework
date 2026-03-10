"""
ShadowFramework — Bluetooth Proximity Prober
Passive and active discovery of nearby Bluetooth devices.
Fingerprints hardware and attempts to guess OS patch levels.
"""
import subprocess
import re
import time
from rich.console import Console
from rich.table import Table
from utils.logger import log_action

console = Console()

class Module:
    MODULE_INFO = {
        'name': 'auxiliary/scanner/bluetooth/proximity_prober',
        'description': 'Discovers and fingerprints nearby Bluetooth devices (Classic & BLE).',
        'options': {
            'SCAN_TIME': 'Duration of scan in seconds [default: 10]',
            'SCAN_TYPE': 'Scan type (CLASSIC, BLE, BOTH) [default: BOTH]',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def _scan_classic(self, duration):
        console.print("  [cyan]→ Scanning for Bluetooth Classic devices (hcitool)...[/cyan]")
        try:
            # Requires hcitool (BlueZ)
            cmd = ['hcitool', 'scan', '--flush']
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=duration + 5)
            # Scanning ...
            # 	00:11:22:33:44:55	Name
            matches = re.findall(r'([0-9A-F:]{17})\s+(.*)', r.stdout, re.I)
            return [{'mac': m[0], 'name': m[1], 'type': 'Classic'} for m in matches]
        except Exception as e:
            console.print(f"    [red][!] Classic scan failed: {e}[/red]")
            return []

    def _scan_ble(self, duration):
        console.print("  [cyan]→ Scanning for Bluetooth Low Energy (BLE) devices...[/cyan]")
        try:
            # Requires bluetoothctl or hcitool lescan
            # Using bluetoothctl for better modern support
            proc = subprocess.Popen(['bluetoothctl', '--timeout', str(duration), 'scan', 'on'], 
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            time.sleep(duration)
            proc.terminate()
            out, _ = proc.communicate()
            
            # [NEW] Device 00:11:22:33:44:55 Name
            matches = re.findall(r'Device\s+([0-9A-F:]{17})\s+(.*)', out, re.I)
            devices = []
            seen = set()
            for mac, name in matches:
                if mac not in seen:
                    devices.append({'mac': mac, 'name': name, 'type': 'BLE'})
                    seen.add(mac)
            return devices
        except Exception as e:
            console.print(f"    [red][!] BLE scan failed: {e}[/red]")
            return []

    def run(self):
        duration = int(self.framework.options.get('SCAN_TIME', 10))
        scan_mode = self.framework.options.get('SCAN_TYPE', 'BOTH').upper()

        console.print(f"\n[bold cyan]╔══════════════════════════════════════════════════╗[/bold cyan]")
        console.print(f"[bold cyan]║   SHADOW Bluetooth Proximity Engine              ║[/bold cyan]")
        console.print(f"[bold cyan]╚══════════════════════════════════════════════════╝[/bold cyan]")
        log_action(f"Bluetooth proximity scan started (mode={scan_mode})")

        found = []
        if scan_mode in ('CLASSIC', 'BOTH'):
            found.extend(self._scan_classic(duration))
        if scan_mode in ('BLE', 'BOTH'):
            found.extend(self._scan_ble(duration))

        if not found:
            console.print("[yellow][!] No Bluetooth devices found in range.[/yellow]")
            return

        table = Table(title="Nearby Bluetooth Devices")
        table.add_column("MAC Address", style="cyan")
        table.add_column("Name / Alias", style="white")
        table.add_column("Type", style="yellow")
        table.add_column("Est. OS", style="green")

        for dev in found:
            # Basic fingerprinting logic
            est_os = "Unknown"
            name = dev['name'].lower()
            if any(x in name for x in ['android', 'pixel', 'samsung', 'galaxy', 'a54', 'a34']):
                est_os = "Android (High Prob)"
            elif any(x in name for x in ['iphone', 'ipad', 'apple']):
                est_os = "iOS"
            elif any(x in name for x in ['buds', 'pods', 'speaker', 'sony', 'jbl']):
                est_os = "Audio Peripheral"

            table.add_row(dev['mac'], dev['name'], dev['type'], est_os)
            log_action(f"Detected BT device: {dev['mac']} ({dev['name']}) type={dev['type']}")

        console.print(table)
        console.print(f"\n[bold green][+] Discovery complete. Found {len(found)} devices.[/bold green]")
