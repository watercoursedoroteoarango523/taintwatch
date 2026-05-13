<p align="center">
  <img src="assets/taintwatch-logo.png" alt="taintwatch logo — a cream spiral with one tainted lime-green petal pierced by a black pin" width="260" />
</p>

<h1 align="center">taintwatch</h1>

<p align="center"><em>Your dependencies are tainted. So is everyone else's logo.</em></p>

---


`taintwatch` scans your local codebases for **known-compromised package versions** — the ones from Shai-Hulud, chalk/debug, Nx s1ngularity, Ultralytics, and the next one that lands tomorrow morning while you're asleep. It pulls real-time feeds from OSV.dev (`MAL-*` records), the OpenSSF malicious-packages repository, and Aikido Intel; matches every lockfile and every installed `node_modules` / `site-packages` directory under the roots you configure; and yells at you on Discord or via a desktop toast when one of your repos has malware on disk.

It does **not** run anything in the background until you ask it to. Nothing is auto-installed at install time. Same consent model as `pre-commit install`.

## Install

**macOS / Linux**
```sh
curl -sSL https://raw.githubusercontent.com/braasdas/taintwatch/master/install.sh | sh
```

**Windows (PowerShell)**
```powershell
irm https://raw.githubusercontent.com/braasdas/taintwatch/master/install.ps1 | iex
```

**Any platform with Python 3.10+**
```sh
pipx install taintwatch        # recommended
# or: pip install --user taintwatch
```

Then on first run:
```sh
taintwatch config init
taintwatch feeds update
taintwatch scan
```

## Three sound tiers

When taintwatch finds something, the desktop toast plays a different sound depending on how scared you should be:

| Severity   | Trigger                                                        | Windows           | macOS    | Linux                           |
|------------|----------------------------------------------------------------|-------------------|----------|---------------------------------|
| `CRITICAL` | Compromised code is **installed on disk** in `node_modules/` or `site-packages/` — it can execute on your next build, dev server, or import. | Looping alarm     | Sosumi   | `dialog-warning.oga` + urgency=critical |
| `HIGH`     | Compromised version pinned in a lockfile. Next `npm ci` / `pip install -r` will pull it. | Default ding      | Glass    | `message-new-instant.oga` + urgency=normal |
| `INFO`     | Informational (e.g. a previously-flagged repo is now clean).   | Short reminder    | Tink     | `complete.oga` + urgency=low    |

The Discord webhook also escalates: `@here` ping only on `CRITICAL`; silent posts otherwise.

## What it does

- Pulls from three free, no-auth, redistributable feeds: OSV.dev bulk mirror, OpenSSF `malicious-packages`, Aikido Intel.
- Parses lockfiles for **npm, yarn, pnpm, pip (requirements + Pipfile), poetry, Cargo, Go modules**.
- Walks `node_modules/` and `site-packages/` to find malware that's *installed* but no longer in your lockfile (the Shai-Hulud case where you rolled back the lockfile but didn't `rm -rf node_modules`).
- Stores everything in one local SQLite file. No cloud, no telemetry, no account.
- Diffs scans so it alerts only on *new* hits.
- Optional opt-in autostart via Windows Task Scheduler, macOS launchd, or Linux systemd-user — one explicit command (`taintwatch install-autostart`), one explicit uninstall.

## CLI

```
taintwatch scan [--root PATH] [--deep/--no-deep] [--skip-update]
taintwatch watch                          # foreground daemon loop
taintwatch feeds update | status
taintwatch report show [--last N]
taintwatch config init | path
taintwatch install-autostart   [--interval 60] [--dry-run]
taintwatch uninstall-autostart
taintwatch autostart-status
```

## Why this exists

In 2025, ReversingLabs logged a 73% YoY jump in malicious open-source packages. Sonatype blocked 454,600 new ones. The Shai-Hulud worm self-replicated across ~500 npm packages in 72 hours (twice — September and November). The chalk/debug compromise sat live in ~2 billion weekly-download packages for two and a half hours. The Nx attack weaponized your AI CLIs against you. The xz backdoor took ~2.5 years of social engineering and was caught by accident because somebody noticed sshd was 500ms slower.

You cannot keep up by reading Twitter.

## License

MIT for the code. Feed data has its own per-source licensing — OSV records are CC-BY 4.0 / Apache-2.0 (per record), OpenSSF data is Apache-2.0, and Aikido Intel's data license is not posted, so we use it only for local lookup. If your org needs redistributable-only sources, set `[feeds] aikido = false` in your config.

## Releasing (maintainer notes)

PyPI publish uses [Trusted Publishing](https://docs.pypi.org/trusted-publishers/) — no API tokens. Tag and push:

```sh
git tag v0.1.1
git push origin v0.1.1
```

The `.github/workflows/release.yml` workflow builds the sdist + wheel with `hatch build` and publishes via OIDC.
