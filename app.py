"""
Franchise Search API v2.1 - Option 2 (Local + S3 Backup)
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import os, sys
import time
from datetime import datetime
from functools import wraps
from threading import Thread

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from config import config
from models.model_manager import ModelManager
from services.data_service import DataService
from services.search_service import SearchService

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask
app = Flask(__name__)
CORS(app, origins=config.ALLOWED_ORIGINS)

# Global instances
model_manager = ModelManager()
data_service = DataService(config.DATA_PATH)
search_service = None
system_ready = False

# ============================================================================
# DECORATORS
# ============================================================================

def timing_decorator(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = f(*args, **kwargs)
        duration = time.time() - start
        logger.info(f"{f.__name__} took {duration:.3f}s")
        return result
    return wrapper

def error_handler(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            logger.error(f"ValueError: {e}")
            return jsonify({"error": str(e), "type": "validation"}), 400
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            return jsonify({"error": "Internal server error", "details": str(e)}), 500
    return wrapper

def require_ready(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not system_ready:
            return jsonify({"error": "System initializing. Please retry."}), 503
        return f(*args, **kwargs)
    return wrapper

# ============================================================================
# INITIALIZATION
# ============================================================================

def initialize_system():
    """Initialize all components"""
    global search_service, system_ready
    
    try:
        logger.info("="*70)
        logger.info("FRANCHISE SEARCH API v2.1 - OPTION 2 (Local + S3 Backup)")
        logger.info("="*70)
        
        # 1. Load data
        if not data_service.load_data():
            raise Exception("Failed to load data")
        
        # 2. Try loading saved models
        models_loaded = model_manager.load_models()
        
        if not models_loaded:
            # Train from scratch
            logger.info("⚠ Models not found. Training from scratch...")
            texts = data_service.get_all_texts()
            model_manager.initialize_models(texts)
        
        # 3. Initialize search service
        search_service = SearchService(model_manager, data_service.listings)
        
        system_ready = True
        
        logger.info("="*70)
        logger.info("✓ SYSTEM READY FOR REQUESTS")
        logger.info(f"✓ Listings: {len(data_service.listings)}")
        logger.info(f"✓ Sectors: {len(data_service.metadata['sectors'])}")
        logger.info(f"✓ Tags: {len(data_service.metadata['tags'])}")
        logger.info(f"✓ Locations: {len(data_service.metadata['locations'])}")
        logger.info(f"✓ S3 Backup: {'Enabled' if model_manager.s3_backup else 'Disabled'}")
        logger.info("="*70)
        
    except Exception as e:
        logger.error(f"Initialization failed: {e}", exc_info=True)
        raise

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/api/health', methods=['GET'])
@error_handler
def health():
    """System health check"""
    s3_info = None
    if model_manager.s3_backup and model_manager.s3_backup.is_available():
        backups = model_manager.s3_backup.list_backups(limit=1)
        s3_info = {
            'bucket': config.S3_BUCKET,
            'latest_backup': backups[0] if backups else None,
            'total_backups': len(backups)
        }
    
    return jsonify({
        "status": "healthy" if system_ready else "initializing",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.1.0",
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
        "storage": {
            "type": "Local + S3 Backup" if s3_info else "Local Only",
            "s3_backup": s3_info
        }
    })

@app.route('/api/search', methods=['GET'])
@error_handler
@timing_decorator
@require_ready
def search():
    """
    Hybrid search - combines semantic + keyword
    
    Params: q (required), top_n, semantic_weight, sector, location, tags
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
        "timestamp": datetime.utcnow().isoformat()
    })

@app.route('/api/recommend/<int:listing_id>', methods=['GET'])
@error_handler
@timing_decorator
@require_ready
def recommend(listing_id):
    """
    Get franchise recommendations by ID
    
    Params: top_n (optional), sector_filter (optional)
    """
    top_n = min(int(request.args.get('top_n', 5)), 20)
    sector_filter = request.args.get('sector_filter', 'true').lower() == 'true'
    
    results = search_service.get_recommendations(listing_id, top_n, sector_filter)
    
    return jsonify({
        "listing_id": listing_id,
        "recommendations": results,
        "total": len(results),
        "timestamp": datetime.utcnow().isoformat()
    })

