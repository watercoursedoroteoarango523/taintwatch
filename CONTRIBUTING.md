# Contributing to taintwatch

Pull requests, issue reports, and "I think you misread this OSV record" emails are all welcome. taintwatch is a security tool, so contributions that touch advisory matching, version comparison, or feed parsing get extra scrutiny — see the testing notes below.

## Setting up

```sh
git clone https://github.com/braasdas/taintwatch.git
cd taintwatch
python -m pip install -e ".[dev,toast]"
python -m pytest -q
```

`requires-python>=3.10`. Pure Python — no native build.

## Running it locally

```sh
taintwatch config init --root ~/code
taintwatch feeds update
taintwatch                       # launches the TUI
taintwatch scan --skip-update    # one-shot, no network
```

The local state lives at:

- **Windows** `%LOCALAPPDATA%\taintwatch\state.db`
- **macOS** `~/Library/Application Support/taintwatch/state.db`
- **Linux** `~/.local/share/taintwatch/state.db`

Delete that file to start fresh. The config file is at `<config_dir>/taintwatch/config.toml` (see `taintwatch config path`).

## Project layout

```
taintwatch/
├── src/taintwatch/
│   ├── alerts/         # pluggable channels (stdout, report, discord, toast)
│   ├── feeds/          # one fetcher per source (osv, openssf, aikido)
│   ├── parsers/        # one parser per lockfile format
│   ├── scheduler/      # per-OS autostart installers
│   ├── branding.py     # palette + glyphs from the logo
│   ├── cli.py          # typer entry, subcommand wiring
│   ├── config.py       # TOML loader + defaults
│   ├── discover.py     # repo walk
│   ├── installed.py    # node_modules / site-packages walk
│   ├── models.py       # dataclasses
│   ├── paths.py        # cross-platform XDG-style path helpers
│   ├── scanner.py      # the core matcher
│   ├── state.py        # SQLite DAO
│   ├── tui.py          # Textual app
│   └── version_match.py
├── tests/              # pytest; uses pytest-mock + pytest-asyncio
├── docs/               # per-command + reference docs
└── pyproject.toml
```

## Adding a new lockfile parser

1. Create `src/taintwatch/parsers/<name>.py` exporting `parse(lockfile: Path, repo: Path) -> set[InstalledPkg]`.
2. Register it in `parsers/__init__.py` under `LOCKFILE_PARSERS` (order matters — earlier entries win for the same `seen_kinds` key).
3. Drop a real-world fixture into `tests/fixtures/lockfiles/`.
4. Add a snapshot test in `tests/test_parsers.py`.

## Adding a new feed source

1. Subclass `taintwatch.feeds.base.Fetcher` in `src/taintwatch/feeds/<name>.py`. Override `update(self, conn, *, force=False) -> int`. Normalize each advisory to a `taintwatch.models.Advisory` and call `state.upsert_advisory`.
2. Update `feeds/__init__.py:enabled_fetchers` to register it under a new config flag.
3. Add a flag to `config.FeedsConfig` and update the default-config template in `config.write_default`.
4. Mock the HTTP layer with `respx` in `tests/`. **Do not hit live endpoints in tests.**

## Testing rules

- **Never mock the version matcher in scanner tests.** False positives like the OSV stub-range bug ([commit cb9f71e](../../commit/cb9f71e)) only get caught when the real matcher runs against real-shaped advisory data.
- **Every new feed source needs a regression test that includes one record from a real incident.** Pull a record from [`ossf/malicious-packages`](https://github.com/ossf/malicious-packages) (Apache-2.0) for fixtures.
- **Version-matching changes require fixture coverage from every supported ecosystem** — npm, PyPI, crates.io, Go all have different version semantics that cannot be papered over by a single comparison routine.

## Running tests

```sh
python -m pytest -q
python -m pytest tests/test_scanner_e2e.py -v   # one file
python -m pytest -k "stub_range"                # one test
```

## Style

We don't have a strict style guide. `ruff` is in the dev deps; running `ruff check src/ tests/` is recommended but not enforced in CI yet. Prefer:

- No comments where a name does the work.
- Comments that explain *why*, not *what*.
- Small, single-purpose modules; large files are a code smell.

## Cutting a release (maintainer)

1. Update `CHANGELOG.md`.
2. Bump `version` in `pyproject.toml`.
3. `git commit -am "v0.X.Y" && git tag vX.Y.Z && git push --tags`.
4. The `release.yml` GitHub Action publishes to PyPI via Trusted Publishing (OIDC) — no tokens needed.

## Security disclosures

Don't open a public issue for a security vulnerability in taintwatch itself. See [SECURITY.md](SECURITY.md) for the disclosure process.
