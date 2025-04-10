import nmap
from colorama import Fore, Style
from utils.logger import log_action

class Module:
    MODULE_INFO = {
        'name': 'auxiliary/scanner',
        'description': 'Perform a comprehensive scan of a target device using Nmap (all ports, services, and OS detection).',
        'options': {
            'RHOST': 'Target IP address',
            'RPORT': 'Target port or port range (e.g., 80 or 1-1000) [default: 1-65535]',
            'TIMEOUT': 'Scan timeout in seconds [default: 1]',
            'SERVICE_SCAN': 'Perform service detection [default: true]',
            'OS_DETECTION': 'Perform OS detection [default: true]'
        }
    }

    def __init__(self, framework):
        """
        Initialize the scanner module.

        Args:
            framework: The framework instance.
        """
        self.framework = framework
        self.run = run
        self.nm = nmap.PortScanner()

    def run(self):
        """
        Run the comprehensive Nmap scan (all ports, services, and OS detection).
        """
        try:
            # Get module options
            rhost = self.framework.options.get('RHOST')
            rport = self.framework.options.get('RPORT', '1-65535')  # Default to all ports
            timeout = self.framework.options.get('TIMEOUT', '1')
            service_scan = self.framework.options.get('SERVICE_SCAN', 'true').lower() == 'true'
            os_detection = self.framework.options.get('OS_DETECTION', 'true').lower() == 'true'

            # Validate RHOST
            if not rhost:
                print(f"{Fore.RED}[!] RHOST is required.{Style.RESET_ALL}")
                return

            # Build Nmap arguments
            scan_args = f"-p {rport} --open -T{timeout}"
            if service_scan:
                scan_args += " -sV"  # Enable service detection
            if os_detection:
                scan_args += " -O"   # Enable OS detection

            # Run Nmap scan
            print(f"{Fore.CYAN}[*] Scanning {rhost} (ports {rport})...{Style.RESET_ALL}")
            log_action(f"Starting Nmap scan on {rhost}:{rport} with args: {scan_args}")

            # Perform the scan
            self.nm.scan(hosts=rhost, arguments=scan_args)

            # Check if the scan was successful
            if not self.nm.all_hosts():
                print(f"{Fore.RED}[!] No hosts found.{Style.RESET_ALL}")
                log_action(f"No hosts found during Nmap scan on {rhost}", level="WARNING")
                return

            # Display and log results
            for host in self.nm.all_hosts():
                print(f"{Fore.GREEN}[+] Host: {host}{Style.RESET_ALL}")
                log_action(f"Scan results for {host}")

                # Host state
                host_state = self.nm[host].state()
                print(f"  State: {Fore.GREEN if host_state == 'up' else Fore.RED}{host_state}{Style.RESET_ALL}")
                log_action(f"Host {host} is {host_state}")

                # OS detection results
                if os_detection and 'osmatch' in self.nm[host]:
                    print(f"  OS Detection:")
                    for os_match in self.nm[host]['osmatch']:
                        print(f"    {os_match['name']} (Accuracy: {os_match['accuracy']}%)")
                        log_action(f"OS detected: {os_match['name']} (Accuracy: {os_match['accuracy']}%)")

                # Port and service results
                for proto in self.nm[host].all_protocols():
                    print(f"  Protocol: {proto}")
                    log_action(f"Protocol {proto} found on {host}")

                    ports = self.nm[host][proto].keys()
                    for port in ports:
                        state = self.nm[host][proto][port]['state']
                        service = self.nm[host][proto][port]['name']
                        product = self.nm[host][proto][port].get('product', '')
                        version = self.nm[host][proto][port].get('version', '')
                        print(f"    Port: {port}/{proto} - {state} ({service} {product} {version})")
                        log_action(f"Port {port}/{proto} is {state} ({service} {product} {version})")

        except nmap.PortScannerError as e:
            print(f"{Fore.RED}[!] Nmap error: {e}{Style.RESET_ALL}")
            log_action(f"Nmap error: {e}", level="ERROR")
        except Exception as e:
            print(f"{Fore.RED}[!] Error during scanning: {e}{Style.RESET_ALL}")
            log_action(f"Scan error: {e}", level="ERROR")