@app.route('/api/autocomplete', methods=['GET'])
@error_handler
@require_ready
def autocomplete():
    """Autocomplete suggestions"""
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

@app.route('/api/filters', methods=['GET'])
@error_handler
@require_ready
def get_filters():
    """Get available filter options"""
    return jsonify({
        "sectors": sorted(list(data_service.metadata['sectors'])),
        "locations": sorted(list(data_service.metadata['locations'])),
        "tags": sorted(list(data_service.metadata['tags'])),
        "total_listings": len(data_service.listings)
    })

@app.route('/api/listings', methods=['GET'])
@error_handler
@require_ready
def get_listings():
    """Get all listings with pagination"""
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

@app.route('/api/retrain', methods=['POST'])
@error_handler
def retrain():
    """Manually trigger model retraining"""
    try:
        if data_service.has_changed():
            logger.info("🔄 Data changed! Retraining models...")
            texts = data_service.get_all_texts()
            model_manager.initialize_models(texts)
            
            return jsonify({
                "status": "success",
                "message": "Models retrained successfully"
            })
        else:
            return jsonify({
                "status": "no_change",
                "message": "No data changes detected"
            })
    except Exception as e:
        logger.error(f"Retrain failed: {e}")
        return jsonify({"error": str(e)}), 500

# ============================================================================
# STORAGE MANAGEMENT ENDPOINTS (OPTIONAL)
# ============================================================================

@app.route('/api/admin/model-storage', methods=['GET'])
@error_handler
@require_ready
def model_storage_info():
    """Get model storage information"""
    return jsonify(model_manager.get_storage_info())

@app.route('/api/admin/model-backups', methods=['GET'])
@error_handler
@require_ready
def list_backups():
    """List available S3 backups"""
    if not model_manager.s3_backup or not model_manager.s3_backup.is_available():
        return jsonify({"error": "S3 backup not enabled"}), 400
    
    limit = int(request.args.get('limit', 10))
    backups = model_manager.s3_backup.list_backups(limit=limit)
    
    return jsonify({
        "backups": backups,
        "total": len(backups)
    })

@app.route('/api/admin/restore-models', methods=['POST'])
@error_handler
def restore_from_backup():
    """Restore models from S3 backup"""
    if not model_manager.s3_backup or not model_manager.s3_backup.is_available():
        return jsonify({"error": "S3 backup not enabled"}), 400
    
    try:
        success = model_manager.s3_backup.restore_latest(config.MODELS_DIR)
        
        if success:
            # Reload models
            model_manager.load_models()
            return jsonify({
                "status": "success",
                "message": "Models restored from S3 backup"
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to restore models"
            }), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================================================
# AUTO-RETRAIN BACKGROUND WORKER
# ============================================================================

def start_auto_retrain():
    """Background thread for periodic model retraining"""
    if not config.AUTO_RETRAIN:
        return
    
    def check_loop():
        while True:
            time.sleep(config.CHECK_INTERVAL)
            try:
                if data_service.has_changed():
                    logger.info("🔄 Auto-retrain triggered - data changed")
                    texts = data_service.get_all_texts()
                    model_manager.initialize_models(texts)
                    logger.info("✓ Auto-retrain completed")
            except Exception as e:
                logger.error(f"Auto-retrain failed: {e}")
    
    thread = Thread(target=check_loop, daemon=True)
    thread.start()
    logger.info(f"✓ Auto-retrain enabled (interval: {config.CHECK_INTERVAL}s)")

# ============================================================================
# STARTUP
# ============================================================================

if __name__ == '__main__':
    initialize_system()
    start_auto_retrain()
    app.run(
        host=config.HOST,
        port=config.PORT,
        debug=config.DEBUG,
        threaded=True
    )