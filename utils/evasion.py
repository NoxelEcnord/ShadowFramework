"""
ShadowFramework — Evasion Utility
Payload obfuscation, encoding, and anti-detection techniques.
"""
import random
import string
import base64
import re
import struct
import hashlib
from rich.console import Console

console = Console()


class Evasion:

    # ─── Core Encoding ───────────────────────────────────────────
    @staticmethod
    def xor_crypt(data, key):
        """XOR encryption for bytes payloads."""
        if isinstance(key, (str,)):
            key = key.encode()
        if isinstance(data, (str,)):
            data = data.encode()
        return bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])

    @staticmethod
    def rc4_crypt(data, key):
        """RC4 stream cipher for payload encryption."""
        if isinstance(key, str):
            key = key.encode()
        if isinstance(data, str):
            data = data.encode()

        S = list(range(256))
        j = 0
        for i in range(256):
            j = (j + S[i] + key[i % len(key)]) % 256
            S[i], S[j] = S[j], S[i]

        i = j = 0
        out = bytearray()
        for byte in data:
            i = (i + 1) % 256
            j = (j + S[i]) % 256
            S[i], S[j] = S[j], S[i]
            out.append(byte ^ S[(S[i] + S[j]) % 256])
        return bytes(out)

    # ─── String Obfuscation ──────────────────────────────────────
    @staticmethod
    def obfuscate_strings(script_content):
        """Replace string literals with base64-decoded equivalents."""
        def b64_replacer(match):
            original = match.group(0)[1:-1]
            if len(original) < 3:
                return match.group(0)
            encoded = base64.b64encode(original.encode()).decode()
            return f"__import__('base64').b64decode('{encoded}').decode()"

        content = re.sub(r'"([^"\\]*(\\.[^"\\]*)*)"', b64_replacer, script_content)
        content = re.sub(r"'([^'\\]*(\\.[^'\\]*)*)'", b64_replacer, content)
        return content

    @staticmethod
    def hex_encode_strings(script_content):
        """Replace string literals with hex-decoded equivalents."""
        def hex_replacer(match):
            original = match.group(0)[1:-1]
            if len(original) < 3:
                return match.group(0)
            hex_val = original.encode().hex()
            return f"bytes.fromhex('{hex_val}').decode()"

        content = re.sub(r'"([^"\\]*(\\.[^"\\]*)*)"', hex_replacer, script_content)
        return content

    # ─── Code Transformation ─────────────────────────────────────
    @staticmethod
    def add_dead_code(script_content):
        """Insert junk code to change hash and confuse analysis."""
        lines = script_content.splitlines()
        obfuscated = []

        junk_blocks = [
            lambda: f"_{Evasion._rand_name()} = [i**2 for i in range({random.randint(1,5)}) if i > {random.randint(10,20)}]",
            lambda: f"if {random.randint(100,999)} == {random.randint(1000,9999)}: pass",
            lambda: f"for _{Evasion._rand_name()} in range(0): pass",
            lambda: f"_{Evasion._rand_name()} = lambda x: x",
            lambda: f"try:\n    _{Evasion._rand_name()} = {random.random()}\nexcept: pass",
        ]

        for line in lines:
            obfuscated.append(line)
            if random.random() > 0.75 and line.strip() and not line.strip().startswith('#'):
                # Match indentation
                indent = len(line) - len(line.lstrip())
                junk = random.choice(junk_blocks)()
                for jl in junk.split('\n'):
                    obfuscated.append(' ' * indent + jl)

        return '\n'.join(obfuscated)

    @staticmethod
    def randomize_logic(script_content):
        """Wrap script in exec(b64decode(...)) wrapper."""
        encoded = base64.b64encode(script_content.encode()).decode()
        return f"import base64;exec(base64.b64decode('{encoded}'))"

    @staticmethod
    def multi_layer_encode(script_content, layers=3):
        """Apply multiple encoding layers for deeper obfuscation."""
        result = script_content
        for _ in range(layers):
            encoded = base64.b64encode(result.encode()).decode()
            result = f"import base64;exec(base64.b64decode('{encoded}'))"
        return result

    # ─── Variable Renaming ───────────────────────────────────────
    @staticmethod
    def rename_variables(script_content):
        """Rename local variables to random strings (simple heuristic)."""
        # Find simple variable assignments
        var_map = {}
        lines = script_content.splitlines()
        result = []

        for line in lines:
            match = re.match(r'^(\s*)([a-z_][a-z0-9_]*)\s*=', line)
            if match and match.group(2) not in ('self', 'cls', 'True', 'False', 'None'):
                var_name = match.group(2)
                if var_name not in var_map:
                    var_map[var_name] = f"_{Evasion._rand_name()}"

        content = script_content
        # Sort by length (longest first) to avoid partial replacements
        for old, new in sorted(var_map.items(), key=lambda x: -len(x[0])):
            content = re.sub(rf'\b{old}\b', new, content)

        return content

    # ─── Payload Wrapping ────────────────────────────────────────
    @staticmethod
    def python_exec_wrapper(payload_code):
        """Wrap Python payload in exec() with runtime decoding."""
        key = Evasion._rand_name(8)
        encrypted = Evasion.xor_crypt(payload_code.encode(), key.encode())
        b64_data = base64.b64encode(encrypted).decode()
        return f"""import base64
_k='{key}'
_d=base64.b64decode('{b64_data}')
exec(bytes([b^ord(_k[i%len(_k)])for i,b in enumerate(_d)]))"""

    @staticmethod
    def powershell_b64_wrapper(ps_command):
        """Wrap PowerShell command in encoded command form."""
        encoded = base64.b64encode(ps_command.encode('utf-16-le')).decode()
        return f"powershell -NoProfile -NonInteractive -EncodedCommand {encoded}"

    @staticmethod
    def bash_eval_wrapper(bash_command):
        """Base64-encode bash command for eval()."""
        encoded = base64.b64encode(bash_command.encode()).decode()
        return f"eval $(echo {encoded} | base64 -d)"

    # ─── File Hash Manipulation ──────────────────────────────────
    @staticmethod
    def append_junk_bytes(data, size=None):
        """Append random bytes to change file hash."""
        if size is None:
            size = random.randint(16, 256)
        junk = bytes(random.randint(0, 255) for _ in range(size))
        return data + junk

    # ─── Helpers ─────────────────────────────────────────────────
    @staticmethod
    def _rand_name(length=6):
        return ''.join(random.choices(string.ascii_lowercase, k=length))

    @staticmethod
    def describe():
        """Print available evasion techniques."""
        techniques = [
            ("xor_crypt", "XOR encrypt payload bytes"),
            ("rc4_crypt", "RC4 stream cipher encryption"),
            ("obfuscate_strings", "Replace strings with b64 decoded calls"),
            ("hex_encode_strings", "Replace strings with hex decoded calls"),
            ("add_dead_code", "Insert junk code blocks"),
            ("randomize_logic", "Wrap in exec(b64decode(...))"),
            ("multi_layer_encode", "N-layer base64 encoding"),
            ("rename_variables", "Randomize variable names"),
            ("python_exec_wrapper", "XOR+b64 exec() payload wrapper"),
            ("powershell_b64_wrapper", "PowerShell EncodedCommand"),
            ("bash_eval_wrapper", "Bash base64 eval wrapper"),
            ("append_junk_bytes", "Change file hash with padding"),
        ]

        from rich.table import Table
        table = Table(title="Evasion Techniques")
        table.add_column("Method", style="cyan")
        table.add_column("Description", style="white")
        for name, desc in techniques:
            table.add_row(name, desc)
        console.print(table)
