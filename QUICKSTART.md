# Quick Start Guide

Get started with Zoho Field Analyzer in 5 minutes.

## Step 1: Installation

```bash
# Clone the repository
cd zoho-field-analyzer

# Install dependencies
pip install -r requirements.txt

# Or install in development mode
pip install -e .
```

## Step 2: Get Your Zoho Credentials

You need to extract credentials from your browser:

1. Open **Chrome** and log into your **Zoho CRM**
2. Press **F12** to open DevTools
3. Go to the **Network** tab
4. Click on any item in Zoho CRM (e.g., a Lead or Contact)
5. Find a request with **200 status** in the Network tab
6. Click on the request and go to **Headers**
7. Copy these three values:
   - **Cookie** - The entire cookie header
   - **x-zcsrf-token** - Include the `crmcsrfparam=` prefix
   - **x-crm-org** - Your organization ID

## Step 3: Create Client Configuration

```bash
# Copy the template
cp config/client_template.yaml config/my_client.yaml

# Edit the file and paste your credentials
nano config/my_client.yaml
```

Replace these values:
```yaml
zoho_credentials:
  cookie: "YOUR_COOKIE_HEADER_HERE"
  csrf_token: "crmcsrfparam=YOUR_CSRF_TOKEN_HERE"
  org_id: "YOUR_ORG_ID_HERE"
```

## Step 4: Extract Data

Extract all data types:
```bash
python -m src.extractors.main --client my_client --extract-all
```

Or extract specific types:
```bash
# Just functions and workflows
python -m src.extractors.main --client my_client --extract functions workflows

# Just modules
python -m src.extractors.main --client my_client --extract modules
```

Your data will be saved to: `data/my_client/raw/`

## Step 5: Analyze Data

Build the field mapping:
```bash
python -m src.analyzers.field_tracker --client my_client
```

Build the Rosetta Stone:
```bash
python -m src.analyzers.rosetta_builder --client my_client
```

Your analysis will be saved to: `data/my_client/analyzed/`

## Output Files

After extraction and analysis, you'll have:

```
data/my_client/
├── raw/
│   ├── functions/
│   │   ├── MyFunction_123456.txt
│   │   └── functions_index.json
│   ├── workflows/
│   │   ├── MyWorkflow_789.json
│   │   └── workflows_index.json
│   └── modules/
│       ├── Leads.json
│       └── modules_index.json
└── analyzed/
    ├── field_map.json
    └── rosetta_stone.json
```

## What's in the Rosetta Stone?

The Rosetta Stone (`rosetta_stone.json`) contains:

- **Every field** in your CRM
- **All functions** that read or modify each field
- **All workflows** that update each field
- **Module relationships** and field dependencies

Example structure:
```json
{
  "fields": {
    "Email": {
      "api_name": "Email",
      "label": "Email",
      "data_type": "email",
      "module": "Leads",
      "transformations": {
        "functions": [
          {
            "type": "function",
            "source": "ValidateEmail_123",
            "file": "ValidateEmail_123.txt"
          }
        ],
        "workflows": [...],
        "total_count": 5
      }
    }
  }
}
```

## Searching Your Data

Use your favorite text search tool:

```bash
# Find all places where a field is used
grep -r "Email" data/my_client/raw/

# Search with ripgrep (faster)
rg "Email" data/my_client/raw/

# Search in VS Code
# Open the data/my_client folder and use Ctrl+Shift+F
```

## Troubleshooting

### "Configuration file not found"
- Make sure you created `config/my_client.yaml`
- The client name must match the config filename (without .yaml)

### "Missing or invalid credentials"
- Double-check you copied all three credential values
- Make sure there are no extra spaces or quotes
- Credentials expire - you may need to refresh them

### "No data returned"
- Your credentials may have expired
- Check your internet connection
- Try refreshing your Zoho credentials

### "Rate limited"
- Zoho has rate limits
- The script will automatically retry with delays
- Consider extracting data types separately if you hit limits

## Next Steps

1. **Explore the data** - Look through the extracted files
2. **Search for fields** - Find where specific fields are modified
3. **Build reports** - Create custom analysis scripts
4. **Share insights** - Export findings for your team

## Need Help?

- Check the main [README.md](README.md) for detailed documentation
- Review the example configuration in `config/client_template.yaml`
- Look at the code comments in the extractor files

Happy analyzing! 🔍
