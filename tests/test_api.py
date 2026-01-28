#!/usr/bin/env python3
"""
Complete API Testing Script
Tests all endpoints of the Franchise Search API

Usage:
    # Test local server
    python test_api.py

    # Test deployed server
    python test_api.py --url https://your-service.run.app

    # Test with admin key
    python test_api.py --admin-key your-secret-key

    # Run specific test
    python test_api.py --test search
"""

import requests
import json
import sys
import argparse
from datetime import datetime
from typing import Dict, List
import time

# Try to ensure stdout can handle UTF-8 on Windows terminals
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
BOLD = '\033[1m'
RESET = '\033[0m'

class APITester:
    """API Testing Class"""
    
    def __init__(self, base_url: str, admin_key: str = None):
        """
        Initialize API tester
        
        Args:
            base_url: Base URL of API (e.g., https://search-api-559078627637.asia-south1.run.app/)
            admin_key: Admin API key for admin endpoints
        """
        self.base_url = base_url.rstrip('/')
        self.admin_key = admin_key
        self.session = requests.Session()
        
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        
        print(f"\n{BOLD}{'='*70}{RESET}")
        print(f"{BOLD}Franchise Search API - Test Suite{RESET}")
        print(f"{BOLD}{'='*70}{RESET}")
        print(f"Base URL: {self.base_url}")
        print(f"Admin Key: {'Set' if admin_key else 'Not set (admin tests will be skipped)'}")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{BOLD}{'='*70}{RESET}\n")
    
    def print_test(self, name: str):
        """Print test name"""
        print(f"\n{BLUE}> Testing: {name}{RESET}")
    
    def print_success(self, message: str):
        """Print success message"""
        print(f"  {GREEN}[OK] {message}{RESET}")
        self.passed += 1
    
    def print_error(self, message: str):
        """Print error message"""
        print(f"  {RED}[ERR] {message}{RESET}")
        self.failed += 1
    
    def print_skip(self, message: str):
        """Print skip message"""
        print(f"  {YELLOW}[SKIP] {message}{RESET}")
        self.skipped += 1
    
    def print_info(self, message: str):
        """Print info message"""
        print(f"  {YELLOW}[INFO] {message}{RESET}")
    
    def make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        Make HTTP request
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (e.g., /api/health)
            **kwargs: Additional arguments for requests
        
        Returns:
            Response object
        """
        url = f"{self.base_url}{endpoint}"
        
        last_err = None
        for attempt in range(1, 4):
            try:
                response = self.session.request(method, url, timeout=30, **kwargs)
                return response
            except requests.exceptions.RequestException as e:
                last_err = e
                # brief retry to avoid flakiness during cold-start / transient socket issues
                time.sleep(0.5)

        print(f"  {RED}Request failed: {last_err}{RESET}")
        return None

    def wait_for_server(self, timeout_s: int = 45) -> bool:
        """
        Wait for the server to accept connections (useful during cold start).
        """
        start = time.time()
        while time.time() - start < timeout_s:
            r = self.make_request('GET', '/api/health')
            if r and r.status_code in (200, 503):
                return True
            time.sleep(1)
        return False
    
    # ========================================================================
    # PUBLIC API TESTS
    # ========================================================================
    
    def test_health(self):
        """Test health endpoint"""
        self.print_test("GET /api/health")
        
        response = self.make_request('GET', '/api/health')
        
        if not response:
            self.print_error("Request failed")
            return
        
        if response.status_code == 200:
            self.print_success(f"Status: {response.status_code}")
            
            data = response.json()
            
            # Check required fields
            required_fields = ['status', 'version', 'models', 'data']
            for field in required_fields:
                if field in data:
                    self.print_success(f"Field '{field}' present")
                else:
                    self.print_error(f"Field '{field}' missing")
            
            # Print some details
            if 'data' in data:
                self.print_info(f"Listings: {data['data'].get('listings', 0)}")
            if 'models' in data:
                self.print_info(f"Models loaded: {data['models']}")
        else:
            self.print_error(f"Status: {response.status_code}")
            self.print_error(f"Response: {response.text}")
    
    def test_search(self):
        """Test search endpoint"""
        self.print_test("GET /api/search")
        
        # Test 1: Search with query
        response = self.make_request('GET', '/api/search', params={'q': 'coffee', 'top_n': 5})
        
        if not response:
            self.print_error("Request failed")
            return
        
        if response.status_code == 200:
            self.print_success(f"Status: {response.status_code}")
            
            data = response.json()
            
            if 'results' in data:
                self.print_success(f"Got {len(data['results'])} results")
                
                if len(data['results']) > 0:
                    result = data['results'][0]
                    self.print_info(f"Top result: {result.get('title', 'N/A')}")
                    self.print_info(f"Score: {result.get('similarity_score', 0):.4f}")
            else:
                self.print_error("No 'results' field in response")
        else:
            self.print_error(f"Status: {response.status_code}")
        
        # Test 2: Search with filters
        self.print_test("GET /api/search (with filters)")
        response = self.make_request('GET', '/api/search', params={
            'q': 'food',
            'top_n': 3,
            'sector': 'Food & Beverage'
        })
        
        if response is not None and response.status_code == 200:
            self.print_success("Search with filters works")
            data = response.json()
            self.print_info(f"Filtered results: {len(data.get('results', []))}")
        
        # Test 3: Empty query (should fail)
        self.print_test("GET /api/search (empty query)")
        response = self.make_request('GET', '/api/search')
        
        if response is not None and response.status_code == 400:
            self.print_success("Empty query correctly rejected")
        else:
            status = response.status_code if response else "no response"
            self.print_error(f"Empty query should return 400 (got {status})")
    
    def test_recommend(self):
        """Test recommendations endpoint"""
        self.print_test("GET /api/recommend/<id>")
        
        # Pick an existing listing ID from the dataset
        list_resp = self.make_request('GET', '/api/listings', params={'limit': 1, 'offset': 0})
        if not list_resp or list_resp.status_code != 200:
            self.print_error("Could not fetch listings to choose an ID")
            return

        listings = (list_resp.json() or {}).get("listings", [])
        if not listings:
            self.print_skip("No listings available for recommendation test")
            return

        listing_id = listings[0].get("id")
        if listing_id is None:
            self.print_skip("Listing has no 'id' field")
            return

        response = self.make_request('GET', f'/api/recommend/{listing_id}', params={'top_n': 5})
        
        if not response:
            self.print_error("Request failed")
            return
        
        if response.status_code == 200:
            self.print_success(f"Status: {response.status_code}")
            
            data = response.json()
            
            if 'recommendations' in data:
                self.print_success(f"Got {len(data['recommendations'])} recommendations")
                
                if len(data['recommendations']) > 0:
                    rec = data['recommendations'][0]
                    self.print_info(f"Top recommendation: {rec.get('title', 'N/A')}")
            else:
                self.print_error("No 'recommendations' field")
        else:
            self.print_error(f"Status: {response.status_code}")
    
    def test_autocomplete(self):
        """Test autocomplete endpoint"""
        self.print_test("GET /api/autocomplete")
        
        response = self.make_request('GET', '/api/autocomplete', params={'q': 'cof', 'max': 5})
        
        if not response:
            self.print_error("Request failed")
            return
        
        if response.status_code == 200:
            self.print_success(f"Status: {response.status_code}")
            
            data = response.json()
            
            if 'suggestions' in data:
                self.print_success(f"Got {len(data['suggestions'])} suggestions")
                
                for i, suggestion in enumerate(data['suggestions'][:3], 1):
                    self.print_info(f"{i}. {suggestion.get('text', 'N/A')} ({suggestion.get('type', 'N/A')})")
            else:
                self.print_error("No 'suggestions' field")
        else:
            self.print_error(f"Status: {response.status_code}")
    
    def test_filters(self):
        """Test filters endpoint"""
        self.print_test("GET /api/filters")
        
        response = self.make_request('GET', '/api/filters')
        
        if not response:
            self.print_error("Request failed")
            return
        
        if response.status_code == 200:
            self.print_success(f"Status: {response.status_code}")
            
            data = response.json()
            
            expected_fields = ['sectors', 'locations', 'tags', 'total_listings']
            for field in expected_fields:
                if field in data:
                    count = len(data[field]) if isinstance(data[field], list) else data[field]
                    self.print_success(f"{field}: {count}")
                else:
                    self.print_error(f"Missing field: {field}")
        else:
            self.print_error(f"Status: {response.status_code}")
    
    def test_listings(self):
        """Test listings endpoint"""
        self.print_test("GET /api/listings")
        
        response = self.make_request('GET', '/api/listings', params={'limit': 10, 'offset': 0})
        
        if not response:
            self.print_error("Request failed")
            return
        
        if response.status_code == 200:
            self.print_success(f"Status: {response.status_code}")
            
            data = response.json()
            
            if 'listings' in data:
                self.print_success(f"Got {len(data['listings'])} listings")
                self.print_info(f"Total listings: {data.get('total', 0)}")
                self.print_info(f"Has more: {data.get('has_more', False)}")
            else:
                self.print_error("No 'listings' field")
        else:
            self.print_error(f"Status: {response.status_code}")
    
    # ========================================================================
    # ADMIN API TESTS
    # ========================================================================
    
    def test_admin_list_listings(self):
        """Test admin list listings"""
        if not self.admin_key:
            self.print_skip("Admin key not provided")
            return
        
        self.print_test("GET /api/admin/listings")
        
        headers = {'X-Admin-API-Key': self.admin_key}
        response = self.make_request('GET', '/api/admin/listings', headers=headers)
        
        if not response:
            self.print_error("Request failed")
            return
        
        if response.status_code == 200:
            self.print_success("Admin authentication works")
            data = response.json()
            self.print_info(f"Total listings: {data.get('total', 0)}")
        elif response.status_code == 401:
            self.print_error("Admin authentication failed (check API key)")
        else:
            self.print_error(f"Status: {response.status_code}")
    
    def test_admin_add_listing(self):
        """Test adding a new listing"""
        if not self.admin_key:
            self.print_skip("Admin key not provided")
            return
        
        self.print_test("POST /api/admin/listings")
        
        new_listing = {
            "title": f"Test Franchise {int(time.time())}",
            "sector": "Testing",
            "description": "This is a test listing created by the test suite",
            "investment_range": "$10k-$50k",
            "location": "Test Location",
            "tags": ["test", "automated"]
        }
        
        headers = {
            'X-Admin-API-Key': self.admin_key,
            'Content-Type': 'application/json'
        }
        
        response = self.make_request('POST', '/api/admin/listings', 
                                     headers=headers, 
                                     json=new_listing)
        
        if not response:
            self.print_error("Request failed")
            return
        
        if response.status_code == 201:
            self.print_success("Listing created successfully")
            data = response.json()
            listing_id = data.get('id')
            self.print_info(f"Created listing ID: {listing_id}")
            
            # Store for cleanup
            if not hasattr(self, 'created_listings'):
                self.created_listings = []
            self.created_listings.append(listing_id)
            
            return listing_id
        else:
            self.print_error(f"Status: {response.status_code}")
            self.print_error(f"Response: {response.text}")
            return None
    
    def test_admin_update_listing(self, listing_id: str = None):
        """Test updating a listing"""
        if not self.admin_key:
            self.print_skip("Admin key not provided")
            return
        
        if not listing_id:
            self.print_skip("No listing ID provided for update test")
            return
        
        self.print_test(f"PUT /api/admin/listings/{listing_id}")
        
        updates = {
            "description": f"Updated at {datetime.now().isoformat()}",
            "tags": ["test", "automated", "updated"]
        }
        
        headers = {
            'X-Admin-API-Key': self.admin_key,
            'Content-Type': 'application/json'
        }
        
        response = self.make_request('PUT', f'/api/admin/listings/{listing_id}',
                                     headers=headers,
                                     json=updates)
        
        if response is not None and response.status_code == 200:
            self.print_success("Listing updated successfully")
        else:
            self.print_error(f"Update failed: {response.status_code if response else 'No response'}")
    
    def test_admin_delete_listing(self, listing_id: str = None):
        """Test deleting a listing"""
        if not self.admin_key:
            self.print_skip("Admin key not provided")
            return
        
        if not listing_id:
            self.print_skip("No listing ID provided for delete test")
            return
        
        self.print_test(f"DELETE /api/admin/listings/{listing_id}")
        
        headers = {'X-Admin-API-Key': self.admin_key}
        
        response = self.make_request('DELETE', f'/api/admin/listings/{listing_id}',
                                     headers=headers)
        
        if response is not None and response.status_code == 200:
            self.print_success("Listing deleted successfully")
        else:
            self.print_error(f"Delete failed: {response.status_code if response else 'No response'}")
    
    def test_admin_retrain_status(self):
        """Test retraining status"""
        if not self.admin_key:
            self.print_skip("Admin key not provided")
            return
        
        self.print_test("GET /api/admin/retrain/status")
        
        headers = {'X-Admin-API-Key': self.admin_key}
        response = self.make_request('GET', '/api/admin/retrain/status', headers=headers)
        
        if response is not None and response.status_code == 200:
            self.print_success("Got retraining status")
            data = response.json()
            self.print_info(f"Is retraining: {data.get('is_retraining', False)}")
            self.print_info(f"Strategy: {data.get('strategy', 'N/A')}")
            self.print_info(f"Additions since retrain: {data.get('additions_since_retrain', 0)}")
        else:
            self.print_error(f"Status check failed")
    
    def test_admin_manual_retrain(self):
        """Test manual retraining trigger"""
        if not self.admin_key:
            self.print_skip("Admin key not provided")
            return
        
        self.print_test("POST /api/admin/retrain")
        self.print_info("This will trigger background retraining...")
        
        headers = {'X-Admin-API-Key': self.admin_key}
        response = self.make_request('POST', '/api/admin/retrain?background=true&force=true',
                                     headers=headers)
        
        if response is not None and response.status_code == 200:
            self.print_success("Retraining triggered")
            data = response.json()
            self.print_info(f"Status: {data.get('status', 'N/A')}")
        else:
            self.print_error("Retrain trigger failed")
    
    def test_admin_stats(self):
        """Test admin stats endpoint"""
        if not self.admin_key:
            self.print_skip("Admin key not provided")
            return
        
        self.print_test("GET /api/admin/stats")
        
        headers = {'X-Admin-API-Key': self.admin_key}
        response = self.make_request('GET', '/api/admin/stats', headers=headers)
        
        if response is not None and response.status_code == 200:
            self.print_success("Got admin stats")
            data = response.json()
            if 'data' in data:
                self.print_info(f"Total listings: {data['data'].get('total_listings', 0)}")
            if 'retraining' in data:
                self.print_info(f"Retraining strategy: {data['retraining'].get('strategy', 'N/A')}")
        else:
            self.print_error("Stats failed")
    
    # ========================================================================
    # PERFORMANCE TESTS
    # ========================================================================
    
    def test_performance(self):
        """Test response times"""
        self.print_test("Performance Tests")
        
        endpoints = [
            ('GET', '/api/health', {}),
            ('GET', '/api/search', {'params': {'q': 'coffee', 'top_n': 5}}),
            ('GET', '/api/autocomplete', {'params': {'q': 'co'}}),
            ('GET', '/api/filters', {}),
        ]
        
        for method, endpoint, kwargs in endpoints:
            start = time.time()
            response = self.make_request(method, endpoint, **kwargs)
            duration = (time.time() - start) * 1000  # ms
            
            if response is not None and response.status_code == 200:
                if duration < 100:
                    status = f"{GREEN}Excellent{RESET}"
                elif duration < 500:
                    status = f"{YELLOW}Good{RESET}"
                else:
                    status = f"{RED}Slow{RESET}"
                
                self.print_info(f"{endpoint}: {duration:.0f}ms {status}")
            else:
                self.print_error(f"{endpoint}: Failed")
    
    # ========================================================================
    # TEST RUNNER
    # ========================================================================
    
    def run_all_tests(self):
        """Run all tests"""
        # Avoid flakiness on cold start (models can take time to load)
        self.print_info("Waiting for server to be ready...")
        if not self.wait_for_server():
            self.print_error("Server did not become ready in time")
            self.print_summary()
            return

        print(f"\n{BOLD}Running Public API Tests...{RESET}")
        self.test_health()
        self.test_search()
        self.test_recommend()
        self.test_autocomplete()
        self.test_filters()
        self.test_listings()
        
        print(f"\n{BOLD}Running Admin API Tests...{RESET}")
        self.test_admin_list_listings()
        
        # Create, update, delete cycle
        created_id = self.test_admin_add_listing()
        if created_id:
            time.sleep(1)  # Wait a bit
            self.test_admin_update_listing(created_id)
            time.sleep(1)
            self.test_admin_delete_listing(created_id)
        
        self.test_admin_retrain_status()
        self.test_admin_stats()
        # Skip manual retrain in normal tests (takes time)
        # self.test_admin_manual_retrain()
        
        print(f"\n{BOLD}Running Performance Tests...{RESET}")
        self.test_performance()
        
        self.print_summary()
    
    def run_specific_test(self, test_name: str):
        """Run specific test by name"""
        test_map = {
            'health': self.test_health,
            'search': self.test_search,
            'recommend': self.test_recommend,
            'autocomplete': self.test_autocomplete,
            'filters': self.test_filters,
            'listings': self.test_listings,
            'admin_list': self.test_admin_list_listings,
            'admin_add': self.test_admin_add_listing,
            'admin_stats': self.test_admin_stats,
            'performance': self.test_performance,
        }
        
        if test_name in test_map:
            test_map[test_name]()
            self.print_summary()
        else:
            print(f"{RED}Unknown test: {test_name}{RESET}")
            print(f"Available tests: {', '.join(test_map.keys())}")
    
    def print_summary(self):
        """Print test summary"""
        total = self.passed + self.failed + self.skipped
        
        print(f"\n{BOLD}{'='*70}{RESET}")
        print(f"{BOLD}Test Summary{RESET}")
        print(f"{BOLD}{'='*70}{RESET}")
        print(f"Total Tests: {total}")
        print(f"{GREEN}Passed: {self.passed}{RESET}")
        print(f"{RED}Failed: {self.failed}{RESET}")
        print(f"{YELLOW}Skipped: {self.skipped}{RESET}")
        
        if self.failed == 0 and self.passed > 0:
            print(f"\n{GREEN}{BOLD}[OK] All tests passed!{RESET}")
        elif self.failed > 0:
            print(f"\n{RED}{BOLD}[ERR] Some tests failed{RESET}")
        
        print(f"{BOLD}{'='*70}{RESET}\n")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Test Franchise Search API')
    parser.add_argument('--url', default='http://localhost:8080',
                       help='Base URL of API (default: http://localhost:8080)')
    parser.add_argument('--admin-key', default=None,
                       help='Admin API key for admin endpoint tests')
    parser.add_argument('--test', default=None,
                       help='Run specific test (e.g., search, health)')
    
    args = parser.parse_args()
    
    # Create tester
    tester = APITester(args.url, args.admin_key)
    
    # Run tests
    if args.test:
        tester.run_specific_test(args.test)
    else:
        tester.run_all_tests()
    
    # Exit with proper code
    sys.exit(0 if tester.failed == 0 else 1)

if __name__ == '__main__':
    main()