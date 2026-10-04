"""pytest plugin entry-point (inlined).

Add this to pyproject.toml under [tool.pytest.ini_options].
This file exists so `pytest --hook-list` works during development.
"""

import pytest


def pytest_addoption(parser: pytest.Parser):
    """Expose --decimal-check flag for explicit Decimal-only verification."""
    parser.addoption(
        "--decimal-check",
        action="store_true",
        default=False,
        help="Run Decimal-only verification on every monetary value (P0).",
    )


def pytest_configure(config: pytest.Config):
    config.addinivalue_line("markers", "decimal: Number Rule — Decimal-only money")
    config.addinivalue_line("markers", "idempotent: idempotency key correctness")
    config.addinivalue_line("markers", "risk: risk_manager hard-limit tests")
    config.addinivalue_line("markers", "strategy: strategy engine coordination tests")
    config.addinivalue_line("markers", "exec: executor error-handling tests")
    config.addinivalue_line("markers", "slow: > 1 s or network-bound")
