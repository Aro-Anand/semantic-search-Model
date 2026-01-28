"""
API Routes Module

This module defines all API endpoints for the Semantic Search API.

Endpoints:
    GET /api/health - System health check
    GET /api/search - Hybrid search
    GET /api/recommend/<id> - Get recommendations
    GET /api/autocomplete - Autocomplete suggestions
    GET /api/filters - Get available filters
    GET /api/listings - Get all listings with pagination
    GET /api/admin/storage-info - Storage information
    POST /api/admin/retrain - Trigger model retraining
    GET / - API information

Example:
    >>> from backend.src.api.routes import create_routes
    >>> app = Flask(__name__)
    >>> create_routes(app, model_manager, data_service, search_service)
"""

import logging
from datetime import datetime, UTC
from flask import request, jsonify, Blueprint
from typing import Any, Dict

from ..core.config import config
from ..utils.timing import timing_decorator
from .deps import error_handler, require_ready, require_admin

logger = logging.getLogger(__name__)

# Create blueprint for API routes
api_bp = Blueprint('api', __name__)

# Global service instances (will be set by main.py)
model_manager = None
data_service = None
search_service = None


def init_routes(mm, ds, ss):
    """
    Initialize routes with service instances.
    
    Args:
        mm: ModelManager instance
        ds: DataService instance
        ss: SearchService instance
    """
    global model_manager, data_service, search_service
    model_manager = mm
    data_service = ds
    search_service = ss


@api_bp.route('/health', methods=['GET'])
@error_handler
def health() -> tuple[Dict[str, Any], int]:
    """
    System health check endpoint.
    
    Returns system status, version information, deployment details,
    model status, and data statistics.
    
    Returns:
        tuple: JSON response and HTTP status code.
        
    Example Response:
        {
            "status": "healthy",
            "timestamp": "2024-01-25T10:30:00Z",
            "version": "3.0.0-gcp",
            "deployment": {...},
            "models": {...},
            "data": {...}
        }
    """
    from .deps import system_ready
    
    storage_info = model_manager.get_storage_info() if model_manager else {}
    
    return jsonify({
        "status": "healthy" if system_ready else "initializing",
        "timestamp": datetime.now(UTC).isoformat(),
        "version": "3.0.0-gcp",
        "deployment": {
            "environment": config.DEPLOYMENT_ENV,
            "is_cloud_run": config.is_cloud_run(),
            "storage_type": config.STORAGE_TYPE
        },
        "models": {
            "use": "loaded" if model_manager.use_model else "not loaded",
            "tfidf": "loaded" if model_manager.tfidf_vectorizer else "not loaded",
            "faiss": model_manager.faiss_index.ntotal if model_manager.faiss_index else 0
        },
        "data": {
            "listings": len(data_service.listings),
            "sectors": len(data_service.metadata['sectors']),
            "tags": len(data_service.metadata['tags']),
            "locations": len(data_service.metadata['locations'])
        },
        "storage": storage_info
    })


@api_bp.route('/search', methods=['GET'])
@error_handler
@timing_decorator
@require_ready
def search() -> tuple[Dict[str, Any], int]:
    """
    Hybrid search endpoint combining semantic and keyword search.
    
    Query Parameters:
        q (str, required): Search query string.
        top_n (int, optional): Number of results to return (default: 10, max: 50).
        semantic_weight (float, optional): Weight for semantic search 0-1 (default: 0.6).
        sector (str, optional): Filter by sector.
        location (str, optional): Filter by location.
        tags (str, optional): Comma-separated tags to filter by.
    
    Returns:
        tuple: JSON response with search results and HTTP status code.
        
    Example Response:
        {
            "query": "coffee franchise",
            "results": [{...}, {...}],
            "total": 10,
            "timestamp": "2024-01-25T10:30:00Z"
        }
    """
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({"error": "Query 'q' required"}), 400
    
    top_n = min(int(request.args.get('top_n', config.DEFAULT_TOP_N)), config.MAX_TOP_N)
    semantic_weight = float(request.args.get('semantic_weight', config.SEMANTIC_WEIGHT))
    
    results = search_service.hybrid_search(query, top_n * 2, semantic_weight)
    
    # Apply filters
    sector = request.args.get('sector')
    location = request.args.get('location')
    tags = request.args.get('tags', '').split(',') if request.args.get('tags') else None
    
    if sector or location or tags:
        filtered = []
        for r in results:
            if sector and r.get('sector', '').lower() != sector.lower():
                continue
            if location and location.lower() not in r.get('location', '').lower():
                continue
            if tags and not any(t.lower() in [x.lower() for x in r.get('tags', [])] for t in tags):
                continue
            filtered.append(r)
        results = filtered[:top_n]
    else:
        results = results[:top_n]
    
    return jsonify({
        "query": query,
        "results": results,
        "total": len(results),
        "timestamp": datetime.now(UTC).isoformat()
    })


