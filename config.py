# config.py
"""
Configuration Management - All settings centralized
Option 2: Local EBS + S3 Backup
"""

import os
from dataclasses import dataclass, field

@dataclass
class Config:
    # ============ Flask Configuration ============
    DEBUG: bool = os.getenv('DEBUG', 'False').lower() == 'true'
    HOST: str = os.getenv('HOST', '0.0.0.0')
    PORT: int = int(os.getenv('PORT', 5000))
    
    # ============ CORS Configuration ============
    ALLOWED_ORIGINS: list = field(default_factory=list)    
    # ============ ML Models Configuration ============
    USE_EMBEDDINGS_PATH: str = os.getenv('USE_EMBEDDINGS_PATH', 
        'https://tfhub.dev/google/universal-sentence-encoder/4')
    
    # ============ Local Model Storage (PRIMARY) ============
    MODELS_DIR: str = os.getenv('MODELS_DIR', './models')
    USE_MODEL_PATH: str = os.path.join(MODELS_DIR, 'use_model')
    TFIDF_MODEL_PATH: str = os.path.join(MODELS_DIR, 'tfidf_model.pkl')
    FAISS_INDEX_PATH: str = os.path.join(MODELS_DIR, 'faiss_index.bin')
    METADATA_PATH: str = os.path.join(MODELS_DIR, 'metadata.json')
    
    # ============ Search Configuration ============
    DEFAULT_TOP_N: int = int(os.getenv('DEFAULT_TOP_N', 10))
    MAX_TOP_N: int = int(os.getenv('MAX_TOP_N', 50))
    SEMANTIC_WEIGHT: float = float(os.getenv('SEMANTIC_WEIGHT', 0.6))
    
    # ============ Data Configuration ============
    DATA_PATH: str = os.getenv('DATA_PATH', './dataset.json')
    
    # ============ Auto-Retrain Configuration ============
    AUTO_RETRAIN: bool = os.getenv('AUTO_RETRAIN', 'True').lower() == 'true'
    CHECK_INTERVAL: int = int(os.getenv('CHECK_INTERVAL', 86400))  # 24 hours
    
    # ============ S3 BACKUP Configuration (Option 2) ============
    USE_S3: bool = os.getenv('USE_S3', 'False').lower() == 'true'
    S3_BUCKET: str = os.getenv('S3_BUCKET', '')
    S3_REGION: str = os.getenv('S3_REGION', 'us-east-1')
    S3_COMPRESSION: str = os.getenv('S3_COMPRESSION', 'gzip')  # gzip or none
    S3_CLEANUP_OLD_VERSIONS: bool = os.getenv('S3_CLEANUP_OLD_VERSIONS', 'True').lower() == 'true'
    S3_KEEP_VERSIONS: int = int(os.getenv('S3_KEEP_VERSIONS', '5'))
    
    # ============ Logging Configuration ============
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')

config = Config()