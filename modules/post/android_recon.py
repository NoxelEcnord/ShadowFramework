import subprocess
from pathlib import Path
from rich.console import Console
from rich.table import Table
from utils.logger import log_action

console = Console()

def _adb(device_id, *args):
    cmd = ['adb', '-s', device_id] + list(args)
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.stdout.strip(), r.stderr.strip()

class Module:
    MODULE_INFO = {
        'name': 'post/android_recon',
        'description': 'Comprehensive Android device recon via ADB: device info, installed apps, accounts, network.',
        'options': {
            'DEVICE_ID': 'Target device serial (run: adb devices)',
            'OUTPUT_DIR': 'Directory to save results [default: loot/android/]',
            'LIST_APPS': 'List all installed packages [default: true]',
            'LIST_ACCOUNTS': 'List synced accounts (requires root) [default: true]',
            'DUMP_NETWORK': 'Dump network config, ARP, connections [default: true]',
            'DUMP_LOCATION': 'Attempt to get last GPS coordinates [default: true]',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def _shell(self, dev, cmd):
        out, _ = _adb(dev, 'shell', cmd)
        return out

    def run(self):
        device_id = self.framework.options.get('DEVICE_ID', '')
        output_dir = self.framework.options.get('OUTPUT_DIR', 'loot/android')
        list_apps = self.framework.options.get('LIST_APPS', 'true').lower() == 'true'
        list_accs = self.framework.options.get('LIST_ACCOUNTS', 'true').lower() == 'true'
        dump_net  = self.framework.options.get('DUMP_NETWORK', 'true').lower() == 'true'
        dump_loc  = self.framework.options.get('DUMP_LOCATION', 'true').lower() == 'true'

        if not device_id:
            console.print("[red][!] DEVICE_ID is required (run: adb devices).[/red]")
            return

        Path(output_dir).mkdir(parents=True, exist_ok=True)
        log_action(f"Android recon on {device_id}")

        # --- Device Info ---
        console.print(f"\n[cyan][*] Device Info — {device_id}[/cyan]")
        props = {
            'Model':        'ro.product.model',
            'Brand':        'ro.product.brand',
            'Android Ver':  'ro.build.version.release',
            'SDK Level':    'ro.build.version.sdk',
            'Build':        'ro.build.display.id',
            'Serial':       'ro.serialno',
            'IMEI':         'ril.serialnumber',
            'WiFi MAC':     'wifi.interface',
        }
        table = Table(title="Device Info")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        info_lines = []
        for label, prop in props.items():
            val = self._shell(device_id, f'getprop {prop}')
            table.add_row(label, val or '—')
            info_lines.append(f"{label}: {val}")
        console.print(table)

        with open(f"{output_dir}/device_info.txt", 'w') as f:
            f.write('\n'.join(info_lines))

        # --- Installed Apps ---
        if list_apps:
            console.print(f"\n[cyan][*] Installed packages...[/cyan]")
            pkgs = self._shell(device_id, 'pm list packages -f')
            console.print(pkgs[:2000] if pkgs else "[yellow]No response.[/yellow]")
            with open(f"{output_dir}/packages.txt", 'w') as f:
                f.write(pkgs)
            console.print(f"[green][+] {pkgs.count('package:')} packages → {output_dir}/packages.txt[/green]")
            log_action(f"Installed packages dumped from {device_id}")

        # --- Accounts ---
        if list_accs:
            console.print(f"\n[cyan][*] User accounts (may need root)...[/cyan]")
            accounts = self._shell(device_id, 'dumpsys account')
            if accounts:
                # Filter relevant lines
                acct_lines = [l for l in accounts.splitlines() if 'name=' in l.lower() or 'type=' in l.lower()]
                for line in acct_lines[:30]:
                    console.print(f"  [yellow]{line.strip()}[/yellow]")
                with open(f"{output_dir}/accounts.txt", 'w') as f:
                    f.write('\n'.join(acct_lines))
                log_action(f"Accounts dump from {device_id}")
            else:
                console.print("[yellow][!] No account data (may need root).[/yellow]")

        # --- Network Info ---
        if dump_net:
            console.print(f"\n[cyan][*] Network configuration...[/cyan]")
            for cmd, label in [
                ('ip addr', 'IP Addresses'),
                ('ip route', 'Routes'),
                ('cat /proc/net/arp', 'ARP Table'),
                ('netstat -an 2>/dev/null || ss -an', 'Connections'),
                ('getprop dhcp.wlan0.ipaddress', 'WiFi IP'),
                ('getprop dhcp.wlan0.gateway', 'Gateway'),
            ]:
                out = self._shell(device_id, cmd)
                if out:
                    console.print(f"\n[bold cyan]{label}:[/bold cyan]")
                    console.print(out[:500])

        # --- GPS location ---
        if dump_loc:
            console.print(f"\n[cyan][*] Last known GPS location...[/cyan]")
            out = self._shell(device_id, 'dumpsys location | grep -A5 "Last Known"')
            if out:
                console.print(f"[yellow]{out[:400]}[/yellow]")
                log_action(f"GPS dump from {device_id}: {out[:100]}")
            else:
                console.print("[yellow][!] No GPS data available.[/yellow]")

        console.print(f"\n[bold green][+] Android recon complete. Results in: {output_dir}[/bold green]")
