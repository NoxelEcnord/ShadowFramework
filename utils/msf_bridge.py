import subprocess
import os
from rich.console import Console

console = Console()

class MSFBridge:
    @staticmethod
    def run_module(msf_path, options):
        """
        Execute a metasploit module via msfconsole.
        
        Args:
            msf_path (str): Path to the MSF module (e.g., exploit/windows/smb/ms17_010_eternalblue)
            options (dict): Key-value pairs of module options.
        """
        command_list = [f"use {msf_path}"]
        for key, value in options.items():
            if value:
                command_list.append(f"set {key} {value}")
        
        command_list.append("run")
        command_list.append("exit -y")
        
        # Join into a single execution string for msfconsole -x
        cmds = " ; ".join(command_list)
        
        console.print(f"[*] Starting MSF module: [cyan]{msf_path}[/cyan]...")
        try:
            # We use -q for quiet mode and -x to execute commands
            process = subprocess.Popen(
                ["msfconsole", "-q", "-x", cmds],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Stream output in real-time
            for line in process.stdout:
                console.print(f"[dim blue]|[/dim blue] {line.strip()}")
            
            process.wait()
            if process.returncode == 0:
                console.print("[green][+] MSF module execution finished.[/green]")
            else:
                console.print(f"[red][!] MSF exited with code {process.returncode}[/red]")
                
        except FileNotFoundError:
            console.print("[red][!] Error: msfconsole not found in PATH. Please install Metasploit.[/red]")
        except Exception as e:
            console.print(f"[red][!] Error executing MSF module: {e}[/red]")
