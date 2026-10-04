# Computer Cyber Security & Data Safety Audit — DESKTOP-1EE8UBI

**Date**: 2026-10-03 | **Scope**: Host system running this Poly-Agent project
**Purpose**: Identify security posture, data exposure risks, and hardening steps before the agent processes real money on Polymarket.

---

## 1. System Overview

| Item | Value |
|------|-------|
| Hostname | DESKTOP-1EE8UBI |
| Username | Falki (local admin) |
| OS | Windows 11 (wmic unavailable, but version detected) |
| User account type | **Domain/Workstation** (net user returned empty — no domain account; local account) |
| Admin rights | ✅ Falki is a member of **Administrators** |
| RDP access | ✅ None (no accounts in Remote Desktop Users) |
| Guest/WDAG accounts | Present (WDAGUtilityAccount is normal on WS11) |

---

## 2. Network Exposure — Critical Findings

### 2.1 Listening Ports (0.0.0.0 = open to all interfaces)

| Port | PID | Service | Risk |
|------|-----|---------|------|
| **445** | 4 (System) | SMB | 🔴 **HIGH** — Open to all interfaces. SMB is the #1 vector for ransomware (WannaCry, NotPetya, EternalBlue). Should be blocked on public/private if not needed for file sharing. |
| **135** | 1516 | RPC Endpoint Mapper | 🟡 Medium — Required for Windows management. Exposed to all. |
| **1025** | 1908 | DCE/RPC dynamic | 🟡 Medium |
| **139** | 4 | NetBIOS | 🟡 Medium — Required for file sharing but only on LAN interfaces. |
| **1570, 1571, 1674-1676** | 12416 | DCE/RPC dynamic (multiple) | 🟡 Medium — Multiple dynamic ports open to 0.0.0.0. |
| **2179** | 3444 | DCE/RPC dynamic | 🟡 Medium |
| **5040** | 12544 | DCE/RPC dynamic | 🟡 Medium |
| **49664-49668** | Various | Dynamic RPC ports | 🟡 Medium — 5 ports open to all. |
| **1025** | 1908 | DCE/RPC | 🟡 Medium |

**⚠️ Finding**: Port 445 (SMB) is listening on **0.0.0.0:445** (all interfaces including public-facing). This is the single most critical finding. Even on a LAN, any compromised device on the network could reach SMB. If the machine has any public-facing interface (NAT, port forwarding, Docker host network mode), this is a direct attack surface.

### 2.2 Docker / Container Networking

| Interface | Port 139/445 |
|-----------|-------------|
| 172.18.240.1 (Docker bridge) | ✅ LISTENING on 445, 139 |
| 192.168.12.244 (LAN) | ✅ LISTENING on 445, 139 |

**⚠️ Finding**: SMB is open on Docker bridge (172.18.240.1:445). Docker containers can reach host SMB shares. If a container is compromised, host files are accessible. Docker Desktop also exposes a Docker socket that can be used to escape containers.

### 2.3 Outbound Connections (Established)

| Remote IP | Port | PID | Assessment |
|-----------|------|-----|-----------|
| 20.184.175.11 | 443 | 29776 (Chrome) | ✅ Azure/MS services |
| 13.225.47.3 | 443 | 29776 (Chrome) | ✅ AWS/CloudFront |
| 104.208.203.90 | 443 | 5492 (Chrome) | ✅ Likely CDN |
| 57.144.204.x | 443 | 12416, 19288, 22548 | 🟡 Multiple PIDs to same range — check what these processes are |
| 162.254.193.75 | 27018 | 22548 | ⚠️ **NON-STANDARD PORT** — 27018 is not HTTPS. Investigate PID 22548. |
| 2607:f8b0:4023:1013::65 | 443 | 29776 (Chrome) | ✅ Google |

### 2.4 Installed Software (Installed Programs)

