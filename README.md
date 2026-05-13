# taintwatch

> Your dependencies are tainted. So is everyone else's logo.

`taintwatch` scans your local codebases for **known-compromised package versions** — the ones from Shai-Hulud, chalk/debug, Nx s1ngularity, Ultralytics, and the next one that lands tomorrow morning while you're asleep. It pulls real-time feeds from OSV.dev (`MAL-*` records), the OpenSSF malicious-packages repository, and Aikido Intel; matches every lockfile and every installed `node_modules` / `site-packages` directory under the roots you configure; and yells at you on Discord or via a desktop toast when one of your repos has malware on disk.

It does **not** run anything in the background until you ask it to. Nothing is auto-installed at `pipx install` time. The same consent model as `pre-commit install`.

## Install

```
pipx install taintwatch
taintwatch config init
taintwatch feeds update
taintwatch scan
```

## What it does

- Pulls from three free, no-auth, redistributable feeds: OSV.dev bulk mirror, OpenSSF `malicious-packages`, Aikido Intel.
- Parses lockfiles for **npm, yarn, pnpm, pip (requirements + Pipfile), poetry, Cargo**.
- Walks `node_modules/` and `site-packages/` to find malware that's *installed* but no longer in your lockfile (the Shai-Hulud case where you rolled back the lockfile but didn't `rm -rf node_modules`).
- Stores everything in one local SQLite file. No cloud, no telemetry, no account.
- Diffs scans so it alerts only on *new* hits.
- Optional opt-in autostart via Windows Task Scheduler, macOS launchd, or Linux systemd-user — one explicit command (`taintwatch install-autostart`), one explicit uninstall.

## Why this exists

In 2025, ReversingLabs logged a 73% YoY jump in malicious open-source packages. Sonatype blocked 454,600 new ones. The Shai-Hulud worm self-replicated across ~500 npm packages in 72 hours (twice — September and November). The chalk/debug compromise sat live in ~2 billion weekly-download packages for two and a half hours. The Nx attack weaponized your AI CLIs against you. The xz backdoor took ~2.5 years of social engineering and was caught by accident because somebody noticed sshd was 500ms slower.

You cannot keep up by reading Twitter.

## License

MIT for the code. Feed data has its own per-source licensing — OSV records are CC-BY 4.0 / Apache-2.0 (per record), OpenSSF data is Apache-2.0, and Aikido Intel's data license is not posted, so we use it only for local lookup. If your org needs redistributable-only sources, set `[feeds] aikido = false` in your config.
