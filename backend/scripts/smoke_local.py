#!/usr/bin/env python3
"""
Local smoke test (no HTTP server required).

Runs the core initialization path:
- Load dataset.json
- Load models (GCS->local) or train from scratch
- Build SearchService
- Execute a few searches/recommendations

Usage:
  python -m backend.scripts.smoke_local
  (or) python DEOPLOYMENT/backend/scripts/smoke_local.py
"""

import os
import sys
from pathlib import Path

# Allow running as a script from repo root
THIS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = THIS_DIR.parent
if str(BACKEND_DIR.parent) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR.parent))

from backend.src.core.config import config
from backend.src.models.model_manager import ModelManager
from backend.src.services.data_service import DataService
from backend.src.services.search_service import SearchService


def main() -> int:
    print("== smoke_local ==")
    print(f"DATA_PATH: {config.DATA_PATH}")
    print(f"MODELS_DIR: {config.MODELS_DIR}")
    print(f"STORAGE_TYPE: {config.STORAGE_TYPE}")

    ds = DataService(config.DATA_PATH)
    if not ds.load_data():
        raise SystemExit("Failed to load dataset")

    mm = ModelManager()
    if not mm.load_models():
        print("Models not found; training from scratch...")
        mm.initialize_models(ds.get_all_texts())

    ss = SearchService(mm, ds.listings)

    # Search
    results = ss.hybrid_search("coffee", top_n=3, semantic_weight=0.6)
    assert isinstance(results, list)
    print(f"Search results: {len(results)}")
    if results:
        print(f"Top title: {results[0].get('title')}")

    # Recommendations (best-effort)
    if ds.listings and isinstance(ds.listings[0], dict) and "id" in ds.listings[0]:
        listing_id = ds.listings[0]["id"]
        recs = ss.get_recommendations(int(listing_id), top_n=3)
        assert isinstance(recs, list)
        print(f"Recommendations: {len(recs)}")

    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


