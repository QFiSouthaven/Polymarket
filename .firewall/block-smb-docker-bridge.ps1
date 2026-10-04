#=== PolyMarket: Block SMB on Docker Bridge ===
# Run as Administrator (right-click -> Run as administrator)
# Uses netsh advfirewall (native to all Windows 10/11)
# Block outbound TCP 445 (SMB) to Docker bridge 172.18.240.1
$bridge = "172.18.240.1"
$ruleName = "PolyMarket-DockerBridge-SMB-Block"

# Remove old rule if it exists
try { netsh advfirewall firewall delete rule name="$ruleName" 2>&1 | Out-Null } catch {}

# Outbound: block TCP 445 to Docker bridge (remoteport = destination port)
netsh advfirewall firewall add rule name="$ruleName Out" dir=out action=block protocol=TCP remoteip="$bridge" remoteport=445

# Inbound: block TCP 445 from Docker bridge (localip + localport = source)
netsh advfirewall firewall add rule name="$ruleName In" dir=in action=block protocol=TCP localip="$bridge" localport=445

Write-Host "=== Rule applied ==="
netsh advfirewall firewall show rule name="$ruleName"