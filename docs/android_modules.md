# ShadowFramework Android Modules Documentation (2026 Update)

This document provides an overview and usage guide for the 23 new Android-focused modules added to ShadowFramework. These modules target vulnerabilities from 2024 to 2026.

## 🔍 Auxiliary Modules (8)
Reconnaissance and vulnerability scanning for Android devices.

| Module | Description | Target CVE |
| :--- | :--- | :--- |
| `auxiliary/android/qualcomm_gfx_check` | Scans for vulnerable Qualcomm chipsets and patch levels. | CVE-2026-21385 |
| `auxiliary/android/sdcard_leak_checker` | Checks for ExternalStorageProvider path bypass. | CVE-2024-43093 |
| `auxiliary/android/content_provider_scanner` | Identifies exported and insecure content providers. | CVE-2026-0024 |
| `auxiliary/android/f2fs_checker` | Detection for Flash-Friendly File System vulnerabilities. | CVE-2024-43859 |
| `auxiliary/android/adb_pairing_brute` | Brute-forces 6-digit wireless ADB pairing codes. | N/A |
| `auxiliary/android/app_cloning_check` | Audits app backup and migration configurations. | N/A |
| `auxiliary/android/intent_interceptor_db` | Scans for broadcast receivers susceptible to hijacking. | N/A |
| `auxiliary/android/network_scan_cve_2024_36971` | Identifies kernels vulnerable to network route UAF. | CVE-2024-36971 |

---

## 💣 Exploit Modules (7)
Proof-of-Concept exploits for critical Android system and kernel flaws.

| Module | Attack Vector | Severity |
| :--- | :--- | :--- |
| `exploit/android/cve_2026_21385_qualcomm_gfx` | Integer Overflow in Graphics component. | High |
| `exploit/android/cve_2024_43093_path_bypass` | Path bypass to access `/Android/data/`. | High |
| `exploit/android/cve_2026_0006_system_rce` | Remote Code Execution in System process. | Critical |
| `exploit/android/cve_2025_48593_zero_click` | Zero-click RCE via notification handling. | Critical |
| `exploit/android/media_provider_leak` | Info disclosure in MediaProvider component. | High |
| `exploit/android/pkvm_eop` | Privilege Escalation via pKVM hypervisor escape. | Critical |
| `exploit/android/cve_2024_36971_uaf` | Kernel UAF in Network Management. | High |

---

## ⚡ Post-Exploitation Modules (8)
Tools for persistence, data exfiltration, and lateral movement.

| Module | High-Level Functionality | Modern Protection Bypass |
| :--- | :--- | :--- |
| `post/android/accessibility_rat` | Remote control and keylogging via Accessibility API. | Bypasses standard sandboxing. |
| `post/android/activity_hijack` | Real-time phishing by overlaying app activities. | Social Engineering. |
| `post/android/notification_listener` | Intercepts 2FA codes and private notifications. | Non-root access. |
| `post/android/overlay_attack` | Stealthy credential theft via transparent fake login screens. | Requires "Draw Over Apps". |
| `post/android/signal_whatsapp_scraper` | Scrapes end-to-end encrypted chats from UI. | Bypasses E2EE via UI scraping. |
| `post/android/sms_phisher_propagate` | Sends malicious links to the victim's contacts. | Self-propagation. |
| `post/android/data_cloner` | Clones app local storage and session cookies. | Session Hijacking. |
| `post/android/screen_recorder_non_root`| Records screen without root or user prompts (hidden). | MediaProjection bypass. |

---

## 🌐 Browser & File-Based Modules (11)
Exploitation vectors for environments where ADB access is restricted.

### Auxiliary (Recon)
| Module | Description | Vector |
| :--- | :--- | :--- |
| `auxiliary/android/webview_uxss_scanner` | Identifies insecure Chromium/WebView configurations. | UXSS/File Access |
| `auxiliary/android/deeplink_analyzer` | Extracts vulnerable URL schemes and intent filters. | Intent Redirection |
| `auxiliary/android/intent_redirect_check`| Audits for blind intent forwarding in exported components. | IPC Hijacking |

### Exploit (Browser & Files)
| Module | Attack Vector | Target CVE |
| :--- | :--- | :--- |
| `exploit/android/cve_2026_0628_webview_bypass` | Bypass Chrome policy to inject scripts. | CVE-2026-0628 |
| `exploit/android/zip_slip_payload_gen` | Generate path traversal archives for file overwrites. | Zip Slip |
| `exploit/android/deeplink_token_stealer` | Intercept sensitive tokens via URL scheme collision. | Hijacking |
| `exploit/android/uxss_file_disclosure` | Read internal app files via `file://` URIs in WebView. | UXSS |

### Post-Exploitation (Social Engineering)
| Module | Technique | Complexity |
| :--- | :--- | :--- |
| `post/android/webapk_phisher` | Stealthy WebAPK/PWA manifest generator for "authless" installs. | Medium |
| `post/android/system_update_spoofer` | Deceptive system update overlays and notifications. | High Effect |
| `post/android/chrome_history_extractor_uxss` | Scrapes Chrome History database via WebView UXSS. | Tactical |
| `post/android/app_downloader_phish` | Google/Samsung themed social engineering templates. | Logic-based |

---

## 🛠️ Usage Example
To perform a Zip Slip attack:
```bash
shadow> use exploit/android/zip_slip_payload_gen
shadow(exploit/android/zip_slip_payload_gen)> set TARGET_FILE ../../../../data/data/com.target/files/rev.sh
shadow(exploit/android/zip_slip_payload_gen)> run
[+] Payload created: exploit.zip
```
