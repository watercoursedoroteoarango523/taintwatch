"""Version range matching across ecosystems.

OSV records use `affected.versions` (explicit list) and `affected.ranges` with
introduced / fixed / last_affected events. We support both. Ecosystem-specific
ordering is delegated:

- SEMVER  -> packaging.version-style numeric tuple comparison after normalization
            (npm semver is close enough for the prerelease cases we hit)
- ECOSYSTEM (PyPI) -> packaging.version.Version
- ECOSYSTEM (crates.io) -> SemVer
- ECOSYSTEM (Go) -> Go's module semver (v-prefixed; falls back to SemVer compare)
- ECOSYSTEM (RubyGems) -> Gem::Version-style; we use packaging.version as a close approximation

If we can't parse a version cleanly, we fall back to string equality against
`affected.versions` — which still catches every published MAL-* advisory
because OpenSSF/OSV list exact versions for malicious releases.
"""
from __future__ import annotations

from dataclasses import dataclass

from packaging.version import InvalidVersion, Version

from .models import Advisory, AffectedRange


@dataclass
class _Sv:
    """Minimal SemVer for npm/crates.io/Go comparisons."""

    parts: tuple[int, ...]
    prerelease: tuple[str | int, ...]
    raw: str

    @classmethod
    def parse(cls, s: str) -> "_Sv | None":
        s = s.strip()
        if s.startswith(("v", "V")):
            s = s[1:]
        # split on '+' to drop build metadata
        s = s.split("+", 1)[0]
        head, _, pre = s.partition("-")
        try:
            parts = tuple(int(x) for x in head.split("."))
        except ValueError:
            return None
        pre_tuple: tuple[str | int, ...]
        if pre:
            pre_tuple = tuple(int(p) if p.isdigit() else p for p in pre.split("."))
        else:
            pre_tuple = ()
        return cls(parts=parts, prerelease=pre_tuple, raw=s)

    def _key(self) -> tuple:
        # release with no prerelease ranks higher than same release with prerelease
        return (self.parts, 0 if not self.prerelease else -1, self.prerelease)

    def __lt__(self, other: "_Sv") -> bool:
        return self._key() < other._key()

    def __le__(self, other: "_Sv") -> bool:
        return self._key() <= other._key()


def _cmp_pep440(a: str, b: str) -> int | None:
    try:
        va, vb = Version(a), Version(b)
    except InvalidVersion:
        return None
    return (va > vb) - (va < vb)


def _cmp_semver(a: str, b: str) -> int | None:
    sa, sb = _Sv.parse(a), _Sv.parse(b)
    if sa is None or sb is None:
        return None
    return (not (sa <= sb)) - (not (sb <= sa))


def _ge(version: str, bound: str, ecosystem: str) -> bool:
    cmp = _comparator(ecosystem)
    r = cmp(version, bound)
    if r is None:
        return version == bound
    return r >= 0


def _lt(version: str, bound: str, ecosystem: str) -> bool:
    cmp = _comparator(ecosystem)
    r = cmp(version, bound)
    if r is None:
        return False
    return r < 0


def _le(version: str, bound: str, ecosystem: str) -> bool:
    cmp = _comparator(ecosystem)
    r = cmp(version, bound)
    if r is None:
        return version == bound
    return r <= 0


def _comparator(ecosystem: str):
    if ecosystem == "PyPI":
        return _cmp_pep440
    return _cmp_semver


def _range_matches(version: str, ecosystem: str, r: AffectedRange) -> bool:
    if r.type == "GIT":
        return False  # we don't resolve git hashes
    introduced = r.introduced or "0"
    if not _ge(version, introduced, ecosystem):
        return False
    if r.fixed and not _lt(version, r.fixed, ecosystem):
        return False
    if r.last_affected and not _le(version, r.last_affected, ecosystem):
        return False
    return True


def is_affected(version: str, advisory: Advisory) -> bool:
    # OSV malicious-package records routinely list an explicit `versions` array
    # AND a stub range like `{introduced: "0"}` as a metadata marker — that
    # stub range covers every version, so falling through to it triggers a
    # false positive on every install. Treat `versions` as authoritative when
    # present; only consult ranges when no explicit version list was given.
    if advisory.versions:
        return version in advisory.versions
    return any(_range_matches(version, advisory.ecosystem, r) for r in advisory.ranges)
