@echo off
:: Block SMB (port 445) on Docker bridge 172.18.240.1
:: Requires: Run as Administrator
netsh advfirewall firewall add rule name="Block SMB Docker Bridge" dir=in action=block remoteip=172.18.240.1 localport=445 protocol=TCP >nul 2>&1
if %errorlevel%==0 (
    echo SUCCESS: Blocked SMB on Docker bridge (172.18.240.1:445)
) else (
    echo ERROR: Requires Administrator privileges
    echo Run this script as Administrator
)
