<!--
Keep this body short and factual. The checklist is the gate; the anchor references are what stop drift.
-->

## What changed

- 

## Anchor references

→ `ENDGAME.md` §\_\_  ·  → `BUILD-PLAN.md` Phase \_\_  ·  → `ROADMAP.md` blocker **B-\_\_** (closed / advanced / opened)

## Risk & money impact

Does this touch a monetary value, a position write or an order path? Does every order still pass
through `risk_manager.approve()`? If yes, name the Number Rule check that covers it
([DATA-SAFETY.md](../Development/docs/DATA-SAFETY.md)).

## Definition of done (CONTRIBUTING §4)

- [ ] `pip install -e ./poly-agent` and `-e "./mcp-server[dev]"` succeed on a clean environment
- [ ] `cd poly-agent && python -m pytest tests -q` — no new failures vs the ROADMAP baseline
- [ ] `cd mcp-server && python -m pytest tests -q` — same
- [ ] No secret in the diff (`.env`, `config.yaml`, keys, tokens)
- [ ] New endpoint → `Development/docs/API-ROUTING.md` updated first
- [ ] New dependency recorded in `pyproject.toml` (and consistent with `requirements.txt`)
- [ ] `Development/docs/ROADMAP.md` iteration log updated
- [ ] `CHANGELOG.md` **Unreleased** updated, version bumped if behaviour changed

## How to verify

```bash

```
