"""
Model Manager with Optional S3 Backup (Option 2)
"""

import os
import json
import pickle
import logging
import hashlib
import numpy as np
import tensorflow_hub as hub
import faiss
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from threading import Lock
from pathlib import Path
from config import config
from services.s3_backup_service import S3BackupService

logger = logging.getLogger(__name__)

class ModelManager:
    """
    Manages ML models with local storage (primary) and S3 backup (optional)
    """
    
    def __init__(self):
        self.use_model = None
        self.tfidf_vectorizer = None
        self.faiss_index = None
        self.embeddings = None
        self.model_lock = Lock()
        self.metadata = {}
        
        # Create models directory
        Path(config.MODELS_DIR).mkdir(parents=True, exist_ok=True)
        
        # Initialize S3 backup if enabled
        self.s3_backup = None
        if config.USE_S3:
            try:
                self.s3_backup = S3BackupService(
                    bucket_name=config.S3_BUCKET,
                    region=config.S3_REGION,
                    compression=config.S3_COMPRESSION,
                    keep_versions=config.S3_KEEP_VERSIONS
                )
            except Exception as e:
                logger.warning(f"S3 backup disabled: {e}")
                self.s3_backup = None
    
    def load_models(self) -> bool:
        """
        Load models from local storage
        
        Returns:
            True if successful
        """
        try:
            if self._models_exist_locally():
                logger.info("📂 Loading models from local storage...")
                return self._load_models_locally()
            
            logger.warning("⚠ Models not found locally")
            return False
            
        except Exception as e:
            logger.error(f"Model load failed: {e}", exc_info=True)
            return False
    
    def _models_exist_locally(self) -> bool:
        """Check if all required model files exist"""
        required_files = [
            config.TFIDF_MODEL_PATH,
            config.FAISS_INDEX_PATH,
            config.METADATA_PATH,
        ]
        
        # Embeddings .npy file
        embeddings_path = config.FAISS_INDEX_PATH.replace('.bin', '.npy')
        required_files.append(embeddings_path)
        
        return all(os.path.exists(f) for f in required_files)
    
    def _load_models_locally(self) -> bool:
        """Load models from local disk"""
        try:
            with self.model_lock:
                # Load USE model
                logger.info("  Loading Universal Sentence Encoder...")
                self.use_model = hub.load(config.USE_EMBEDDINGS_PATH)
                
                # Load TF-IDF
                logger.info("  Loading TF-IDF vectorizer...")
                with open(config.TFIDF_MODEL_PATH, 'rb') as f:
                    self.tfidf_vectorizer = pickle.load(f)
                
                # Load FAISS index
                logger.info("  Loading FAISS index...")
                self.faiss_index = faiss.read_index(config.FAISS_INDEX_PATH)
                
                # Load embeddings
                logger.info("  Loading embeddings...")
                embeddings_path = config.FAISS_INDEX_PATH.replace('.bin', '.npy')
                self.embeddings = np.load(embeddings_path)
                
                # Load metadata
                with open(config.METADATA_PATH, 'r') as f:
                    self.metadata = json.load(f)
                
                logger.info("✓ All models loaded successfully")
                return True
                
        except Exception as e:
            logger.error(f"Local load failed: {e}", exc_info=True)
            return False
    
    def initialize_models(self, texts: list) -> None:
        """
        Initialize/train models from scratch
        
        Args:
            texts: List of training texts
        """
        with self.model_lock:
            try:
                logger.info("🚀 Initializing ML models...")
                
                # 1. Load USE model
                if self.use_model is None:
                    logger.info("  Loading Universal Sentence Encoder (first time - 30-60s)...")
                    self.use_model = hub.load(config.USE_EMBEDDINGS_PATH)
                
                # 2. Generate embeddings
                logger.info(f"  Generating embeddings for {len(texts)} texts...")
                self.embeddings = self.use_model(texts).numpy().astype("float32")
                faiss.normalize_L2(self.embeddings)
                logger.info(f"    ✓ Shape: {self.embeddings.shape}")
                
                # 3. Build FAISS index
                dimension = self.embeddings.shape[1]
                self.faiss_index = faiss.IndexFlatIP(dimension)
                self.faiss_index.add(self.embeddings)
                logger.info(f"    ✓ FAISS index: {self.faiss_index.ntotal} vectors")
                
                # 4. Train TF-IDF
                logger.info("  Training TF-IDF model...")
                self.tfidf_vectorizer = TfidfVectorizer(
                    max_features=500,
                    ngram_range=(1, 2),
                    stop_words='english',
                    min_df=1
                )
                self.tfidf_vectorizer.fit(texts)
                logger.info(f"    ✓ Features: {self.tfidf_vectorizer.n_features_}")
                
                # 5. Save models locally
                self._save_models_locally(texts)
                
                # 6. Backup to S3 if enabled
                if self.s3_backup and self.s3_backup.is_available():
                    self.s3_backup.backup_models(
                        tfidf_path=config.TFIDF_MODEL_PATH,
                        faiss_path=config.FAISS_INDEX_PATH,
                        embeddings_path=config.FAISS_INDEX_PATH.replace('.bin', '.npy'),
                        metadata_path=config.METADATA_PATH
                    )
                
                logger.info("✓ Models initialized successfully")
                
            except Exception as e:
                logger.error(f"Model initialization failed: {e}", exc_info=True)
                raise
    
    def _save_models_locally(self, texts: list):
        """Save models to local storage"""
        logger.info("💾 Saving models to local storage...")
        
        try:
            # Save TF-IDF
            with open(config.TFIDF_MODEL_PATH, 'wb') as f:
                pickle.dump(self.tfidf_vectorizer, f)
            size_mb = os.path.getsize(config.TFIDF_MODEL_PATH) / 1024 / 1024
            logger.info(f"  ✓ TF-IDF saved ({size_mb:.1f}MB)")
            
            # Save FAISS
            faiss.write_index(self.faiss_index, config.FAISS_INDEX_PATH)
            size_mb = os.path.getsize(config.FAISS_INDEX_PATH) / 1024 / 1024
            logger.info(f"  ✓ FAISS index saved ({size_mb:.1f}MB)")
            
            # Save embeddings
            embeddings_path = config.FAISS_INDEX_PATH.replace('.bin', '.npy')
            np.save(embeddings_path, self.embeddings)
            size_mb = os.path.getsize(embeddings_path) / 1024 / 1024
            logger.info(f"  ✓ Embeddings saved ({size_mb:.1f}MB)")
            
            # Save metadata
            self.metadata.update({
                'num_texts': len(texts),
                'saved_at': str(__import__('datetime').datetime.utcnow()),
                's3_backup_enabled': self.s3_backup is not None
            })
            with open(config.METADATA_PATH, 'w') as f:
                json.dump(self.metadata, f, indent=2)
            logger.info("  ✓ Metadata saved")
            
        except Exception as e:
            logger.error(f"Save failed: {e}", exc_info=True)
            raise
    
    def get_storage_info(self) -> dict:
        """Get storage information"""
        info = {
            'storage_type': 'Local + S3 Backup' if (self.s3_backup and self.s3_backup.is_available()) else 'Local Only',
            'local_models_dir': config.MODELS_DIR,
            'local_size': self._get_local_size(),
        }
        
        if self.s3_backup and self.s3_backup.is_available():
            info['s3_bucket'] = config.S3_BUCKET
            info['s3_region'] = config.S3_REGION
            backups = self.s3_backup.list_backups(limit=5)
            info['latest_backups'] = backups
            info['total_backups'] = len(backups)
        
        return info
    
    def _get_local_size(self) -> str:
        """Get total local models size"""
        total_size = 0
        for file in Path(config.MODELS_DIR).glob('*'):
            if file.is_file():
                total_size += file.stat().st_size
        
        return f"{total_size / 1024 / 1024:.1f}MB"
