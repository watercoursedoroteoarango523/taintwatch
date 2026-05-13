# Feed sources

taintwatch matches installed package versions against three feeds. All three are free, no-auth, and redistributable for local lookup; together they triangulate so a false-negative in one is usually caught by another.

## OSV.dev bulk mirror

**URL:** `https://osv-vulnerabilities.storage.googleapis.com/<ECOSYSTEM>/all.zip`
**License:** per-record, mostly CC-BY 4.0 / Apache-2.0
**Cadence:** continuous; records appear minutes-to-hours after upstream publication
**Ecosystems:** npm, PyPI, crates.io, Go, RubyGems (taintwatch v1 set)
**Tag:** `osv`

OSV (Open Source Vulnerabilities) is Google's aggregator. It ingests GHSA, PyPA, RustSec, AND the OpenSSF malicious-packages feed. taintwatch filters OSV down to **`MAL-*` prefixed records** — the malicious-package advisories — and ignores ordinary CVEs. (`npm audit` and `pip-audit` cover CVEs already.)

This is the backbone. If you only enable one feed, enable this one.

## OpenSSF malicious-packages archive

**URL:** `https://github.com/ossf/malicious-packages/archive/refs/heads/main.tar.gz`
**License:** Apache-2.0 (fully redistributable)
**Cadence:** daily+
**Ecosystems:** npm, PyPI, RubyGems, crates.io, NuGet, Packagist — malicious-only
**Tag:** `openssf`

OpenSSF ingests automated sources (Checkmarx, ReversingLabs, Datadog, Stacklok) and human-curated submissions. OSV mirrors this, so they overlap heavily, but having OpenSSF as a redundant source means taintwatch keeps working if OSV's bucket has an outage.

## Aikido Intel

**URL:** `https://malware-list.aikido.dev/malware_predictions.json` (npm) + `/malware_pypi.json` (PyPI)
**License:** not formally posted — taintwatch uses for local lookup only
**Cadence:** real-time
**Ecosystems:** npm, PyPI
**Tag:** `aikido`

Aikido publishes their malware classifier output. It's often *the* fastest signal during a live incident — sometimes hours ahead of GHSA on novel waves like Shai-Hulud. Coverage is narrower (npm + PyPI) but the latency edge is real.

Because the data license isn't posted, taintwatch defaults to local-only use. If your org needs strictly-redistributable feeds, set `[feeds] aikido = false`. OSV + OpenSSF still cover the same incidents at slightly higher latency.

## Schemas

OSV and OpenSSF records are in [OSV schema](https://ossf.github.io/osv-schema/). Aikido records are a flat JSON list; taintwatch normalizes them into OSV-shaped advisories at ingest. The local cache stores everything under one `advisories` table keyed by `id`.

## What we DO NOT pull

- **CVE / vulnerability advisories** that aren't malicious-package events. Use `npm audit` / `pip-audit` / `cargo audit` / `osv-scanner` for those.
- **Yanked packages** with no malicious-flag attached.
- **GitHub Dependabot alerts** — they cover roughly the same data as the GHSA advisory database (which OSV ingests), but Dependabot is GitHub-side and not a feed we can pull locally.

## Adding a new feed

See [CONTRIBUTING.md](../CONTRIBUTING.md#adding-a-new-feed-source). Short version: subclass `taintwatch.feeds.base.Fetcher`, register it under a new config flag, never hit live endpoints in tests.
