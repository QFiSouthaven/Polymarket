"""PolyAgent MCP Server - Persistent Memory for Dev Lifecycle and Polymarket App."""

# Only import the server when explicitly requested (avoids mcp dependency for basic imports)
def get_mcp():
    """Get the MCP server instance. Requires 'mcp' package to be installed."""
    from .server import mcp, main
    return mcp, main


__all__ = ["get_mcp"]
