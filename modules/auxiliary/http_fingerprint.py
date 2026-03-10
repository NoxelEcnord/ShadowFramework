import requests
import re
from rich.console import Console
from rich.table import Table
from utils.logger import log_action

console = Console()

# Common headers that reveal server/tech info
INTERESTING_HEADERS = ['Server', 'X-Powered-By', 'X-Generator', 'X-AspNet-Version',
                       'X-Runtime', 'X-Framework', 'Via', 'X-Backend-Server']

# CMS fingerprints: {name: [url patterns or header patterns]}
CMS_SIGNATURES = {
    'WordPress': ['/wp-login.php', '/wp-content/', '/wp-includes/'],
    'Joomla': ['/administrator/', '/components/', 'Joomla'],
    'Drupal': ['/sites/default/', 'X-Generator: Drupal', '/misc/drupal.js'],
    'Magento': ['/mage/', '/skin/frontend/', 'Mage.Cookies'],
    'Laravel': ['laravel_session', 'X-Powered-By: PHP'],
    'Django': ['csrfmiddlewaretoken', 'django'],
    'Rails': ['X-Runtime', '_rails_'],
}

WAF_SIGNATURES = {
    'Cloudflare': ['CF-RAY', 'cf-cache-status', '__cfduid'],
    'AWS WAF': ['x-amzn-requestid', 'x-amzn-trace-id'],
    'ModSecurity': ['Mod_Security', 'NAXSI'],
    'Sucuri': ['X-Sucuri-ID', 'sucuri'],
    'Akamai': ['X-Check-Cacheable', 'AkamaiGHost'],
    'Imperva': ['X-Iinfo', 'visid_incap'],
}

class Module:
    MODULE_INFO = {
        'name': 'auxiliary/http_fingerprint',
        'description': 'Fingerprint web server, CMS, WAF, and technology stack.',
        'options': {
            'URL': 'Target URL (e.g. http://example.com)',
            'TIMEOUT': 'Request timeout in seconds [default: 10]',
            'USER_AGENT': 'User agent string [default: ShadowFramework/1.0]',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def _check_path(self, session, base_url, path, timeout):
        try:
            r = session.get(base_url.rstrip('/') + path, timeout=timeout, allow_redirects=True)
            return r.status_code, r.text
        except Exception:
            return None, ''

    def run(self):
        url = self.framework.options.get('URL')
        timeout = int(self.framework.options.get('TIMEOUT', 10))
        ua = self.framework.options.get('USER_AGENT', 'ShadowFramework/1.0 (Recon)')

        if not url:
            console.print("[red][!] URL is required.[/red]")
            return

        session = requests.Session()
        session.headers['User-Agent'] = ua

        console.print(f"[cyan][*] Fingerprinting {url}...[/cyan]")
        log_action(f"HTTP fingerprint on {url}")

        try:
            resp = session.get(url, timeout=timeout, allow_redirects=True)
        except requests.RequestException as e:
            console.print(f"[red][!] Connection error: {e}[/red]")
            return

        # --- Server Headers ---
        table = Table(title="HTTP Headers of Interest")
        table.add_column("Header", style="cyan")
        table.add_column("Value", style="green")
        for h in INTERESTING_HEADERS:
            if h in resp.headers:
                table.add_row(h, resp.headers[h])
                log_action(f"Header {h}: {resp.headers[h]}")
        console.print(table)

        # --- WAF Detection ---
        waf_detected = []
        all_headers = str(resp.headers).lower()
        cookies = str(resp.cookies).lower()
        for waf, sigs in WAF_SIGNATURES.items():
            for sig in sigs:
                if sig.lower() in all_headers or sig.lower() in cookies:
                    waf_detected.append(waf)
                    break
        if waf_detected:
            console.print(f"[bold yellow][!] WAF Detected: {', '.join(waf_detected)}[/bold yellow]")
            log_action(f"WAF detected: {waf_detected}")
        else:
            console.print("[green][+] No WAF signatures detected.[/green]")

        # --- CMS Detection ---
        body = resp.text.lower()
        cms_found = []
        for cms, sigs in CMS_SIGNATURES.items():
            for sig in sigs:
                if sig.lower() in body or sig.lower() in all_headers:
                    cms_found.append(cms)
                    break
            else:
                # Check paths
                for sig in sigs:
                    if sig.startswith('/'):
                        code, _ = self._check_path(session, url, sig, timeout)
                        if code and code < 404:
                            cms_found.append(cms)
                            break

        if cms_found:
            console.print(f"[bold green][+] CMS Detected: {', '.join(set(cms_found))}[/bold green]")
            log_action(f"CMS detected: {cms_found}")
        else:
            console.print("[yellow][!] No known CMS detected.[/yellow]")

        # --- PHP/ASP version from headers ---
        php_match = re.search(r'PHP/([\d.]+)', resp.headers.get('X-Powered-By', ''))
        if php_match:
            console.print(f"[bold cyan][+] PHP Version: {php_match.group(1)}[/bold cyan]")

        # --- robots.txt & sitemap ---
        for path in ['/robots.txt', '/sitemap.xml']:
            code, content = self._check_path(session, url, path, timeout)
            if code == 200:
                console.print(f"\n[green][+] Found {path}:[/green]")
                console.print(content[:800])
