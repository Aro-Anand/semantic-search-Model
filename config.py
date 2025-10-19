# config.py
import os
from dataclasses import dataclass, field

@dataclass
class Config:
    # Flask
    DEBUG: bool = os.getenv('DEBUG', 'False').lower() == 'true'
    HOST: str = os.getenv('HOST', '0.0.0.0')
    PORT: int = int(os.getenv('PORT', 5000))
    
    # CORS
    ALLOWED_ORIGINS: list = field(default_factory=lambda: ["*"])
    
    # ML Models
    USE_EMBEDDINGS_PATH: str = os.getenv('USE_EMBEDDINGS_PATH', 
        'https://tfhub.dev/google/universal-sentence-encoder/4')
    
    # Model persistence
    MODELS_DIR: str = os.getenv('MODELS_DIR', './models')
    USE_MODEL_PATH: str = os.path.join(MODELS_DIR, 'use_model')
    TFIDF_MODEL_PATH: str = os.path.join(MODELS_DIR, 'tfidf_model.pkl')
    FAISS_INDEX_PATH: str = os.path.join(MODELS_DIR, 'faiss_index.bin')
    METADATA_PATH: str = os.path.join(MODELS_DIR, 'metadata.json')
    
    # Search
    DEFAULT_TOP_N: int = int(os.getenv('DEFAULT_TOP_N', 10))
    MAX_TOP_N: int = int(os.getenv('MAX_TOP_N', 50))
    SEMANTIC_WEIGHT: float = float(os.getenv('SEMANTIC_WEIGHT', 0.6))
    
    # Data
    DATA_PATH: str = os.getenv('DATA_PATH', 'dataset.json')
    
    # Auto-retrain
    AUTO_RETRAIN: bool = os.getenv('AUTO_RETRAIN', 'True').lower() == 'true'
    CHECK_INTERVAL: int = int(os.getenv('CHECK_INTERVAL', 86400))
    
    # AWS S3 (optional)
    USE_S3: bool = os.getenv('USE_S3', 'False').lower() == 'true'
    S3_BUCKET: str = os.getenv('S3_BUCKET', '')
    S3_REGION: str = os.getenv('S3_REGION', 'us-east-1')

config = Config()