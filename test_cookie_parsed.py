# test_cookie_parsed.py
import yaml
import requests

# Load config
with open('config/mrtarget.yaml', 'r') as f:
    config = yaml.safe_load(f)

creds = config['zoho_credentials']

# Create session
session = requests.Session()

# Parse cookie string into individual cookies
cookie_string = creds['cookie']
for cookie in cookie_string.split('; '):
    if '=' in cookie:
        name, value = cookie.split('=', 1)
        session.cookies.set(name, value, domain='.zoho.com')

# Set other headers (NOT Cookie - let session handle it)
session.headers.update({
    'x-zcsrf-token': creds['csrf_token'],
    'x-crm-org': creds['org_id'],
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'x-requested-with': 'XMLHttpRequest, XMLHttpRequest'
})

print(f"Parsed {len(session.cookies)} cookies")
print()

# Test request
url = f"https://crm.zoho.com/crm/org{creds['org_id']}/ProcessFlow.do"
params = {
    'pageTitle': 'crm.label.process.automation',
    'allowMultiClick': 'true',
    'action': 'showAllProcesses',
    'isFromBack': 'true',
    'module': 'All'
}

response = session.get(url, params=params)

print("Status:", response.status_code)
print("Content-Type:", response.headers.get('Content-Type'))
print()

if 'application/json' in response.headers.get('Content-Type', ''):
    print("SUCCESS! Got JSON response")
    data = response.json()
    print(f"Found {len(data.get('Processes', []))} blueprints")
else:
    print("FAILED: Still getting HTML")
    print("Response starts with:", response.text[:200])