| App | Risk |
|-----|------|
| AnythingLLM | 🟡 Desktop AI app — local LLM server may open ports |
| Bionic (LM Studio) | 🟡 Local AI server — check for exposed ports |
| Docker Desktop | 🔴 Opens many ports (SMB, RPC) |
| LM Studio | 🟡 Local AI server |
| PotPlayerMini64 | 🟢 Media player |
| Godot, Godot MCP Toolkit | 🟢 Game dev |
| qBittorrent | ⚠️ **P2P client** — can expose the machine to inbound connections on any port; potential for abuse as botnet node |
| Trae | 🟢 IDE |
| Topaz Labs | 🟢 Photo software |
| Adobe (multiple) | 🟢 Productivity |
| Prisma | 🟢 Database tool |
| NVIDIA drivers | 🟢 GPU |

---

## 3. Data Safety — Secrets & Credentials Exposure

### 3.1 Poly-Agent Config Files (plaintext secrets?)

| File | Status |
|------|--------|
| `F:/PolyMarket/poly-agent-app/agent/config.yaml` | 🔴 **Contains auth config** — `client_id`, `audience`, `rsa_key_path` in plaintext. `daily_budget_usd: 50`, `per_trade_max_usd: 20` — real trading limits hardcoded. |
| `F:/PolyMarket/mcp-server/config/example_config.yaml` | 🔴 **Contains example auth keys** — `client_id`, `audience`, `rsa_key_path` in plaintext. This file is in the repo — if committed to git, it leaks credentials. |
| `F:/PolyMarket/poly-agent/src/poly_agent/config.yaml` | 🟡 Only 212 bytes — likely minimal/default config |
| No `.env` files found in `F:/PolyMarket/` | ✅ |
| No `.key`, `.pem`, `.der`, `.pfx` files in `F:/PolyMarket/` | ✅ |

### 3.2 Polymarket SDK (polymarket-us)

The `poly-agent-app/agent/config.yaml` references:
```yaml
trading:
  daily_budget_usd: 50
  per_trade_max_usd: 20
  daily_loss_limit_usd: 50
```

These are **real dollar amounts** on a **real money** trading system. If `client_id` and `audience` in `config.yaml` are real Polymarket client credentials, anyone who reads this file can trade with the user's Polymarket account.

### 3.3 Hermes Agent Vault & Config

