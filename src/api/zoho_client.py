"""
Zoho CRM API Client
Handles authentication and requests to Zoho CRM API with proper header support
"""
import requests
import time
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class ZohoAPIClient:
    """
    Client for making authenticated requests to Zoho CRM API
    
    Handles:
    - Cookie-based authentication
    - CSRF token management
    - Org ID headers
    - X-Static-Token header (required for some endpoints)
    - Retry logic with exponential backoff
    - Rate limiting
    """
    
    def __init__(self, cookie: str, csrf_token: str, org_id: str, 
                 static_token: Optional[str] = None,
                 max_retries: int = 3, retry_delay: float = 1.0):
        """
        Initialize the Zoho API client
        
        Args:
            cookie: Full Cookie header value from browser
            csrf_token: CSRF token (with crmcsrfparam= prefix)
            org_id: Organization ID
            static_token: Optional X-Static-Token value (required for some endpoints)
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries in seconds
        """
        self.org_id = org_id
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Create session
        self.session = requests.Session()
        
        # Parse and set cookies
        #self._parse_cookies(cookie)
        #self.session.headers['Cookie'] = cookie
        
        # Set standard headers
        self.session.headers.update({
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': 'https://crm.zoho.com/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
            'x-crm-org': org_id,
            'x-requested-with': 'XMLHttpRequest',
            'x-static-version': static_token or '',
            'x-zcsrf-token': csrf_token,
            'Cookie': cookie,
        })  
        
        # Add X-Static-Token if provided (CRITICAL for some endpoints like blueprints)
        if static_token:
            self.session.headers['x-static-version'] = static_token
            logger.info(f"Added X-Static-Token header: {static_token}")
        else:
            logger.warning("No static_token provided - some endpoints may fail")
        
        logger.info(f"Initialized Zoho API client for org {org_id}")
        logger.info(f"Parsed {len(self.session.cookies)} cookies")
        logger.info(f"Headers: {list(self.session.headers.keys())}")
    
    def _parse_cookies(self, cookie_string: str):
        """
        Parse cookie string and add to session
        
        Args:
            cookie_string: Cookie header value from browser
        """
        for cookie in cookie_string.split('; '):
            if '=' in cookie:
                name, value = cookie.split('=', 1)
                self.session.cookies.set(name, value, domain='.zoho.com')
    
    def get(self, url: str, params: Optional[Dict[str, Any]] = None, 
            **kwargs) -> requests.Response:
        """
        Make GET request with retry logic
        
        Args:
            url: Request URL
            params: Query parameters
            **kwargs: Additional arguments for requests.get()
            
        Returns:
            Response object
        """
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, params=params, **kwargs)
                
                # Log response details
                logger.debug(f"GET {url}")
                logger.debug(f"Status: {response.status_code}")
                logger.debug(f"Content-Type: {response.headers.get('Content-Type')}")
                
                # Check if we got HTML instead of JSON (auth issue)
                content_type = response.headers.get('Content-Type', '')
                if 'html' in content_type.lower() and 'json' not in content_type.lower():
                    logger.warning(f"Got HTML response (expected JSON) - possible auth issue")
                    
                    # Check if it's a login page
                    if 'login' in response.text.lower() or 'signin' in response.text.lower():
                        logger.error("Got login page - credentials expired/invalid")
                        raise Exception("Authentication failed - credentials expired")
                
                if response.status_code == 200:
                    return response
                elif response.status_code == 429:
                    # Rate limited
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Rate limited (429). Waiting {wait_time}s before retry {attempt + 1}/{self.max_retries}")
                    time.sleep(wait_time)
                elif response.status_code >= 500:
                    # Server error
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Server error ({response.status_code}). Waiting {wait_time}s before retry {attempt + 1}/{self.max_retries}")
                    time.sleep(wait_time)
                else:
                    # Other error - don't retry
                    logger.error(f"Request failed with status {response.status_code}")
                    return response
                    
            except requests.exceptions.RequestException as e:
                wait_time = self.retry_delay * (2 ** attempt)
                logger.warning(f"Request exception: {e}. Waiting {wait_time}s before retry {attempt + 1}/{self.max_retries}")
                time.sleep(wait_time)
        
        # All retries failed
        raise Exception(f"Failed after {self.max_retries} retries")
    
    def post(self, url: str, data: Optional[Dict[str, Any]] = None,
             json_data: Optional[Dict[str, Any]] = None,
             **kwargs) -> requests.Response:
        """
        Make POST request with retry logic
        
        Args:
            url: Request URL
            data: Form data
            json_data: JSON data
            **kwargs: Additional arguments for requests.post()
            
        Returns:
            Response object
        """
        for attempt in range(self.max_retries):
            try:
                if json_data:
                    response = self.session.post(url, json=json_data, **kwargs)
                else:
                    response = self.session.post(url, data=data, **kwargs)
                
                logger.debug(f"POST {url}")
                logger.debug(f"Status: {response.status_code}")
                
                if response.status_code == 200:
                    return response
                elif response.status_code == 429:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Rate limited. Waiting {wait_time}s before retry {attempt + 1}/{self.max_retries}")
                    time.sleep(wait_time)
                elif response.status_code >= 500:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Server error. Waiting {wait_time}s before retry {attempt + 1}/{self.max_retries}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Request failed with status {response.status_code}")
                    return response
                    
            except requests.exceptions.RequestException as e:
                wait_time = self.retry_delay * (2 ** attempt)
                logger.warning(f"Request exception: {e}. Waiting {wait_time}s before retry {attempt + 1}/{self.max_retries}")
                time.sleep(wait_time)
        
        raise Exception(f"Failed after {self.max_retries} retries")
    
    def paginated_get(self, url: str, params: Optional[Dict[str, Any]] = None,
                      page_param: str = 'page', start_page: int = 1,
                      max_pages: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Make paginated GET requests
        
        Args:
            url: Base URL
            params: Query parameters
            page_param: Name of the page parameter
            start_page: Starting page number
            max_pages: Maximum number of pages to fetch
            
        Returns:
            List of all results from all pages
        """
        all_results = []
        current_page = start_page
        params = params or {}
        
        while True:
            if max_pages and current_page >= start_page + max_pages:
                break
            
            params[page_param] = current_page
            response = self.get(url, params=params)
            
            if response.status_code != 200:
                logger.error(f"Pagination failed on page {current_page}")
                break
            
            try:
                data = response.json()
                
                # Zoho typically returns data in a 'data' field
                page_results = data.get('data', [])
                
                if not page_results:
                    break
                
                all_results.extend(page_results)
                logger.info(f"Page {current_page}: {len(page_results)} results")
                
                # Check if there are more pages
                info = data.get('info', {})
                if not info.get('more_records', False):
                    break
                
                current_page += 1
                time.sleep(self.retry_delay)  # Rate limiting
                
            except Exception as e:
                logger.error(f"Error parsing page {current_page}: {e}")
                break
        
        logger.info(f"Paginated fetch complete: {len(all_results)} total results")
        return all_results


def create_client_from_config(config: Dict[str, Any]) -> ZohoAPIClient:
    """
    Create a ZohoAPIClient from a configuration dictionary
    
    Args:
        config: Configuration dictionary with zoho_credentials and extraction settings
        
    Returns:
        Configured ZohoAPIClient instance
    """
    creds = config['zoho_credentials']
    extraction_settings = config.get('extraction', {})
    
    # Get static_token if present (CRITICAL for blueprint extraction)
    static_token = creds.get('static_token')
    if not static_token:
        logger.warning("No static_token in config - blueprint extraction may fail!")
        logger.warning("To fix: Add 'static_token: \"YOUR_TOKEN\"' to zoho_credentials in your YAML")
    
    return ZohoAPIClient(
        cookie=creds['cookie'],
        csrf_token=creds['csrf_token'],
        org_id=creds['org_id'],
        static_token=static_token,  # Pass static_token to client
        max_retries=extraction_settings.get('max_retries', 3),
        retry_delay=extraction_settings.get('retry_delay', 1.0)
    )
