"""
Zoho Flow Functions Extractor
Extracts all Deluge functions from Zoho Flow

Different API pattern from CRM/Recruit:
  List:   GET https://flow.zoho.com/rest/flow-deluge-functions/
          Returns: { "user_functions": [...] }  (no pagination, all at once)
  Detail: GET https://flow.zoho.com/rest/flow-deluge-functions/{functionID}
          Returns: { "custom_function": { "script": "...", ... } }

Credentials: Flow uses flow.zoho.com cookies (separate from CRM and Recruit).
  Capture cURL from Flow DevTools, save as a separate client:
    python save_curl.py blades-flow
"""
from pathlib import Path
from typing import Dict, Any, List
import logging
import time

from ..base import BaseExtractor
from ...api.zoho_client import ZohoAPIClient

logger = logging.getLogger(__name__)

BASE_URL = 'https://flow.zoho.com/rest/flow-deluge-functions'


class FlowFunctionsExtractor(BaseExtractor):
    """Extract Deluge functions from Zoho Flow"""

    def __init__(self, client: ZohoAPIClient, output_dir: Path, client_name: str):
        super().__init__(client, output_dir, client_name)
        self.functions_dir = output_dir / 'flow_functions'
        self.functions_dir.mkdir(exist_ok=True)

    def get_extractor_name(self) -> str:
        return "flow_functions"

    def get_all_functions(self) -> List[Dict[str, Any]]:
        """
        Get list of all Flow functions.

        Endpoint: GET /rest/flow-deluge-functions/
        Returns all functions at once (no pagination).
        Response: { "user_functions": [...] }
        """
        logger.info("Fetching all Flow functions...")

        url = f"{BASE_URL}/"

        try:
            response = self.client.session.get(url)

            if response.status_code != 200:
                logger.error(f"  Error: {response.status_code}")
                if response.text and '<html' in response.text[:200].lower():
                    logger.error("  Got HTML response -- credentials likely expired")
                    logger.error("  Flow needs its own credentials (separate from CRM/Recruit)")
                    logger.error(f"  Response preview: {response.text[:300]}")
                else:
                    logger.error(f"  Response: {response.text[:500]}")
                return []

            data = response.json()
            functions = data.get('user_functions', [])

            logger.info(f"Found {len(functions)} Flow functions")
            return functions

        except Exception as e:
            logger.error(f"  Exception fetching Flow functions: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    def get_function_source(self, function_id: str) -> Dict[str, Any]:
        """
        Get source code for a specific Flow function.

        Endpoint: GET /rest/flow-deluge-functions/{functionID}
        Returns: { "custom_function": { "script": "...", ... }, "status": "success" }
        """
        url = f"{BASE_URL}/{function_id}"

        try:
            response = self.client.session.get(url)

            if response.status_code != 200:
                logger.warning(f"  Error getting source: {response.status_code}")
                return {}

            return response.json()

        except Exception as e:
            logger.error(f"  Exception getting function {function_id}: {e}")
            return {}

    def extract_script_from_response(self, response: Dict[str, Any]) -> str:
        """Extract script content from Flow API response"""
        custom_func = response.get('custom_function', {})
        return custom_func.get('script', '')

    def build_metadata_header(self, func_list: Dict[str, Any],
                              func_detail: Dict[str, Any]) -> str:
        """
        Build a metadata header for the script file.

        Flow's list and detail responses have different fields, so we
        merge them for a complete header.
        """
        func_name = func_list.get('functionName', 'Unknown')
        func_id = func_list.get('functionID', 'Unknown')
        created_by = func_list.get('createdBy', 'Unknown')
        return_type = func_list.get('returnType', 'Unknown')
        link_name = func_list.get('functionLinkName', '')
        namespace = func_detail.get('nameSpace', '')

        # Build params string
        params = func_list.get('params', [])
        params_str = ', '.join(
            f"{p.get('param_name', '?')}: {p.get('param_type', '?')}"
            for p in params
        )

        # Flow mappings (which flows use this function)
        mappings = func_detail.get('functionFlowMapping', [])
        mapping_lines = []
        for m in mappings:
            status = m.get('workflowStatus', '?')
            wf_id = m.get('userWorkflowId', '?')
            mapping_lines.append(f"//   Flow {wf_id} ({status})")

        header = f"""// Function: {func_name}
// ID: {func_id}
// Link Name: {link_name}
// Namespace: {namespace}
// Return Type: {return_type}
// Parameters: {params_str if params_str else 'none'}
// Created By: {created_by}
// Source: Zoho Flow
"""
        if mapping_lines:
            header += "// Used By:\n"
            header += "\n".join(mapping_lines) + "\n"

        header += "// ============================================\n\n"
        return header

    def extract(self) -> Dict[str, Any]:
        """Extract all Flow Deluge functions and save to files"""

        functions = self.get_all_functions()
        self.stats['total'] = len(functions)

        if not functions:
            logger.warning("No Flow functions found!")
            return {
                'status': 'no_data',
                'stats': self.stats
            }

        failed_items = []
        all_functions_data = []

        for i, func in enumerate(functions, 1):
            func_id = func.get('functionID')
            func_name = func.get('functionName', f'function_{func_id}')

            logger.info(f"[{i}/{len(functions)}] Extracting: {func_name}")

            try:
                source_data = self.get_function_source(func_id)
                script = self.extract_script_from_response(source_data)

                if script:
                    # Get detail for richer metadata
                    func_detail = source_data.get('custom_function', {})

                    # Build header from merged list + detail data
                    header = self.build_metadata_header(func, func_detail)
                    full_content = header + script

                    # Save script to file
                    filename = f"{self.sanitize_filename(func_name)}_{func_id}.txt"
                    self.save_text(full_content, f"flow_functions/{filename}")

                    # Flow mappings for the index
                    flow_mappings = func_detail.get('functionFlowMapping', [])

                    all_functions_data.append({
                        'metadata': func,
                        'detail': func_detail,
                        'script': script,
                        'filename': filename,
                        'flow_mappings': flow_mappings
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
        self.save_json(all_functions_data, 'flow_functions_index.json')

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
    print("Usage: python -m src.extractors.main --client CLIENT_NAME --extract flow_functions")
    sys.exit(1)


if __name__ == '__main__':
    main()
