"""
S3 Backup Service for Option 2 (Local + S3 Backup)
Handles model backup and restore from S3
"""

import os
import boto3
import logging
import json
import gzip
import io
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class S3BackupService:
    """
    S3 Backup Service - Backup local models to S3
    Used as backup for local cache (not primary storage)
    """
    
    def __init__(self, 
                 bucket_name: str,
                 region: str = 'us-east-1',
                 compression: str = 'gzip',
                 keep_versions: int = 5):
        """
        Initialize S3 backup service
        
        Args:
            bucket_name: S3 bucket name
            region: AWS region
            compression: Compression method (gzip or none)
            keep_versions: Number of old versions to keep
        """
        self.bucket_name = bucket_name
        self.region = region
        self.compression = compression
        self.keep_versions = keep_versions
        self.s3_client = None
        
        # Test S3 connection
        self._initialize_s3()
    
    def _initialize_s3(self):
        """Initialize S3 client and test connection"""
        try:
            self.s3_client = boto3.client('s3', region_name=self.region)
            # Test connection
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"✓ Connected to S3 bucket: {self.bucket_name}")
        except Exception as e:
            logger.warning(f"⚠ S3 connection failed: {e}. Continuing without S3 backup.")
            self.s3_client = None
    
    def is_available(self) -> bool:
        """Check if S3 backup is available"""
        return self.s3_client is not None
    
    def backup_models(self,
                     tfidf_path: str,
                     faiss_path: str,
                     embeddings_path: str,
                     metadata_path: str) -> bool:
        """
        Backup models to S3
        
        Args:
            tfidf_path: Local path to TF-IDF model
            faiss_path: Local path to FAISS index
            embeddings_path: Local path to embeddings
            metadata_path: Local path to metadata
            
        Returns:
            True if successful
        """
        if not self.s3_client:
            return False
        
        try:
            logger.info("🔄 Backing up models to S3...")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            files_to_backup = [
                (tfidf_path, f"models/backups/tfidf_model_{timestamp}.pkl.gz"),
                (faiss_path, f"models/backups/faiss_index_{timestamp}.bin.gz"),
                (embeddings_path, f"models/backups/embeddings_{timestamp}.npy.gz"),
                (metadata_path, f"models/backups/metadata_{timestamp}.json"),
            ]
            
            for local_file, s3_key in files_to_backup:
                if not os.path.exists(local_file):
                    logger.warning(f"File not found: {local_file}")
                    continue
                
                # Compress and upload
                if local_file.endswith(('.pkl', '.bin', '.npy')):
                    self._upload_compressed(local_file, s3_key)
                else:
                    self._upload_file(local_file, s3_key)
            
            # Create/update latest pointer
            self._create_latest_pointer(timestamp)
            
            # Cleanup old versions
            if self.bucket_name:
                self._cleanup_old_backups()
            
            logger.info("✓ Models backed up to S3")
            return True
            
        except Exception as e:
            logger.error(f"S3 backup failed: {e}", exc_info=True)
            return False
    
    def _upload_compressed(self, local_path: str, s3_key: str):
        """Upload file with gzip compression"""
        try:
            file_size = os.path.getsize(local_path)
            
            with open(local_path, 'rb') as f:
                data = f.read()
                compressed_data = gzip.compress(data)
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=compressed_data,
                ContentEncoding='gzip',
                Metadata={
                    'original_size': str(file_size),
                    'uploaded_at': datetime.utcnow().isoformat()
                }
            )
            
            compressed_size = len(compressed_data)
            ratio = (1 - compressed_size / file_size) * 100
            logger.info(f"  ✓ {Path(local_path).name} - Compressed {ratio:.0f}%")
            
        except Exception as e:
            logger.error(f"Compression upload failed: {e}")
    
    def _upload_file(self, local_path: str, s3_key: str):
        """Upload file without compression"""
        try:
            self.s3_client.upload_file(local_path, self.bucket_name, s3_key)
            logger.info(f"  ✓ {Path(local_path).name} backed up")
        except Exception as e:
            logger.error(f"File upload failed: {e}")
    
    def _create_latest_pointer(self, timestamp: str):
        """Create pointer to latest backup"""
        try:
            pointer = {
                'latest_backup': timestamp,
                'updated_at': datetime.utcnow().isoformat(),
                'backup_files': {
                    'tfidf': f"models/backups/tfidf_model_{timestamp}.pkl.gz",
                    'faiss': f"models/backups/faiss_index_{timestamp}.bin.gz",
                    'embeddings': f"models/backups/embeddings_{timestamp}.npy.gz",
                    'metadata': f"models/backups/metadata_{timestamp}.json"
                }
            }
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key='models/latest_backup.json',
                Body=json.dumps(pointer, indent=2),
                ContentType='application/json'
            )
        except Exception as e:
            logger.error(f"Failed to create pointer: {e}")
    
    def restore_latest(self, target_dir: str) -> bool:
        """
        Restore latest backup from S3
        
        Args:
            target_dir: Directory to restore to
            
        Returns:
            True if successful
        """
        if not self.s3_client:
            return False
        
        try:
            logger.info("📥 Restoring models from S3...")
            
            # Get latest pointer
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key='models/latest_backup.json'
            )
            latest_info = json.loads(response['Body'].read())
            
            files_to_restore = [
                (latest_info['backup_files']['tfidf'], os.path.join(target_dir, 'tfidf_model.pkl')),
                (latest_info['backup_files']['faiss'], os.path.join(target_dir, 'faiss_index.bin')),
                (latest_info['backup_files']['embeddings'], os.path.join(target_dir, 'embeddings.npy')),
                (latest_info['backup_files']['metadata'], os.path.join(target_dir, 'metadata.json')),
            ]
            
            for s3_key, local_path in files_to_restore:
                self._download_file(s3_key, local_path)
            
            logger.info("✓ Models restored from S3")
            return True
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False
    
    def _download_file(self, s3_key: str, local_path: str):
        """Download and decompress file"""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            data = response['Body'].read()
            
            # Decompress if needed
            if s3_key.endswith('.gz'):
                data = gzip.decompress(data)
            
            # Write to local file
            with open(local_path, 'wb') as f:
                f.write(data)
            
            logger.info(f"  ✓ {Path(local_path).name} restored")
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            raise
    
    def list_backups(self, limit: int = 10) -> list:
        """List available backups"""
        if not self.s3_client:
            return []
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix='models/backups/metadata_',
                MaxKeys=limit
            )
            
            if 'Contents' not in response:
                return []
            
            backups = []
            for obj in response['Contents']:
                backups.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'modified': obj['LastModified'].isoformat()
                })
            
            return sorted(backups, key=lambda x: x['modified'], reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
            return []
    
    def _cleanup_old_backups(self):
        """Delete old backups, keeping only latest N versions"""
        try:
            backups = self.list_backups(limit=100)
            
            if len(backups) <= self.keep_versions:
                return
            
            backups_to_delete = backups[self.keep_versions:]
            deleted_count = 0
            
            for backup in backups_to_delete:
                timestamp = backup['key'].split('_')[-1].replace('.json', '')
                
                keys_to_delete = [
                    f"models/backups/tfidf_model_{timestamp}.pkl.gz",
                    f"models/backups/faiss_index_{timestamp}.bin.gz",
                    f"models/backups/embeddings_{timestamp}.npy.gz",
                    f"models/backups/metadata_{timestamp}.json"
                ]
                
                for key in keys_to_delete:
                    try:
                        self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
                        deleted_count += 1
                    except:
                        pass
            
            if deleted_count > 0:
                logger.info(f"✓ Cleaned up {deleted_count} old backup files")
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
