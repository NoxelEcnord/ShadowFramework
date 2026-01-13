# 🌑 ShadowFramework

**ShadowFramework** is a modern, modular penetration testing framework designed for security professionals and researchers. It provides a suite of tools for scanning, exploitation, and post-exploitation, all managed through a premium interactive shell.

---

## 🚀 Features

- **Modern UI**: Powered by the `rich` library for beautiful tables, panels, and status messages.
- **Modular Architecture**: Easily extendable with core modules and user-defined plugins.
- **Advanced Tools**:
    - **Scanning**: Multi-threaded Nmap and SMB enumeration.
    - **Exploitation**: MSFVenom-powered payload generation (EXE, DLL, APK).
    - **Post-Exploitation**: ADB-based Android backdoor installation, persistence via Cron, and data exfiltration.
- **Payload Automation**: Custom Python/Bash reverse shells with optional XOR obfuscation.

---

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/NoxelEcnord/ShadowFramework.git
   cd ShadowFramework
   ```

2. **Setup Virtual Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **External Dependencies**:
    - `nmap`: Required for the scanner modules.
    - `adb`: Required for Android modules.
    - `msfvenom`: Required for binary payload generation.
    - `metasploit-framework`: Required for `exploit/msf_exploit`.
    - `shodan`: Required for `auxiliary/shodan_search` (API key needed).

---

## 📖 Usage

Start the framework:
```bash
python3 main.py
```

### Core Commands
- `help`: Show the help menu.
- `use <module>`: Load a specific module (e.g., `use auxiliary/scanner`).
- `options`: List configurable options for the loaded module.
- `set <option> <value>`: Configure a module option.
- `run`: Execute the loaded module.
- `exit`: Quit the framework.

### Example: Scanning a Target
```bash
shadow> use auxiliary/scanner
shadow(auxiliary/scanner)> set RHOST 192.168.1.1
shadow(auxiliary/scanner)> run
```

---

## 🌐 External Integrations

### Metasploit Bridge
Run any MSF module directly:
```bash
shadow> use exploit/msf_exploit
shadow(exploit/msf_exploit)> set MSF_PATH exploit/multi/handler
shadow(exploit/msf_exploit)> set EXTRA_OPTS PAYLOAD=python/meterpreter/reverse_tcp,LHOST=10.0.0.5
shadow(exploit/msf_exploit)> run
```

### Shodan Intel
Discover targets globally:
```bash
shadow> use auxiliary/shodan_search
shadow(auxiliary/shodan_search)> set API_KEY YOUR_KEY_HERE
shadow(auxiliary/shodan_search)> set QUERY "port:22 OpenSSH"
shadow(auxiliary/shodan_search)> run
```

---

## 🔌 Developer Guide

### Writing a Module
Modules are stored in `modules/`. Each module must be a class named `Module` with a `MODULE_INFO` dictionary.

```python
class Module:
    MODULE_INFO = {
        'name': 'category/my_tool',
        'description': 'Description of my tool',
        'options': {
            'TARGET': 'The target IP'
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def run(self):
        target = self.framework.options.get('TARGET')
        print(f"Running on {target}")
```

---

## ⚖️ License & Disclaimer
This tool is for **educational and authorized testing only**. Unauthorized use against systems you do not have explicit permission to test is illegal and unethical. The developers are not responsible for any misuse.
