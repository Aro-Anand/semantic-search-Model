"""
Google Cloud Storage Service
Handles model storage and retrieval from GCS
"""

import os
import logging
from pathlib import Path
from typing import Optional, List, Dict
from google.cloud import storage
from google.api_core.exceptions import GoogleAPIError, NotFound

logger = logging.getLogger(__name__)

class GCSStorageService:
    """
    Google Cloud Storage Service for model storage
    """
    
    def __init__(self, bucket_name: str, project: str = None, prefix: str = 'models/'):
        """
        Initialize GCS storage service
        
        Args:
            bucket_name: GCS bucket name
            project: GCP project ID (optional, uses default)
            prefix: Folder prefix in bucket
        """
        self.bucket_name = bucket_name
        self.project = project
        self.prefix = prefix
        self.client = None
        self.bucket = None
        
        self._initialize_gcs()
    
    def _initialize_gcs(self):
        """Initialize GCS client and bucket"""
        try:
            if self.project:
                self.client = storage.Client(project=self.project)
            else:
                # Uses Application Default Credentials (ADC)
                self.client = storage.Client()
            
            self.bucket = self.client.bucket(self.bucket_name)
            
            # Test connection
            if self.bucket.exists():
                logger.info(f"✓ Connected to GCS bucket: {self.bucket_name}")
            else:
                logger.error(f"❌ Bucket {self.bucket_name} does not exist")
                self.client = None
                self.bucket = None
                
        except Exception as e:
            logger.error(f"GCS initialization failed: {e}")
            logger.warning("Continuing without GCS - will use local storage only")
            self.client = None
            self.bucket = None
    
    def is_available(self) -> bool:
        """Check if GCS is available"""
        return self.client is not None and self.bucket is not None
    
    def download_models(self, local_dir: str, required_files: Optional[List[str]] = None) -> bool:
        """
        Download all models from GCS to local directory
        
        Args:
            local_dir: Local directory to download to
            required_files: Optional list of required files (uses default if None)
            
        Returns:
            True if successful
        """
        if not self.is_available():
            logger.warning("GCS not available, cannot download models")
            return False
        
        # Default required files
        if required_files is None:
            required_files = [
                'tfidf_model.pkl',
                'faiss_index.bin',
                'faiss_index.npy',
                'metadata.json',
            ]
        
        try:
            logger.info(f"📥 Downloading models from GCS: gs://{self.bucket_name}/{self.prefix}")
            
            # Create local directory
            local_path = Path(local_dir)
            local_path.mkdir(parents=True, exist_ok=True)
            
            # Track downloads
            downloaded = []
            failed = []
            
            for filename in required_files:
                blob_name = f"{self.prefix}{filename}"
                file_path = local_path / filename
                
                if self._download_blob(blob_name, str(file_path)):
                    downloaded.append(filename)
                else:
                    failed.append(filename)
            
            # Determine success
            all_downloaded = len(failed) == 0
            
            if all_downloaded:
                logger.info(f"✓ Successfully downloaded all {len(downloaded)} model files")
                return True
            elif downloaded:
                # Partial failure - cleanup and report
                logger.error(f"❌ Partial download failed. Missing: {failed}")
                logger.info("Cleaning up partial downloads...")
                for filename in downloaded:
                    try:
                        (local_path / filename).unlink()
                    except Exception as e:
                        logger.warning(f"Failed to cleanup {filename}: {e}")
                return False
            else:
                logger.error(f"❌ No files downloaded. All failed: {failed}")
                return False
                
        except Exception as e:
            logger.error(f"Model download failed: {e}", exc_info=True)
            return False

    def _download_blob(self, blob_name: str, local_path: str, expected_min_size: int = 1024) -> bool:
        """Download a single blob with validation"""
        try:
            blob = self.bucket.blob(blob_name)
            
            if not blob.exists():
                logger.warning(f"Blob does not exist: {blob_name}")
                return False
            
            # Check remote size
            remote_size = blob.size
            logger.info(f"  Downloading {Path(local_path).name} ({remote_size / 1024:.1f} KB)...")
            
            # Download to file
            blob.download_to_filename(local_path)
            
            # Verify local file
            if not os.path.exists(local_path):
                logger.error(f"Download failed: file not created")
                return False
            
            local_size = os.path.getsize(local_path)
            
            # Verify size matches
            if local_size != remote_size:
                logger.error(f"Size mismatch: local={local_size}, remote={remote_size}")
                os.remove(local_path)  # Clean up corrupt file
                return False
            
            # Verify minimum size
            if local_size < expected_min_size:
                logger.warning(f"File unusually small: {local_size} bytes (expected >{expected_min_size})")
            
            size_kb = local_size / 1024
            logger.info(f"  ✓ {Path(local_path).name} ({size_kb:.1f} KB)")
            return True
            
        except NotFound:
            logger.warning(f"Blob not found: {blob_name}")
            return False
        except Exception as e:
            logger.error(f"Failed to download {blob_name}: {e}")
            if os.path.exists(local_path):
                os.remove(local_path)  # Clean up partial download
            return False

    def upload_models(self, local_dir: str) -> bool:
        """
        Upload all models from local directory to GCS
        
        Args:
            local_dir: Local directory containing models
            
        Returns:
            True if successful
        """
        if not self.is_available():
            logger.warning("GCS not available, cannot upload models")
            return False
        
        try:
            logger.info(f"📤 Uploading models to GCS: gs://{self.bucket_name}/{self.prefix}")
            
            files_to_upload = [
                'tfidf_model.pkl',
                'faiss_index.bin',
                'faiss_index.npy',
                'metadata.json',
            ]
            
            uploaded = 0
            for filename in files_to_upload:
                local_path = os.path.join(local_dir, filename)
                
                if not os.path.exists(local_path):
                    logger.warning(f"⚠ File not found: {local_path}")
                    continue
                
                blob_name = f"{self.prefix}{filename}"
                if self._upload_blob(local_path, blob_name):
                    uploaded += 1
            
            if uploaded > 0:
                logger.info(f"✓ Uploaded {uploaded}/{len(files_to_upload)} model files")
                return True
            else:
                logger.error("❌ No files uploaded")
                return False
                
        except Exception as e:
            logger.error(f"Model upload failed: {e}", exc_info=True)
            return False
    
    def _upload_blob(self, local_path: str, blob_name: str) -> bool:
        """Upload a single blob"""
        try:
            blob = self.bucket.blob(blob_name)
            blob.upload_from_filename(local_path)
            
            size_mb = os.path.getsize(local_path) / 1024 / 1024
            logger.info(f"  ✓ {Path(local_path).name} ({size_mb:.1f}MB)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload {local_path}: {e}")
            return False
    
    def models_exist(self) -> bool:
        """Check if models exist in GCS"""
        if not self.is_available():
            return False
        
        try:
            required_files = [
                'tfidf_model.pkl',
                'faiss_index.bin',
                'faiss_index.npy',
                'metadata.json'
            ]
            
            for filename in required_files:
                blob_name = f"{self.prefix}{filename}"
                blob = self.bucket.blob(blob_name)
                
                if not blob.exists():
                    logger.debug(f"Model file not found in GCS: {blob_name}")
                    return False
            
            logger.info(f"✓ All model files found in GCS")
            return True
            
        except Exception as e:
            logger.error(f"Error checking models in GCS: {e}")
            return False
    
    def get_storage_info(self) -> Dict:
        """Get storage information"""
        if not self.is_available():
            return {
                'status': 'unavailable',
                'bucket': self.bucket_name,
                'error': 'GCS client not initialized'
            }
        
        try:
            info = {
                'status': 'available',
                'bucket': self.bucket_name,
                'project': self.project,
                'prefix': self.prefix,
                'models_exist': self.models_exist(),
                'files': []
            }
            
            # List model files
            blobs = self.client.list_blobs(self.bucket_name, prefix=self.prefix)
            for blob in blobs:
                info['files'].append({
                    'name': blob.name.replace(self.prefix, ''),
                    'size_mb': round(blob.size / 1024 / 1024, 2),
                    'updated': blob.updated.isoformat() if blob.updated else None
                })
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting storage info: {e}")
            return {
                'status': 'error', 
                'bucket': self.bucket_name,
                'error': str(e)
            }
    
    def delete_models(self) -> bool:
        """Delete all models from GCS (use with caution!)"""
        if not self.is_available():
            return False
        
        try:
            logger.warning(f"🗑️ Deleting all models from GCS: gs://{self.bucket_name}/{self.prefix}")
            
            blobs = self.client.list_blobs(self.bucket_name, prefix=self.prefix)
            deleted = 0
            
            for blob in blobs:
                blob.delete()
                deleted += 1
                logger.info(f"  ✓ Deleted: {blob.name}")
            
            logger.info(f"✓ Deleted {deleted} files from GCS")
            return True
            
        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return False