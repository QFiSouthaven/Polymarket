"""Risk Dashboard tools — query PolyAgent risk state and trading permissions.

Uses the existing RiskManager from poly-agent/src/poly_agent/risk_manager.py
to check hard limits, kill switch status, and PnL tracking.

Provides:
- get_risk_state: current risk state (budget, PnL, kill switch)
- check_can_trade: whether trading is allowed right now
"""

import yaml
from typing import Any


def _get_config() -> dict[str, Any]:
    """Load the PolyAgent configuration."""
    workspace_root = __file__.resolve().parent.parent.parent.parent
    config_path = workspace_root / "poly-agent" / "config.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def _get_risk_manager() -> Any:
    """Get the RiskManager instance."""
    import sys
    workspace_root = __file__.resolve().parent.parent.parent.parent
    agent_src = workspace_root / "poly-agent" / "src"
    if str(agent_src) not in sys.path:
        sys.path.insert(0, str(agent_src))

    config = _get_config()
    from poly_agent.risk_manager import RiskManager
    return RiskManager(config)


def get_risk_state() -> dict[str, Any]:
    """Get the current risk state of the PolyAgent.

    Returns:
        dict with full risk state including budget, PnL, kill switch status, etc.
    """
    try:
        config = _get_config()
        from poly_agent.risk_manager import RiskManager
        rm = RiskManager(config)

        # Get current portfolio to update state
        executor = None
        try:
            from poly_agent.execution.executor import PolymarketExecutor
            executor = PolymarketExecutor(auth_config=config.get("auth", {}))
            import asyncio
            portfolio = asyncio.get_event_loop().run_until_complete(executor.get_portfolio())

            # Update risk state with live data
            rm.state.current_open_positions = len(portfolio.get("positions", []))
            rm.state.remaining_budget_usdc = portfolio.get("current_balance", 0) or config["capital"]["total_budget_usdc"]
        except Exception:
            pass  # Use config defaults if API unavailable

        state = rm.state

        return {
            "success": True,
            "risk_state": {
                "total_budget_usdc": state.total_budget_usdc,
                "remaining_budget_usdc": round(state.remaining_budget_usdc, 2),
                "daily_pnl_usdc": round(state.daily_pnl, 2),
                "max_daily_loss_usdc": abs(state.max_daily_loss) if hasattr(state, 'max_daily_loss') else config["risk"]["stop_loss_pct"] * state.total_budget_usdc,
                "profit_target_daily_usdc": state.profit_target_daily,
                "current_open_positions": state.current_open_positions,
                "max_open_positions": state.max_open_positions,
                "max_per_trade_usdc": state.max_per_trade_usdc,
                "consecutive_losses": state.consecutive_losses,
                "total_drawdown_pct": round(state.total_drawdown_pct * 100, 2),
                "kill_switch_triggered": state.kill_switch_triggered,
            },
            "config": {
                "stop_loss_pct": config["risk"]["stop_loss_pct"],
                "take_profit_pct": config["risk"].get("take_profit_pct", 0.15),
                "max_correlation_exposure": config["risk"].get("max_correlation_exposure", 0.4),
                "kill_switch_enabled": config["risk"]["kill_switch"]["enabled"],
                "consecutive_losses_limit": config["risk"]["kill_switch"]["consecutive_losses"],
            },
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def check_can_trade(size_usdc: float = 0) -> dict[str, Any]:
    """Check if trading is allowed right now based on all risk limits.

    Args:
        size_usdc: The proposed trade size to check against per-trade limit

    Returns:
        dict with can_trade boolean and reason for denial (if applicable)
    """
    try:
        config = _get_config()
        from poly_agent.risk_manager import RiskManager
        rm = RiskManager(config)

        # Get live portfolio state
        executor = None
        try:
            from poly_agent.execution.executor import PolymarketExecutor
            executor = PolymarketExecutor(auth_config=config.get("auth", {}))
            import asyncio
            portfolio = asyncio.get_event_loop().run_until_complete(executor.get_portfolio())
            rm.state.current_open_positions = len(portfolio.get("positions", []))
            rm.state.remaining_budget_usdc = portfolio.get("current_balance", 0) or config["capital"]["total_budget_usdc"]
        except Exception:
            pass

        # Check all conditions
        reasons = []

        # Kill switch check
        if rm.state.kill_switch_triggered:
            reasons.append("KILL SWITCH ACTIVE — no trades until manually reset")

        # Daily loss limit check
        daily_loss_limit = config["risk"]["stop_loss_pct"] * rm.state.total_budget_usdc
        if rm.state.daily_pnl <= daily_loss_limit:
            reasons.append(
                f"Daily loss limit hit (${rm.state.daily_pnl:+,.2f} / ${daily_loss_limit:+,.2f})"
            )

        # Profit target check
        profit_target = config["capital"].get("profit_target_daily_usdc", 0)
        if profit_target > 0 and rm.state.daily_pnl >= profit_target:
            reasons.append(f"Daily profit target ${profit_target} hit — pausing")

        # Max positions check
        if rm.state.current_open_positions >= rm.state.max_open_positions:
            reasons.append(
                f"Max open positions reached ({rm.state.current_open_positions}/{rm.state.max_open_positions})"
            )

        # Per-trade limit check
        max_per_trade = config["capital"]["max_per_trade_usdc"]
        if size_usdc > 0 and size_usdc > max_per_trade:
            reasons.append(
                f"Trade ${size_usdc:.2f} exceeds per-trade limit ${max_per_trade}"
            )

        # Remaining budget check
        remaining = rm.state.remaining_budget_usdc - (rm.state.current_open_positions * 10)
        if size_usdc > 0 and remaining < size_usdc:
            reasons.append(
                f"Not enough remaining budget (${remaining:.2f} available, ${size_usdc:.2f} requested)"
            )

        can_trade = len(reasons) == 0

        return {
            "success": True,
            "can_trade": can_trade,
            "reasons_denied": reasons if not can_trade else [],
            "risk_summary": {
                "daily_pnl_usdc": round(rm.state.daily_pnl, 2),
                "remaining_budget_usdc": round(rm.state.remaining_budget_usdc, 2),
                "open_positions": rm.state.current_open_positions,
                "consecutive_losses": rm.state.consecutive_losses,
            },
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def get_risk_alerts() -> dict[str, Any]:
    """Get current risk alerts and warnings.

    Returns:
        dict with active alerts (kill switch, loss limits, etc.)
    """
    try:
        config = _get_config()
        from poly_agent.risk_manager import RiskManager
        rm = RiskManager(config)

        alerts = []

        # Kill switch alert
        if rm.state.kill_switch_triggered:
            alerts.append({
                "level": "CRITICAL",
                "message": "Kill switch is ACTIVE — all trading halted",
                "action": "Manually reset kill_switch_triggered in config or via set_project_state",
            })

        # Consecutive losses alert
        ks_config = config["risk"]["kill_switch"]
        if rm.state.consecutive_losses >= ks_config.get("consecutive_losses", 5):
            alerts.append({
                "level": "WARNING",
                "message": f"Consecutive losses ({rm.state.consecutive_losses}) approaching kill switch threshold ({ks_config['consecutive_losses']})",
                "action": "Review strategy performance and consider pausing",
            })

        # Drawdown alert
        drawdown_limit = config["risk"]["kill_switch"].get("drawdown_pct", -0.15)
        if rm.state.total_drawdown_pct <= abs(drawdown_limit):
            alerts.append({
                "level": "WARNING",
                "message": f"Portfolio drawdown ({rm.state.total_drawdown_pct*100:.2f}%) approaching limit ({abs(drawdown_limit)*100:.2f}%)",
                "action": "Reduce position sizes or pause trading",
            })

        # Daily loss alert
        daily_loss_limit = config["risk"]["stop_loss_pct"] * rm.state.total_budget_usdc
        if rm.state.daily_pnl <= daily_loss_limit * 0.8:  # 80% of limit
            alerts.append({
                "level": "INFO",
                "message": f"Daily PnL ({rm.state.daily_pnl:+,.2f}) approaching loss limit (${daily_loss_limit:+,.2f})",
                "action": "Monitor closely, consider reducing size",
            })

        return {
            "success": True,
            "alert_count": len(alerts),
            "alerts": alerts,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }
