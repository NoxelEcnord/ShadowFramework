import shodan
from rich.console import Console
from rich.table import Table
from utils.logger import log_action

console = Console()

class Module:
    MODULE_INFO = {
        'name': 'auxiliary/shodan_search',
        'description': 'Search for target devices on the internet using Shodan API.',
        'options': {
            'QUERY': 'Shodan search query (e.g., "port:23", "apache")',
            'API_KEY': 'Your Shodan API Key',
            'LIMIT': 'Maximum number of results to display [default: 10]'
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def run(self):
        query = self.framework.options.get('QUERY')
        api_key = self.framework.options.get('API_KEY')
        limit = int(self.framework.options.get('LIMIT', 10))

        if not query or not api_key:
            console.print("[red][!] QUERY and API_KEY are required.[/red]")
            return

        console.print(f"[*] Searching Shodan for: [cyan]{query}[/cyan]...")
        try:
            api = shodan.Shodan(api_key)
            results = api.search(query, limit=limit)

            console.print(f"[green][+] Found {results['total']} total results. Showing top {len(results['matches'])}:[/green]")
            
            table = Table(title=f"Shodan Results: {query}")
            table.add_column("IP", style="cyan")
            table.add_column("Port", style="magenta")
            table.add_column("Org", style="green")
            table.add_column("Location", style="white")

            for result in results['matches']:
                ip = result['ip_str']
                port = str(result['port'])
                org = result.get('org', 'Unknown')
                location = f"{result['location'].get('city', '')}, {result['location'].get('country_name', '')}"
                
                table.add_row(ip, port, org, location)
            
            console.print(table)
            log_action(f"Shodan search for '{query}' returned {len(results['matches'])} results.")

        except shodan.APIError as e:
            console.print(f"[red][!] Shodan API Error: {e}[/red]")
        except Exception as e:
            console.print(f"[red][!] Unexpected Error: {e}[/red]")
