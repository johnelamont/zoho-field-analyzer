"""
Zoho CRM API Client
Uses curl.exe for HTTP requests (requests library fails with Zoho's cookie format).

Credential loading from plain text files:
  config/{client_name}/cookie.txt
  config/{client_name}/csrf_token.txt
  config/{client_name}/org_id.txt
  config/{client_name}/static_token.txt (optional)
"""
import subprocess
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class CurlResponse:
    """
    Mimics requests.Response so existing extractors work unchanged.
    
    Supports:
      .status_code
      .text
      .json()
      .headers (minimal -- curl doesn't capture response headers by default)
    """
    
    def __init__(self, status_code: int, body: str):
        self.status_code = status_code
        self.text = body
        self.headers = {}
    
    def json(self):
        return json.loads(self.text)


class ZohoAPIClient:
    """
    Client for Zoho CRM API using curl.exe.
    
    Python's requests library corrupts Zoho cookies that contain
    embedded double quotes. curl.exe handles them correctly.
    """
    
    def __init__(self, cookie: str, csrf_token: str, org_id: str, 
                 static_token: Optional[str] = None,
                 all_headers: Optional[Dict[str, str]] = None,
                 max_retries: int = 3, retry_delay: float = 1.0):
        self.csrf_token = csrf_token.strip()
        self.org_id = org_id.strip()
        self.static_token = static_token.strip() if static_token else None
        
        # Keep cookie as-is -- embedded quotes are escaped in the .ps1 generator
        self.cookie = cookie.strip()
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Use all original headers if provided (from headers.json)
        # Otherwise fall back to minimal set
        if all_headers:
            self.base_headers = {k: v for k, v in all_headers.items()
                                 if k.lower() != 'cookie'}
            logger.info(f"Using {len(self.base_headers)} headers from headers.json")
        else:
            self.base_headers = {
                'x-zcsrf-token': self.csrf_token,
                'x-crm-org': self.org_id,
                'x-requested-with': 'XMLHttpRequest',
                'accept': '*/*',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            if self.static_token:
                self.base_headers['x-static-version'] = self.static_token
        
        # Backward compat: extractors like blueprints.py call client.session.get()
        self.session = _SessionCompat(self)
        
        # Validate
        if not self.csrf_token.startswith('crmcsrfparam='):
            logger.warning(f"CSRF token missing 'crmcsrfparam=' prefix")
        
        if 'JSESSIONID' not in self.cookie:
            logger.warning("Cookie missing JSESSIONID")
        
        logger.info(f"Initialized Zoho API client for org {self.org_id}")
        logger.info(f"Cookie: {len(self.cookie)} chars")
    
    def _build_curl_cmd(self, url: str, headers: Optional[Dict[str, str]] = None) -> list:
        """Build curl.exe command with all headers"""
        cmd = ['curl.exe', '-s', url]
        
        # Add cookie via -b flag
        cmd.extend(['-b', self.cookie])
        
        # Add base headers
        for name, value in self.base_headers.items():
            cmd.extend(['-H', f'{name}: {value}'])
        
        # Add extra headers
        if headers:
            for name, value in headers.items():
                cmd.extend(['-H', f'{name}: {value}'])
        
        return cmd
    
    def _exec_curl(self, cmd: list) -> tuple:
        """
        Execute curl via a temp .ps1 file.
        
        Direct subprocess calls to curl.exe on Windows mangle special
        characters in cookies (%, ;, etc). PowerShell .ps1 files don't.
        """
        import tempfile
        
        # Build PowerShell command string
        # Don't quote flags like -s, -w, -b, -H -- only quote their values
        ps_parts = []
        i = 0
        while i < len(cmd):
            token = cmd[i]
            if token == 'curl.exe':
                ps_parts.append('curl.exe')
            elif token in ('-s', '-X'):
                ps_parts.append(token)
            elif token in ('-w', '-b', '-H', '-d', '--data-urlencode'):
                # Next token is the value -- quote it with PS escaping
                i += 1
                if i < len(cmd):
                    val = cmd[i].replace('`', '``').replace('"', '`"')
                    ps_parts.append(f'{token} "{val}"')
            else:
                # URL or other value -- quote it
                val = token.replace('`', '``').replace('"', '`"')
                ps_parts.append(f'"{val}"')
            i += 1
        
        ps_cmd = ' '.join(ps_parts)
        
        # Debug: log the generated command (truncate cookie for readability)
        debug_cmd = ps_cmd
        if len(debug_cmd) > 500:
            debug_cmd = debug_cmd[:250] + ' ... ' + debug_cmd[-250:]
        logger.debug(f"PS1 command: {debug_cmd}")
        
        try:
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.ps1', delete=False, 
                encoding='utf-8', dir='.'
            ) as f:
                f.write(ps_cmd)
                ps1_path = f.name
            
            result = subprocess.run(
                ['powershell', '-ExecutionPolicy', 'Bypass', '-File', ps1_path],
                capture_output=True, text=True, timeout=30,
                encoding='utf-8'
            )
            
            output = result.stdout
            
            if not output:
                logger.error("curl returned empty output")
                if result.stderr:
                    logger.error(f"stderr: {result.stderr[:300]}")
                return 0, ''
            
            body = output.strip()
            
            # Infer status from response content
            # Zoho returns JSON with "code" field on errors
            status = 200  # assume success
            try:
                j = json.loads(body)
                code = j.get('code', '')
                if code == 'AUTHENTICATION_FAILURE':
                    status = 401
                elif code == 'INVALID_REQUEST':
                    status = 400
                elif code == 'INTERNAL_ERROR':
                    status = 500
                elif 'code' in j and j['code'] not in ('SUCCESS', '', 0):
                    status = 400
            except (json.JSONDecodeError, ValueError):
                # Not JSON -- could be HTML login page
                if '<html' in body.lower()[:200]:
                    status = 401
            
            return status, body
            
        except subprocess.TimeoutExpired:
            logger.error("curl timed out after 30s")
            return 0, ''
        except Exception as e:
            logger.error(f"curl execution failed: {e}")
            return 0, ''
        finally:
            try:
                Path(ps1_path).unlink(missing_ok=True)
            except:
                pass
    
    def get(self, url: str, params: Optional[Dict[str, Any]] = None,
            headers: Optional[Dict[str, str]] = None, **kwargs) -> CurlResponse:
        """
        Make GET request with retry logic.
        Returns CurlResponse (compatible with requests.Response).
        """
        # Build URL with query params
        if params:
            param_str = '&'.join(f'{k}={v}' for k, v in params.items())
            full_url = f'{url}{"&" if "?" in url else "?"}{param_str}'
        else:
            full_url = url
        
        for attempt in range(self.max_retries):
            cmd = self._build_curl_cmd(full_url, headers)
            
            logger.debug(f"GET {full_url}")
            status, body = self._exec_curl(cmd)
            logger.debug(f"Status: {status}")
            
            if status == 200:
                return CurlResponse(status, body)
            elif status == 429:
                wait = self.retry_delay * (2 ** attempt)
                logger.warning(f"Rate limited (429). Waiting {wait}s...")
                time.sleep(wait)
            elif status >= 500:
                wait = self.retry_delay * (2 ** attempt)
                logger.warning(f"Server error ({status}). Waiting {wait}s...")
                time.sleep(wait)
            else:
                logger.error(f"Request failed: {status}")
                return CurlResponse(status, body)
        
        raise Exception(f"Failed after {self.max_retries} retries")
    
    def post(self, url: str, data: Optional[Dict[str, Any]] = None,
             json_data: Optional[Dict[str, Any]] = None,
             headers: Optional[Dict[str, str]] = None, **kwargs) -> CurlResponse:
        """Make POST request with retry logic."""
        for attempt in range(self.max_retries):
            cmd = self._build_curl_cmd(url, headers)
            cmd.extend(['-X', 'POST'])
            
            if json_data:
                cmd.extend(['-H', 'Content-Type: application/json'])
                cmd.extend(['-d', json.dumps(json_data)])
            elif data:
                for k, v in data.items():
                    cmd.extend(['--data-urlencode', f'{k}={v}'])
            
            logger.debug(f"POST {url}")
            status, body = self._exec_curl(cmd)
            
            if status == 200:
                return CurlResponse(status, body)
            elif status == 429:
                wait = self.retry_delay * (2 ** attempt)
                logger.warning(f"Rate limited. Waiting {wait}s...")
                time.sleep(wait)
            elif status >= 500:
                wait = self.retry_delay * (2 ** attempt)
                logger.warning(f"Server error. Waiting {wait}s...")
                time.sleep(wait)
            else:
                logger.error(f"Request failed: {status}")
                return CurlResponse(status, body)
        
        raise Exception(f"Failed after {self.max_retries} retries")
    
    def test_connection(self, test_url: Optional[str] = None) -> bool:
        """Quick connection test. Defaults to CRM functions endpoint."""
        url = test_url or 'https://crm.zoho.com/crm/v2/settings/functions?type=org&start=1&limit=1'
        resp = self.get(url)
        if resp.status_code == 200:
            try:
                data = resp.json()
                # Valid JSON with no error code = success
                if data.get('code') not in ('INVALID_REQUEST', 'AUTHENTICATION_FAILURE', 'INTERNAL_ERROR'):
                    logger.info("Connection test passed")
                    return True
            except:
                logger.info("Connection test passed (status 200)")
                return True
        
        logger.error(f"Connection test failed: {resp.status_code}")
        logger.error(f"Response: {resp.text[:300]}")
        return False


