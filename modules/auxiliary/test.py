class Module:
    MODULE_INFO = {
        'name': 'auxiliary/nmap_scanner',
        'description': 'Perform a comprehensive scan of a target device using Nmap (all ports, services, and OS detection).',
        'options': {
            'RHOST': 'Target IP address or range (e.g., 192.168.1.1 or 192.168.1.0/24)',
            'RPORT': 'Target port or port range (e.g., 80 or 1-1000) [default: 1-65535]',
            'TIMEOUT': 'Scan timeout in seconds [default: 1]',
            'SERVICE_SCAN': 'Perform service detection [default: true]',
            'OS_DETECTION': 'Perform OS detection [default: true]'
        }
    }

    def __init__(self, framework):
        self.framework = framework
        self.nm = nmap.PortScanner()

    def run(self):
        print("[+] Running")