@api_bp.route('/recommend/<int:listing_id>', methods=['GET'])
@error_handler
@timing_decorator
@require_ready
def recommend(listing_id: int) -> tuple[Dict[str, Any], int]:
    """
    Get franchise recommendations based on a listing ID.
    
    Path Parameters:
        listing_id (int): ID of the listing to get recommendations for.
    
    Query Parameters:
        top_n (int, optional): Number of recommendations (default: 5, max: 20).
        sector_filter (bool, optional): Filter to same sector (default: true).
    
    Returns:
        tuple: JSON response with recommendations and HTTP status code.
        
    Example Response:
        {
            "listing_id": 42,
            "recommendations": [{...}, {...}],
            "total": 5,
            "timestamp": "2024-01-25T10:30:00Z"
        }
    """
    top_n = min(int(request.args.get('top_n', 5)), 20)
    sector_filter = request.args.get('sector_filter', 'true').lower() == 'true'
    
    results = search_service.get_recommendations(listing_id, top_n, sector_filter)
    
    return jsonify({
        "listing_id": listing_id,
        "recommendations": results,
        "total": len(results),
        "timestamp": datetime.now(UTC).isoformat()
    })


@api_bp.route('/autocomplete', methods=['GET'])
@error_handler
@require_ready
def autocomplete() -> tuple[Dict[str, Any], int]:
    """
    Autocomplete suggestions endpoint.
    
    Query Parameters:
        q (str, required): Partial query string.
        max (int, optional): Maximum suggestions to return (default: 8, max: 20).
    
    Returns:
        tuple: JSON response with suggestions and HTTP status code.
        
    Example Response:
        {
            "query": "cof",
            "suggestions": [
                {"text": "Coffee Shop", "type": "title", "category": "Food & Beverage"},
                ...
            ],
            "total": 5
        }
    """
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
    
    max_suggestions = min(int(request.args.get('max', 8)), 20)
    suggestions = search_service.autocomplete(query, max_suggestions)
    
    return jsonify({
        "query": query,
        "suggestions": suggestions,
        "total": len(suggestions)
    })


@api_bp.route('/filters', methods=['GET'])
@error_handler
@require_ready
def get_filters() -> tuple[Dict[str, Any], int]:
    """
    Get available filter options.
    
    Returns all unique sectors, locations, and tags from the dataset.
    
    Returns:
        tuple: JSON response with filter options and HTTP status code.
        
    Example Response:
        {
            "sectors": ["Food & Beverage", "Retail", ...],
            "locations": ["New York", "California", ...],
            "tags": ["coffee", "fast-food", ...],
            "total_listings": 150
        }
    """
    return jsonify({
        "sectors": sorted(list(data_service.metadata['sectors'])),
        "locations": sorted(list(data_service.metadata['locations'])),
        "tags": sorted(list(data_service.metadata['tags'])),
        "total_listings": len(data_service.listings)
    })


@api_bp.route('/listings', methods=['GET'])
@error_handler
@require_ready
def get_listings() -> tuple[Dict[str, Any], int]:
    """
    Get all listings with pagination.
    
    Query Parameters:
        limit (int, optional): Number of listings per page (default: 100, max: 500).
        offset (int, optional): Number of listings to skip (default: 0).
    
    Returns:
        tuple: JSON response with paginated listings and HTTP status code.
        
    Example Response:
        {
            "listings": [{...}, {...}],
            "total": 150,
            "limit": 100,
            "offset": 0,
            "has_more": true
        }
    """
    limit = min(int(request.args.get('limit', 100)), 500)
    offset = int(request.args.get('offset', 0))
    
    paginated = data_service.listings[offset:offset + limit]
    
    return jsonify({
        "listings": paginated,
        "total": len(data_service.listings),
        "limit": limit,
        "offset": offset,
        "has_more": (offset + limit) < len(data_service.listings)
    })


@api_bp.route('/admin/storage-info', methods=['GET'])
@error_handler
@require_ready
def storage_info() -> tuple[Dict[str, Any], int]:
    """
    Get storage information (admin endpoint).
    
    Returns details about model storage configuration and status.
    
    Returns:
        tuple: JSON response with storage info and HTTP status code.
    """
    return jsonify(model_manager.get_storage_info())


