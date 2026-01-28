"""
Search Service Module

This module provides hybrid search functionality combining semantic and keyword-based search.
It uses FAISS for efficient semantic similarity search and TF-IDF for keyword matching.

Classes:
    SearchService: Main service class for search operations.

Example:
    >>> from backend.src.services.search_service import SearchService
    >>> service = SearchService(model_manager, listings)
    >>> results = service.hybrid_search("coffee franchise", top_n=10)
"""

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from threading import Lock
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class SearchService:
    """
    Hybrid search service combining semantic and keyword-based search.
    
    This class provides advanced search functionality by combining:
    - Semantic search using Universal Sentence Encoder and FAISS
    - Keyword search using TF-IDF vectorization
    - Autocomplete suggestions
    - Content-based recommendations
    
    Attributes:
        model_manager: Manager for ML models (USE, TF-IDF, FAISS).
        listings (List[Dict]): List of franchise listings to search.
        tfidf_matrix: Sparse matrix of TF-IDF vectors for all listings.
        search_lock (Lock): Thread lock for safe concurrent access.
    
    Example:
        >>> service = SearchService(model_manager, listings)
        >>> results = service.hybrid_search("restaurant franchise", top_n=5)
        >>> for result in results:
        ...     print(result['title'], result['similarity_score'])
    """
    
    def __init__(self, model_manager, listings: List[Dict[str, Any]]):
        """
        Initialize the SearchService.
        
        Args:
            model_manager: Instance of ModelManager with loaded models.
            listings (List[Dict]): List of franchise listings.
        """
        self.model_manager = model_manager
        self.listings = listings
        self.tfidf_matrix = None
        self.search_lock = Lock()
        self._build_tfidf_matrix()
    
    def _build_tfidf_matrix(self) -> None:
        """
        Build TF-IDF matrix from current listings.
        
        This private method transforms all listing texts into TF-IDF vectors
        for efficient keyword-based search.
        """
        texts = [self._prepare_text(listing) for listing in self.listings]
        with self.model_manager.model_lock:
            if self.model_manager.tfidf_vectorizer:
                self.tfidf_matrix = self.model_manager.tfidf_vectorizer.transform(texts)
    
    @staticmethod
    def _prepare_text(listing: Dict[str, Any]) -> str:
        """
        Prepare listing text for embedding and vectorization.
        
        Combines multiple fields from a listing into a single text string
        for processing by ML models.
        
        Args:
            listing (Dict): A franchise listing dictionary.
        
        Returns:
            str: Concatenated text from all relevant fields.
        """
        return " ".join([
            str(listing.get("title", "")),
            str(listing.get("sector", "")),
            str(listing.get("description", "")),
            str(listing.get("investment_range", "")),
            str(listing.get("location", "")),
            " ".join(listing.get("tags", []))
        ])
    
    def hybrid_search(
        self, 
        query: str, 
        top_n: int = 10, 
        semantic_weight: float = 0.6
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining semantic and keyword matching.
        
        This method combines semantic similarity (using Universal Sentence Encoder
        and FAISS) with keyword matching (using TF-IDF) to provide more accurate
        and relevant search results.
        
        Args:
            query (str): Search query string.
            top_n (int, optional): Number of results to return. Defaults to 10.
            semantic_weight (float, optional): Weight for semantic score (0.0-1.0).
                Defaults to 0.6 (60% semantic, 40% keyword).
        
        Returns:
            List[Dict]: List of matching listings with similarity scores.
                Each result includes:
                - All original listing fields
                - similarity_score: Combined score
                - semantic_score: Semantic similarity score
                - keyword_score: Keyword matching score
        
        Example:
            >>> results = service.hybrid_search("coffee shop", top_n=5, semantic_weight=0.7)
            >>> for result in results:
            ...     print(f"{result['title']}: {result['similarity_score']:.3f}")
        """
        with self.search_lock:
            try:
                # 1. Semantic search using FAISS
                with self.model_manager.model_lock:
                    query_emb = self.model_manager.use_model([query]).numpy().astype("float32")
                    import faiss
                    faiss.normalize_L2(query_emb)
                    semantic_scores, semantic_indices = self.model_manager.faiss_index.search(
                        query_emb, len(self.listings)
                    )
                
                # 2. Keyword search using TF-IDF
                with self.model_manager.model_lock:
                    query_tfidf = self.model_manager.tfidf_vectorizer.transform([query])
                    keyword_scores = cosine_similarity(query_tfidf, self.tfidf_matrix).flatten()
                
                # 3. Combine scores with weighted average
                combined_scores = {}
                for idx in range(len(self.listings)):
                    sem_idx = np.where(semantic_indices[0] == idx)[0]
                    if len(sem_idx) > 0:
                        semantic_score = semantic_scores[0][sem_idx[0]]
                    else:
                        semantic_score = 0.0
                    keyword_score = keyword_scores[idx]
                    combined_scores[idx] = (
                        semantic_weight * semantic_score +
                        (1 - semantic_weight) * keyword_score
                    )
                
                # 4. Sort by combined score and return top results
                sorted_results = sorted(
                    combined_scores.items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )
                results = []
                
                for idx, score in sorted_results[:top_n]:
                    result = self.listings[idx].copy()
                    result["similarity_score"] = float(score)
                    result["semantic_score"] = float(
                        semantic_scores[0][np.where(semantic_indices[0] == idx)[0][0]]
                    )
                    result["keyword_score"] = float(keyword_scores[idx])
                    results.append(result)
                
                return results
                
            except Exception as e:
                logger.error(f"Search failed: {e}", exc_info=True)
                return []
    
    def get_recommendations(
        self, 
        listing_id: int, 
        top_n: int = 5, 
        sector_filter: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get similar franchise recommendations based on a listing ID.
        
        This method finds franchises similar to a given listing using semantic
        similarity. Optionally filters results to the same sector.
        
        Args:
            listing_id (int): ID of the base listing to find recommendations for.
            top_n (int, optional): Number of recommendations to return. Defaults to 5.
            sector_filter (bool, optional): If True, only return franchises in the
                same sector. Defaults to True.
        
        Returns:
            List[Dict]: List of similar listings with similarity scores.
        
        Raises:
            ValueError: If the listing_id is not found.
        
        Example:
            >>> recommendations = service.get_recommendations(listing_id=42, top_n=5)
            >>> for rec in recommendations:
            ...     print(f"{rec['title']}: {rec['similarity_score']:.3f}")
        """
        idx = next(
            (i for i, listing in enumerate(self.listings) if listing.get("id") == listing_id), 
            None
        )
        if idx is None:
            raise ValueError(f"Listing ID {listing_id} not found")
        
        try:
            with self.model_manager.model_lock:
                sim_scores, indices = self.model_manager.faiss_index.search(
                    self.model_manager.embeddings[idx].reshape(1, -1), 
                    top_n + 10
                )
            
            base_listing = self.listings[idx]
            results = []
            
            for i, candidate_idx in enumerate(indices[0]):
                # Skip the base listing itself
                if candidate_idx == idx:
                    continue
                
                # Apply sector filter if enabled
                if sector_filter and self.listings[candidate_idx].get('sector') != base_listing.get('sector'):
                    continue
                
                result = self.listings[candidate_idx].copy()
                result["similarity_score"] = float(sim_scores[0][i])
                results.append(result)
                
                if len(results) >= top_n:
                    break
            
            return results
            
        except Exception as e:
            logger.error(f"Recommendation failed: {e}", exc_info=True)
            return []
    
    def autocomplete(self, query: str, max_suggestions: int = 8) -> List[Dict[str, str]]:
        """
        Generate autocomplete suggestions based on a partial query.
        
        This method searches through listing titles, sectors, and tags to find
        matches for the query string and returns them as autocomplete suggestions.
        
        Args:
            query (str): Partial query string to autocomplete.
            max_suggestions (int, optional): Maximum number of suggestions to return.
                Defaults to 8.
        
        Returns:
            List[Dict]: List of suggestion dictionaries, each containing:
                - text: The suggestion text
                - type: Field type ('title', 'sector', or 'tags')
                - category: The sector of the listing
        
        Example:
            >>> suggestions = service.autocomplete("cof", max_suggestions=5)
            >>> for suggestion in suggestions:
            ...     print(f"{suggestion['text']} ({suggestion['type']})")
            Coffee Shop (title)
            Coffee & Beverages (sector)
        """
        query = query.lower().strip()
        if not query:
            return []
        
        suggestions = []
        seen = set()
        
        for listing in self.listings:
            for field in ["title", "sector", "tags"]:
                values = listing.get(field, [])
                if field == "tags":
                    items = values
                else:
                    items = [values]
                
                for item in items:
                    text = str(item).lower()
                    if query in text and text not in seen:
                        suggestions.append({
                            "text": str(item),
                            "type": field,
                            "category": listing.get("sector", "Other")
                        })
                        seen.add(text)
            
            if len(suggestions) >= max_suggestions:
                break
        
        return suggestions
