"""
Search Service - Hybrid Search (Semantic + Keyword)
"""

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from threading import Lock
import logging

logger = logging.getLogger(__name__)

class SearchService:
    """Hybrid search combining semantic and keyword search"""
    
    def __init__(self, model_manager, listings):
        self.model_manager = model_manager
        self.listings = listings
        self.tfidf_matrix = None
        self.search_lock = Lock()
        self._build_tfidf_matrix()
    
    def _build_tfidf_matrix(self):
        """Build TF-IDF matrix from current listings"""
        texts = [self._prepare_text(l) for l in self.listings]
        with self.model_manager.model_lock:
            if self.model_manager.tfidf_vectorizer:
                self.tfidf_matrix = self.model_manager.tfidf_vectorizer.transform(texts)
    
    @staticmethod
    def _prepare_text(listing: dict) -> str:
        """Prepare text for embedding"""
        return " ".join([
            str(listing.get("title", "")),
            str(listing.get("sector", "")),
            str(listing.get("description", "")),
            str(listing.get("investment_range", "")),
            str(listing.get("location", "")),
            " ".join(listing.get("tags", []))
        ])
    
    def hybrid_search(self, query: str, top_n: int = 10, semantic_weight: float = 0.6) -> list:
        """Hybrid search combining semantic + keyword"""
        with self.search_lock:
            try:
                # 1. Semantic search
                with self.model_manager.model_lock:
                    query_emb = self.model_manager.use_model([query]).numpy().astype("float32")
                    import faiss
                    faiss.normalize_L2(query_emb)
                    semantic_scores, semantic_indices = self.model_manager.faiss_index.search(
                        query_emb, len(self.listings)
                    )
                
                # 2. Keyword search
                with self.model_manager.model_lock:
                    query_tfidf = self.model_manager.tfidf_vectorizer.transform([query])
                    keyword_scores = cosine_similarity(query_tfidf, self.tfidf_matrix).flatten()
                
                # 3. Combine scores
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
                
                # 4. Sort and return
                sorted_results = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
                results = []
                
                for idx, score in sorted_results[:top_n]:
                    result = self.listings[idx].copy()
                    result["similarity_score"] = float(score)
                    result["semantic_score"] = float(semantic_scores[0][np.where(semantic_indices[0] == idx)[0][0]])
                    result["keyword_score"] = float(keyword_scores[idx])
                    results.append(result)
                
                return results
                
            except Exception as e:
                logger.error(f"Search failed: {e}", exc_info=True)
                return []
    
    def get_recommendations(self, listing_id: int, top_n: int = 5, sector_filter: bool = True) -> list:
        """Get similar franchises"""
        idx = next((i for i, l in enumerate(self.listings) if l.get("id") == listing_id), None)
        if idx is None:
            raise ValueError(f"Listing ID {listing_id} not found")
        
        try:
            with self.model_manager.model_lock:
                sim_scores, indices = self.model_manager.faiss_index.search(
                    self.model_manager.embeddings[idx].reshape(1, -1), top_n + 10
                )
            
            base_listing = self.listings[idx]
            results = []
            
            for i, candidate_idx in enumerate(indices[0]):
                if candidate_idx == idx:
                    continue
                
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
    
    def autocomplete(self, query: str, max_suggestions: int = 8) -> list:
        """Generate autocomplete suggestions"""
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