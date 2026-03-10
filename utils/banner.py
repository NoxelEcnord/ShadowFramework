import random
import time
from colorama import Fore, Style

# Style 1: Bold filled block — "SHADOW" in big blocky font
_BANNER1 = r"""
  ███████╗██╗  ██╗ █████╗ ██████╗  ██████╗ ██╗    ██╗
  ██╔════╝██║  ██║██╔══██╗██╔══██╗██╔═══██╗██║    ██║
  ███████╗███████║███████║██║  ██║██║   ██║██║ █╗ ██║
  ╚════██║██╔══██║██╔══██║██║  ██║██║   ██║██║███╗██║
  ███████║██║  ██║██║  ██║██████╔╝╚██████╔╝╚███╔███╔╝
  ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝  ╚═════╝  ╚══╝╚══╝
"""

# Style 2: Small double-line box letters
_BANNER2 = r"""
  ╔═╗ ╦ ╦ ╔═╗ ╔╦╗ ╔═╗ ╦ ╦
  ╚═╗ ╠═╣ ╠═╣  ║║ ║ ║ ║║║
  ╚═╝ ╩ ╩ ╩ ╩ ═╩╝ ╚═╝ ╚╩╝
        [ F R A M E W O R K ]
"""

# Style 3: Dot/mixed style
_BANNER3 = r"""
   .▄▄ · ▄ •▄  ▄▄▄· ·▄▄▄▄  ▄▄▄   ▄▄▌ ▌ ▐·
   ▐█ ▀. █▌▄▌▪▐█ ▀█ ██▪ ██ ▀▄ █·  ██· █▌▐█▌
   ▄▀▀▀█▄▐▀▀▄·▄█▀▀█ ▐█· ▐█▌▐▀▀▄   ██▪▐█▐▐▌
   ▐█▄▪▐█▐█.█▌▐█ ▪▐▌██. ██ ▐█•█▌  ▐█▌██▐█▌
    ▀▀▀▀ ·▀  ▀ ▀  ▀ ▀▀▀▀▀• .▀  ▀   ▀▀▀▀ ▀▪
"""

BANNERS = [_BANNER1, _BANNER2, _BANNER3]

QUOTES = [
    # Atmosphere
    "In the realm of shadows, we reign supreme.",
    "In the shadows, we find the light.",
    "From the shadows, we strike.",
    "Where there's a shadow, there's a way.",
    "The shadow knows no bounds.",
    "The shadow is your ally, and your weapon.",
    "Unleash the power of the shadow.",
    # Hacker culture
    "Root is a privilege. Persistence is a lifestyle.",
    "Every system has a door. We find the window.",
    "We don't hack systems. We liberate them.",
    "Your firewall is not a fortress, it's a speed bump.",
    "Silence is the loudest payload.",
    "In anonymity we trust.",
    "The best exploit is the one they never patch.",
    "Access granted. Auditors: denied.",
    "Penetrate. Persist. Pivot. Prevail.",
    "Not all who wander are lost — some are enumerating.",
    "A clean shell leaves no logs.",
    "The only true security is obscurity... and we found you.",
    "0x41414141 — where art meets overflow.",
    "We came, we scanned, we conquered.",
    "Exploit the unseen, control the unknown.",
    "Making shells where shells never been before.",
    "Penetrate the darkness, own the light.",
]


def clear_screen():
    """Clear the terminal screen."""
    print("\033[H\033[J", end="")


def gradual_brightness(banner):
    """Gradually increase the brightness of the banner (black -> grey -> white)."""
    for i in range(0, 256, 16):
        color = f"\033[38;2;{i};{i};{i}m"
        clear_screen()
        print(color + banner + Style.RESET_ALL)
        time.sleep(0.05)


def random_blink(banner, duration=2):
    """Blink the banner with random colors for a specified duration."""
    start_time = time.time()
    while time.time() - start_time < duration:
        color = f"\033[38;2;{random.randint(0, 255)};{random.randint(0, 255)};{random.randint(0, 255)}m"
        clear_screen()
        print(color + banner + Style.RESET_ALL)
        time.sleep(0.1)


def display_banner():
    """Display a random banner with gradual brightness and random blinking."""
    banner = random.choice(BANNERS)
    quote = random.choice(QUOTES)

    # Start with a clear black screen
    clear_screen()
    time.sleep(0.01)

    # Gradually increase brightness
    gradual_brightness(banner)

    # Blink with random colors
    random_blink(banner)

    # Display the final banner and quote
    clear_screen()
    print(f"{Fore.CYAN}{banner}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}  {quote}{Style.RESET_ALL}\n")
