from colorama import Fore, Style

class CVEPlugin:
    """
    Base class for all CVE-based plugins.
    """
    def __init__(self, shell):
        self.shell = shell
        self.name = "CVE-XXXX-XXXX"
        self.description = "Description of the CVE"
        self.author = "Author Name"
        self.options = {
            'RHOSTS': {'description': 'The target host(s)', 'required': True, 'value': ''},
            'RPORT': {'description': 'The target port', 'required': True, 'value': ''},
        }

    def run(self):
        """
        Execute the plugin.
        """
        raise NotImplementedError("The run method must be implemented by the plugin.")

    def show_options(self):
        """
        Display the plugin's options.
        """
        print(f"\n{Fore.CYAN}Plugin Options for {self.name}{Style.RESET_ALL}")
        print("========================")
        print(f"  {'Name':<15} {'Description':<40} {'Required':<10} {'Value'}")
        print(f"  {'-'*15} {'-'*40} {'-'*10} {'-'*20}")
        for name, option in self.options.items():
            print(f"  {name:<15} {option['description']:<40} {str(option['required']):<10} {option['value']}")
        print()

    def set_option(self, name, value):
        """
        Set a plugin option.
        """
        if name in self.options:
            self.options[name]['value'] = value
            print(f"{Fore.GREEN}[+] {name} => {value}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}[!] Invalid option: {name}{Style.RESET_ALL}")
