# Docker Network / Firewall Audit Report
**Date:** 2026-10-06 | **Host:** Falki (Windows 11) | **Profile:** app-developer

---

## FINDING 1 (P0 — CRITICAL): SMB (port 445) listening on 0.0.0.0 and [::]

**Status:** Active, all interfaces including Docker bridge.

```
TCP    0.0.0.0:445            LISTENING       4        (System)
TCP    [::]:445               LISTENING       4        (System)
TCP    172.30.192.1:139       LISTENING       4        (Docker bridge)
TCP    172.27.80.1:139        LISTENING       4        (Docker bridge)
```

- PID 4 = `System` (Windows kernel). SMB is enabled globally, not bound to a specific interface.
- Docker's own network interfaces (172.27.80.1, 172.30.192.1) also expose port 139 (NetBIOS/SMB legacy).
- **Risk:** Any container or host process on the Docker bridge network can reach SMB. If Docker bridge is 0.0.0.0 bound, even external hosts on that network segment could reach SMB.

**Current mitigation (BLOCKING rules exist):**

| Rule | Dir | RemoteIP | LocalPort | Action | Enabled |
|------|-----|----------|-----------|--------|---------|
| Block SMB Docker Bridge | In | 172.18.240.1/32 | 445 | Block | ✅ |
| PolyMarket-DockerBridge-SMB-Block In | In | 172.18.240.1/32 | 445 | Block | ✅ |
| PolyMarket-DockerBridge-SMB-Block Out | Out | 172.18.240.1/32 | 445 | Block | ✅ |

**⚠️ THE BLOCK RULES TARGET THE WRONG IP:**

- **Block rules target:** `172.18.240.1` (Docker bridge gateway)
- **Actual Docker bridge gateway:** `172.17.0.1` (default bridge subnet `172.17.0.0/16`)
- **Result:** The block rules do NOT match the real Docker bridge. SMB on 445 is effectively **UNBLOCKED** for Docker traffic.

---

## FINDING 2: Firewall rule duplication

- `Block SMB Docker Bridge`: **3 duplicate rules** (identical — all inbound block 445 from 172.18.240.1)
- `PolyMarket-DockerBridge-SMB-Block In`: **4 duplicate rules** (identical)
- `PolyMarket-DockerBridge-SMB-Block Out`: **3 duplicate rules** (identical outbound)

These accumulated from running the `.ps1` script multiple times (it only deletes by name `PolyMarket-DockerBridge-SMB-Block`, not by direction, so old "Out" rules remain).

---

## FINDING 3: No qBittorrent currently running

- No process listening on port 51413 (qBittorrent default port)
- No process listening on port 6881 (Bittorrent DHT)
- No `qbittorrent` or `qbt` process in netstat
- qBittorrent is **not currently active**, so this is not an immediate risk. However, when it starts, it will attempt to open P2P ports on 0.0.0.0 and could be reachable via Docker bridge interfaces.

---

## FINDING 4: HNS (Docker) firewall rules

Only **4 HNS rules** exist — all are **DNS** rules (allow UDP/TCP 53 from any IP):
- `HNS Container Networking - DNS (UDP-In)` — 790E58B4-... and C08CB7B8-...
- `HNS Container Networking - ICS DNS (TCP-In)` — same two UUIDs

**No HNS rules for SMB, no HNS rules exposing container services.** Docker's firewall rules are minimal and benign.

---

## FINDING 5: Dynamic RPC ports

Windows dynamic RPC port range is open: `49664-49668`. These are WSMAN/WMI RPC endpoints (standard Windows). They are on 0.0.0.0 but are standard for Windows management. **Not a Docker-specific issue.**

---

## FINDING 6: Docker bridge subnet mismatch

| Source | Reported Bridge | Actual Bridge |
|--------|----------------|---------------|
| Block rules | 172.18.240.1 | **172.17.0.1** |
| .bat script | 172.18.240.1 | **172.17.0.1** |
| .ps1 script | 172.18.240.1 | **172.17.0.1** |
| docker network inspect | 172.17.0.1 (172.17.0.0/16) | ✅ correct |

**Root cause:** A previous Docker install (likely Docker Desktop v19.x or earlier, or a WSL2 distro) used 172.18.240.0/20. Current Docker uses 172.17.0.0/16. The firewall rules were never updated.

---

## P0 FIXES

1. **Update block-smb scripts** to target `172.17.0.1` (actual Docker bridge gateway)
2. **Deduplicate** firewall rules (delete old duplicates, keep one of each)
3. **Block Docker bridge interfaces for SMB at the interface level** (more robust than IP-based rules since Docker assigns dynamic IPs to containers)
4. **Add qBittorrent block rules** when it's re-enabled
