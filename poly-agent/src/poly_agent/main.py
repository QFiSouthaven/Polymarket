"""
PolyAgent — Autonomous PolyMarket Trading Agent
=================================================
You flip `agent.enabled: true` in config.yaml, run this script, and I take over.

Usage:
    python -m poly_agent.main              # Start the agent (runs until killed)
    python -m poly_agent.dashboard         # Start monitoring dashboard only
"""

import asyncio
import signal
import sys
from pathlib import Path
from typing import Optional

import yaml
from loguru import logger

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def load_config(path: str = "config.yaml") -> dict:
    """Load and validate configuration."""
    config_path = Path(__file__).parent.parent / path
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # Validate required fields
    if not config["auth"]["key_id"] or not config["auth"]["secret_key"]:
        logger.error("Auth credentials not configured. Set key_id and secret_key in config.yaml")
        sys.exit(1)

    return config


class PolyAgent:
    """Main agent orchestrator — the 'brain' that runs strategies."""

    def __init__(self, config: dict):
        self.config = config
        self.running = False
        self.cycle_count = 0
        self.total_pnl = 0.0
        self.trades_executed = 0
        self.wins = 0
        self.losses = 0

    async def start(self):
        """Start the autonomous agent loop."""
        if not self.config["agent"]["enabled"]:
            logger.warning("Agent is DISABLED in config.yaml. Set enabled: true to start.")
            return

        logger.info("=" * 60)
        logger.info(f"🚀 {self.config['agent']['name']} starting up")
        logger.info(f"   Budget: ${self.config['capital']['total_budget_usdc']:,.2f} USDC")
        logger.info(f"   Max per trade: ${self.config['capital']['max_per_trade_usdc']:,.2f}")
        logger.info(f"   Daily loss limit: ${self.config['risk']['stop_loss_pct']*100:.0f}%")
        logger.info("=" * 60)

        # Import and initialize components
        from poly_agent.engine import StrategyEngine
        from poly_agent.risk_manager import RiskManager
        from poly_agent.position_tracker import PositionTracker
        from poly_agent.monitoring.dashboard import DashboardServer

        self.risk_manager = RiskManager(self.config)
        self.position_tracker = PositionTracker(self.config, self.risk_manager)
        self.engine = StrategyEngine(
            config=self.config,
            risk_manager=self.risk_manager,
            position_tracker=self.position_tracker,
        )
        self.dashboard = DashboardServer(config=self.config)

        # Set up signal handlers for graceful shutdown
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.shutdown()))

        self.running = True
        await self._main_loop()

    async def _main_loop(self):
        """Main autonomous trading loop."""
        interval = self.config["agent"]["cycle_interval_seconds"]

        logger.info("🔍 Scanning markets for opportunities...")

        while self.running:
            try:
                self.cycle_count += 1
                logger.info(f"\n{'='*60}")
                logger.info(f"📊 CYCLE #{self.cycle_count} — Scanning {interval}s interval")
                logger.info(f"   PnL so far: ${self.total_pnl:+,.2f} | Trades: {self.trades_executed} (W:{self.wins} L:{self.losses})")

                # Check risk limits before scanning
                if not self.risk_manager.can_trade():
                    logger.warning("⛔ Risk limit hit — pausing trading for this cycle")
                    await asyncio.sleep(interval)
                    continue

                # Run all enabled strategies in parallel
                opportunities = await self.engine.scan_all_strategies()

                if opportunities:
                    logger.info(f"   Found {len(opportunities)} opportunity(s)")
                    for opp in opportunities[:5]:  # Log top 5
                        logger.info(f"     → {opp['description']} | Edge: {opp.get('edge_pct', 0):.2%} | Size: ${opp.get('size_usdc', 0):,.2f}")

                # Execute trades from opportunities (risk-managed)
                executed = await self.engine.execute_opportunities(opportunities)
                if executed:
                    logger.info(f"   ✅ Executed {len(executed)} trade(s)")

                # Check auto-cashout conditions
                cashed_out = await self.position_tracker.check_auto_cashouts()
                if cashed_out:
                    logger.info(f"   💰 Auto-cashed out {len(cashed_out)} position(s)")

                # Update dashboard state
                await self.dashboard.update_state(
                    pnl=self.total_pnl,
                    trades=self.trades_executed,
                    wins=self.wins,
                    losses=self.losses,
                    open_positions=len(self.position_tracker.open_positions),
                    opportunities=len(opportunities),
                )

            except Exception as e:
                logger.error(f"❌ Cycle error: {e}", exc_info=True)

            await asyncio.sleep(interval)

    async def shutdown(self):
        """Graceful shutdown — close all positions, stop dashboard."""
        if not self.running:
            return

        self.running = False
        logger.info("\n🛑 Shutting down PolyAgent...")

        # Close open positions gracefully
        if self.position_tracker.open_positions:
            logger.info(f"   Closing {len(self.position_tracker.open_positions)} open position(s)")
            await self.position_tracker.close_all_positions()

        # Stop dashboard
        await self.dashboard.stop()

        logger.info(f"\n{'='*60}")
        logger.info("📈 FINAL REPORT")
        logger.info(f"   Total PnL: ${self.total_pnl:+,.2f} USDC")
        logger.info(f"   Trades: {self.trades_executed} | Win rate: {self.wins/max(self.trades_executed,1)*100:.1f}%")
        logger.info(f"   Cycles completed: {self.cycle_count}")
        logger.info("=" * 60)


async def main():
    """Entry point."""
    config = load_config()

    agent = PolyAgent(config)
    await agent.start()


if __name__ == "__main__":
    asyncio.run(main())
