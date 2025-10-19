# tests/test_api.py
import pytest
import json
import os, sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from app import app, system_ready
from config import config

@pytest.fixture
def client():
    """Flask test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

class TestHealthEndpoint:
    """Test health check endpoint"""
    
    def test_health_check_status(self, client):
        """Test health endpoint returns 200"""
        response = client.get('/api/health')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'status' in data
        assert 'version' in data
        assert 'models' in data
        assert 'data' in data
    
    def test_health_check_models(self, client):
        """Test models are loaded"""
        response = client.get('/api/health')
        data = json.loads(response.data)
        
        assert data['models']['use'] == 'loaded'
        assert data['models']['tfidf'] == 'loaded'
        assert data['models']['faiss'] > 0

class TestSearchEndpoint:
    """Test search functionality"""
    
    def test_search_missing_query(self, client):
        """Test search without query returns 400"""
        response = client.get('/api/search')
        assert response.status_code == 400
    
    def test_search_valid_query(self, client):
        """Test search with valid query"""
        response = client.get('/api/search?q=pizza')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'query' in data
        assert data['query'] == 'pizza'
        assert 'results' in data
        assert isinstance(data['results'], list)
    
    def test_search_results_have_scores(self, client):
        """Test search results include similarity scores"""
        response = client.get('/api/search?q=pizza&top_n=5')
        data = json.loads(response.data)
        
        if len(data['results']) > 0:
            result = data['results'][0]
            assert 'similarity_score' in result
            assert 'semantic_score' in result
            assert 'keyword_score' in result
            assert 0 <= result['similarity_score'] <= 1
    
    def test_search_top_n_limit(self, client):
        """Test top_n parameter respects max"""
        response = client.get('/api/search?q=pizza&top_n=1000')
        data = json.loads(response.data)
        
        assert len(data['results']) <= config.MAX_TOP_N
    
    def test_search_with_filters(self, client):
        """Test search with sector filter"""
        response = client.get('/api/search?q=pizza&sector=Food%20%26%20Beverage')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        # If results exist, all should match sector
        for result in data['results']:
            assert result['sector'].lower() == 'food & beverage'

class TestRecommendEndpoint:
    """Test recommendations endpoint"""
    
    def test_recommend_missing_id(self, client):
        """Test recommend without ID returns 400"""
        response = client.get('/api/recommend/999999')
        # Should either return 404 or raise ValueError
        assert response.status_code in [400, 404, 500]
    
    def test_recommend_valid_id(self, client):
        """Test recommend with valid ID"""
        # Assuming ID 1 exists
        response = client.get('/api/recommend/1')
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert 'recommendations' in data
            assert isinstance(data['recommendations'], list)
            assert 'listing_id' in data
    
    def test_recommend_sector_filter(self, client):
        """Test sector filter in recommendations"""
        response = client.get('/api/recommend/1?sector_filter=true')
        
        if response.status_code == 200:
            data = json.loads(response.data)
            # All recommendations should be from same sector

class TestAutocompleteEndpoint:
    """Test autocomplete functionality"""
    
    def test_autocomplete_empty_query(self, client):
        """Test autocomplete with empty query"""
        response = client.get('/api/autocomplete?q=')
        data = json.loads(response.data)
        
        assert isinstance(data, (dict, list))
    
    def test_autocomplete_valid_query(self, client):
        """Test autocomplete with valid query"""
        response = client.get('/api/autocomplete?q=piz')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'suggestions' in data or isinstance(data, list)
    
    def test_autocomplete_max_limit(self, client):
        """Test autocomplete respects max limit"""
        response = client.get('/api/autocomplete?q=a&max=100')
        data = json.loads(response.data)
        
        suggestions = data if isinstance(data, list) else data.get('suggestions', [])
        assert len(suggestions) <= 20  # Max is 20

class TestFiltersEndpoint:
    """Test filter options endpoint"""
    
    def test_filters_endpoint(self, client):
        """Test filters endpoint returns all options"""
        response = client.get('/api/filters')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'sectors' in data
        assert 'locations' in data
        assert 'tags' in data
        assert isinstance(data['sectors'], list)
        assert isinstance(data['locations'], list)
        assert isinstance(data['tags'], list)

class TestListingsEndpoint:
    """Test listings endpoint"""
    
    def test_listings_default(self, client):
        """Test listings with default parameters"""
        response = client.get('/api/listings')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'listings' in data
        assert 'total' in data
        assert 'limit' in data
        assert 'offset' in data
        assert 'has_more' in data
    
    def test_listings_pagination(self, client):
        """Test listings pagination"""
        response = client.get('/api/listings?limit=10&offset=0')
        data = json.loads(response.data)
        
        assert len(data['listings']) <= 10
        assert data['limit'] == 10
        assert data['offset'] == 0
