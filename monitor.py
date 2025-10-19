import requests
import logging
from datetime import datetime
from config import config

logger = logging.getLogger(__name__)

class HealthMonitor:
    """Monitor API health and performance"""
    
    def __init__(self, api_url: str, check_interval: int = 300):
        self.api_url = api_url
        self.check_interval = check_interval
        self.metrics = {
            'total_checks': 0,
            'successful': 0,
            'failed': 0,
            'avg_response_time': 0
        }
    
    def check_health(self) -> bool:
        """Check API health endpoint"""
        try:
            start = datetime.now()
            response = requests.get(
                f"{self.api_url}/api/health",
                timeout=10
            )
            duration = (datetime.now() - start).total_seconds()
            
            self.metrics['total_checks'] += 1
            
            if response.status_code == 200:
                data = response.json()
                self.metrics['successful'] += 1
                
                logger.info(f"✅ Health check passed ({duration:.2f}s)")
                logger.info(f"   Status: {data['status']}")
                logger.info(f"   Listings: {data['data']['listings']}")
                return True
            else:
                self.metrics['failed'] += 1
                logger.error(f"❌ Health check failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.metrics['failed'] += 1
            logger.error(f"❌ Health check error: {e}")
            return False
    
    def check_search(self, query: str) -> bool:
        """Test search functionality"""
        try:
            response = requests.get(
                f"{self.api_url}/api/search",
                params={'q': query, 'top_n': 5},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Search test passed: {len(data['results'])} results")
                return True
            else:
                logger.error(f"❌ Search test failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Search test error: {e}")
            return False
    
    def generate_report(self) -> dict:
        """Generate monitoring report"""
        success_rate = (
            self.metrics['successful'] / self.metrics['total_checks'] * 100
            if self.metrics['total_checks'] > 0 else 0
        )
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'total_checks': self.metrics['total_checks'],
            'successful': self.metrics['successful'],
            'failed': self.metrics['failed'],
            'success_rate': f"{success_rate:.2f}%"
        }

# Usage
if __name__ == '__main__':
    monitor = HealthMonitor('http://localhost:5000')
    
    # Run checks
    monitor.check_health()
    monitor.check_search('pizza')
    
    # Print report
    import json
    print(json.dumps(monitor.generate_report(), indent=2))