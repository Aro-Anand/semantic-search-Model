import pytest
import os, sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.search_service import SearchService
from services.data_service import DataService
from models.model_manager import ModelManager
from config import config

@pytest.fixture
def data_service():
    """Initialize data service"""
    return DataService(config.DATA_PATH)

@pytest.fixture
def model_manager(data_service):
    """Initialize model manager"""
    mm = ModelManager()
    texts = data_service.get_all_texts()
    mm.initialize_models(texts)
    return mm

@pytest.fixture
def search_service(model_manager, data_service):
    """Initialize search service"""
    return SearchService(model_manager, data_service.listings)

class TestSearchService:
    """Test search service"""
    
    def test_hybrid_search_returns_results(self, search_service):
        """Test hybrid search returns results"""
        results = search_service.hybrid_search("pizza", top_n=5)
        assert isinstance(results, list)
    
    def test_hybrid_search_has_scores(self, search_service):
        """Test results have similarity scores"""
        results = search_service.hybrid_search("pizza", top_n=1)
        
        if len(results) > 0:
            result = results[0]
            assert 'similarity_score' in result
            assert 'semantic_score' in result
            assert 'keyword_score' in result
    
    def test_get_recommendations(self, search_service):
        """Test recommendations"""
        if len(search_service.listings) > 1:
            listing_id = search_service.listings[0]['id']
            results = search_service.get_recommendations(listing_id, top_n=5)
            assert isinstance(results, list)
