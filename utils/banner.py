import random
import time
from colorama import Fore, Style

BANNERS = [
    f"""
    ╔═══╗╔═══╗╔═══╗╔═══╗╔═══╗╔═══╗╔═══╗
    ║╔═╗║║╔═╗║║╔═╗║║╔═╗║║╔═╗║║╔═╗║║╔═╗║
    ║║ ║║║║ ║║║║ ║║║║ ║║║║ ║║║║ ║║║║ ║║
    ║╚═╝║║╚═╝║║║ ║║║║ ║║║║ ║║║║ ║║║║ ║║
    ║╔═╗║║╔═╗║║║ ║║║║ ║║║║ ║║║║ ║║║║ ║║
    ║║ ║║║║ ║║║╚═╝║║╚═╝║║╚═╝║║╚═╝║║╚═╝║
    ╚╝ ╚╝╚╝ ╚╝╚═══╝╚═══╝╚═══╝╚═══╝╚═══╝
    """,
    f"""
    ███████╗██╗  ██╗ █████╗ ██████╗ ██████╗ ██╗    ██╗
    ██╔════╝██║  ██║██╔══██╗██╔══██╗██╔══██╗██║    ██║
    ███████╗███████║███████║██║  ██║██║  ██║██║ █╗ ██║
    ╚════██║██╔══██║██╔══██║██║  ██║██║  ██║██║███╗██║
    ███████║██║  ██║██║  ██║██████╔╝██████╔╝╚███╔███╔╝
    ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚═════╝  ╚══╝╚══╝ 
    """,
    f"""
    ░██████╗██╗░░██╗░█████╗░░█████╗░██████╗░██╗░░░██╗
    ██╔════╝██║░░██║██╔══██╗██╔══██╗██╔══██╗╚██╗░██╔╝
    ╚█████╗░███████║███████║██║░░╚═╝██║░░██║░╚████╔╝░
    ░╚═══██╗██╔══██║██╔══██║██║░░██╗██║░░██║░░╚██╔╝░░
    ██████╔╝██║░░██║██║░░██║╚█████╔╝██████╔╝░░░██║░░░
    ╚═════╝░╚═╝░░╚═╝╚═╝░░╚═╝░╚════╝░╚═════╝░░░░╚═╝░░░
    """
]

QUOTES = [
    "Making shells where shells never been before.",
    "In the shadows, we find the light.",
    "Exploit the unseen, control the unknown.",
    "Where there's a shadow, there's a way.",
    "Penetrate the darkness, own the light.",
    "The shadow knows no bounds.",
    "From the shadows, we strike.",
    "Unleash the power of the shadow.",
    "In the realm of shadows, we reign supreme.",
    "The shadow is your ally, and your weapon."
]

def clear_screen():
    """
    Clear the terminal screen.
    """
    print("\033[H\033[J", end="")

def gradual_brightness(banner):
    """
    Gradually increase the brightness of the banner (black -> grey -> white).
    """
    for i in range(0, 256, 16):
        color = f"\033[38;2;{i};{i};{i}m"
        clear_screen()
        print(color + banner + Style.RESET_ALL)
        time.sleep(0.05)

def random_blink(banner, duration=5):
    """
    Blink the banner with random colors for a specified duration.
    """
    start_time = time.time()
    while time.time() - start_time < duration:
        color = f"\033[38;2;{random.randint(0, 255)};{random.randint(0, 255)};{random.randint(0, 255)}m"
        clear_screen()
        print(color + random.choice(BANNERS) + Style.RESET_ALL)

def display_banner():
    """
    Display a random banner with gradual brightness and random blinking.
    """
    banner = random.choice(BANNERS)
    quote = random.choice(QUOTES)

    # Start with a clear black screen
    clear_screen()
    time.sleep(.01)

    # Gradually increase brightness
    gradual_brightness(banner)

    # Blink with random colors for 5 seconds
    random_blink(banner)

    # Display the final banner and quote
    clear_screen()
    print(f"{Fore.YELLOW}{banner}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{quote}{Style.RESET_ALL}\n")
