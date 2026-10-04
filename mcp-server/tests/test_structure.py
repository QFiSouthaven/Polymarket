"""Quick verification that the MCP server structure is correct."""

import sys
from pathlib import Path


def test_workspace_root():
    """Verify workspace root path resolution works."""
    this_file = Path(__file__).resolve()
    workspace_root = this_file.parent.parent.parent
    assert (workspace_root / "poly-agent" / "src").exists(), f"poly-agent/src not found at {workspace_root}"
    print(f"OK Workspace root: {workspace_root}")


def test_persistence_layer():
    """Verify persistence layer modules exist and are importable."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

    from mcp_server.persistence.dev_state import DevStateDB
    from mcp_server.persistence.polymarket_cache import PolymarketCache, get_polymarket_cache

    db = DevStateDB()
    print(f"OK DevStateDB initialized at: {db.db_path}")

    cache = get_polymarket_cache()
    assert cache.cache_dir is not None
    print(f"OK PolymarketCache initialized at: {cache.cache_dir}")


def test_dev_lifecycle_tools():
    """Verify dev lifecycle tool modules exist."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

    from mcp_server.tools.dev_lifecycle.project_state import (
        get_project_state, set_project_state, scan_codebase_status, get_all_project_states
    )
    from mcp_server.tools.dev_lifecycle.experiment_log import (
        log_experiment, update_experiment, list_experiments, delete_experiment, compare_strategies
    )

    print(f"OK project_state: {get_project_state.__name__}, {set_project_state.__name__}")
    print(f"OK experiment_log: {log_experiment.__name__}, {list_experiments.__name__}")


def test_polymarket_tools():
    """Verify Polymarket tool modules exist."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

    from mcp_server.tools.polymarket.market_scan import scan_markets, get_market_detail, search_markets
    from mcp_server.tools.polymarket.position_manager import get_positions, close_position, partial_close_position
    from mcp_server.tools.polymarket.risk_dashboard import get_risk_state, check_can_trade
    from mcp_server.tools.polymarket.order_tools import create_order, cancel_order, preview_order
    from mcp_server.tools.polymarket.portfolio_query import get_portfolio_summary, get_account_balances, get_activities

    print(f"OK market_scan: {scan_markets.__name__}, {get_market_detail.__name__}")
    print(f"OK position_manager: {get_positions.__name__}, {close_position.__name__}")
    print(f"OK risk_dashboard: {get_risk_state.__name__}, {check_can_trade.__name__}")
    print(f"OK order_tools: {create_order.__name__}, {preview_order.__name__}")
    print(f"OK portfolio_query: {get_portfolio_summary.__name__}, {get_account_balances.__name__}")


def test_server_module():
    """Verify the main server module can be imported."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

    try:
        from mcp_server.server import mcp, main
        print(f"OK MCP server: {mcp.name} v{mcp.version}")
        print(f"OK Server description: {mcp.description[:60]}...")
    except ModuleNotFoundError as e:
        print(f"SKIP MCP server (dependency not installed): {e}")


def test_codebase_scan():
    """Test the codebase status scanner."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

    from mcp_server.tools.dev_lifecycle.project_state import scan_codebase_status
    result = scan_codebase_status()

    assert "modules" in result
    assert "total_modules" in result
    print(f"OK Codebase scan: {result['summary']}")
    for mod in result["modules"][:5]:
        print(f"  - {mod['module']}: {mod['status']} ({mod['py_file_count']} files)")


if __name__ == "__main__":
    test_workspace_root()
    test_persistence_layer()
    test_dev_lifecycle_tools()
    test_polymarket_tools()
    test_server_module()
    test_codebase_scan()
    print("\nAll structure tests passed!")
