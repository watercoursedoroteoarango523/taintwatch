# Severity tiers

taintwatch classifies every batch of new hits into one of three tiers. The tier drives the toast sound, the Discord embed color, the stdout table color, and whether the Discord channel gets `@here`-pinged.

## CRITICAL

**Trigger:** At least one hit's `source == "installed"`. That means taintwatch found the malicious package's actual code in a `node_modules/` or `site-packages/` directory on disk — *not* just a reference in a lockfile.

**Implication:** The next time anything in that repo runs (a dev server, a build script, a test, an editor that imports a config), the malicious code can execute. This is the worst case.

| Channel | Treatment |
|---|---|
| Toast (Windows) | `audio.LoopingAlarm` (loops until dismissed) |
| Toast (macOS) | `sound name "Sosumi"` |
| Toast (Linux) | `paplay …/dialog-warning.oga` + `notify-send --urgency=critical` |
| Discord | Red embed (`#C0392B`) + `@here` ping |
| Stdout | `bold #FF4D4D` table title + bold-red `installed` cell |
| Report file | `◉⟶ CRITICAL` badge at the top of the markdown |

## HIGH

**Trigger:** Hits exist but every one of them is `source == "lockfile"`. The malicious version is pinned in a `package-lock.json` / `Cargo.lock` / `poetry.lock` / etc. but is not currently installed on disk.

**Implication:** The next `npm ci` / `pip install -r` / `cargo build` will pull the malicious package. You have until then to fix it.

| Channel | Treatment |
|---|---|
| Toast (Windows) | `audio.Default` |
| Toast (macOS) | `sound name "Glass"` |
| Toast (Linux) | `paplay …/message-new-instant.oga` + `notify-send --urgency=normal` |
| Discord | Amber embed (`#E67E22`), silent post (no ping) |
| Stdout | `bold #FFB85F` table title + amber `lockfile` cell |
| Report file | `◉⟶ HIGH` badge |

## INFO

**Trigger:** No new hits this run. Reserved for future "previously-flagged repo cleared" alerts and ambient signals; v1 does not actually fire INFO alerts by default.

| Channel | Treatment |
|---|---|
| Toast | Short reminder sound (Windows: `audio.Reminder`, macOS: `Tink`, Linux: `complete.oga` + low urgency) |
| Discord | Blue embed (`#3498DB`), silent |
| Stdout | `bold #5BB52D` |

## Customizing

There's no per-tier override in v1. If you find the sound mapping wrong for your environment, file an issue with a concrete suggestion. The mapping lives in `src/taintwatch/alerts/toast.py` if you want to fork and edit locally.

## Why these specific signals

- **Loop-on-CRITICAL only.** A looping alarm for a lockfile-only hit would condition you to dismiss it without reading. The alarm needs to mean "drop what you're doing." Anything less should be a single chime you can ignore for an hour.
- **`@here` ping on CRITICAL only.** Same logic. Channel notification overhead has to map to actual urgency.
- **Color: red breaks the cream/lime scheme on purpose.** Every other state lives inside the brand palette; red is reserved for the one case where pattern-recognition has to win against tunnel vision.
