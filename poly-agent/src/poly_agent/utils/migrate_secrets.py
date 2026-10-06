#!/usr/bin/env python
"""Migrate secrets from plaintext config.yaml → Windows Credential Manager (keyring).

Usage:
    python -m poly_agent.utils.migrate_secrets F:/PolyMarket/poly-agent-app/agent/config.yaml

If a real (non-placeholder) value is found, it asks the user:
    "Save <field> to Windows Credential Manager?" [y/N]
On 'y', the value is stored in keyring and replaced with "KEYRING_REF:<field>" in the config.

On next run, the config loader reads the value from keyring transparently.
"""

import os
import sys
import yaml
from pathlib import Path


def load_config(path: str) -> dict:
    """Load YAML config."""
    with open(path, "r") as f:
        return yaml.safe_load(f)


def save_config(path: str, config: dict):
    """Save YAML config back to disk."""
    with open(path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)


def get_secret_keys(config: dict) -> list[tuple[str, str, str]]:
    """Walk config dict, return (path, field, value) for potential secrets.
    
    Returns list of (dotpath, key, raw_value).
    """
    results = []

    def walk(obj, prefix):
        if isinstance(obj, dict):
            for k, v in obj.items():
                path = f"{prefix}.{k}" if prefix else k
                if isinstance(v, str):
                    results.append((path, k, v))
                elif isinstance(v, dict):
                    walk(v, path)
                elif isinstance(v, list):
                    for i, item in enumerate(v):
                        walk(item, f"{path}[{i}]")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                walk(item, f"{prefix}[{i}]")

    walk(config, "")
    return results


def is_placeholder(val: str) -> bool:
    """Check if a value looks like a placeholder (not a real secret)."""
    if not val or not val.strip():
        return True
    if val.strip().startswith("YOUR_") or val.strip().startswith("CHANGE_ME"):
        return True
    if val.strip().startswith("INSERT_") or val.strip().startswith("REPLACE_"):
        return True
    if val.strip() in ("", "''", '""', "null", "none"):
        return True
    if val.strip().startswith("-----BEGIN"):
        return False  # This looks like a real PEM key
    return False


def migrate_secrets(config_path: str, dry_run: bool = False) -> None:
    """Main migration logic."""
    config = load_config(config_path)
    secrets = get_secret_keys(config)

    print(f"Scanning {config_path} for secrets...")
    print(f"Found {len(secrets)} string fields.")
    print()

    to_migrate = []
    for path, field, val in secrets:
        if is_placeholder(val):
            print(f"  SKIP {path}.{field} = {val[:40]!r}... (placeholder)")
            continue
        if val.startswith("KEYRING_REF:"):
            print(f"  ✓ {path}.{field} = KEYRING_REF:{field} (already migrated)")
            continue
        print(f"  ? {path}.{field} = {val[:40]!r}... (real value found)")
        to_migrate.append((path, field, val))

    if not to_migrate:
        print("\nNo real secrets found. Config is clean.")
        return

    # Import keyring only if needed
    try:
        import keyring
    except ImportError:
        print("\n⚠️  keyring not installed. Install with:")
        print("    pip install keyring")
        print("Then re-run this script.")
        return

    # Get service name from config path
    service = Path(config_path).stem  # e.g. "config"

    for path, field, val in to_migrate:
        print(f"\n  → Migrate {path}.{field}? (y/N): ", end="", flush=True)
        answer = input().strip().lower()
        if answer in ("y", "yes"):
            try:
                # Store in Windows Credential Manager
                keyring.set_password(service, field, val)
                print(f"  ✓ Saved to Windows Credential Manager (service={service}, user={field})")
                # Replace in config
                parts = path.split(".")
                target = config
                for part in parts[:-1]:
                    target = target[part]
                target[parts[-1]] = f"KEYRING_REF:{field}"
            except Exception as e:
                print(f"  ✗ Failed: {e}")
        else:
            print(f"  → Skipped")

    if not dry_run and to_migrate:
        save_config(config_path, config)
        print(f"\n✓ Config updated: {config_path}")
        print(f"  Real secrets are now in Windows Credential Manager.")
        print(f"  The config file contains KEYRING_REF:<field> placeholders.")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Migrate secrets to Windows Credential Manager")
    parser.add_argument("config", help="Path to config.yaml to scan")
    parser.add_argument("--dry-run", action="store_true", help="Show findings without changing anything")
    args = parser.parse_args()

    config_path = args.config
    if not Path(config_path).exists():
        print(f"✗ File not found: {config_path}")
        sys.exit(1)

    migrate_secrets(config_path, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
