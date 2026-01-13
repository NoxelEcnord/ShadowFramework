"""
Evasion Utility
Provides basic techniques to bypass simple signature-based detection.
"""

import random
import string
from rich.console import Console

console = Console()

class Evasion:
    @staticmethod
    def add_junk_code(script_content):
        """
        Insert random junk comments into a Python script.
        """
        lines = script_content.splitlines()
        obfuscated_lines = []
        
        for line in lines:
            obfuscated_lines.append(line)
            if random.random() > 0.7: # 30% chance to add junk
                junk = ''.join(random.choice(string.ascii_letters) for _ in range(10))
                obfuscated_lines.append(f"# {junk}")
        
        return "\n".join(obfuscated_lines)

    @staticmethod
    def variable_randomization(script_content):
        """
        Simplified variable randomization (placeholder for more complex logic).
        """
        # This is complex to do right without a parser, 
        # but we can simulate it for certain common patterns.
        return script_content.replace("connect", "c_" + ''.join(random.choice(string.digits) for _ in range(3)))
