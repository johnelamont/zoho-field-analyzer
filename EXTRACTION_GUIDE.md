# Zoho Field Analyzer - Extraction Guide

## Quick Start

```powershell
# 1. Get credentials from Chrome DevTools
#    - Open Zoho CRM, press F12, go to Network tab
#    - Click any function/workflow in the CRM
#    - Right-click the XHR request > Copy as cURL (bash)

# 2. Paste into curl.txt
notepad curl.txt    # Ctrl+A, Ctrl+V, Ctrl+S, close

# 3. Save & test credentials
python save_curl.py blades

# 4. Extract
python -m src.extractors.main --client blades --extract functions
python -m src.extractors.main --client blades --extract workflows
python -m src.extractors.main --client blades --extract blueprints
python -m src.extractors.main --client blades --extract modules
python -m src.extractors.main --client blades --extract-all
```

## How It Works

### Why curl.exe?

Python's `requests` library corrupts Zoho cookies that contain embedded
double quotes (e.g. `ZohoMarkRef="https://..."`). This causes 400 errors
on every request. The solution: all HTTP requests go through `curl.exe`
via temporary PowerShell scripts, which handle quoting correctly.

### Why all headers?

Zoho requires more than just Cookie/CSRF/Org headers. The full set of
headers from Chrome DevTools includes additional headers that Zoho
validates. `save_curl.py` captures ALL headers from your cURL command
and saves them as `headers.json` for the client to replay.

## Zoho Recruit

Recruit uses a separate domain (recruit.zoho.com) with its own session cookies.
CRM credentials will NOT work for Recruit and vice versa. Treat them as separate
clients from a credential perspective.

### Setup

```powershell
# 1. Open Zoho RECRUIT in Chrome (not CRM), press F12 > Network
# 2. Click a function or any request in Recruit
# 3. Right-click the XHR request > Copy as cURL (bash)
# 4. Paste into curl.txt

python save_curl.py blades-recruit
```

### Extract

```powershell
python -m src.extractors.main --client blades-recruit --extract recruit_functions
```

Output goes to `data/blades-recruit/raw/recruit_functions/`.

### Why a Separate Client Name?

Zoho CRM, Zoho Recruit, and Zoho Flow each have completely separate authentication
sessions. The cookie from one domain does not work on another. By using different
client names (e.g. `blades`, `blades-recruit`, `blades-flow`), credentials and
output data stay cleanly separated.

## Zoho Flow

Flow also uses a separate domain (flow.zoho.com) with its own session cookies.

### Setup

```powershell
# 1. Open Zoho FLOW in Chrome, press F12 > Network
# 2. Click any custom function in Flow
# 3. Right-click the XHR request > Copy as cURL (bash)
# 4. Paste into curl.txt

python save_curl.py blades-flow
```

### Extract

```powershell
python -m src.extractors.main --client blades-flow --extract flow_functions
```

Output goes to `data/blades-flow/raw/flow_functions/`.

## File Layout

```
project/
  save_curl.py                    # Credential capture & test
  curl.txt                        # Paste your cURL here (not committed)
  config/
    blades/
      cookie.txt                  # Raw cookie value
      csrf_token.txt              # crmcsrfparam=...
      org_id.txt                  # e.g. 666154101
      static_token.txt            # (optional) for blueprints
      headers.json                # All HTTP headers from cURL
    blades-recruit/               # Recruit credentials (separate!)
      cookie.txt
      csrf_token.txt
      org_id.txt
      headers.json
    blades-flow/                  # Flow credentials (separate!)
      cookie.txt
      headers.json
    blades.yaml                   # Rate limits, output settings (no creds)
  src/
    api/
      zoho_client.py              # curl.exe-based HTTP client
    extractors/
      main.py                     # CLI entry point
      functions.py                # CRM Deluge functions extractor
      blueprints.py               # Blueprint extractor
      workflows.py                # Workflow extractor
      modules.py                  # Module/field extractor
      base.py                     # Base extractor class
      recruit/                    # Zoho Recruit extractors
        __init__.py
        functions.py              # Recruit functions extractor
      flow/                       # Zoho Flow extractors
        __init__.py
        functions.py              # Flow functions extractor
  data/
    blades/
      raw/
        functions/                # Individual .txt files per function
        functions_index.json      # Master index
        blueprints/               # Blueprint data
        workflows/                # Workflow data
    blades-recruit/
      raw/
        recruit_functions/        # Individual .txt files per function
        recruit_functions_index.json
    blades-flow/
      raw/
        flow_functions/           # Individual .txt files per function
        flow_functions_index.json
```

