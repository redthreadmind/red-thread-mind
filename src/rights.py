import logging

log = logging.getLogger("rtm.rights")

# Providers allowed in the pipeline. Anything else is blocked.
ENABLED_PROVIDERS = {"pixabay", "internet_archive", "own"}

# Exact license pages accepted for monetized videos. Add a URL only after checking its terms.
ALLOWED_LICENSE_URLS = {
    "https://pixabay.com/service/license/",
    "https://creativecommons.org/publicdomain/zero/1.0/",
    "https://creativecommons.org/publicdomain/mark/1.0/",
    "https://creativecommons.org/licenses/by/4.0/",
    "https://creativecommons.org/licenses/by/3.0/",
}

# Your own assets: you declare ownership in the asset record.
OWN_LICENSE = "own:declared-by-owner"


def _normalize(url):
    u = (url or "").strip().lower().replace("http://", "https://")
    if u and not u.endswith("/"):
        u += "/"
    return u


def check(asset):
    """Return (allowed, reason). Never infers a license from a filename or category."""
    provider = asset.get("provider", "")
    if provider not in ENABLED_PROVIDERS:
        return False, f"provider '{provider}' is not enabled"

    if provider == "own":
        if asset.get("license_url") == OWN_LICENSE:
            return True, "own asset with owner declaration"
        return False, "own asset is missing its owner declaration"

    url = _normalize(asset.get("license_url"))
    if not url:
        return False, "no license evidence"
    if "-nc" in url or "-nd" in url:
        return False, "license forbids commercial use or edits"
    if url not in ALLOWED_LICENSE_URLS:
        return False, "license not on the allowlist; manual review needed"
    return True, "license on allowlist"


def manifest_record(asset, allowed, reason):
    """Evidence kept for every asset in a video's manifest."""
    return {
        "provider": asset.get("provider"),
        "asset_id": asset.get("asset_id"),
        "title": asset.get("title", ""),
        "source_page_url": asset.get("source_page_url", ""),
        "license_url": asset.get("license_url", ""),
        "attribution_required": asset.get("attribution_required", False),
        "allowed": allowed,
        "reason": reason,
    }