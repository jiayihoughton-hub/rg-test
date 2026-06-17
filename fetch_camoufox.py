"""Fetch the Camoufox browser + geoip db, authenticating GitHub API calls.

`camoufox fetch` hits api.github.com (browser release + GeoLite mmdb release +
addons) UNauthenticated -> on CI those calls get 403 rate-limited (worse with a
40-job matrix). We monkeypatch requests to attach the workflow GITHUB_TOKEN to
any api.github.com request (1000 req/hr authenticated), then run the fetch.
Release-asset downloads go to a different host and are left untouched.
"""
import os

import requests

_token = (os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN") or "").strip()
if _token:
    _orig = requests.sessions.Session.request

    def _patched(self, method, url, *args, **kwargs):
        if "api.github.com" in str(url):
            headers = dict(kwargs.get("headers") or {})
            headers.setdefault("Authorization", f"Bearer {_token}")
            kwargs["headers"] = headers
        return _orig(self, method, url, *args, **kwargs)

    requests.sessions.Session.request = _patched
    print("[fetch_camoufox] GitHub API calls authenticated via token")
else:
    print("[fetch_camoufox] no GITHUB_TOKEN; fetching unauthenticated (may rate-limit)")

from camoufox.__main__ import cli

cli.main(["fetch"], standalone_mode=False)
print("[fetch_camoufox] done")
