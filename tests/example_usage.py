# example_usage.py
"""
Examples of how to use the Franchise API
"""

import requests
import json

API_BASE = "http://localhost:5000"

def print_response(title, response):
    """Helper to print responses nicely"""
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print(f"{'='*60}")
    print(json.dumps(response.json(), indent=2))

# 1. Health Check
print("1️⃣  Health Check")
response = requests.get(f"{API_BASE}/api/health")
print_response("Health Status", response)

# 2. Search
print("\n2️⃣  Search for 'pizza'")
response = requests.get(
    f"{API_BASE}/api/search",
    params={
        'q': 'pizza',
        'top_n': 5,
        'semantic_weight': 0.7
    }
)
print_response("Search Results", response)

# 3. Get Recommendations
print("\n3️⃣  Get Recommendations for Listing ID 1")
response = requests.get(f"{API_BASE}/api/recommend/1?top_n=5")
print_response("Recommendations", response)

# 4. Autocomplete
print("\n4️⃣  Autocomplete for 'coff'")
response = requests.get(
    f"{API_BASE}/api/autocomplete",
    params={'q': 'coff', 'max': 5}
)
print_response("Autocomplete Suggestions", response)

# 5. Get Filters
print("\n5️⃣  Available Filters")
response = requests.get(f"{API_BASE}/api/filters")
print_response("Available Filters", response)

# 6. Get Listings
print("\n6️⃣  Get All Listings (Paginated)")
response = requests.get(
    f"{API_BASE}/api/listings",
    params={'limit': 3, 'offset': 0}
)
print_response("Listings", response)

# 7. Search with Filters
print("\n7️⃣  Search with Sector Filter")
response = requests.get(
    f"{API_BASE}/api/search",
    params={
        'q': 'food',
        'sector': 'Food & Beverage',
        'top_n': 3
    }
)
print_response("Filtered Search", response)

# 8. Benchmark Performance
print("\n8️⃣  Performance Benchmark")
import time

queries = ['pizza', 'coffee', 'fitness', 'retail', 'food']
times = []

for query in queries:
    start = time.time()
    response = requests.get(
        f"{API_BASE}/api/search",
        params={'q': query, 'top_n': 10}
    )
    elapsed = time.time() - start
    times.append(elapsed)
    print(f"  Query: '{query}' - {elapsed*1000:.2f}ms")

avg_time = sum(times) / len(times)
print(f"\n  Average response time: {avg_time*1000:.2f}ms")
print(f"  Throughput: {1/avg_time:.1f} queries/sec")