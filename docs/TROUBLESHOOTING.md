# 🛠️ Troubleshooting Guide

This guide covers common issues you might encounter while installing or using the ShadowFramework and provides solutions to resolve them.

---

## 🐍 Python & Dependencies

### `ImportError: No module named '...'`
- **Cause**: A required Python library is not installed in the current environment.
- **Solution**: Ensure you are in the virtual environment and run:
  ```bash
  pip install -r requirements.txt
  ```

### `ModuleNotFoundError: No module named 'rich'`
- **Cause**: The `rich` library, which powers the UI, is missing.
- **Solution**: `pip install rich`

---

## 🛠️ External Tool Issues

### `nmap` not found
- **Cause**: The scanner modules require `nmap` to be installed on the host system.
- **Solution**: 
  - Ubuntu/Debian: `sudo apt install nmap`
  - Arch: `sudo pacman -S nmap`

### `adb` connection failed
- **Cause**: The Android modules cannot communicate with the device or emulator.
- **Solution**:
  - Ensure Developer Options and USB Debugging are enabled on the device.
  - Run `adb devices` to check for connected devices.
  - Try restarting the adb server: `adb kill-server && adb start-server`.

### `msfvenom` or `msfconsole` issues
- **Cause**: Metasploit is not installed or not in the system's PATH.
- **Solution**: Install Metasploit Framework and verify by running `msfconsole -v` in your terminal.

---

## 🌐 Network & Permissions

### `Permission Denied` when running modules
- **Cause**: Some modules (like low-level port scanners) require root privileges.
- **Solution**: Try running the framework with `sudo` (though usage within a venv is preferred):
  ```bash
  sudo ./venv/bin/python main.py
  ```

### Module fails to connect to RHOST
- **Cause**: Connectivity issues, firewall blocking, or target is down.
- **Solution**:
  - Ping the target to verify it's reachable.
  - Check local and remote firewall rules.
  - Ensure you have specified the correct `RHOST` and `RPORT`.

---

## 📜 Logging
If you encounter an unhandled exception, check the logs for detailed error messages:
- `logs/error.log`: Contains stack traces for crashes.
- `logs/framework.log`: General framework activity.
