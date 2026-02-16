import yaml
import requests

with open('config/mrtarget.yaml', 'r') as f:
    config = yaml.safe_load(f)

creds = config['zoho_credentials']

session = requests.Session()

# Parse cookies
for cookie in creds['cookie'].split('; '):
    if '=' in cookie:
        name, value = cookie.split('=', 1)
        session.cookies.set(name, value, domain='.zoho.com')

# Set headers INCLUDING X-Static-Token
session.headers.update({
    'x-zcsrf-token': creds['csrf_token'],
    'x-crm-org': creds['org_id'],
    'X-Static-Token': creds.get('static_token', '12593739'),  # ADD THIS
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'X-Requested-With': 'XMLHttpRequest, XMLHttpRequest'
})

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

if 'json' in response.headers.get('Content-Type', ''):
    print("SUCCESS! Got JSON")
    data = response.json()
    print(f"Blueprints: {len(data.get('Processes', []))}")
else:
    print("Still HTML:", response.text[:200])