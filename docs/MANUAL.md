# 📖 ShadowFramework Manual

Welcome to the **ShadowFramework** user manual. This guide provides comprehensive instructions on how to use the framework effectively for your security research and penetration testing needs.

---

## 🛠️ Getting Started

Before using the framework, ensure all dependencies are installed as described in the `README.md`.

### Launching the Framework
Run the main script from the root directory:
```bash
python3 main.py
```

---

## 🕹️ Interactive Shell Commands

ShadowFramework uses a premium interactive shell. Below are the core commands:

| Command | Description | Example |
| :--- | :--- | :--- |
| `help` | Display the help menu with all available commands. | `help` |
| `use <module>` | Load a module into the active context. | `use auxiliary/scanner` |
| `options` | Show configuration options for the current module. | `options` |
| `set <KEY> <VAL>` | Set a value for a module option. | `set RHOST 192.168.1.5` |
| `run` / `explode` | Execute the currently loaded module. | `run` |
| `back` | Unload the module and return to the main prompt. | `back` |
| `exit` / `quit` | Exit the ShadowFramework. | `exit` |
| `banner` | Display a fresh ASCII banner. | `banner` |
| `clear` | Clear the terminal screen. | `clear` |

---

## 🧩 Modules Overview

Modules are categorized into three main types:

1.  **Auxiliary**: Scanning, discovery, and utility tools.
2.  **Exploit**: Tools designed to gain access to remote systems.
3.  **Post**: Post-exploitation tools for persistence, data exfiltration, etc.

### Example Workflow: Port Scanning

1.  **Load the module**: `use auxiliary/scanner`
2.  **View options**: `options`
3.  **Set target**: `set RHOST 192.168.1.1`
4.  **Execute**: `run`

---

## ⚙️ Advanced Configuration

### Global Config
Global settings are stored in `config/config.ini`. You can modify this file to change default behaviors like logging levels or default timeout values.

### Module Persistence
Some modules support loading their state from `.ini` files in `config/module_configs/`. This allows you to pre-define complex setups for repeated tasks.

---

## 🛡️ External Integrations

### Metasploit (MSF) Bridge
The `exploit/msf_exploit` module allows you to run Metasploit modules directly from ShadowFramework.
- **Requirement**: `msfconsole` must be in your PATH.
- **Usage**:
    ```bash
    use exploit/msf_exploit
    set MSF_PATH exploit/unix/ftp/vsftpd_234_backdoor
    set RHOST 10.0.0.15
    run
    ```

### Shodan Search
Search for internet-connected devices using Shodan.
- **Requirement**: A valid Shodan API Key.
- **Usage**:
    ```bash
    use auxiliary/shodan_search
    set API_KEY <your_key>
    set QUERY "apache"
    run
    ```

---

## 📂 Loot & Data
Data exfiltrated or gathered during sessions is stored in the `loot/` directory. Check `loot/exfiltrated_data/` for files retrieved from targets.
