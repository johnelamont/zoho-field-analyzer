"""
Zoho Recruit Functions Extractor
Extracts all Deluge functions from Zoho Recruit

Same API pattern as CRM functions but different base URL and params:
  List:   GET /recruit/v2/settings/functions?type=org&start=1&limit=50
  Detail: GET /recruit/v2/settings/functions/{id}?language=deluge&category={cat}&source=recruit

Credentials: Recruit uses recruit.zoho.com cookies (separate from CRM).
  Capture cURL from Recruit DevTools, save as a separate client:
    python save_curl.py blades-recruit
"""
from pathlib import Path
from typing import Dict, Any, List
import logging
import time

from ..base import BaseExtractor
from ...api.zoho_client import ZohoAPIClient

logger = logging.getLogger(__name__)

BASE_URL = 'https://recruit.zoho.com/recruit/v2'


class RecruitFunctionsExtractor(BaseExtractor):
    """Extract Deluge functions from Zoho Recruit"""

    def __init__(self, client: ZohoAPIClient, output_dir: Path, client_name: str):
        super().__init__(client, output_dir, client_name)
        self.functions_dir = output_dir / 'recruit_functions'
        self.functions_dir.mkdir(exist_ok=True)

    def get_extractor_name(self) -> str:
        return "recruit_functions"

    def get_all_functions(self) -> List[Dict[str, Any]]:
        """
        Get list of all Recruit functions using offset pagination.

        Endpoint: GET /recruit/v2/settings/functions?type=org&start=1&limit=50
        Returns: { "functions": [...] }
        """
        logger.info("Fetching all Recruit functions...")

        all_functions = []
        start = 1
        limit = 50
        page = 1

        while True:
            url = f"{BASE_URL}/settings/functions"
            params = {
                'type': 'org',
                'start': start,
                'limit': limit
            }

            logger.info(f"  Page {page} (functions {start}-{start+limit-1})...")

            try:
                response = self.client.session.get(url, params=params)

                if response.status_code != 200:
                    logger.error(f"  Error: {response.status_code}")
                    if response.text and '<html' in response.text[:200].lower():
                        logger.error("  Got HTML response -- credentials likely expired")
                        logger.error("  Recruit needs its own credentials (separate from CRM)")
                        logger.error(f"  Response preview: {response.text[:300]}")
                    else:
                        logger.error(f"  Response: {response.text[:500]}")
                    break

                data = response.json()
                functions = data.get('functions', [])

                if not functions:
                    logger.info("  No more functions -- done")
                    break

                all_functions.extend(functions)
                logger.info(f"  Found {len(functions)} (total: {len(all_functions)})")

                if len(functions) < limit:
                    break

                start += limit
                page += 1
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"  Exception fetching functions page {page}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                break

        logger.info(f"Found {len(all_functions)} total Recruit functions")
        return all_functions

    def get_function_source(self, function_id: str,
                            category: str = 'automation') -> Dict[str, Any]:
        """
        Get source code for a specific Recruit function.

        Endpoint: GET /recruit/v2/settings/functions/{id}
                      ?language=deluge&category={cat}&source=recruit

        The category param must match the function's category from the list
        response (usually 'automation').
        """
        url = f"{BASE_URL}/settings/functions/{function_id}"
        params = {
            'language': 'deluge',
            'category': category,
            'source': 'recruit'
        }

        try:
            response = self.client.session.get(url, params=params)

            if response.status_code != 200:
                logger.warning(f"  Error getting source: {response.status_code}")
                return {}

            return response.json()

        except Exception as e:
            logger.error(f"  Exception getting function {function_id}: {e}")
            return {}

    def extract_script_from_response(self, response: Dict[str, Any]) -> str:
        """Extract script content from API response"""
        if response and 'functions' in response and len(response['functions']) > 0:
            func_detail = response['functions'][0]
            return func_detail.get('script', '')
        return ''

    def extract_connections_from_response(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract connection details from API response (Recruit-specific)"""
        if response and 'functions' in response and len(response['functions']) > 0:
            func_detail = response['functions'][0]
            return func_detail.get('connections', [])
        return []

    def extract(self) -> Dict[str, Any]:
        """Extract all Recruit Deluge functions and save to files"""

        functions = self.get_all_functions()
        self.stats['total'] = len(functions)

        if not functions:
            logger.warning("No Recruit functions found!")
            return {
                'status': 'no_data',
                'stats': self.stats
            }

        failed_items = []
        all_functions_data = []

        for i, func in enumerate(functions, 1):
            func_id = func['id']
            func_name = func.get('display_name', f'function_{func_id}')
            func_category = func.get('category', 'automation')

            logger.info(f"[{i}/{len(functions)}] Extracting: {func_name}")

            try:
                source_data = self.get_function_source(func_id, func_category)
                script = self.extract_script_from_response(source_data)

                if script:
                    # Create metadata header
                    header = self.create_metadata_header(
                        func,
                        id_field='id',
                        name_field='display_name'
                    )

                    full_content = header + script

                    # Save script to individual file
                    filename = f"{self.sanitize_filename(func_name)}_{func_id}.txt"
                    self.save_text(full_content, f"recruit_functions/{filename}")

                    # Extract connections for the index
                    connections = self.extract_connections_from_response(source_data)

                    # Extract associated_place from detail (richer than list)
                    detail_func = source_data.get('functions', [{}])[0]
                    associated_place = detail_func.get('associated_place', [])
                    tasks = detail_func.get('tasks', {})

                    all_functions_data.append({
                        'metadata': func,
                        'script': script,
                        'filename': filename,
                        'connections': connections,
                        'associated_place': associated_place,
                        'tasks': tasks
                    })

                    self.stats['successful'] += 1
                    logger.info(f"  [OK] Saved")

                else:
                    reason = "No script in response"
                    logger.warning(f"  [FAIL] {reason}")
                    failed_items.append({
                        'name': func_name,
                        'id': func_id,
                        'reason': reason
                    })
                    self.stats['failed'] += 1

            except Exception as e:
                reason = str(e)
                logger.error(f"  [FAIL] {reason}")
                failed_items.append({
                    'name': func_name,
                    'id': func_id,
                    'reason': reason
                })
                self.stats['failed'] += 1

            time.sleep(0.5)

        # Save master index
        self.save_json(all_functions_data, 'recruit_functions_index.json')

        # Save failed log if any
        if failed_items:
            self.save_failed_log(failed_items)

        return {
            'status': 'success',
            'stats': self.stats,
            'functions': all_functions_data,
            'failed': failed_items
        }


def main():
    """Standalone execution for testing"""
    import sys
    print("This extractor should be run through the main extraction script")
    print("Usage: python -m src.extractors.main --client CLIENT_NAME --extract recruit_functions")
    sys.exit(1)


if __name__ == '__main__':
    main()
