import subprocess
from colorama import Fore, Style

class ADBManager:
    def __init__(self, device_id=None):
        """
        Initialize the ADBManager.

        Args:
            device_id: The ID of the device to connect to.
        """
        self.device_id = device_id

    def get_devices(self):
        """
        Get a list of connected devices.
        """
        try:
            result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
            devices = result.stdout.strip().split('\n')[1:]
            return [line.split('\t')[0] for line in devices]
        except Exception as e:
            print(f'{Fore.RED}[!] Error getting devices: {e}{Style.RESET_ALL}')
            return []

    def execute_shell_command(self, command):
        """
        Execute a shell command on the device.
        """
        try:
            if self.device_id:
                result = subprocess.run(['adb', '-s', self.device_id, 'shell', command], capture_output=True, text=True)
            else:
                result = subprocess.run(['adb', 'shell', command], capture_output=True, text=True)
            return result.stdout.strip()
        except Exception as e:
            print(f'{Fore.RED}[!] Error executing command: {e}{Style.RESET_ALL}')
            return None

    def push_file(self, local_path, remote_path):
        """
        Push a file to the device.
        """
        try:
            if self.device_id:
                subprocess.run(['adb', '-s', self.device_id, 'push', local_path, remote_path])
            else:
                subprocess.run(['adb', 'push', local_path, remote_path])
            print(f'{Fore.GREEN}[+] File pushed successfully.{Style.RESET_ALL}')
        except Exception as e:
            print(f'{Fore.RED}[!] Error pushing file: {e}{Style.RESET_ALL}')

    def pull_file(self, remote_path, local_path):
        """
        Pull a file from the device.
        """
        try:
            if self.device_id:
                subprocess.run(['adb', '-s', self.device_id, 'pull', remote_path, local_path])
            else:
                subprocess.run(['adb', 'pull', remote_path, local_path])
            print(f'{Fore.GREEN}[+] File pulled successfully.{Style.RESET_ALL}')
        except Exception as e:
            print(f'{Fore.RED}[!] Error pulling file: {e}{Style.RESET_ALL}')
