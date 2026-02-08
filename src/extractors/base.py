"""
Base Extractor Class
All Zoho data extractors inherit from this base class
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, List, Optional
import json
import logging
from datetime import datetime

from ..api.zoho_client import ZohoAPIClient

logger = logging.getLogger(__name__)


class BaseExtractor(ABC):
    """Base class for all Zoho data extractors"""
    
    def __init__(self, client: ZohoAPIClient, output_dir: Path, client_name: str):
        """
        Initialize base extractor
        
        Args:
            client: Initialized Zoho API client
            output_dir: Directory to save extracted data
            client_name: Name of the client (for logging/tracking)
        """
        self.client = client
        self.output_dir = output_dir
        self.client_name = client_name
        self.stats = {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'start_time': None,
            'end_time': None
        }
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    @abstractmethod
    def extract(self) -> Dict[str, Any]:
        """
        Extract data from Zoho
        Must be implemented by subclasses
        
        Returns:
            Dictionary with extraction results and statistics
        """
        pass
    
    @abstractmethod
    def get_extractor_name(self) -> str:
        """
        Get the name of this extractor (e.g., 'functions', 'workflows')
        
        Returns:
            Name of extractor type
        """
        pass
    
    def save_json(self, data: Any, filename: str) -> Path:
        """
        Save data as JSON file
        
        Args:
            data: Data to save
            filename: Name of file
            
        Returns:
            Path to saved file
        """
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved to: {filepath}")
        return filepath
    
    def save_text(self, content: str, filename: str) -> Path:
        """
        Save text content to file
        
        Args:
            content: Text content
            filename: Name of file
            
        Returns:
            Path to saved file
        """
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Saved to: {filepath}")
        return filepath
    
    def sanitize_filename(self, name: str) -> str:
        """
        Remove invalid filename characters
        
        Args:
            name: Original name
            
        Returns:
            Sanitized filename
        """
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        return name
    
    def create_metadata_header(self, item: Dict[str, Any], 
                               id_field: str = 'id',
                               name_field: str = 'name') -> str:
        """
        Create a metadata header for extracted items
        
        Args:
            item: Item dictionary
            id_field: Field name for ID
            name_field: Field name for display name
            
        Returns:
            Formatted header string
        """
        header_lines = [
            f"// {name_field.title()}: {item.get(name_field, 'Unknown')}",
            f"// ID: {item.get(id_field, 'Unknown')}",
            f"// Extracted: {datetime.now().isoformat()}",
        ]
        
        # Add optional metadata
        if 'created_time' in item:
            header_lines.append(f"// Created: {item['created_time']}")
        if 'modified_time' in item:
            header_lines.append(f"// Modified: {item['modified_time']}")
        if 'created_by' in item:
            creator = item['created_by']
            if isinstance(creator, dict):
                header_lines.append(f"// Created By: {creator.get('name', 'Unknown')}")
        
        header_lines.append("// " + "=" * 50)
        header_lines.append("")
        
        return "\n".join(header_lines)
    
    def log_stats(self) -> None:
        """Log extraction statistics"""
        extractor_name = self.get_extractor_name()
        
        logger.info(f"\n{'='*60}")
        logger.info(f"{extractor_name.upper()} EXTRACTION COMPLETE")
        logger.info(f"{'='*60}")
        logger.info(f"Client: {self.client_name}")
        logger.info(f"Total items: {self.stats['total']}")
        logger.info(f"Successful: {self.stats['successful']}")
        logger.info(f"Failed: {self.stats['failed']}")
        
        if self.stats['start_time'] and self.stats['end_time']:
            duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
            logger.info(f"Duration: {duration:.2f} seconds")
        
        logger.info(f"Output directory: {self.output_dir.absolute()}")
        logger.info(f"{'='*60}\n")
    
    def save_failed_log(self, failed_items: List[Dict[str, Any]]) -> Optional[Path]:
        """
        Save log of failed extractions
        
        Args:
            failed_items: List of failed items with reasons
            
        Returns:
            Path to failed log file or None
        """
        if not failed_items:
            return None
        
        log_content = [
            f"Failed Extractions: {len(failed_items)}/{self.stats['total']}",
            "=" * 60,
            ""
        ]
        
        for item in failed_items:
            log_content.append(f"Name: {item.get('name', 'Unknown')}")
            log_content.append(f"ID: {item.get('id', 'Unknown')}")
            log_content.append(f"Reason: {item.get('reason', 'Unknown error')}")
            log_content.append("")
        
        return self.save_text("\n".join(log_content), "FAILED_EXTRACTIONS.txt")
    
    def run(self) -> Dict[str, Any]:
        """
        Run the extraction with timing and statistics
        
        Returns:
            Extraction results and statistics
        """
        logger.info(f"Starting {self.get_extractor_name()} extraction for {self.client_name}...")
        
        self.stats['start_time'] = datetime.now()
        
        try:
            results = self.extract()
            self.stats['end_time'] = datetime.now()
            self.log_stats()
            return results
            
        except Exception as e:
            self.stats['end_time'] = datetime.now()
            logger.error(f"Extraction failed: {e}", exc_info=True)
            self.log_stats()
            raise
