# Security Policy

## Supported versions

taintwatch is pre-1.0. Only the latest published version on PyPI is supported.

## Reporting a vulnerability

If you find a security issue **in taintwatch itself** (an exploit in the scanner, the feed fetchers, the alert channels, the autostart installer, etc.), please report it privately:

- Email: **benjaminb.barlick@gmail.com** with subject prefix `[taintwatch security]`
- Or use GitHub's [private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability) on the repo

Include:
- The version of taintwatch you tested against (`taintwatch --version`)
- Steps to reproduce
- The impact you believe a malicious party could achieve
- Optional: a suggested fix

We aim to acknowledge reports within 72 hours and to ship a fix or mitigation within 14 days for high-severity issues.

## Out of scope

- **Reports of malicious packages in the wild.** Those go to the upstream registry (npmjs.com, pypi.org, etc.) and to the advisory databases we ingest:
  - OSV.dev: https://github.com/google/osv.dev/issues
  - OpenSSF malicious-packages: https://github.com/ossf/malicious-packages
  - Aikido Intel: https://intel.aikido.dev/
- **False-positive advisory matches** — these are bugs but not security vulnerabilities. Open a normal GitHub issue with the advisory ID and the version that incorrectly matched.
- **False-negative matches** (a known-malicious package not detected) — also a normal bug report unless the cause is a deliberately introduced flaw in taintwatch.

## Threat model

taintwatch is a **local-only** tool. It:

- Pulls feed data over HTTPS from OSV.dev, GitHub (OpenSSF tarball), and Aikido. A network adversary who can MITM these would be able to plant a false-negative (hide a real malicious advisory) or a false-positive (block a legitimate package).
- Reads lockfiles and package metadata from the filesystem. It does not execute any of that code.
- Writes a SQLite database and report files to the user's local data directory.
- Optionally posts to a user-configured Discord webhook.
- Does not collect or transmit any telemetry.

If you find a way to make taintwatch execute attacker-controlled code (e.g. via a malformed lockfile, a hostile feed payload, or a crafted advisory reference URL) — that's a vulnerability we want to know about.
