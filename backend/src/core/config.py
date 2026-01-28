"""
Configuration Module for Semantic Search API

This module provides centralized configuration management for the application,
supporting deployment on Google Cloud Platform (Cloud Run and Compute Engine).

Classes:
    Config: Main configuration class containing all application settings.

Attributes:
    config (Config): Global configuration instance.

Environment Variables:
    HOST: Server host address (default: '0.0.0.0')
    PORT: Server port (default: 8080)
    DEBUG: Debug mode flag (default: 'False')
    STORAGE_TYPE: Storage backend type - 'gcs' or 'local' (default: 'gcs')
    GCS_BUCKET: Google Cloud Storage bucket name
    GCP_PROJECT: Google Cloud Platform project ID
    DATA_PATH: Path to dataset JSON file
    AUTO_RETRAIN: Enable automatic model retraining (default: 'False')
    CHECK_INTERVAL: Interval for checking updates in seconds (default: 3600)
    ALLOWED_ORIGINS: CORS allowed origins, comma-separated (default: '*')
    DEPLOYMENT_ENV: Deployment environment - 'development', 'cloud-run', or 'compute-engine'

Example:
    >>> from backend.src.core.config import config
    >>> print(config.PORT)
    8080
    >>> if config.is_cloud_run():
    ...     print("Running on Cloud Run")
"""

import os
from pathlib import Path


class Config:
    """
    Application configuration class.
    
    This class encapsulates all configuration settings for the semantic search API,
    including server settings, GCP integration, model paths, and deployment options.
    
    Attributes:
        HOST (str): Server host address.
        PORT (int): Server port number.
        DEBUG (bool): Debug mode flag.
        STORAGE_TYPE (str): Storage backend type ('gcs' or 'local').
        GCS_BUCKET (str): Google Cloud Storage bucket name.
        GCS_PROJECT (str): Google Cloud Platform project ID.
        GCS_PREFIX (str): Prefix path for models in GCS bucket.
        BASE_DIR (Path): Base directory of the application.
        MODELS_DIR (str): Directory path for storing models.
        DATA_PATH (str): Path to the dataset JSON file.
        USE_EMBEDDINGS_PATH (str): URL for Universal Sentence Encoder model.
        TFIDF_MODEL_PATH (str): Path to TF-IDF model file.
        FAISS_INDEX_PATH (str): Path to FAISS index file.
        METADATA_PATH (str): Path to metadata JSON file.
        DEFAULT_TOP_N (int): Default number of search results to return.
        MAX_TOP_N (int): Maximum number of search results allowed.
        SEMANTIC_WEIGHT (float): Weight for semantic search (0.0-1.0).
        AUTO_RETRAIN (bool): Flag to enable automatic model retraining.
        CHECK_INTERVAL (int): Interval in seconds for checking updates.
        ALLOWED_ORIGINS (list): List of allowed CORS origins.
        CACHE_MODELS_IN_MEMORY (bool): Flag to cache models in memory.
        DEPLOYMENT_ENV (str): Current deployment environment.
    """
    
    # ============================================================================
    # SERVER CONFIG
    # ============================================================================
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 8080))  # Cloud Run uses PORT env var
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # ============================================================================
    # GCP CONFIG
    # ============================================================================
    # Storage Options: 'gcs' (Cloud Storage) or 'local' (Compute Engine disk)
    STORAGE_TYPE = os.getenv('STORAGE_TYPE', 'local')
    
    # Google Cloud Storage
    GCS_BUCKET = os.getenv('GCS_BUCKET', 'search-api-models')
    GCS_PROJECT = os.getenv('GCP_PROJECT', 'sigma-archery-467104-d5')
    GCS_PREFIX = 'models/'  # Folder in bucket for models
    
    # For Cloud Run: use /tmp (ephemeral), gets recreated on each instance
    # For Compute Engine: use persistent disk
    BASE_DIR = Path(__file__).parent.parent.parent.parent
    MODELS_DIR = os.path.join(BASE_DIR, "models")
    
    # ============================================================================
    # DATA CONFIG
    # ============================================================================
    DATA_PATH = os.getenv('DATA_PATH', os.path.join(BASE_DIR, 'dataset.json'))
    
    # ============================================================================
    # MODEL PATHS
    # ============================================================================
    USE_EMBEDDINGS_PATH = "https://tfhub.dev/google/universal-sentence-encoder/4"
    TFIDF_MODEL_PATH = os.path.join(MODELS_DIR, 'tfidf_model.pkl')
    FAISS_INDEX_PATH = os.path.join(MODELS_DIR, 'faiss_index.bin')
    METADATA_PATH = os.path.join(MODELS_DIR, 'metadata.json')
    
    # ============================================================================
    # SEARCH CONFIG
    # ============================================================================
    DEFAULT_TOP_N = 10
    MAX_TOP_N = 50
    SEMANTIC_WEIGHT = 0.6  # 60% semantic, 40% keyword
    
    # ============================================================================
    # AUTO-RETRAIN CONFIG (Disabled for Cloud Run, optional for Compute Engine)
    # ============================================================================
    AUTO_RETRAIN = os.getenv('AUTO_RETRAIN', 'False').lower() == 'true'
    CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', 3600))  # 1 hour
    
    # ============================================================================
    # CORS CONFIG
    # ============================================================================
    ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', '*').split(',')

    # ============================================================================
    # ADMIN / SECURITY
    # ============================================================================
    # If set, admin endpoints require header: X-Admin-API-Key: <value>
    # If empty, admin endpoints will be effectively disabled (return 401).
    ADMIN_API_KEY = os.getenv('ADMIN_API_KEY', '')
    
    # ============================================================================
    # CACHE CONFIG (Cloud Run specific)
    # ============================================================================
    # Cloud Run instances can be reused, cache models in memory
    CACHE_MODELS_IN_MEMORY = True
    
    # ============================================================================
    # DEPLOYMENT INFO
    # ============================================================================
    DEPLOYMENT_ENV = os.getenv('DEPLOYMENT_ENV', 'development')  # development, cloud-run, compute-engine
    
    @classmethod
    def is_cloud_run(cls):
        """
        Check if the application is running on Google Cloud Run.
        
        Returns:
            bool: True if running on Cloud Run, False otherwise.
            
        Note:
            Detection is based on DEPLOYMENT_ENV or the presence of K_SERVICE environment variable.
        """
        return cls.DEPLOYMENT_ENV == 'cloud-run' or os.getenv('K_SERVICE') is not None
    
    @classmethod
    def is_compute_engine(cls):
        """
        Check if the application is running on Google Compute Engine.
        
        Returns:
            bool: True if running on Compute Engine, False otherwise.
        """
        return cls.DEPLOYMENT_ENV == 'compute-engine'
    
    @classmethod
    def should_use_gcs(cls):
        """
        Determine if Google Cloud Storage should be used for model storage.
        
        Returns:
            bool: True if GCS should be used, False otherwise.
            
        Note:
            GCS is used when STORAGE_TYPE is 'gcs' and a bucket name is configured.
        """
        return cls.STORAGE_TYPE == 'gcs' and cls.GCS_BUCKET


# Global configuration instance
config = Config()
