"""
Semantic Search API - Main Application Entry Point

This is the main entry point for the Franchise Search API, optimized for
deployment on Google Cloud Platform (Cloud Run and Compute Engine).

The application provides:
- Hybrid search combining semantic and keyword matching
- Autocomplete suggestions
- Content-based recommendations
- RESTful API endpoints

Environment Variables:
    See backend.src.core.config for all available environment variables.

Example:
    Run locally:
        $ python backend/main.py
    
    Deploy to Cloud Run:
        $ gcloud run deploy search-api --source .

Author: Anand
Version: 3.0.0-gcp
"""

from flask import Flask, jsonify
from flask_cors import CORS
import logging
import sys
import os

# Suppress TensorFlow logs and oneDNN warnings
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # 0=all, 1=info, 2=warning, 3=error

import warnings
# Filter specific deprecation warnings
warnings.filterwarnings('ignore', category=UserWarning, module='tensorflow_hub')
warnings.filterwarnings('ignore', category=UserWarning, module='google.auth')
warnings.filterwarnings('ignore', message='The name tf.losses.sparse_softmax_cross_entropy is deprecated')

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.src.core.config import config
from backend.src.models.model_manager import ModelManager
from backend.src.services.data_service import DataService
from backend.src.services.search_service import SearchService
from backend.src.api import api_bp, init_routes, set_system_state
from backend.src.utils.logging import setup_logging

# Setup logging
setup_logging(
    level=logging.DEBUG if config.DEBUG else logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize Flask application
app = Flask(__name__)
CORS(app, origins=config.ALLOWED_ORIGINS)

# Global service instances
model_manager = None
data_service = None
search_service = None


def initialize_system() -> bool:
    """
    Initialize all system components.
    
    This function performs the following initialization steps:
    1. Load franchise data from JSON file
    2. Load or train machine learning models
    3. Initialize search service
    4. Update system state
    
    Returns:
        bool: True if initialization succeeded, False otherwise.
        
    Side Effects:
        - Sets global variables: model_manager, data_service, search_service
        - Updates system state via set_system_state()
        - Logs initialization progress and results
    """
    global model_manager, data_service, search_service
    
    try:
        logger.info("=" * 70)
        logger.info("FRANCHISE SEARCH API - GCP DEPLOYMENT")
        logger.info(f"Environment: {config.DEPLOYMENT_ENV}")
        logger.info(f"Storage: {config.STORAGE_TYPE}")
        logger.info("=" * 70)
        
        # Step 1: Initialize model manager
        logger.info("🤖 Initializing model manager...")
        model_manager = ModelManager()
        
        # Step 2: Load data
        logger.info("📖 Loading franchise data...")
        data_service = DataService(config.DATA_PATH)
        if not data_service.load_data():
            raise Exception("Failed to load franchise data")
        
        # Step 3: Load or initialize models
        logger.info("🤖 Loading ML models...")
        models_loaded = model_manager.load_models()
        
        if not models_loaded:
            logger.warning("⚠ Pre-trained models not found")
            logger.info("🏋️ Training models from scratch (this may take 2-5 minutes)...")
            logger.info("💡 TIP: Pre-train and upload to GCS to avoid this delay")
            
            texts = data_service.get_all_texts()
            model_manager.initialize_models(texts)
            logger.info("✓ Models trained and saved")
        
        # Step 4: Initialize search service
        logger.info("🔍 Initializing search service...")
        search_service = SearchService(model_manager, data_service.listings)
        
        # Step 5: Register routes
        init_routes(model_manager, data_service, search_service)
        
        # Update system state
        set_system_state(ready=True, error=None)
        
        logger.info("=" * 70)
        logger.info("✅ SYSTEM READY")
        logger.info(f"✓ Listings: {len(data_service.listings)}")
        logger.info(f"✓ Sectors: {len(data_service.metadata['sectors'])}")
        logger.info(f"✓ Tags: {len(data_service.metadata['tags'])}")
        logger.info(f"✓ Locations: {len(data_service.metadata['locations'])}")
        logger.info(f"✓ Storage: {config.STORAGE_TYPE}")
        if model_manager.gcs_storage:
            logger.info(f"✓ GCS Bucket: {config.GCS_BUCKET}")
        logger.info("=" * 70)
        
        return True
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Initialization failed: {error_msg}", exc_info=True)
        set_system_state(ready=False, error=error_msg)
        return False


# Register API blueprint
app.register_blueprint(api_bp, url_prefix='/api')


@app.route('/', methods=['GET'])
def root():
    """
    Root endpoint providing API information.
    
    Returns:
        JSON response with API metadata and available endpoints.
        
    Example Response:
        {
            "name": "Franchise Search API",
            "version": "3.0.0-gcp",
            "status": "ready",
            "endpoints": {...}
        }
    """
    from backend.src.api.deps import system_ready
    
    return jsonify({
        "name": "Franchise Search API",
        "version": "3.0.0-gcp",
        "deployment": config.DEPLOYMENT_ENV,
        "status": "ready" if system_ready else "initializing",
        "endpoints": {
            "health": "/api/health",
            "search": "/api/search?q=<query>",
            "recommend": "/api/recommend/<id>",
            "autocomplete": "/api/autocomplete?q=<query>",
            "filters": "/api/filters",
            "listings": "/api/listings"
        },
        "docs": "See README.md for full API documentation"
    })


# Initialize on module load (required for Cloud Run)
initialize_system()


if __name__ == '__main__':
    """
    Run the application in development mode.
    
    For production deployment on Cloud Run or Compute Engine,
    use a production WSGI server like Gunicorn.
    """
    logger.info(f"Starting development server on {config.HOST}:{config.PORT}")
    app.run(
        host=config.HOST,
        port=config.PORT,
        debug=config.DEBUG,
        threaded=True
    )
