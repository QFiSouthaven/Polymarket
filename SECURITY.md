# SECURITY

**NEVER** commit `config.yaml`, `.env`, or any file containing credentials. This repo must only contain `.example` templates (placeholders only) and source code.

## Secrets handling

1. **Hermes vault** is the source of truth for Polymarket credentials (`POLYMARKET_PRIVATE_KEY_BASE64`, `POLYMARKET_CLIENT_ID`, `POLYMARKET_AUDIENCE`). Fill `.env` from vault — never from plaintext.
2. **RSA key ACLs**: The RSA private key referenced by `secret_key` / `private_key_path` must be owned by Falki only (Windows ACL `icacls` / `cacls`). No group, no other user. Verify with `icacls <keyfile>`.
3. **Never** put real `client_id`, `audience`, or `secret_key` values into a `.example` file or git history.

## Known finding

`COMPUTER-AUDIT.md` (Development/docs) flagged:

> `poly-agent-app/agent/config.yaml` contains `client_id`, `audience`, `rsa_key_path` in plaintext — real trading limits hardcoded. `mcp-server/config/example_config.yaml` also leaks example auth keys.

Fix: delete plaintext config files from the repo root; use only the `.example` templates below.

## Checklist before first live trade

- [ ] `.gitignore` includes `config.yaml`, `*.pem`, `*.key`, `.env`, `.env.*`
- [ ] RSA key file ACL: Falki-only read/write
- [ ] All `config.yaml` files in this repo contain `REDACTED` placeholders only
- [ ] `.env` file exists locally (not committed) and is filled from vault
- [ ] Strategy `enabled: false` in `poly-agent/config.yaml.example` until QA complete
