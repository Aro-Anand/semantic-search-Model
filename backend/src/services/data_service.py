"""
Data Service Module

This module handles data loading, management, and change detection for franchise listings.
It provides functionality to load data from JSON files, track changes, and extract metadata.

Classes:
    DataService: Main service class for data management.

Example:
    >>> from backend.src.services.data_service import DataService
    >>> service = DataService('dataset.json')
    >>> if service.load_data():
    ...     print(f"Loaded {len(service.listings)} listings")
"""

import json
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Set, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class DataService:
    """
    Manages data loading and change detection for franchise listings.
    
    This class handles loading franchise data from JSON files, tracking changes
    to the data, and extracting metadata such as sectors, tags, and locations.
    
    Attributes:
        data_path (str): Path to the data JSON file.
        listings (List[Dict]): List of franchise listings loaded from the file.
        data_hash (str): MD5 hash of the data file for change detection.
        metadata (Dict[str, Set]): Extracted metadata including sectors, tags, and locations.
    
    Example:
        >>> service = DataService('dataset.json')
        >>> service.load_data()
        >>> print(service.metadata['sectors'])
        {'Food & Beverage', 'Retail', 'Services'}
    """
    
    def __init__(self, data_path: str):
        """
        Initialize the DataService.
        
        Args:
            data_path (str): Path to the JSON file containing franchise listings.
        """
        self.data_path = data_path
        self.listings: List[Dict[str, Any]] = []
        self.data_hash: str = None
        self.metadata: Dict[str, Set] = {
            'sectors': set(),
            'tags': set(),
            'locations': set()
        }
        # Tracks input file format so we can write back in the same shape
        # - 'array': file is a JSON array
        # - 'wrapped': file is an object with a 'listings' key
        self._file_format: str = 'array'
    
    def load_data(self) -> bool:
        """
        Load franchise listings from the JSON file.
        
        This method reads the JSON file, parses the listings, updates the data hash,
        and extracts metadata. It supports both array format and object format with
        a 'listings' key.
        
        Returns:
            bool: True if data was loaded successfully, False otherwise.
            
        Raises:
            Exception: Logs error if file reading or parsing fails.
            
        Example:
            >>> service = DataService('dataset.json')
            >>> success = service.load_data()
            >>> if success:
            ...     print(f"Loaded {len(service.listings)} listings")
        """
        try:
            logger.info(f"📖 Loading data from {self.data_path}")
            
            with open(self.data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Support both formats: array or object with 'listings' key
            if isinstance(data, dict) and 'listings' in data:
                self.listings = data['listings']
                self._file_format = 'wrapped'
            else:
                self.listings = data
                self._file_format = 'array'
            
            # Update hash and metadata
            self._update_hash()
            self._extract_metadata()
            
            logger.info(f"✓ Loaded {len(self.listings)} listings")
            logger.info(
                f"  - {len(self.metadata['sectors'])} sectors, "
                f"{len(self.metadata['tags'])} tags, "
                f"{len(self.metadata['locations'])} locations"
            )
            return True
            
        except Exception as e:
            logger.error(f"Data loading failed: {e}", exc_info=True)
            return False

    def _persist(self) -> None:
        """
        Persist the current listings back to disk, preserving the original file shape.
        """
        payload: Any
        if self._file_format == 'wrapped':
            payload = {"listings": self.listings}
        else:
            payload = self.listings

        path = Path(self.data_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        # Refresh hash + metadata after write
        self._update_hash()
        self._extract_metadata()

    def _next_id(self) -> int:
        """
        Compute next numeric ID based on current listings.
        """
        max_id = 0
        for listing in self.listings:
            try:
                max_id = max(max_id, int(listing.get("id", 0)))
            except Exception:
                continue
        return max_id + 1

    def add_listing(self, listing: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new listing, persist to disk, and update in-memory metadata/hash.

        Required fields: title, sector
        If 'id' is missing, an auto-incremented integer ID is assigned.
        """
        if not isinstance(listing, dict):
            raise ValueError("Listing must be a JSON object")

        title = str(listing.get("title", "")).strip()
        sector = str(listing.get("sector", "")).strip()
        if not title or not sector:
            raise ValueError("Fields 'title' and 'sector' are required")

        # Copy to avoid mutating caller's object
        new_listing = dict(listing)

        if "id" not in new_listing or new_listing.get("id") in (None, "", 0):
            new_listing["id"] = self._next_id()
        else:
            # Ensure unique
            existing_ids = {str(x.get("id")) for x in self.listings}
            if str(new_listing.get("id")) in existing_ids:
                raise ValueError(f"Listing id '{new_listing.get('id')}' already exists")

        # Normalize tags to list
        if "tags" in new_listing and new_listing["tags"] is not None and not isinstance(new_listing["tags"], list):
            raise ValueError("Field 'tags' must be an array of strings")

        self.listings.append(new_listing)
        self._persist()
        return new_listing

    def update_listing(self, listing_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing listing by id and persist.
        """
        if not isinstance(updates, dict):
            raise ValueError("Updates must be a JSON object")

        idx = next((i for i, l in enumerate(self.listings) if int(l.get("id", -1)) == int(listing_id)), None)
        if idx is None:
            raise ValueError(f"Listing ID {listing_id} not found")

        updated = dict(self.listings[idx])
        # Disallow id change
        if "id" in updates and updates["id"] != updated.get("id"):
            raise ValueError("Field 'id' cannot be modified")

        updated.update(updates)
        # Revalidate required fields
        if not str(updated.get("title", "")).strip() or not str(updated.get("sector", "")).strip():
            raise ValueError("Fields 'title' and 'sector' are required")

        if "tags" in updated and updated["tags"] is not None and not isinstance(updated["tags"], list):
            raise ValueError("Field 'tags' must be an array of strings")

        self.listings[idx] = updated
        self._persist()
        return updated

    def delete_listing(self, listing_id: int) -> None:
        """
        Delete a listing by id and persist.
        """
        before = len(self.listings)
        self.listings = [l for l in self.listings if int(l.get("id", -1)) != int(listing_id)]
        if len(self.listings) == before:
            raise ValueError(f"Listing ID {listing_id} not found")
        self._persist()
    
    def _update_hash(self) -> None:
        """
        Calculate MD5 hash of the data file for change detection.
        
        This private method computes the MD5 hash of the data file to enable
        detection of changes to the underlying data.
        
        Note:
            Sets self.data_hash to None if hash calculation fails.
        """
        try:
            with open(self.data_path, 'rb') as f:
                self.data_hash = hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"Hash calculation failed: {e}")
            self.data_hash = None
    
    def _extract_metadata(self) -> None:
        """
        Extract unique sectors, tags, and locations from listings.
        
        This private method processes all listings to build sets of unique
        values for sectors, tags, and locations, which are stored in the
        metadata dictionary.
        """
        self.metadata['sectors'] = set(
            listing.get("sector", "Other") for listing in self.listings
        )
        self.metadata['tags'] = set(
            tag for listing in self.listings for tag in listing.get("tags", [])
        )
        self.metadata['locations'] = set(
            listing.get("location", "Unknown") for listing in self.listings
        )
    
    def has_changed(self) -> bool:
        """
        Check if the data file has changed since last load.
        
        This method compares the current file hash with the stored hash to
        detect if the data file has been modified.
        
        Returns:
            bool: True if the data has changed, False otherwise.
            
        Example:
            >>> service = DataService('dataset.json')
            >>> service.load_data()
            >>> # ... time passes, file might be updated ...
            >>> if service.has_changed():
            ...     service.load_data()  # Reload data
        """
        old_hash = self.data_hash
        self._update_hash()
        return old_hash != self.data_hash
    
    def get_all_texts(self) -> List[str]:
        """
        Get concatenated text from all listings for model training.
        
        This method combines all relevant fields from each listing into a single
        text string, which is useful for training machine learning models.
        
        Returns:
            List[str]: List of concatenated text strings, one per listing.
            
        Example:
            >>> service = DataService('dataset.json')
            >>> service.load_data()
            >>> texts = service.get_all_texts()
            >>> print(texts[0])
            'McDonald's Food & Beverage Fast food franchise...'
        """
        return [
            " ".join([
                str(listing.get("title", "")),
                str(listing.get("sector", "")),
                str(listing.get("description", "")),
                str(listing.get("investment_range", "")),
                str(listing.get("location", "")),
                " ".join(listing.get("tags", []))
            ])
            for listing in self.listings
        ]