class _SessionCompat:
    """
    Backward compatibility: blueprints.py calls client.session.get().
    Routes through the curl-based client.
    """
    
    def __init__(self, client: ZohoAPIClient):
        self._client = client
        # Expose cookies count for the init log message
        self.cookies = type('obj', (object,), {'__len__': lambda s: 0})()
        self.headers = client.base_headers
    
    def get(self, url: str, params: Optional[Dict[str, Any]] = None,
            **kwargs) -> CurlResponse:
        return self._client.get(url, params=params)
    
    def post(self, url: str, data: Optional[Dict[str, Any]] = None,
             json: Optional[Dict[str, Any]] = None,
             **kwargs) -> CurlResponse:
        return self._client.post(url, data=data, json_data=json)


def load_credentials(client_name: str, config_dir: Path = None) -> Dict[str, str]:
    """
    Load credentials from plain text files.
    Falls back to YAML if text files don't exist.
    """
    if config_dir is None:
        config_dir = Path('config')
    
    creds_dir = config_dir / client_name
    cookie_file = creds_dir / 'cookie.txt'
    
    if cookie_file.exists():
        logger.info(f"Loading credentials from: {creds_dir}/")
        
        creds = {}
        for key, filename, required in [
            ('cookie', 'cookie.txt', True),
            ('csrf_token', 'csrf_token.txt', True),
            ('org_id', 'org_id.txt', True),
            ('static_token', 'static_token.txt', False),
        ]:
            filepath = creds_dir / filename
            if filepath.exists():
                value = filepath.read_text(encoding='utf-8').strip()
                # Strip accidental wrapping quotes
                if len(value) > 2 and \
                   ((value[0] == "'" and value[-1] == "'") or
                    (value[0] == '"' and value[-1] == '"')):
                    value = value[1:-1]
                creds[key] = value
                logger.info(f"  {filename}: {len(value)} chars")
            elif required:
                raise FileNotFoundError(f"Missing: {filepath}")
        
        # Load all headers if available (saved by save_curl.py)
        headers_file = creds_dir / 'headers.json'
        if headers_file.exists():
            creds['all_headers'] = json.loads(
                headers_file.read_text(encoding='utf-8')
            )
            logger.info(f"  headers.json: {len(creds['all_headers'])} headers")
        
        return creds
    
    # Fall back to YAML
    yaml_file = config_dir / f'{client_name}.yaml'
    if yaml_file.exists():
        logger.info(f"Loading credentials from YAML: {yaml_file}")
        logger.warning("YAML is deprecated for credentials -- use text files")
        
        import yaml
        with open(yaml_file) as f:
            config = yaml.safe_load(f)
        
        zoho_creds = config.get('zoho_credentials', {})
        return {
            'cookie': zoho_creds.get('cookie', ''),
            'csrf_token': zoho_creds.get('csrf_token', ''),
            'org_id': str(zoho_creds.get('org_id', '')),
            'static_token': zoho_creds.get('static_token'),
        }
    
    raise FileNotFoundError(
        f"No credentials for '{client_name}'.\n"
        f"Run: python save_curl.py {client_name}\n"
        f"Or create: {creds_dir}/cookie.txt"
    )


def create_client_from_credentials(client_name: str, 
                                    config_dir: Path = None,
                                    max_retries: int = 3,
                                    retry_delay: float = 1.0) -> ZohoAPIClient:
    """Create a ZohoAPIClient by loading credentials for a client."""
    creds = load_credentials(client_name, config_dir)
    
    return ZohoAPIClient(
        cookie=creds['cookie'],
        csrf_token=creds['csrf_token'],
        org_id=creds['org_id'],
        static_token=creds.get('static_token'),
        all_headers=creds.get('all_headers'),
        max_retries=max_retries,
        retry_delay=retry_delay,
    )
