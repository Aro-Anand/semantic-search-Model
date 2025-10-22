"""
Data Service - Data Loading & Management
"""

import json
import hashlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class DataService:
    """Manages data loading and change detection"""
    
    def __init__(self, data_path: str):
        self.data_path = data_path
        self.listings = []
        self.data_hash = None
        self.metadata = {
            'sectors': set(),
            'tags': set(),
            'locations': set()
        }
    
    def load_data(self) -> bool:
        """Load listings from JSON"""
        try:
            logger.info(f"📖 Loading data from {self.data_path}")
            
            with open(self.data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Support both formats
            if isinstance(data, dict) and 'listings' in data:
                self.listings = data['listings']
            else:
                self.listings = data
            
            # Update hash and metadata
            self._update_hash()
            self._extract_metadata()
            
            logger.info(f"✓ Loaded {len(self.listings)} listings")
            logger.info(f"  - {len(self.metadata['sectors'])} sectors, {len(self.metadata['tags'])} tags, {len(self.metadata['locations'])} locations")
            return True
            
        except Exception as e:
            logger.error(f"Data loading failed: {e}", exc_info=True)
            return False
    
    def _update_hash(self):
        """Calculate data file hash for change detection"""
        try:
            with open(self.data_path, 'rb') as f:
                self.data_hash = hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"Hash calculation failed: {e}")
            self.data_hash = None
    
    def _extract_metadata(self):
        """Extract unique sectors, tags, locations"""
        self.metadata['sectors'] = set(l.get("sector", "Other") for l in self.listings)
        self.metadata['tags'] = set(tag for l in self.listings for tag in l.get("tags", []))
        self.metadata['locations'] = set(l.get("location", "Unknown") for l in self.listings)
    
    def has_changed(self) -> bool:
        """Check if data has changed"""
        old_hash = self.data_hash
        self._update_hash()
        return old_hash != self.data_hash
    
    def get_all_texts(self) -> list:
        """Get all listing texts for training"""
        return [" ".join([
            str(l.get("title", "")),
            str(l.get("sector", "")),
            str(l.get("description", "")),
            str(l.get("investment_range", "")),
            str(l.get("location", "")),
            " ".join(l.get("tags", []))
        ]) for l in self.listings]