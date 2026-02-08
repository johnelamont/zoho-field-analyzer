import requests
import json
import time
from pathlib import Path

'''
To refresh Zoho API credentials:
1. Open Chrome DevTools (F12) â†’ Network tab
2. Click any Zoho CRM function
3. Find successful request (200 status)
4. Copy Cookie header value
5. Copy x-zcsrf-token (include crmcsrfparam= prefix)
6. Copy x-crm-org value
'''
# Copy these from your DevTools
HEADERS = {
    'Cookie': 'ZW_CSRF_TOKEN=86e7115fc22d387b9307c7bee94171d9636f48acdfbd0ebd471d88105299374a837e0e10b16153fa00df0a41f816898220f9a0379f327f2d62ba87541fe50615; zfcsr=69e5546f0413212a130ca50be2f186043afab4f7f13f91894333bd8f4cad107997b0890fb0d2f7c9d7988d6dbb287c987e3ca7a94db29eeb379ec45e7fa6fc19; zalb_6e4b8efee4=041823df17142a603b71c7c7ccf2999f; CROSSCDNID=0c2364d43096b4fe741a7f1c5eb597dbad6813b3660d31c62d02283e3d08171289def1c4c1afa009553f3ecb578e90d8; CROSSCDNCOUNTRY=US; JSESSIONID=8DB1112D43319DB143F3BF4D8FE14C04; zalb_8b7213828d=fc91ce56b06549e057e33feb1291e75f; zalb_3309580ed5=28deba1711e0f9c8ea8919a4fbd8ae65; __Secure-iamsdt=0.EnQSMAGolMYxs1dWzTXG4jFdYCtPfyd-iw713qt3uGwPoxYs7g-FNN6EbxY3WPF8T9JQ4RpAyrg9v37Gx6cFngT_bqEnGtQ0PSzwCDMGNgwhT1bd97Eb2pJTPEG5DL0wj0VbOhi3rdIN8Rlm3VxHauVOO_a4RQ; _iamadt=01a894c631b35756cd35c6e2315d602b4f7f277e8b0ef5deab77b86c0fa3162cee0f8534de846f163758f17c4fd250e1; _iambdt=cab83dbf7ec6c7a7059e04ff6ea1271ad4343d2cf0083306360c214f56ddf7b11bda92533c41b90cbd308f455b3a18b7add20df11966dd5c476ae54e3bf6b845; wms-tkp-token=892084811-3a5ca966-72929837a173be881d76dfa4fdafac25; crmcsr=0bc8499984cde0bb1b75be673ef9a091d13706a54b63242d88245a47855dcfff50d80b5c5fe8e2be21f47dc21eb48fd0b9d1b8bd4f3e3ca8c8cfe0dc52b89369; _zcsr_tmp=0bc8499984cde0bb1b75be673ef9a091d13706a54b63242d88245a47855dcfff50d80b5c5fe8e2be21f47dc21eb48fd0b9d1b8bd4f3e3ca8c8cfe0dc52b89369; CSRF_TOKEN=0bc8499984cde0bb1b75be673ef9a091d13706a54b63242d88245a47855dcfff50d80b5c5fe8e2be21f47dc21eb48fd0b9d1b8bd4f3e3ca8c8cfe0dc52b89369; CT_CSRF_TOKEN=0bc8499984cde0bb1b75be673ef9a091d13706a54b63242d88245a47855dcfff50d80b5c5fe8e2be21f47dc21eb48fd0b9d1b8bd4f3e3ca8c8cfe0dc52b89369; drecn=0bc8499984cde0bb1b75be673ef9a091d13706a54b63242d88245a47855dcfff50d80b5c5fe8e2be21f47dc21eb48fd0b9d1b8bd4f3e3ca8c8cfe0dc52b89369; showEditorLeftPane=undefined; zalb_zid=666154101; _zwaf_ua=Ulaa',
    'x-zcsrf-token': 'crmcsrfparam=0bc8499984cde0bb1b75be673ef9a091d13706a54b63242d88245a47855dcfff50d80b5c5fe8e2be21f47dc21eb48fd0b9d1b8bd4f3e3ca8c8cfe0dc52b89369',
    'x-crm-org': '666154101',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
    'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'x-requested-with': 'XMLHttpRequest, XMLHttpRequest'
}

BASE_URL = 'https://crm.zoho.com/crm/v2'

