# 🌑 ShadowFramework v2.0

![Shadow Banner](https://raw.githubusercontent.com/NoxelEcnord/ShadowFramework/main/assets/banner.png)

**ShadowFramework** is a professional-grade, modular penetration testing framework developed by **Ecnord**. It is designed for security researchers and red teamers, providing a robust suite for network scanning, target exploitation, and advanced post-exploitation—especially focusing on Android ecosystem vulnerabilities.

---

## ⚡ Quick Start

```bash
python3 main.py
```

```text
  ███████╗██╗  ██╗ █████╗ ██████╗  ██████╗ ██╗    ██╗
  ██╔════╝██║  ██║██╔══██╗██╔══██╗██╔═══██╗██║    ██║
  ███████╗███████║███████║██║  ██║██║   ██║██║ █╗ ██║
  ╚════██║██╔══██║██╔══██║██║  ██║██║   ██║██║███╗██║
  ███████║██║  ██║██║  ██║██████╔╝╚██████╔╝╚███╔███╔╝
  ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝  ╚═════╝  ╚══╝╚══╝
  ⚡ ShadowFramework ready — 81 commands loaded.
```

---

## 🚀 Key Features

- **81+ Professional Modules**: Integrated tools for full engagement lifecycle.
- **Android Specialist**: Real-world exploits for CVE-2024/2025 Android vulnerabilities.
- **Encrypted C2**: Full Command & Control server with TLS-encrypted beacons and agents.
- **Modern Shell UI**: Interactive CLI with tab-completion, history, and `rich` visual formatting.
- **Advanced Evasion**: 12+ built-in obfuscation techniques (RC4, XOR, Multi-layer B64, Junk code).
- **Engagement Reporting**: Automatic generation of HTML, PDF, and JSON reports.

---

## 🛠️ Installation

### 1. Requirements
Ensure you have Python 3.10+ and the following system tools:
- `adb`: For Android modules.
- `nmap`: For network discovery.
- `msfvenom`: For payload generation.
- `wkhtmltopdf`: Optional, for PDF report generation.

### 2. Setup
```bash
git clone https://github.com/NoxelEcnord/ShadowFramework.git
cd ShadowFramework
pip install -r requirements.txt
```

---

## 📖 Module Library

| Category | Modules | Key Tools |
| :--- | :--- | :--- |
| **Exploit** | 22 | EternalBlue, Log4Shell, Android Zero-Click (CVE-2025), UXSS, ZipSlip |
| **Post-Ex** | 33 | Accessibility RAT, Signal Scraper, Overlay Attacks, Keyloggers, C2 Beacon |
| **Auxiliary** | 26 | Device Discovery, Shodan Search, ADB Pairing Brute, Subnet Sweep |

---

## 💻 Interaction

### Shell Commands
- `use <module>`: Load a module by name or index.
- `set <option> <value>`: Configure parameters.
- `run` / `exploit`: Execute the current task.
- `loot`: Browse or clean collected data.
- `report`: Generate a summary of the engagement.
- `back`: Deselect the current module.
- `scopeList` / `scopeAdd`: Manage target devices with auto-assigned codenames (Pulse, Axel, etc.).

### C2 Operations
- `listener`: Start/stop the encrypted C2 server.
- `agents`: List and manage active beacons.
- `generate`: Create payload-ready agents for deployment.

---

## 🛡️ Disclaimer
ShadowFramework is intended for **authorized security testing only**. The developer, **Ecnord**, and contributors are not responsible for any misuse or legal consequences arising from the use of this software.

---

**Developed with 💀 by Ecnord**
