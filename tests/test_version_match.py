from __future__ import annotations

from taintwatch.models import Advisory, AffectedRange
from taintwatch.version_match import is_affected


def adv(eco, name, versions=(), ranges=()):
    return Advisory(
        id="MAL-X",
        ecosystem=eco,
        name=name,
        versions=list(versions),
        ranges=list(ranges),
    )


def test_explicit_version_match_npm():
    a = adv("npm", "chalk", versions=["5.6.1"])
    assert is_affected("5.6.1", a)
    assert not is_affected("5.6.2", a)


def test_range_npm():
    a = adv("npm", "x", ranges=[AffectedRange(type="SEMVER", introduced="1.0.0", fixed="2.0.0")])
    assert is_affected("1.5.0", a)
    assert is_affected("1.99.0", a)
    assert not is_affected("0.9.9", a)
    assert not is_affected("2.0.0", a)
    assert not is_affected("2.0.1", a)


def test_range_pypi_pep440():
    a = adv("PyPI", "ultralytics", ranges=[AffectedRange(type="ECOSYSTEM", introduced="8.3.41", fixed="8.3.47")])
    assert is_affected("8.3.41", a)
    assert is_affected("8.3.45", a)
    assert not is_affected("8.3.40", a)
    assert not is_affected("8.3.47", a)


def test_last_affected():
    a = adv("crates.io", "x", ranges=[AffectedRange(type="SEMVER", introduced="0.1.0", last_affected="0.5.0")])
    assert is_affected("0.5.0", a)
    assert not is_affected("0.5.1", a)


def test_go_v_prefix():
    a = adv("Go", "github.com/x/y", versions=["v1.3.1"])
    assert is_affected("v1.3.1", a)


def test_no_match_when_unparseable():
    a = adv("npm", "x", ranges=[AffectedRange(type="SEMVER", introduced="not-a-version")])
    # Should not match, should not crash
    assert not is_affected("1.0.0", a)


def test_stub_range_does_not_override_explicit_versions():
    """Regression: OSV malicious-package records often include both an explicit
    `versions` list and a stub range like `[{introduced: "0"}]`. The stub range
    is a metadata marker, not a real range — it must NOT cause every version
    to match.
    """
    a = adv(
        "npm",
        "@mistralai/mistralai",
        versions=["2.2.4", "2.2.3", "2.2.2"],
        ranges=[AffectedRange(type="SEMVER", introduced="0")],
    )
    assert is_affected("2.2.4", a)
    assert is_affected("2.2.3", a)
    # The real bug: 1.10.0 must NOT match.
    assert not is_affected("1.10.0", a)
    assert not is_affected("3.0.0", a)
    assert not is_affected("0.0.1", a)


def test_open_ended_range_when_no_explicit_versions():
    """If a record genuinely has no `versions` list (e.g. typosquat where every
    published version is bad), the open-ended range SHOULD match everything.
    """
    a = adv("npm", "evil-typosquat", versions=[], ranges=[AffectedRange(type="SEMVER", introduced="0")])
    assert is_affected("0.0.1", a)
    assert is_affected("99.99.99", a)