@api_bp.route('/admin/retrain', methods=['POST'])
@error_handler
def retrain() -> tuple[Dict[str, Any], int]:
    """
    Manually trigger model retraining (admin endpoint).
    
    Note: Not recommended on Cloud Run due to ephemeral storage.
    
    Returns:
        tuple: JSON response with retrain status and HTTP status code.
    """
    if config.is_cloud_run():
        return jsonify({
            "error": "Retraining not recommended on Cloud Run",
            "suggestion": "Train locally and upload to GCS instead"
        }), 400
    
    try:
        logger.info("🔄 Manual retrain triggered...")
        texts = data_service.get_all_texts()
        model_manager.initialize_models(texts)
        
        return jsonify({
            "status": "success",
            "message": "Models retrained successfully"
        })
    except Exception as e:
        logger.error(f"Retrain failed: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route('/admin/retrain/status', methods=['GET'])
@error_handler
@require_admin
@require_ready
def retrain_status() -> tuple[Dict[str, Any], int]:
    """
    Retrain status endpoint (admin).

    This project runs retraining synchronously today (no background worker),
    so `is_retraining` is always False unless you later add async retraining.
    """
    meta = model_manager.metadata or {}
    return jsonify({
        "is_retraining": False,
        "strategy": "manual_only",
        "additions_since_retrain": 0,
        "last_retrain_at": meta.get("saved_at"),
        "trained_on_texts": meta.get("num_texts"),
    })


@api_bp.route('/admin/stats', methods=['GET'])
@error_handler
@require_admin
@require_ready
def admin_stats() -> tuple[Dict[str, Any], int]:
    """
    Simple admin stats endpoint used by test scripts.
    """
    return jsonify({
        "data": {
            "total_listings": len(data_service.listings),
            "sectors": len(data_service.metadata.get("sectors", [])),
            "tags": len(data_service.metadata.get("tags", [])),
            "locations": len(data_service.metadata.get("locations", [])),
        },
        "models": {
            "tfidf_loaded": bool(model_manager.tfidf_vectorizer),
            "faiss_vectors": model_manager.faiss_index.ntotal if model_manager.faiss_index else 0,
            "use_loaded": bool(model_manager.use_model),
        },
        "storage": model_manager.get_storage_info(),
    })


# ============================================================================
# ADMIN + ADD LISTINGS
# ============================================================================

def _create_listing_from_request() -> Dict[str, Any]:
    payload = request.get_json(silent=True)
    if payload is None:
        raise ValueError("JSON body required")

    # Support either a single listing object or {\"listing\": {...}}
    if isinstance(payload, dict) and "listing" in payload and isinstance(payload["listing"], dict):
        return payload["listing"]

    if isinstance(payload, dict):
        return payload

    raise ValueError("Invalid JSON body: expected an object")


@api_bp.route('/admin/listings', methods=['POST'])
@error_handler
@require_admin
@require_ready
def admin_add_listing() -> tuple[Dict[str, Any], int]:
    """
    Add a new franchise listing (admin endpoint).

    Persists to dataset.json and updates in-memory listings/metadata.
    Does NOT retrain models by default; call POST /api/admin/retrain manually.
    """
    listing = _create_listing_from_request()
    created = data_service.add_listing(listing)

    # Refresh search service listings reference (SearchService holds a list reference)
    search_service.listings = data_service.listings
    search_service._build_tfidf_matrix()

    return jsonify({
        "status": "created",
        "id": created.get("id"),
        "listing": created,
        "retrain_required": True,
        "retrain_endpoint": "/api/admin/retrain",
    }), 201


@api_bp.route('/add/listings', methods=['POST'])
@error_handler
@require_ready
def add_listing_alias() -> tuple[Dict[str, Any], int]:
    """
    Public alias endpoint to add a listing.

    NOTE: This is intentionally NOT auto-retraining. If you need auth here,
    switch this to @require_admin or set up a separate auth mechanism.
    """
    listing = _create_listing_from_request()
    created = data_service.add_listing(listing)

    search_service.listings = data_service.listings
    search_service._build_tfidf_matrix()

    return jsonify({
        "status": "created",
        "id": created.get("id"),
        "listing": created,
        "retrain_required": True,
        "retrain_endpoint": "/api/admin/retrain",
    }), 201


@api_bp.route('/admin/listings', methods=['GET'])
@error_handler
@require_admin
@require_ready
def admin_list_listings() -> tuple[Dict[str, Any], int]:
    """
    List all listings (admin endpoint) with pagination.
    """
    limit = min(int(request.args.get('limit', 100)), 500)
    offset = int(request.args.get('offset', 0))
    paginated = data_service.listings[offset:offset + limit]

    return jsonify({
        "listings": paginated,
        "total": len(data_service.listings),
        "limit": limit,
        "offset": offset,
        "has_more": (offset + limit) < len(data_service.listings)
    })


@api_bp.route('/admin/listings/<int:listing_id>', methods=['PUT'])
@error_handler
@require_admin
@require_ready
def admin_update_listing(listing_id: int) -> tuple[Dict[str, Any], int]:
    updates = request.get_json(silent=True) or {}
    updated = data_service.update_listing(listing_id, updates)

    search_service.listings = data_service.listings
    search_service._build_tfidf_matrix()

    return jsonify({
        "status": "updated",
        "id": updated.get("id"),
        "listing": updated,
        "retrain_required": True,
        "retrain_endpoint": "/api/admin/retrain",
    })


@api_bp.route('/admin/listings/<int:listing_id>', methods=['DELETE'])
@error_handler
@require_admin
@require_ready
def admin_delete_listing(listing_id: int) -> tuple[Dict[str, Any], int]:
    data_service.delete_listing(listing_id)

    search_service.listings = data_service.listings
    search_service._build_tfidf_matrix()

    return jsonify({
        "status": "deleted",
        "id": listing_id,
        "retrain_required": True,
        "retrain_endpoint": "/api/admin/retrain",
    })
