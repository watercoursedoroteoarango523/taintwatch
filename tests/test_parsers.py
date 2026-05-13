from __future__ import annotations

from pathlib import Path

from taintwatch.parsers import cargo, gomod, npm, pip, pnpm, poetry, yarn

FIXTURES = Path(__file__).parent / "fixtures" / "lockfiles"


def test_npm_lockfile_v3_packages_map():
    repo = FIXTURES
    pkgs = npm.parse(FIXTURES / "package-lock.json", repo)
    by_name = {(p.name, p.version) for p in pkgs}
    assert ("chalk", "5.6.1") in by_name
    assert ("debug", "4.4.2") in by_name
    assert ("@ctrl/tinycolor", "4.1.1") in by_name
    # nested under tinycolor
    assert ("lodash", "4.17.21") in by_name


def test_yarn_lockfile_classic():
    pkgs = yarn.parse(FIXTURES / "yarn.lock", FIXTURES)
    by_name = {(p.name, p.version) for p in pkgs}
    assert ("chalk", "5.6.1") in by_name
    assert ("@ctrl/tinycolor", "4.1.1") in by_name


def test_pnpm_lockfile():
    pkgs = pnpm.parse(FIXTURES / "pnpm-lock.yaml", FIXTURES)
    by_name = {(p.name, p.version) for p in pkgs}
    assert ("chalk", "5.6.1") in by_name
    assert ("@ctrl/tinycolor", "4.1.1") in by_name


def test_pip_requirements():
    pkgs = pip.parse_requirements(FIXTURES / "requirements.txt", FIXTURES)
    by_name = {(p.name, p.version) for p in pkgs}
    assert ("ultralytics", "8.3.41") in by_name
    assert ("requests", "2.32.3") in by_name
    # name canonicalization
    assert ("some-package", "1.0.0") in by_name


def test_poetry_lockfile():
    pkgs = poetry.parse(FIXTURES / "poetry.lock", FIXTURES)
    by_name = {(p.name, p.version) for p in pkgs}
    assert ("ultralytics", "8.3.41") in by_name


def test_cargo_lockfile():
    pkgs = cargo.parse(FIXTURES / "Cargo.lock", FIXTURES)
    by_name = {(p.name, p.version) for p in pkgs}
    assert ("serde", "1.0.203") in by_name
    assert ("tokio", "1.38.0") in by_name


def test_gomod_lockfile():
    pkgs = gomod.parse(FIXTURES / "go.sum", FIXTURES)
    by_name = {(p.name, p.version) for p in pkgs}
    assert ("github.com/boltdb-go/bolt", "v1.3.1") in by_name
    assert ("github.com/stretchr/testify", "v1.7.0") in by_name
    # ensure /go.mod suffix stripped
    for _, v in by_name:
        assert not v.endswith("/go.mod")