## Commands Reference

### Credential Management

```powershell
# Save credentials (parse cURL, test, save)
python save_curl.py <client_name>
python save_curl.py blades              # reads curl.txt
python save_curl.py blades mycurl.txt   # reads custom file

# Output: config/<client_name>/cookie.txt, csrf_token.txt, org_id.txt, headers.json
```

### Extraction

```powershell
# Extract specific data types
python -m src.extractors.main --client <name> --extract functions
python -m src.extractors.main --client <name> --extract workflows
python -m src.extractors.main --client <name> --extract blueprints
python -m src.extractors.main --client <name> --extract modules

# Extract everything
python -m src.extractors.main --client <name> --extract-all

# Blueprint options
python -m src.extractors.main --client <name> --extract blueprints --with-transitions

# Workflow options
python -m src.extractors.main --client <name> --extract workflows --with-field-updates

# List configured clients
python -m src.extractors.main --list-clients
```

### Output

Extracted data goes to `data/<client>/raw/`. Each extractor creates:
- Individual files per item (functions as .txt, others as .json)
- A master index file (e.g. `functions_index.json`)
- A failed downloads log if any items failed

## Troubleshooting

### "Credential test failed"

Credentials have expired. Refresh:
1. Open Zoho CRM in Chrome, click something to generate network traffic
2. DevTools > Network > right-click request > Copy as cURL (bash)
3. Paste into `curl.txt`
4. `python save_curl.py <client>`

### "All tests failed. Credentials expired."

`save_curl.py` tests credentials immediately after parsing. If this fails,
the session expired between copying and running. Try again -- be fast.
Typical Zoho sessions last 15-30 minutes, so this usually isn't a race.

### "curl returned empty output"

PowerShell execution policy may be blocking .ps1 files. The client uses
`-ExecutionPolicy Bypass` but your system may override this. Check:
```powershell
Get-ExecutionPolicy -List
```

### Encoding errors in logs

All log messages use ASCII only. If you see encoding errors, a file
may have been edited with unicode characters. Check for em-dashes,
smart quotes, or emoji in Python source files.

### Adding a New Client

```powershell
# 1. Log into the client's Zoho CRM in Chrome
# 2. Copy as cURL from any request
# 3. Paste into curl.txt
python save_curl.py newclient
# 4. Extract
python -m src.extractors.main --client newclient --extract-all
```

No YAML file is needed unless you want custom rate limits or output settings.

## Architecture Notes

### ZohoAPIClient (zoho_client.py)

- All HTTP goes through `curl.exe` via temp `.ps1` files
- `CurlResponse` mimics `requests.Response` for backward compatibility
- `_SessionCompat` shim lets extractors call `client.session.get()`
- HTTP status is inferred from Zoho's JSON error codes (not HTTP status)
- Retries on 429 (rate limit) and 5xx (server error) with exponential backoff

### Credential Loading Priority

1. Plain text files: `config/<client>/cookie.txt` etc.
2. `headers.json`: all HTTP headers (saved by `save_curl.py`)
3. YAML fallback: `config/<client>.yaml` (deprecated, cookie quoting issues)

### Why Not requests?

Zoho cookies contain values like:
```
ZohoMarkRef="https://catalyst.zoho.com/"
```

The embedded double quotes cause failures at multiple levels:
- Python `requests` corrupts the Cookie header
- Windows `subprocess` mangles quotes when passing to `curl.exe`
- YAML parsers mangle the quotes during load/save
- PowerShell `.ps1` files with proper backtick escaping work correctly

The solution writes a temp `.ps1` file for each request, with proper
PowerShell escaping (`"` becomes `` `" ``), then executes it.
