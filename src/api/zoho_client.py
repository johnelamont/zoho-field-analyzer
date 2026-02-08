"""
Zoho API Client
Handles authentication and API requests to Zoho CRM
"""
import requests
import time
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ZohoAPIClient:
    """Client for interacting with Zoho CRM API"""
    
    BASE_URL = 'https://crm.zoho.com/crm/v2'
    
    def __init__(self, cookie: str, csrf_token: str, org_id: str):
        """
        Initialize Zoho API client
        
        Args:
            cookie: Full Cookie header value from browser
            csrf_token: CSRF token (with crmcsrfparam= prefix)
            org_id: Zoho organization ID
        """
        self.headers = {
            'Cookie': cookie,
            'x-zcsrf-token': csrf_token,
            'x-crm-org': org_id,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'x-requested-with': 'XMLHttpRequest, XMLHttpRequest'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def get(self, endpoint: str, params: Optional[Dict] = None, 
            retry_count: int = 3, delay: float = 0.5) -> Optional[Dict[str, Any]]:
        """
        Make GET request to Zoho API with retry logic
        
        Args:
            endpoint: API endpoint (will be appended to BASE_URL)
            params: Query parameters
            retry_count: Number of retries on failure
            delay: Delay between retries in seconds
            
        Returns:
            JSON response data or None on failure
        """
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        
        for attempt in range(retry_count):
            try:
                response = self.session.get(url, params=params)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:  # Rate limit
                    logger.warning(f"Rate limited, waiting {delay * 2} seconds...")
                    time.sleep(delay * 2)
                    continue
                else:
                    logger.error(f"Error {response.status_code}: {response.text}")
                    if attempt < retry_count - 1:
                        time.sleep(delay)
                        continue
                    return None
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed: {e}")
                if attempt < retry_count - 1:
                    time.sleep(delay)
                    continue
                return None
                
        return None
    
    def post(self, endpoint: str, data: Optional[Dict] = None,
             retry_count: int = 3, delay: float = 0.5) -> Optional[Dict[str, Any]]:
        """
        Make POST request to Zoho API with retry logic
        
        Args:
            endpoint: API endpoint
            data: POST data
            retry_count: Number of retries
            delay: Delay between retries
            
        Returns:
            JSON response or None
        """
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        
        for attempt in range(retry_count):
            try:
                response = self.session.post(url, data=data)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    logger.warning(f"Rate limited, waiting {delay * 2} seconds...")
                    time.sleep(delay * 2)
                    continue
                else:
                    logger.error(f"Error {response.status_code}: {response.text}")
                    if attempt < retry_count - 1:
                        time.sleep(delay)
                        continue
                    return None
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed: {e}")
                if attempt < retry_count - 1:
                    time.sleep(delay)
                    continue
                return None
                
        return None
    
    def paginated_get(self, endpoint: str, start_param: str = 'start',
                     limit: int = 50, max_items: Optional[int] = None) -> list:
        """
        Get paginated results from Zoho API
        
        Args:
            endpoint: API endpoint
            start_param: Name of the pagination start parameter
            limit: Items per page
            max_items: Maximum items to fetch (None = all)
            
        Returns:
            List of all items from all pages
        """
        all_items = []
        start = 1
        page = 1
        
        while True:
            params = {start_param: start, 'limit': limit}
            
            logger.info(f"Fetching page {page} (items {start}-{start+limit-1})...")
            data = self.get(endpoint, params=params)
            
            if not data:
                logger.warning("No data returned, stopping pagination")
                break
            
            # Try to extract items from different possible response structures
            items = None
            for key in ['functions', 'workflows', 'blueprints', 'modules', 'data']:
                if key in data:
                    items = data[key]
                    break
            
            if not items or len(items) == 0:
                logger.info("No more items found")
                break
            
            all_items.extend(items)
            logger.info(f"  Found {len(items)} items (total: {len(all_items)})")
            
            # Check if we've hit the max
            if max_items and len(all_items) >= max_items:
                logger.info(f"Reached max items limit: {max_items}")
                break
            
            # Check if we're done
            if len(items) < limit:
                logger.info("Received fewer than limit - last page")
                break
            
            start += limit
            page += 1
            time.sleep(0.5)  # Be nice to the API
        
        return all_items
