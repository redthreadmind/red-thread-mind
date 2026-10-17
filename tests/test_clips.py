from src import clips, config


def fake(asset_id, tags, w=1920, dur=5):
    return {"provider": "pixabay", "asset_id": asset_id, "tags": tags,
            "w": w, "duration": dur, "url": "x", "source_page_url": "",
            "license_url": clips.PIXABAY_LICENSE_URL}


def test_prefers_relevant_clip(monkeypatch):
    monkeypatch.setattr(clips, "_search",
                        lambda q: [fake("a", "gym weights"), fake("b", "man running sunrise")])
    pick = clips._pick("man running", used=set(), strict=True)
    assert pick["asset_id"] == "b"


def test_skips_already_used_clip(monkeypatch):
    monkeypatch.setattr(clips, "_search",
                        lambda q: [fake("a", "man running"), fake("b", "man running")])
    pick = clips._pick("man running", used={"a"}, strict=True)
    assert pick["asset_id"] == "b"


def test_strict_rejects_irrelevant_clip(monkeypatch):
    monkeypatch.setattr(clips, "_search", lambda q: [fake("a", "ocean waves")])
    assert clips._pick("man running", used=set(), strict=True) is None


def test_nonstrict_accepts_irrelevant_clip(monkeypatch):
    monkeypatch.setattr(clips, "_search", lambda q: [fake("a", "ocean waves")])
    assert clips._pick("man running", used=set(), strict=False)["asset_id"] == "a"


def test_cache_avoids_repeat_requests(monkeypatch):
    calls = []

    def fake_get(url, params):
        calls.append(url)
        return {"hits": []}

    monkeypatch.setattr(clips, "_get", fake_get)
    monkeypatch.setattr(clips.time, "sleep", lambda s: None)
    monkeypatch.setattr(config, "PIXABAY_API_KEY", "test-key")
    clips._search_cache.clear()

    clips._search("man running")
    clips._search("man running")
    assert len(calls) == 1