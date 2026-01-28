"""
Model Manager for GCP Deployment
Supports both Cloud Storage and local disk storage
"""

import os
import json
import pickle
import logging
import numpy as np
import tensorflow_hub as hub
import faiss
from sklearn.feature_extraction.text import TfidfVectorizer
from threading import Lock
from pathlib import Path
from datetime import datetime, UTC
from ..core.config import config
from ..services.gcs_storage_service import GCSStorageService

logger = logging.getLogger(__name__)

class ModelManager:
    """
    Manages ML models with GCS or local storage
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
        logger.info(f"Models directory: {config.MODELS_DIR}")
        
        # Initialize GCS if enabled
        self.gcs_storage = None
        if config.should_use_gcs():
            try:
                logger.info("Initializing GCS storage...")
                self.gcs_storage = GCSStorageService(
                    bucket_name=config.GCS_BUCKET,
                    project=config.GCS_PROJECT,
                    prefix=config.GCS_PREFIX
                )
                if not self.gcs_storage.is_available():
                    logger.warning("⚠ GCS not available, using local storage only")
                    self.gcs_storage = None
                else:
                    logger.info(f"✓ GCS storage initialized: gs://{config.GCS_BUCKET}/{config.GCS_PREFIX}")
            except Exception as e:
                logger.warning(f"GCS initialization failed: {e}")
                logger.warning("Continuing with local storage only")
                self.gcs_storage = None
        else:
            logger.info("GCS disabled, using local storage only")
    
    def load_models(self) -> bool:
        """
        Load models from GCS or local storage
        
        Priority:
        1. Download from GCS if available (source of truth)
        2. Try local cache
        3. Return False if not found anywhere (caller can train from scratch)
        
        Returns:
            True if successful
        """
        try:
            # Strategy 1: Download from GCS and load (preferred)
            if self.gcs_storage and self.gcs_storage.is_available():
                logger.info("🔍 Checking GCS for models...")
                if self.gcs_storage.models_exist():
                    logger.info("📥 Downloading models from GCS...")
                    if self.gcs_storage.download_models(config.MODELS_DIR):
                        logger.info("✓ Models downloaded from GCS")
                        return self._load_models_locally()
                    else:
                        logger.error("❌ Failed to download models from GCS")
                else:
                    logger.warning("⚠ Models not found in GCS")

            # Strategy 2: Try loading from local cache (fallback)
            if self._models_exist_locally():
                logger.info("📂 Loading models from local cache...")
                return self._load_models_locally()
            
            logger.warning("⚠ No models found in local cache or GCS")
            logger.info("💡 You need to train models first:")
            logger.info("   1. Run: python train_models.py")
            logger.info("   2. Run: ./upload_models.sh")
            return False
            
        except Exception as e:
            logger.error(f"Model load failed: {e}", exc_info=True)
            return False
    
    def _models_exist_locally(self) -> bool:
        """Check if all required model files exist locally"""
        required_files = [
            config.TFIDF_MODEL_PATH,
            config.FAISS_INDEX_PATH,
            config.METADATA_PATH,
            config.FAISS_INDEX_PATH.replace('.bin', '.npy'),  # embeddings
        ]
        
        exists = all(os.path.exists(f) for f in required_files)
        
        if exists:
            logger.info("✓ All model files found locally")
            # Show sizes
            for f in required_files:
                size_mb = os.path.getsize(f) / 1024 / 1024
                logger.info(f"  - {Path(f).name}: {size_mb:.1f}MB")
        else:
            logger.debug("Some model files missing locally")
            for f in required_files:
                if not os.path.exists(f):
                    logger.debug(f"  Missing: {Path(f).name}")
        
        return exists
    
    def _load_models_locally(self) -> bool:
        """Load models from local disk"""
        try:
            with self.model_lock:
                logger.info("Loading ML models into memory...")
                
                # Load USE model (downloads on first use, then cached by TF Hub)
                logger.info("  Loading Universal Sentence Encoder...")
                self.use_model = hub.load(config.USE_EMBEDDINGS_PATH)
                logger.info("    ✓ USE model loaded")
                
                # Load TF-IDF
                logger.info("  Loading TF-IDF vectorizer...")
                with open(config.TFIDF_MODEL_PATH, 'rb') as f:
                    self.tfidf_vectorizer = pickle.load(f)
                logger.info(f"    ✓ TF-IDF loaded ({len(self.tfidf_vectorizer.get_feature_names_out())} features)")
                
                # Load FAISS index
                logger.info("  Loading FAISS index...")
                self.faiss_index = faiss.read_index(config.FAISS_INDEX_PATH)
                logger.info(f"    ✓ FAISS index loaded ({self.faiss_index.ntotal} vectors)")
                
                # Load embeddings
                logger.info("  Loading embeddings...")
                embeddings_path = config.FAISS_INDEX_PATH.replace('.bin', '.npy')
                self.embeddings = np.load(embeddings_path)
                logger.info(f"    ✓ Embeddings loaded (shape: {self.embeddings.shape})")
                
                # Load metadata
                with open(config.METADATA_PATH, 'r') as f:
                    self.metadata = json.load(f)
                logger.info(f"    ✓ Metadata loaded (trained on {self.metadata.get('num_texts', 'unknown')} texts)")
                
                logger.info("✓ All models loaded successfully into memory")
                return True
                
        except Exception as e:
            logger.error(f"Local model load failed: {e}", exc_info=True)
            return False
    
    def initialize_models(self, texts: list) -> None:
        """
        Initialize/train models from scratch and save to storage
        
        Args:
            texts: List of training texts
        """
        with self.model_lock:
            try:
                logger.info("="*70)
                logger.info("🚀 INITIALIZING ML MODELS FROM SCRATCH")
                logger.info("="*70)
                logger.info(f"Training on {len(texts)} texts")
                logger.info("This will take 2-5 minutes...")
                logger.info("")
                
                # 1. Load USE model
                if self.use_model is None:
                    logger.info("1/4 Loading Universal Sentence Encoder...")
                    logger.info("    (First time: downloading ~1GB model, may take 30-60s)")
                    self.use_model = hub.load(config.USE_EMBEDDINGS_PATH)
                    logger.info("    ✓ USE model loaded")
                else:
                    logger.info("1/4 USE model already loaded")
                
                # 2. Generate embeddings
                logger.info("")
                logger.info(f"2/4 Generating embeddings for {len(texts)} texts...")
                logger.info("    (This may take 1-3 minutes)")
                self.embeddings = self.use_model(texts).numpy().astype("float32")
                faiss.normalize_L2(self.embeddings)
                logger.info(f"    ✓ Embeddings generated (shape: {self.embeddings.shape})")
                
                # 3. Build FAISS index
                logger.info("")
                logger.info("3/4 Building FAISS index...")
                dimension = self.embeddings.shape[1]
                self.faiss_index = faiss.IndexFlatIP(dimension)
                self.faiss_index.add(self.embeddings)
                logger.info(f"    ✓ FAISS index built ({self.faiss_index.ntotal} vectors)")
                
                # 4. Train TF-IDF
                logger.info("")
                logger.info("4/4 Training TF-IDF vectorizer...")
                self.tfidf_vectorizer = TfidfVectorizer(
                    max_features=500,
                    ngram_range=(1, 2),
                    stop_words='english',
                    min_df=1
                )
                self.tfidf_vectorizer.fit(texts)
                logger.info(f"    ✓ TF-IDF trained ({len(self.tfidf_vectorizer.get_feature_names_out())} features)")
                
                # 5. Save models locally
                logger.info("")
                self._save_models_locally(texts)
                
                # 6. Upload to GCS if enabled
                if self.gcs_storage and self.gcs_storage.is_available():
                    logger.info("")
                    logger.info("📤 Uploading models to GCS...")
                    if self.gcs_storage.upload_models(config.MODELS_DIR):
                        logger.info("✓ Models backed up to GCS")
                    else:
                        logger.warning("⚠ GCS upload failed (models saved locally only)")
                
                logger.info("")
                logger.info("="*70)
                logger.info("✅ MODEL INITIALIZATION COMPLETE")
                logger.info("="*70)
                
            except Exception as e:
                logger.error(f"❌ Model initialization failed: {e}", exc_info=True)
                raise
    
    def _save_models_locally(self, texts: list):
        """Save models to local storage"""
        logger.info("💾 Saving models to local storage...")
        
        try:
            # Save TF-IDF
            logger.info("  Saving TF-IDF vectorizer...")
            with open(config.TFIDF_MODEL_PATH, 'wb') as f:
                pickle.dump(self.tfidf_vectorizer, f)
            size_mb = os.path.getsize(config.TFIDF_MODEL_PATH) / 1024 / 1024
            logger.info(f"    ✓ TF-IDF saved ({size_mb:.1f}MB)")
            
            # Save FAISS
            logger.info("  Saving FAISS index...")
            faiss.write_index(self.faiss_index, config.FAISS_INDEX_PATH)
            size_mb = os.path.getsize(config.FAISS_INDEX_PATH) / 1024 / 1024
            logger.info(f"    ✓ FAISS index saved ({size_mb:.1f}MB)")
            
            # Save embeddings
            logger.info("  Saving embeddings...")
            embeddings_path = config.FAISS_INDEX_PATH.replace('.bin', '.npy')
            np.save(embeddings_path, self.embeddings)
            size_mb = os.path.getsize(embeddings_path) / 1024 / 1024
            logger.info(f"    ✓ Embeddings saved ({size_mb:.1f}MB)")
            
            # Save metadata
            logger.info("  Saving metadata...")
            self.metadata.update({
                'num_texts': len(texts),
                'saved_at': datetime.now(UTC).isoformat(),
                'storage_type': 'gcs' if self.gcs_storage else 'local',
                'deployment_env': config.DEPLOYMENT_ENV,
                'gcs_bucket': config.GCS_BUCKET if self.gcs_storage else None
            })
            with open(config.METADATA_PATH, 'w') as f:
                json.dump(self.metadata, f, indent=2)
            logger.info("    ✓ Metadata saved")
            
            # Calculate total size
            total_size = sum([
                os.path.getsize(config.TFIDF_MODEL_PATH),
                os.path.getsize(config.FAISS_INDEX_PATH),
                os.path.getsize(embeddings_path),
                os.path.getsize(config.METADATA_PATH)
            ]) / 1024 / 1024
            
            logger.info(f"  ✓ Total model size: {total_size:.1f}MB")
            logger.info(f"  ✓ Models saved to: {config.MODELS_DIR}")
            
        except Exception as e:
            logger.error(f"Save failed: {e}", exc_info=True)
            raise
    
    def get_storage_info(self) -> dict:
        """Get storage information"""
        info = {
            'storage_type': 'GCS' if (self.gcs_storage and self.gcs_storage.is_available()) else 'Local Only',
            'deployment_env': config.DEPLOYMENT_ENV,
            'local_models_dir': config.MODELS_DIR,
            'local_size': self._get_local_size(),
            'models_loaded': all([
                self.use_model is not None,
                self.tfidf_vectorizer is not None,
                self.faiss_index is not None,
                self.embeddings is not None
            ]),
            'model_details': {}
        }
        
        if self.tfidf_vectorizer:
            info['model_details']['tfidf_features'] = len(self.tfidf_vectorizer.get_feature_names_out())
        
        if self.faiss_index:
            info['model_details']['faiss_vectors'] = self.faiss_index.ntotal
        
        if self.embeddings is not None:
            info['model_details']['embeddings_shape'] = self.embeddings.shape
        
        if self.metadata:
            info['model_details']['metadata'] = self.metadata
        
        if self.gcs_storage and self.gcs_storage.is_available():
            info['gcs'] = self.gcs_storage.get_storage_info()
        
        return info
    
    def _get_local_size(self) -> str:
        """Get total local models size"""
        try:
            total_size = 0
            models_path = Path(config.MODELS_DIR)
            
            if models_path.exists():
                for file in models_path.glob('*'):
                    if file.is_file():
                        total_size += file.stat().st_size
            
            return f"{total_size / 1024 / 1024:.1f}MB"
        except Exception as e:
            logger.error(f"Error calculating local size: {e}")
            return "N/A"