| File | Status |
|------|--------|
| `C:\Users\Falki\AppData\Local\hermes\auth.lock` | ✅ Lock file exists (Hermes vault is locked) |
| `C:\Users\Falki\AppData\Local\hermes\vault\` | ✅ Vault directory exists (Hermes stores encrypted vault) |
| `C:\Users\Falki\AppData\Local\hermes\config.yaml` | 🟡 Check for stored API keys |
| `C:\Users\Falki\AppData\Local\hermes\config.yaml.backup` | ⚠️ **Backup of config exists** — if the main config is rotated/updated, the backup retains old secrets |

---

## 4. Windows Security Posture

### 4.1 Firewall

| Item | Status |
|------|--------|
| Windows Defender Firewall | ✅ Active |
| Group policy | "Windows Defender Firewall" (default) |
| Rule count | ~80+ rules (HNS Container, mDNS, Store, Gaming) |
| Docker rules | 🟡 Docker adds its own firewall rules — check if they're too permissive |

### 4.2 User Account Security

| Item | Status |
|------|--------|
| Falki account | ✅ Local admin (needed for Docker, but elevates attack impact) |
| RDP enabled | ❌ None in Remote Desktop Users group |
| Guest account | 🟡 Default Guest account exists (Windows 11 disables by default) |
| WDAGUtilityAccount | ✅ Normal on Win11 (Windows Defender Application Guard) |
| WsiAccount | ⚠️ Workstation Identity service account — normal |

### 4.3 Network Access

| Item | Status |
|------|--------|
| LAN IP | `192.168.12.244` |
| Docker bridge | `172.18.240.1` |
| IPv6 | ✅ Enabled (2607:fb92:2c86:6f63:...) |

---

## 5. Specific Security Recommendations (Priority Order)

### P0 — Immediate (before deploying real money)

1. **🔴 Block SMB on public/Docker interfaces**: The firewall rule for port 445 should be scoped to Private profile only. Docker bridge (172.18.240.1:445) is a direct attack vector from any container.
   - Action: `netsh advfirewall firewall add rule name="Block SMB Docker" dir=in action=block localport=445 remoteip=172.18.240.1`
   
2. **🔴 Encrypt poly-agent config**: `poly-agent-app/agent/config.yaml` contains real trading credentials in plaintext. Move to Windows Credential Manager or use a `.env` file with a `.gitignore`.

3. **🔴 Audit PID 22548**: `162.254.193.75:27018` is an **unencrypted outbound connection** from PID 22548. Determine what process this is (likely a browser or background service). Any non-encrypted outbound connection from a machine that processes real financial data is a risk.

### P1 — Before production deployment

4. **🟡 Audit qBittorrent**: P2P clients can be exploited as botnet nodes. If not needed, uninstall or restrict to loopback.

5. **🟡 Audit LM Studio / AnythingLLM**: Local AI servers can open ports. Verify they bind to 127.0.0.1 only.

6. **🟡 Remove `config.yaml.backup`**: `C:\Users\Falki\AppData\Local\hermes\config.yaml.backup` retains old secrets.

7. **🟡 Audit Docker firewall rules**: Docker Desktop adds `Allow` rules for all ports. Verify no container ports are exposed to 0.0.0.0 unnecessarily.

8. **🟡 Check `polymarket-us>=0.2` auth method**: The `main.py` in `poly-agent-app/agent/main.py` uses JWT/RSA key auth. Verify the RSA key path in config.yaml actually points to a file that exists and has restricted permissions (ACLs).

### P2 — Operational hardening

9. **🟢 No git tracking of secrets**: `poly-agent-docs-index.md` and `polymarket-docs-index.md` are fine, but ensure `.env.example` is used instead of real `config.yaml` in any git repo.

10. **🟢 Process monitoring**: Add `pslist` to the agent's startup sequence to log all processes before the first trade. This creates a baseline for detecting injection.

11. **🟢 Network egress filtering**: Only allow outbound to known Polymarket endpoints (`*.polymarketexchange.com`, `*.polymarket.us`, BRTI endpoints). All other outbound should be logged or blocked.

12. **🟢 Disk encryption**: If this machine stores real money trading credentials, BitLocker should be enabled (Win11 Home doesn't support it; Win11 Pro does).

---

## 6. Data Safety — Polymarket-Specific Findings

| Issue | Severity | Detail |
|-------|----------|--------|
| `position_tracker.py` uses in-memory dict | 🔴 CRITICAL | Crash = lose all real-money positions. No persistence. |
| `executor.py` no idempotency key on POST | 🔴 CRITICAL | Re-sent orders on retry = double-bets (real money). |
| `risk_manager.py` no Number Rule enforcement | 🔴 CRITICAL | The Number Rule (three-source verification) is documented but not implemented in code. |
| `config.yaml` plaintext trading limits | 🟡 MEDIUM | `daily_budget_usd: 50` is real money. Anyone reading the file can see budget. |
| No `.gitignore` in `F:/PolyMarket/` | 🟡 MEDIUM | `config.yaml` could be committed to a public repo. |
| `mcp-server/src/mcp_server/__init__.py` unreadable (non-ASCII filename) | 🟡 MEDIUM | Module won't import — MCP server won't start. |
| `poly-agent-app/agent/__init__.py` missing | 🟡 MEDIUM | Dead import path. |
| No secrets management for Polymarket auth | 🔴 CRITICAL | RSA key path in plaintext config — if this is real credentials, the entire Polymarket account is accessible to anyone who reads the file. |

---

## 7. Summary

**Overall risk: HIGH.** The machine is running legitimate financial trading software with real money limits hardcoded in plaintext configs, exposed SMB on all interfaces (including Docker bridge), a P2P client that could be abused, and a trading engine that has zero persistence and no idempotency. The codebase is not yet ready for real money. The **number-one action** is:

1. Block SMB on Docker bridge (immediate)
2. Audit/encrypt all Polymarket auth credentials
3. Audit PID 22548's connection (non-standard port)
4. Fix the three critical code-level data safety gaps (persistence, idempotency, Number Rule)

This audit covers the **host computer**. The **code-level data safety** gaps are tracked in `ENDGAME.md` and `DATA-SAFETY.md`. The code fixes should be done before any deployment.
 
