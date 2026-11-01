"""Live monitoring dashboard for PolyAgent — shows PnL, positions, and activity in real-time."""

import asyncio
import json
from pathlib import Path
from typing import Optional

from loguru import logger


class DashboardServer:
    """FastAPI-based web dashboard showing agent state in real-time.

    Access at http://localhost:{port} while the agent is running.
    Auto-refreshes every 5 seconds to show live data.
    """

    def __init__(self, config: dict):
        self.config = config["monitoring"]
        self.port = self.config.get("dashboard_port", 8080)
        self.state = {
            "pnl": 0.0,
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "open_positions": 0,
            "opportunities": 0,
            "status": "idle",
            "last_update": "",
        }
        self._server_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the dashboard server."""
        try:
            from fastapi import FastAPI
            from fastapi.responses import HTMLResponse, JSONResponse
            from fastapi.staticfiles import StaticFiles
            import uvicorn

            app = FastAPI(title="PolyAgent Dashboard")

            @app.get("/")
            async def index():
                return HTMLResponse(content=self._html_template())

            @app.get("/state")
            async def get_state():
                return JSONResponse(self.state)

            @app.post("/stop")
            async def stop_agent():
                self.state["status"] = "stopping"
                logger.info("🛑 Dashboard stop signal received")
                return {"status": "stopping"}

            # Start server in background task
            config_obj = uvicorn.Config(
                app, host="127.0.0.1", port=self.port, log_level="warning"
            )
            self._server_task = asyncio.create_task(uvicorn.Server(config_obj).serve())

            logger.info(f"   📊 Dashboard running at http://localhost:{self.port}")

        except ImportError:
            logger.warning("   ⚠️ FastAPI/uvicorn not installed — dashboard unavailable")
            logger.info("   Install with: pip install fastapi uvicorn")

    async def update_state(self, **kwargs):
        """Update the dashboard state."""
        self.state.update(kwargs)
        import datetime
        self.state["last_update"] = datetime.datetime.now().strftime("%H:%M:%S")

    async def stop(self):
        """Stop the dashboard server."""
        if self._server_task:
            self._server_task.cancel()
            try:
                await self._server_task
            except asyncio.CancelledError:
                pass
            logger.info("   📊 Dashboard stopped")

    def _html_template(self) -> str:
        """Generate the HTML dashboard page."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>PolyAgent — Live Dashboard</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #0a0e17; color: #e2e8f0; min-height: 100vh; }}
  .container {{ max-width: 900px; margin: 0 auto; padding: 2rem; }}
  h1 {{ font-size: 2rem; margin-bottom: 0.5rem; color: #38bdf8; }}
  .subtitle {{ color: #64748b; margin-bottom: 2rem; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}
  .card {{ background: #1e293b; border-radius: 12px; padding: 1.5rem; border: 1px solid #334155; }}
  .card .label {{ font-size: 0.85rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; }}
  .card .value {{ font-size: 2rem; font-weight: 700; margin-top: 0.5rem; }}
  .pnl-positive {{ color: #4ade80; }}
  .pnl-negative {{ color: #f87171; }}
  .status {{ display: inline-block; padding: 0.25rem 0.75rem; border-radius: 999px; font-size: 0.85rem; font-weight: 600; }}
  .status-running {{ background: #166534; color: #bbf7d0; }}
  .status-idle {{ background: #713f12; color: #fef08a; }}
  .log {{ background: #0f172a; border-radius: 8px; padding: 1rem; font-family: 'Fira Code', monospace; font-size: 0.85rem; max-height: 400px; overflow-y: auto; margin-top: 1rem; }}
  .log-entry {{ padding: 0.25rem 0; border-bottom: 1px solid #1e293b; }}
  .btn {{ display: inline-block; background: #dc2626; color: white; padding: 0.75rem 1.5rem; border-radius: 8px; text-decoration: none; font-weight: 600; cursor: pointer; border: none; }}
  .btn:hover {{ background: #b91c1c; }}
</style>
</head>
<body>
<div class="container">
  <h1>PolyAgent 🤖</h1>
  <p class="subtitle">Autonomous PolyMarket Trading Agent — Live Status</p>

  <div style="margin-bottom: 2rem;">
    <span id="status" class="status status-idle">● IDLE</span>
    <span style="color:#64748b; margin-left:1rem;" id="last-update"></span>
  </div>

  <div class="grid">
    <div class="card">
      <div class="label">Total PnL</div>
      <div class="value" id="pnl">$0.00</div>
    </div>
    <div class="card">
      <div class="label">Trades Executed</div>
      <div class="value" id="trades">0</div>
    </div>
    <div class="card">
      <div class="label">Win Rate</div>
      <div class="value" id="winrate">—</div>
    </div>
    <div class="card">
      <div class="label">Open Positions</div>
      <div class="value" id="positions">0</div>
    </div>
  </div>

  <h2 style="margin: 2rem 0 1rem;">Activity Log</h2>
  <div class="log" id="log"></div>

  <div style="margin-top: 2rem; text-align: center;">
    <button class="btn" onclick="stopAgent()">🛑 STOP AGENT</button>
  </div>
</div>

<script>
async function fetchState() {{
  try {{
    const res = await fetch('/state');
    const data = await res.json();
    document.getElementById('pnl').textContent = '$' + (data.pnl || 0).toFixed(2);
    document.getElementById('pnl').className = 'value ' + ((data.pnl||0)>=0?'pnl-positive':'pnl-negative');
    document.getElementById('trades').textContent = data.trades || 0;
    const w = data.wins || 0, l = data.losses || 0;
    document.getElementById('winrate').textContent = (w+l>0 ? ((w/(w+l))*100).toFixed(1)+'%' : '—');
    document.getElementById('positions').textContent = data.open_positions || 0;
    document.getElementById('status').className = 'status ' + (data.status==='running'?'status-running':'status-idle');
    document.getElementById('status').textContent = '● ' + (data.status||'IDLE').toUpperCase();
    document.getElementById('last-update').textContent = data.last_update ? 'Updated: '+data.last_update : '';
  }} catch(e) {{}}
}}

async function stopAgent() {{
  if(confirm('Stop the agent? All open positions will be closed.')) {{
    await fetch('/stop', {{method:'POST'}});
    alert('Agent stopping...');
  }}
}}

fetchState();
setInterval(fetchState, 5000);
</script>
</body>
</html>"""
