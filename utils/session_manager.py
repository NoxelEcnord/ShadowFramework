import os
from colorama import Fore, Style

class SessionManager:
    def __init__(self, db_manager):
        """
        Initialize the session manager.

        Args:
            db_manager: Database manager instance.
        """
        self.db_manager = db_manager
        self.devices = {}  # Dictionary of devices: {id: {'ip': '192.168.1.1', 'serial': 'abc123', 'rooted': False}}
        self.sessions = []  # List of active sessions

    def add_device(self, ip_address, serial, rooted=False):
        """
        Add a new device to the session manager.

        Args:
            ip_address: The device IP address.
            serial: The device serial number.
            rooted: Whether the device is rooted.

        Returns:
            The device ID (e.g., #1, #2).
        """
        device_id = f"#{len(self.devices) + 1}"
        self.devices[device_id] = {
            'ip': ip_address,
            'serial': serial,
            'rooted': rooted
        }
        print(f"{Fore.GREEN}[+] Added device: {device_id} ({ip_address}){Style.RESET_ALL}")
        return device_id

    def get_devices(self):
        """
        Get a list of connected devices.

        Returns:
            A list of device IDs and their details.
        """
        return self.devices

    def add_session(self, device_id, module_name, output):
        """
        Add a new session to the session manager.

        Args:
            device_id: The device ID.
            module_name: The module name.
            output: The module output.
        """
        if device_id not in self.devices:
            print(f"{Fore.RED}[!] Device not found: {device_id}{Style.RESET_ALL}")
            return

        session_id = len(self.sessions) + 1
        session = {
            'id': session_id,
            'device_id': device_id,
            'module_name': module_name,
            'output': output
        }
        self.sessions.append(session)
        print(f"{Fore.GREEN}[+] Added session: {session_id} ({module_name}){Style.RESET_ALL}")

    def get_sessions(self):
        """
        Get a list of active sessions.

        Returns:
            A list of active sessions.
        """
        return self.sessions

    def get_device_info(self, device_id):
        """
        Get information about a specific device.

        Args:
            device_id: The device ID.

        Returns:
            A dictionary containing device information.
        """
        return self.devices.get(device_id)

    def list_devices(self):
        """
        List all connected devices.
        """
        if not self.devices:
            print(f"{Fore.YELLOW}[!] No devices connected.{Style.RESET_ALL}")
            return

        print(f"{Fore.CYAN}[+] Connected devices:{Style.RESET_ALL}")
        for device_id, info in self.devices.items():
            print(f"  {device_id}: {info['ip']} (Serial: {info['serial']}, Rooted: {info['rooted']})")

    def list_sessions(self):
        """
        List all active sessions.
        """
        if not self.sessions:
            print(f"{Fore.YELLOW}[!] No active sessions.{Style.RESET_ALL}")
            return

        print(f"{Fore.CYAN}[+] Active sessions:{Style.RESET_ALL}")
        for session in self.sessions:
            print(f"  Session {session['id']}: Device {session['device_id']}, Module {session['module_name']}")

    def close_session(self, session_id):
        """
        Close an active session.

        Args:
            session_id: The session ID.
        """
        for session in self.sessions:
            if session['id'] == session_id:
                self.sessions.remove(session)
                print(f"{Fore.GREEN}[+] Closed session: {session_id}{Style.RESET_ALL}")
                return
        print(f"{Fore.RED}[!] Session not found: {session_id}{Style.RESET_ALL}")
