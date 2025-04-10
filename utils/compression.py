import zipfile
from pathlib import Path
from colorama import Fore, Style

def compress_loot(output_file, loot_dir):
    """
    Compress loot files into a .zip archive.

    Args:
        output_file: Path to the output .zip file.
        loot_dir: Path to the directory containing loot files.
    """
    try:
        loot_dir = Path(loot_dir).expanduser()
        if not loot_dir.exists():
            print(f"{Fore.RED}[!] Loot directory not found: {loot_dir}{Style.RESET_ALL}")
            return

        with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in loot_dir.rglob("*"):
                if file.is_file():
                    zipf.write(file, file.relative_to(loot_dir))
                    print(f"{Fore.GREEN}[+] Added to archive: {file}{Style.RESET_ALL}")

        print(f"{Fore.CYAN}[+] Loot compressed: {output_file}{Style.RESET_ALL}")

    except Exception as e:
        print(f"{Fore.RED}[!] Error during compression: {e}{Style.RESET_ALL}")