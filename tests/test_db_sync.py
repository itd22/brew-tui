"""Regression test for the first-`brew-tui list` IntegrityError:

    IntegrityError: (sqlite3.IntegrityError) UNIQUE constraint failed: packages.name

`RealCellarReader.scan()` can return two `InstalledPackageInfo` for the same formula
name when the real Cellar has more than one version directory for it (e.g. right
after an upgrade, before `brew cleanup`). `BrewDB.sync_from_cellar` must collapse
those to one row instead of trying to INSERT the same primary key twice. No docker
needed — this exercises `sync_from_cellar` directly against a throwaway sqlite file.
"""
from brew_tui.db import BrewDB, InstalledPackageInfo, dedupe_infos_by_name


def test_sync_from_cellar_dedupes_same_name_on_fresh_db(tmp_path):
    db = BrewDB(tmp_path / "brew.db")
    db.create_schema()

    infos = [
        InstalledPackageInfo(name="ripgrep", version="13.0.0", poured_from_bottle=True),
        InstalledPackageInfo(name="ripgrep", version="14.1.0", poured_from_bottle=True),
    ]

    added, updated, removed = db.sync_from_cellar(infos)  # must not raise IntegrityError

    assert added == ["ripgrep"]
    assert updated == []
    assert removed == []

    rows = [r for r in db.all_packages() if r.name == "ripgrep"]
    assert len(rows) == 1
    assert rows[0].version == "14.1.0"
    assert rows[0].status == "installed"


def test_dedupe_infos_by_name_collapses_duplicates_last_wins():
    """Same helper the TUI's package table now uses before building rows — without
    it, `table.add_row(..., key=info.name)` would raise Textual's DuplicateKey for
    the same reason sync_from_cellar used to raise sqlite's IntegrityError."""
    infos = [
        InstalledPackageInfo(name="ripgrep", version="13.0.0"),
        InstalledPackageInfo(name="jq", version="1.7"),
        InstalledPackageInfo(name="ripgrep", version="14.1.0"),
    ]

    deduped = dedupe_infos_by_name(infos)

    assert sorted(info.name for info in deduped) == ["jq", "ripgrep"]
    assert len(deduped) == 2
    ripgrep = next(info for info in deduped if info.name == "ripgrep")
    assert ripgrep.version == "14.1.0"


def test_dedupe_infos_by_name_no_duplicates_is_unchanged():
    infos = [
        InstalledPackageInfo(name="jq", version="1.7"),
        InstalledPackageInfo(name="ripgrep", version="14.1.0"),
    ]

    assert dedupe_infos_by_name(infos) == infos


def test_sync_from_cellar_dedupes_same_name_on_existing_row(tmp_path):
    db = BrewDB(tmp_path / "brew.db")
    db.create_schema()
    db.sync_from_cellar([InstalledPackageInfo(name="ripgrep", version="13.0.0")])

    added, updated, removed = db.sync_from_cellar([
        InstalledPackageInfo(name="ripgrep", version="13.0.0"),
        InstalledPackageInfo(name="ripgrep", version="14.1.0"),
    ])

    assert added == []
    assert updated == ["ripgrep"]
    rows = [r for r in db.all_packages() if r.name == "ripgrep"]
    assert len(rows) == 1
    assert rows[0].version == "14.1.0"
