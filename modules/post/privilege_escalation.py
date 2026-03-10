import os
import subprocess
import glob
import stat
from rich.console import Console
from rich.table import Table
from utils.logger import log_action

console = Console()

class Module:
    MODULE_INFO = {
        'name': 'post/privilege_escalation',
        'description': 'Local privilege escalation checker: SUID/SGID, sudo misconfigs, writable /etc/passwd, cron, and kernel.',
        'options': {
            'CHECK_SUID': 'Check for SUID/SGID binaries [default: true]',
            'CHECK_SUDO': 'Check sudo -l misconfigs [default: true]',
            'CHECK_CRON': 'Check writable cron jobs [default: true]',
            'CHECK_PASSWD': 'Check if /etc/passwd is writable [default: true]',
            'CHECK_KERNEL': 'Check kernel version for known vulns [default: true]',
            'CHECK_PATH': 'Check for PATH hijacking opportunities [default: true]',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def _run(self, cmd):
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            return r.stdout.strip()
        except Exception:
            return ''

    def _check_suid(self):
        console.print("\n[cyan][*] Searching for SUID/SGID binaries...[/cyan]")
        suid_bins = self._run("find / -perm /4000 -type f 2>/dev/null").splitlines()
        sgid_bins = self._run("find / -perm /2000 -type f 2>/dev/null").splitlines()

        gtfobins_suid = ['bash','sh','python','python3','perl','ruby','awk','find','nmap',
                         'vim','vi','more','less','man','tar','zip','cp','mv','cat','env',
                         'tee','wget','curl','nc','ncat','socat','dash','ash']

        table = Table(title="SUID Binaries")
        table.add_column("Binary", style="cyan")
        table.add_column("GTFOBins?", style="yellow")

        found_gtfo = False
        for b in suid_bins:
            name = os.path.basename(b).lower()
            is_gtfo = name in gtfobins_suid
            if is_gtfo:
                found_gtfo = True
            table.add_row(b, "[bold red]YES — exploitable![/bold red]" if is_gtfo else "no")
            log_action(f"SUID: {b} {'(GTFOBins)' if is_gtfo else ''}")

        console.print(table)
        if found_gtfo:
            console.print(f"[bold red][!] Exploitable SUID found! Check https://gtfobins.github.io[/bold red]")

    def _check_sudo(self):
        console.print("\n[cyan][*] Checking sudo configuration...[/cyan]")
        output = self._run("sudo -l 2>/dev/null")
        if output:
            console.print(f"[green][+] sudo -l output:[/green]")
            for line in output.splitlines():
                if 'NOPASSWD' in line:
                    console.print(f"  [bold red][!] NOPASSWD entry: {line}[/bold red]")
                    log_action(f"Sudo NOPASSWD: {line}")
                else:
                    console.print(f"  {line}")
        else:
            console.print("[yellow][!] No sudo access or sudo not found.[/yellow]")

    def _check_cron(self):
        console.print("\n[cyan][*] Checking writable cron jobs...[/cyan]")
        cron_paths = ['/etc/crontab', '/etc/cron.d/', '/var/spool/cron/', '/etc/cron.hourly/',
                      '/etc/cron.daily/', '/etc/cron.weekly/', '/etc/cron.monthly/']
        for path in cron_paths:
            if os.path.exists(path):
                if os.access(path, os.W_OK):
                    console.print(f"  [bold red][!] WRITABLE: {path}[/bold red]")
                    log_action(f"Writable cron: {path}")
                    try:
                        content = open(path).read() if os.path.isfile(path) else ''
                        if content:
                            console.print(f"  [yellow]{content[:300]}[/yellow]")
                    except Exception:
                        pass
                else:
                    console.print(f"  [dim]{path} (not writable)[/dim]")

    def _check_passwd(self):
        console.print("\n[cyan][*] Checking /etc/passwd writability...[/cyan]")
        if os.access('/etc/passwd', os.W_OK):
            console.print("[bold red][!] /etc/passwd is WRITABLE! Can add root user:[/bold red]")
            console.print("[yellow]  echo 'hax:$1$hax$TzyKlv0/R/c28R.GAeLw.1:0:0:root:/root:/bin/bash' >> /etc/passwd[/yellow]")
            log_action("PRIVESC: /etc/passwd is writable!")
        else:
            console.print("[green][+] /etc/passwd is not writable (good).[/green]")

    def _check_kernel(self):
        console.print("\n[cyan][*] Checking kernel version...[/cyan]")
        kernel = self._run("uname -r")
        console.print(f"  Kernel: [cyan]{kernel}[/cyan]")
        # Simple version checks
        known_vulns = {
            '3.': ['CVE-2016-5195 (Dirty COW)', 'CVE-2015-1328 (overlayfs)'],
            '4.': ['CVE-2017-1000112 (UFO)', 'CVE-2016-5195 (Dirty COW)'],
            '5.': ['CVE-2022-0847 (Dirty Pipe)', 'CVE-2021-3493 (OverlayFS Ubuntu)'],
        }
        for prefix, cves in known_vulns.items():
            if kernel.startswith(prefix):
                console.print(f"  [yellow][!] Kernel {kernel} may be vulnerable to:[/yellow]")
                for cve in cves:
                    console.print(f"    [red]{cve}[/red]")
                log_action(f"Kernel {kernel} potential privesc CVEs")

    def _check_path(self):
        console.print("\n[cyan][*] Checking PATH for hijacking opportunities...[/cyan]")
        path = os.environ.get('PATH', '').split(':')
        for p in path:
            if p and os.path.isdir(p) and os.access(p, os.W_OK):
                console.print(f"  [bold red][!] Writable PATH dir: {p}[/bold red]")
                log_action(f"Writable PATH directory: {p}")

    def run(self):
        do_suid   = self.framework.options.get('CHECK_SUID', 'true').lower() == 'true'
        do_sudo   = self.framework.options.get('CHECK_SUDO', 'true').lower() == 'true'
        do_cron   = self.framework.options.get('CHECK_CRON', 'true').lower() == 'true'
        do_passwd = self.framework.options.get('CHECK_PASSWD', 'true').lower() == 'true'
        do_kernel = self.framework.options.get('CHECK_KERNEL', 'true').lower() == 'true'
        do_path   = self.framework.options.get('CHECK_PATH', 'true').lower() == 'true'

        console.print(f"[cyan][*] Running privilege escalation checks as {os.getlogin() if hasattr(os, 'getlogin') else 'unknown'}...[/cyan]")
        log_action("Privilege escalation check started")

        if do_suid:   self._check_suid()
        if do_sudo:   self._check_sudo()
        if do_cron:   self._check_cron()
        if do_passwd: self._check_passwd()
        if do_kernel: self._check_kernel()
        if do_path:   self._check_path()

        console.print("\n[bold green][+] Privilege escalation check complete.[/bold green]")
