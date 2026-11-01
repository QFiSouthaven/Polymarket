# Contributing — how work moves through this repo

This project is built in small, provable iterations. The rules below exist to keep that possible
without drift: the product anchor is [ENDGAME.md](ENDGAME.md), the phase plan is
[Development/docs/BUILD-PLAN.md](Development/docs/BUILD-PLAN.md), and the live backlog is
[Development/docs/ROADMAP.md](Development/docs/ROADMAP.md).

## 1. Doc hierarchy (who wins an argument)

1. `ENDGAME.md` — product intent, architecture, module contracts. If it conflicts with a README, the
   README is stale; if it conflicts with code, either the code is wrong or ENDGAME needs updating in
   the same PR.
2. `Development/docs/BUILD-PLAN.md` — what gets built next and the hard risk limits.
3. `Development/docs/DATA-SAFETY.md` (Number Rule) + `API-ROUTING.md` — non-negotiable data/API rules.
4. `Development/docs/ROADMAP.md` — current position, blockers, iteration log.
5. Anything else (`README.md`, per-package READMEs) — explanatory only; never authoritative.

## 2. Branches & worktrees

- `main` is the integration branch and must always install, import and pass the test suite.
- Work on short-lived branches: `feat/<scope>-<summary>`, `fix/<scope>-<summary>`,
  `docs/<summary>`, `chore/<summary>`. Agent-driven sessions may use a `bionic/` prefix.
- Parallel worktrees live in `.worktrees/` (git-ignored, never committed):

  ```bash
  git worktree add .worktrees/<short-name> -b feat/engine-restart-resume
  # ...work, commit...
  git worktree remove .worktrees/<short-name>     # keep metadata tidy
  git worktree prune                              # after moving/renaming the repo folder
  ```

  `git worktree list` should only ever show paths that exist. If the repo directory is moved or
  renamed, stale registrations must be pruned — this already happened once (the repo moved from
  `F:/PolyMarket` to `F:/polym-saves/PolyMarket`).

## 3. Commits

Conventional Commit subjects, scoped to the package you touched:

```
fix(risk_manager): reject when stop-loss distance exceeds max exposure
feat(strategies): wire BRTI reference price into _crypto_edge_estimate()
chore(repo): add CI workflow for pytest suites
docs(ENDGAME): record deviation from §4 executor contract
```

- Reference the anchor doc in the body: `→ ENDGAME.md §4` / `→ BUILD-PLAN.md Phase 1`.
- Explain *why* in the body; the diff already shows *what*. Measured evidence ("before: BackendUnavailable,
  after: Would install poly-agent-0.2.0") is worth more than adjectives.
- One logical change per commit. Never mix formatting churn with behaviour changes.

## 4. Pull-request gate (definition of done)

- [ ] `python -m pip install -e ./poly-agent` and `-e "./mcp-server[dev]"` succeed on a clean env.
- [ ] `cd poly-agent && python -m pytest tests -q` — no new failures vs the ROADMAP baseline.
- [ ] `cd mcp-server && python -m pytest tests -q` — same.
- [ ] No secret in the diff: `.env`, `config.yaml`, keys, tokens (see [SECURITY.md](SECURITY.md)).
- [ ] New endpoint? `Development/docs/API-ROUTING.md` updated **first** (auth layer, timeout, rate limit).
- [ ] Money values go through the Number Rule (`DATA-SAFETY.md`); no new `float` for price/size.
- [ ] Any order path still passes through `risk_manager.approve()` — a bypass is a security bug.
- [ ] New dependency? It appears in `pyproject.toml` (and `requirements.txt` stays consistent with it).
- [ ] `Development/docs/ROADMAP.md` updated: blocker closed/opened, iteration log line appended.
- [ ] User-visible or contract change? `CHANGELOG.md` updated under **Unreleased**.

## 5. Testing conventions

- Engine tests live in `poly-agent/tests/`; markers are registered in `poly-agent/tests/pytest.ini`:
  `risk`, `exec`, `decimal`, `idempotent`, `strategy`, `slow`. Default runs skip `slow` and
  `strategy` integration work.
- Money-related tests must run under `--decimal-check` (see `tests/conftest.py`) to catch float leakage.
- A fix is not done until a test fails without it. For `risk_manager` the target from ENDGAME §9 is
  **≥ 10 tests** covering approve/reject paths — that suite is currently empty, so start there.

## 6. Line endings & formatting

`.gitattributes` pins the policy: LF in the index and for all sources; CRLF only for `.bat`/`.cmd`/`.ps1`.
The system gitconfig on Windows sets `core.autocrlf=true`, which is why the attribute file exists —
do not fight it with per-machine overrides. Ruff config lives in `poly-agent/pyproject.toml`
(`line-length = 120`, `target-version = "py310"`).

## 7. Versioning & releases

SemVer per package (`poly-agent`, `polyagent-mcp-server`). Bump the version in the same commit that
changes behaviour, and record it in `CHANGELOG.md`. No tag is published until the ENDGAME §9 endstate
checklist passes; tags are annotated: `git tag -a v0.3.0 -m "Phase 1: first preprod trade"`.
