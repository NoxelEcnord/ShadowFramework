import requests
from urllib.parse import urljoin, urlparse
from html.parser import HTMLParser
from collections import deque
from rich.console import Console
from rich.table import Table
from utils.logger import log_action

console = Console()

class _LinkParser(HTMLParser):
    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url
        self.links = set()
        self.forms = []
        self._current_form = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and 'href' in attrs:
            href = attrs['href']
            if not href.startswith(('javascript:', 'mailto:', '#')):
                self.links.add(urljoin(self.base_url, href))
        elif tag == 'form':
            self._current_form = {
                'action': urljoin(self.base_url, attrs.get('action', '')),
                'method': attrs.get('method', 'GET').upper(),
                'inputs': []
            }
        elif tag in ('input', 'textarea', 'select') and self._current_form is not None:
            self._current_form['inputs'].append({
                'name': attrs.get('name', ''),
                'type': attrs.get('type', 'text'),
                'value': attrs.get('value', '')
            })

    def handle_endtag(self, tag):
        if tag == 'form' and self._current_form:
            self.forms.append(self._current_form)
            self._current_form = None


class Module:
    MODULE_INFO = {
        'name': 'auxiliary/web_crawler',
        'description': 'Crawl a web application, extract links, forms, and hidden parameters.',
        'options': {
            'URL': 'Starting URL (e.g. http://example.com)',
            'DEPTH': 'Maximum crawl depth [default: 3]',
            'MAX_PAGES': 'Maximum pages to crawl [default: 100]',
            'SAME_DOMAIN': 'Only follow links on the same domain [default: true]',
            'TIMEOUT': 'Request timeout in seconds [default: 5]',
            'USER_AGENT': 'User agent string [default: Mozilla/5.0]',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def run(self):
        start_url = self.framework.options.get('URL')
        depth = int(self.framework.options.get('DEPTH', 3))
        max_pages = int(self.framework.options.get('MAX_PAGES', 100))
        same_domain = self.framework.options.get('SAME_DOMAIN', 'true').lower() == 'true'
        timeout = int(self.framework.options.get('TIMEOUT', 5))
        ua = self.framework.options.get('USER_AGENT', 'Mozilla/5.0 (ShadowFramework)')

        if not start_url:
            console.print("[red][!] URL is required.[/red]")
            return

        base_domain = urlparse(start_url).netloc
        session = requests.Session()
        session.headers['User-Agent'] = ua

        visited = set()
        queue = deque([(start_url, 0)])
        all_forms = []

        console.print(f"[cyan][*] Crawling {start_url} (depth={depth}, max={max_pages})...[/cyan]")
        log_action(f"Web crawl started on {start_url}")

        while queue and len(visited) < max_pages:
            url, current_depth = queue.popleft()
            if url in visited or current_depth > depth:
                continue
            visited.add(url)

            try:
                resp = session.get(url, timeout=timeout, allow_redirects=True)
                console.print(f"  [{'green' if resp.status_code == 200 else 'yellow'}][{resp.status_code}] {url}[/{'green' if resp.status_code == 200 else 'yellow'}]")
                log_action(f"Crawled: {url} [{resp.status_code}]")

                if 'text/html' not in resp.headers.get('Content-Type', ''):
                    continue

                parser = _LinkParser(url)
                parser.feed(resp.text)

                for form in parser.forms:
                    form['page'] = url
                    all_forms.append(form)

                for link in parser.links:
                    if link not in visited:
                        if same_domain and urlparse(link).netloc != base_domain:
                            continue
                        queue.append((link, current_depth + 1))

            except requests.RequestException as e:
                console.print(f"  [red][!] Error on {url}: {e}[/red]")

        console.print(f"\n[green][+] Crawl complete. {len(visited)} pages visited.[/green]")

        if all_forms:
            table = Table(title="Forms Found")
            table.add_column("Page", style="cyan")
            table.add_column("Action", style="green")
            table.add_column("Method", style="yellow")
            table.add_column("Inputs", style="white")
            for f in all_forms:
                inputs = ', '.join(f"{i['name']}({i['type']})" for i in f['inputs'] if i['name'])
                table.add_row(f['page'], f['action'], f['method'], inputs)
                log_action(f"Form on {f['page']}: {f['method']} {f['action']} inputs={inputs}")
            console.print(table)
