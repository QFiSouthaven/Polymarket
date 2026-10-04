"""Strategy Engine — runs all strategies in parallel and manages execution."""

import asyncio
from dataclasses import dataclass, field
from typing import Any

from loguru import logger


@dataclass
class Opportunity:
    """Represents a trading opportunity found by any strategy."""
    strategy_name: str
    description: str
    market_slug: str
    side: str  # "BUY" or "SELL"
    price: float
    size_usdc: float
    edge_pct: float  # Expected edge (profit %)
    confidence: float  # 0-1 confidence score
    metadata: dict = field(default_factory=dict)


class StrategyEngine:
    """Orchestrates all strategies and executes trades."""

    def __init__(self, config: dict, risk_manager, position_tracker):
        self.config = config
        self.risk_manager = risk_manager
        self.position_tracker = position_tracker
        self._strategies = {}
        self._register_strategies()

    def _register_strategies(self):
        """Register all enabled strategies."""
        from poly_agent.strategies.arbitrage import BundleArbitrageStrategy
        from poly_agent.strategies.edge_detection import EdgeDetectionStrategy
        from poly_agent.strategies.momentum import MomentumStrategy
        from poly_agent.strategies.market_making import MarketMakingStrategy

        strategy_map = {
            "bundle_arbitrage": ("strategies.arbitrage", BundleArbitrageStrategy),
            "edge_detection": ("strategies.edge_detection", EdgeDetectionStrategy),
            "momentum": ("strategies.momentum", MomentumStrategy),
            "market_making": ("strategies.market_making", MarketMakingStrategy),
        }

        for key, (module_path, cls) in strategy_map.items():
            if self.config["strategies"][key]["enabled"]:
                strat = cls(self.config[key], self.risk_manager, self.position_tracker)
                self._strategies[key] = strat
                logger.info(f"   ✅ Strategy loaded: {cls.__name__}")

    async def scan_all_strategies(self) -> list[Opportunity]:
        """Run all strategies in parallel and collect opportunities."""
        tasks = [self._run_strategy(name, strat) for name, strat in self._strategies.items()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        opportunities: list[Opportunity] = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Strategy error: {result}")
            elif isinstance(result, list):
                opportunities.extend(result)

        # Sort by edge (highest first) and deduplicate markets
        opportunities.sort(key=lambda o: o.edge_pct, reverse=True)
        return self._deduplicate(opportunities)

    async def _run_strategy(self, name: str, strategy) -> list[Opportunity]:
        """Run a single strategy with timeout."""
        try:
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: strategy.scan()),
                timeout=30,  # 30s max per strategy
            )
            return result if isinstance(result, list) else []
        except asyncio.TimeoutError:
            logger.warning(f"⏱️ Strategy '{name}' timed out after 30s")
            return []

    def _deduplicate(self, opportunities: list[Opportunity]) -> list[Opportunity]:
        """Remove duplicate market entries, keeping highest edge."""
        seen = {}
        for opp in opportunities:
            key = (opp.market_slug, opp.side)
            if key not in seen or opp.edge_pct > seen[key].edge_pct:
                seen[key] = opp
        return list(seen.values())

    async def execute_opportunities(self, opportunities: list[Opportunity]) -> list[dict]:
        """Execute trades from opportunities with risk checks."""
        executed = []

        for opp in opportunities:
            # Risk check
            if not self.risk_manager.can_open_position(opp.size_usdc):
                logger.debug(f"   ⛔ Skipped {opp.market_slug}: risk limit")
                continue

            # Confidence threshold
            if opp.confidence < 0.3:
                logger.debug(f"   ⏭️ Skipped {opp.market_slug}: low confidence ({opp.confidence:.2f})")
                continue

            # Execute the trade
            try:
                from poly_agent.execution.executor import TradeExecutor
                executor = TradeExecutor(self.config["auth"], self.risk_manager)
                result = await executor.execute(opp)
                executed.append(result)

                if result.get("success"):
                    logger.info(f"   ✅ {result['description']}")
                    self.position_tracker.add_position(opp, result)
                    self.trades_executed += 1
                else:
                    logger.warning(f"   ❌ Failed: {result.get('error', 'unknown')}")

            except Exception as e:
                logger.error(f"   ❌ Trade error on {opp.market_slug}: {e}")

        return executed


class StrategyEngineResult:
    """Container for strategy scan results."""
    def __init__(self, opportunities: list[Opportunity]):
        self.opportunities = opportunities
        self.total_edge = sum(o.edge_pct * o.size_usdc for o in opportunities) if opportunities else 0
