# Changelog

All notable changes to this repository are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) per package (`poly-agent`,
`polyagent-mcp-server`).

## [Unreleased]

### Added
- `README.md` at the repo root: repository map, read-first doc order, verified quickstart, test baseline.
- `CONTRIBUTING.md`: branch/worktree model, commit convention, PR gate (definition of done), testing
  and line-ending conventions, versioning policy.
- `Development/docs/ROADMAP.md`: measured repo baseline, blockers B-1…B-7 with evidence, backlog mapped
  to BUILD-PLAN phases, iteration log.
- `.github/` issue forms, pull-request template and a CI workflow running both pytest suites.
- `CHANGELOG.md` (this file).
- `.gitattributes`: LF index, LF sources, CRLF for Windows launchers, binaries marked.
- `.env.example` is now tracked (it was previously swallowed by the `.env.*` ignore rule).

### Fixed
- **Build:** both Python packages declared `build-backend = "setuptools.backends._legacy:_Backend"`,
  which is not importable in installed setuptools — `pip install -e .` failed with
  `BackendUnavailable: Cannot import 'setuptools.backends._legacy'`. Steps 2–3 of the ENDGAME §6 build
  order could therefore never run. Now `setuptools.build_meta`; both packages resolve.
- **Engine:** package `__init__.py` files for `analysis`, `execution`, `instrument_schema`,
  `monitoring`, `public_client` and `strategies` now declare imports plus `__all__`, so
  `from poly_agent.strategies import arbitrage` works (ENDGAME §9 gaps 6, 8).
- **Monitoring:** `_html_template()` is an f-string but the `<script>` braces were not escaped, which
  broke rendering of the live dashboard.
- **MCP server:** non-ASCII characters removed from the package docstring (ENDGAME §9 gap 5).
- **App:** `poly-agent-app/agent/__init__.py` added with `core` exports (ENDGAME §9 gap 7).

### Changed
- `poly-agent` version `0.1.0` → `0.2.0`.
- `.gitignore`: ignores git worktrees under `.worktrees/`, the archived `player -clean-/` tree, virtualenvs,
  tool caches, logs and runtime state; negates the templates so `.env.example` / `config.yaml.example`
  can be committed.
- Dropped the self-referential requirement `"poly-agent>=0.2"` from `poly-agent/pyproject.toml` (no such
  distribution exists on PyPI), and added `[tool.setuptools.packages.find] where = ["src"]`.

### Removed
- Root `README.txt` (zero bytes; superseded by `README.md`).

## [0.1.0] — 2026-10-03

Initial import of the three codebases (`poly-agent`, `poly-agent-app`, `mcp-server`) plus the design
docs, docker/firewall infrastructure and secrets migration. See `ENDGAME.md` and
`Development/docs/BUILD-PLAN.md`.
