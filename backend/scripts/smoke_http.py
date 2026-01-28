#!/usr/bin/env python3
"""
HTTP smoke test (requires the API server to be running).

Usage:
  python DEOPLOYMENT/backend/scripts/smoke_http.py --url http://localhost:8080 --admin-key <key>
"""

import argparse
import json
import time
import requests


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8080", help="Base URL (no trailing slash)")
    parser.add_argument("--admin-key", default=None, help="Admin key for admin endpoints")
    args = parser.parse_args()

    base = args.url.rstrip("/")
    s = requests.Session()

    def get(path, **kwargs):
        r = s.get(base + path, timeout=60, **kwargs)
        return r

    def post(path, **kwargs):
        r = s.post(base + path, timeout=60, **kwargs)
        return r

    print("== smoke_http ==")

    r = get("/api/health")
    print("health:", r.status_code)
    r.raise_for_status()

    r = get("/api/search", params={"q": "coffee", "top_n": 3})
    print("search:", r.status_code)
    r.raise_for_status()

    r = get("/api/listings", params={"limit": 1, "offset": 0})
    print("listings:", r.status_code)
    r.raise_for_status()
    before_total = r.json().get("total", 0)

    payload = {
        "title": f"SmokeTestFranchise_{int(time.time())}",
        "sector": "Testing",
        "description": "Created by smoke_http.py",
        "investment_range": "$1k-$2k",
        "location": "Local",
        "tags": ["smoke", "test"],
    }

    # Alias endpoint (no admin key required by default)
    r = post("/api/add/listings", json=payload)
    print("add/listings:", r.status_code)
    r.raise_for_status()

    r = get("/api/listings", params={"limit": 1, "offset": 0})
    r.raise_for_status()
    after_total = r.json().get("total", 0)
    print("listings total:", before_total, "->", after_total)

    if args.admin_key:
        headers = {"X-Admin-API-Key": args.admin_key}
        r = get("/api/admin/stats", headers=headers)
        print("admin/stats:", r.status_code)
        r.raise_for_status()
        print(json.dumps(r.json().get("data", {}), indent=2))

    print("OK (note: models not retrained; call POST /api/admin/retrain when needed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


