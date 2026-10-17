from src import rights


def test_pixabay_license_allowed():
    ok, _ = rights.check({"provider": "pixabay",
                          "license_url": "https://pixabay.com/service/license/"})
    assert ok


def test_noncommercial_license_blocked():
    ok, _ = rights.check({"provider": "internet_archive",
                          "license_url": "https://creativecommons.org/licenses/by-nc/4.0/"})
    assert not ok


def test_missing_license_blocked():
    ok, _ = rights.check({"provider": "pixabay", "license_url": ""})
    assert not ok


def test_disabled_provider_blocked():
    ok, _ = rights.check({"provider": "kinocheck",
                          "license_url": "https://pixabay.com/service/license/"})
    assert not ok


def test_own_asset_needs_declaration():
    ok, _ = rights.check({"provider": "own", "license_url": ""})
    assert not ok
    ok, _ = rights.check({"provider": "own", "license_url": rights.OWN_LICENSE})
    assert ok