def get_all_functions():
    """Get list of all functions with offset pagination"""
    all_functions = []
    start = 1
    limit = 50
    page = 1
    
    while True:
        url = f"{BASE_URL}/settings/functions?type=org&start={start}&limit={limit}"
        print(f"Fetching page {page} (functions {start}-{start+limit-1})...")
        
        response = requests.get(url, headers=HEADERS)
        
        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            print(response.text)
            break
            
        data = response.json()
        functions = data.get('functions', [])
        
        if not functions or len(functions) == 0:
            print("  No more functions found - done!")
            break
            
        all_functions.extend(functions)
        print(f"  Found {len(functions)} functions (total so far: {len(all_functions)})")
        
        # If we got fewer than limit, we're probably done
        if len(functions) < limit:
            print("  Received fewer than limit - assuming last page")
            break
        
        # Move to next page
        start += limit
        page += 1
        time.sleep(0.5)  # Be nice to the API
    
    return all_functions

def get_function_source(function_id):
    """Get source code for a specific function"""
    url = f"{BASE_URL}/settings/functions/{function_id}?category=standalone&source=crm&language=deluge"
    
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code != 200:
        print(f"  Error getting source: {response.status_code}")
        return None
        
    return response.json()

def sanitize_filename(name):
    """Remove invalid filename characters"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')
    return name

def save_all_scripts():
    """Download and save all scripts"""
    print("Starting download...\n")
    
    # Get all functions
    functions = get_all_functions()
    print(f"\nTotal functions found: {len(functions)}\n")
    
    # Create output directory
    output_dir = Path('./deluge-scripts')
    output_dir.mkdir(exist_ok=True)
    
    # Download each function's source
    success_count = 0
    failed = []
    
    for i, func in enumerate(functions, 1):
        func_id = func['id']
        func_name = func['display_name']
        
        print(f"[{i}/{len(functions)}] {func_name}... ", end='')
        
        try:
            source_data = get_function_source(func_id)
            
            # Handle nested structure: {'functions': [{'script': '...'}]}
            if source_data and 'functions' in source_data and len(source_data['functions']) > 0:
                func_detail = source_data['functions'][0]
                
                if 'script' in func_detail:
                    # Create header with metadata
                    header = f"""// Function: {func_name}
// ID: {func_id}
// Created: {func.get('created_time', 'Unknown')}
// Modified: {func.get('modified_time', 'Unknown')}
// Created By: {func.get('created_by', {}).get('name', 'Unknown')}
// ============================================

"""
                    script_content = header + func_detail['script']
                    
                    # Save to file
                    filename = f"{sanitize_filename(func_name)}_{func_id}.txt"
                    filepath = output_dir / filename
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(script_content)
                    
                    print("âœ“")
                    success_count += 1
                else:
                    reason = "no script in response"
                    print(f"âœ— ({reason})")
                    failed.append({'name': func_name, 'id': func_id, 'reason': reason})
            else:
                reason = "unexpected response structure"
                print(f"âœ— ({reason})")
                failed.append({'name': func_name, 'id': func_id, 'reason': reason})
                
        except Exception as e:
            reason = str(e)
            print(f"âœ— ({reason})")
            failed.append({'name': func_name, 'id': func_id, 'reason': reason})
        
        # Be nice to their servers
        time.sleep(0.5)
    
    # Summary
    print(f"\n{'='*50}")
    print(f"Successfully saved: {success_count}/{len(functions)}")
    print(f"Output directory: {output_dir.absolute()}")
    
    if failed:
        print(f"\nFailed to download {len(failed)} functions:")
        
        # Save to file
        failed_log = output_dir / 'FAILED_DOWNLOADS.txt'
        with open(failed_log, 'w', encoding='utf-8') as f:
            f.write(f"Failed Downloads: {len(failed)}/{len(functions)}\n")
            f.write("="*50 + "\n\n")
            for item in failed:
                print(f"  - {item['name']} ({item['reason']})")
                f.write(f"Name: {item['name']}\n")
                f.write(f"ID: {item['id']}\n")
                f.write(f"Reason: {item['reason']}\n\n")
        
        print(f"\nFailed downloads logged to: {failed_log}")
    
    print(f"\nYou can now search with VS Code or:")
    print(f"  rg 'fieldname' {output_dir}")

def check_for_duplicate_names():
    """Check if any functions would create duplicate filenames"""
    functions = get_all_functions()
    
    filenames = {}
    duplicates = []
    
    for func in functions:
        func_name = func['display_name']
        filename = sanitize_filename(func_name) + '.txt'
        
        if filename in filenames:
            duplicates.append({
                'filename': filename,
                'original1': filenames[filename],
                'original2': func_name
            })
        else:
            filenames[filename] = func_name
    
    if duplicates:
        print(f"\nFound {len(duplicates)} filename collisions:")
        for dup in duplicates:
            print(f"\nFile: {dup['filename']}")
            print(f"  1. {dup['original1']}")
            print(f"  2. {dup['original2']}")
    else:
        print("\nNo duplicate filenames found!")
    
    return duplicates

if __name__ == '__main__':
    check_for_duplicate_names()  # Run this first
    # save_all_scripts()  # Comment out for now